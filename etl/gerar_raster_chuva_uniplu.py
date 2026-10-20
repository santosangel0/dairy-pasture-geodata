# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy",
#     "polars",
#     "rasterio",
#     "shapely",
# ]
# ///
"""Processa os dados de chuva do UNIPLU-BR (2008-2023) para a Regiao Sudeste (MG, SP, RJ, ES)
com Controle de Qualidade Meteorologico (QC) e interpolacao IDW otimizada.

Gera:
  1. chuva_uniplu_anual_sudeste.tif: Precipitacao Total Anual Climatologica (mm/ano)
  2. chuva_uniplu_clim_sudeste.tif: Multibanda de 12 meses climatologicos (mm/mes)
  3. chuva_uniplu_mensal_sudeste_2008_2023/: 12 Rasters mensais individuais
  4. chuva_uniplu_anual_pastagem_sudeste.tif: Recorte na mascara MapBiomas Pastagem.
"""
import gzip
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Remove conflitos com PROJ_LIB
os.environ.pop("PROJ_LIB", None)
os.environ.pop("PROJ_DATA", None)

import numpy as np
import polars as pl
import rasterio
import rasterio.features
import shapely.geometry

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
RAW_DIR = PROJECT_DIR / "raw"
OUT_DIR_MENSAL = SCRIPT_DIR / "chuva_uniplu_mensal_sudeste_2008_2023"
OUT_DIR_MENSAL.mkdir(parents=True, exist_ok=True)

IBGE_CACHE_FILE = SCRIPT_DIR / "malha_sudeste_ibge.geojson"
NDVI_REF_FILE = SCRIPT_DIR / "ndvi_pastagem_sudeste.tif"

_R_EARTH_KM = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    """Calcula distancias geodesicas de Haversine (km)."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2)**2
    return 2 * _R_EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

def loo_rmse(src_lat, src_lon, src_val, p, d_matrix, eps=1e-6):
    """Calcula o RMSE de validacao cruzada Leave-One-Out reusando a matriz de distancias."""
    w = d_matrix ** (-p)
    np.fill_diagonal(w, 0.0)
    w_sum = w.sum(axis=1)
    pred = (w @ src_val) / w_sum
    err = pred - src_val
    return float(np.sqrt(np.mean(err ** 2)))

def choose_p_cv(src_lat, src_lon, src_val, d_matrix, candidates=(1.0, 1.5, 2.0, 2.5, 3.0)):
    """Seleciona a potencia p otima que minimiza o RMSE da LOO-CV."""
    scores = {}
    for p in candidates:
        err = loo_rmse(src_lat, src_lon, src_val, p, d_matrix)
        scores[p] = err
    best_p = min(scores, key=scores.get)
    return best_p, scores

def carregar_geometria_sudeste():
    """Carrega ou baixa a malha oficial do Sudeste do IBGE."""
    if IBGE_CACHE_FILE.exists():
        with open(IBGE_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        url = "https://servicodados.ibge.gov.br/api/v3/malhas/regioes/3?formato=application/vnd.geo+json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
        with open(IBGE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    return [shapely.geometry.shape(f["geometry"]) for f in data.get("features", [])]

def main():
    print("=" * 70)
    print("INTERPOLACAO IDW DA PRECIPITACAO UNIPLU-BR NO SUDESTE (COM QC)")
    print("=" * 70)
    
    t0 = time.time()
    
    # 1. Carrega dados brutos agregados
    f_mensal = RAW_DIR / "uniplu_sudeste_mensal.parquet"
    f_info = RAW_DIR / "uniplu_sudeste_estacoes.parquet"
    
    print("[1/6] Carregando e aplicando Controle de Qualidade (QC) no UNIPLU-BR...")
    df_m = pl.read_parquet(f_mensal)
    df_info = pl.read_parquet(f_info)
    
    # QC 1: Filtra meses anomalos (> 800 mm/mes gerados por glitches de sensor)
    df_clean_mo = df_m.filter((pl.col("rain_mo") >= 0) & (pl.col("rain_mo") <= 800))
    
    # QC 2: Agrega por estacao-ano e exige >= 300 dias validos e 500-3500 mm/ano
    df_annual = (df_clean_mo
                 .group_by(["gauge_code", "year"])
                 .agg(
                     pl.col("rain_mo").sum().alias("rain_year"),
                     pl.col("n_days_mo").sum().alias("total_days")
                 )
                 .filter((pl.col("total_days") >= 300) & (pl.col("rain_year") >= 500) & (pl.col("rain_year") <= 3500))
    )
    
    # QC 3: Nucleo estavel (>= 10 anos validos no periodo 2008-2023)
    stable_gauges = (df_annual
                     .group_by("gauge_code")
                     .agg(pl.col("year").n_unique().alias("ny"))
                     .filter(pl.col("ny") >= 10)["gauge_code"].to_list())
    
    print(f"      Nucleo estavel validado (>= 10 anos no periodo): {len(stable_gauges):,} estacoes.")
    
    # Climatologia anual das estacoes
    clim_annual = (df_annual
                   .filter(pl.col("gauge_code").is_in(stable_gauges))
                   .group_by("gauge_code")
                   .agg(pl.col("rain_year").mean().alias("rain_anual_clim"))
                   .join(df_info, on="gauge_code", how="inner")
                   .filter(pl.col("lat").is_not_null() & pl.col("long").is_not_null())
                   .sort("gauge_code")
    )
    
    src_lat = clim_annual["lat"].to_numpy().astype(np.float32)
    src_lon = clim_annual["long"].to_numpy().astype(np.float32)
    src_anual = clim_annual["rain_anual_clim"].to_numpy().astype(np.float32)
    n_src = len(src_anual)
    
    print(f"      Estacoes com coordenadas: {n_src:,}")
    print(f"      Precipitacao media anual nas estacoes: {src_anual.mean():.1f} mm "
          f"(min: {src_anual.min():.1f} mm, max: {src_anual.max():.1f} mm, mediana: {np.median(src_anual):.1f} mm)")
    
    # Matriz de distancias entre estacoes para LOO-CV rapido
    d_stations = haversine_km(src_lat[:, None], src_lon[:, None], src_lat[None, :], src_lon[None, :])
    np.maximum(d_stations, 1e-6, out=d_stations)
    
    # 2. Validacao Cruzada LOO-CV para p* da chuva anual
    print("\n[2/6] Validacao Cruzada Leave-One-Out (LOO-CV)...")
    p_opt_anual, scores_anual = choose_p_cv(src_lat, src_lon, src_anual, d_stations, candidates=(1.0, 1.5, 2.0, 2.5, 3.0))
    print(f"      Potencia otima anual p*: {p_opt_anual} (RMSE: {scores_anual[p_opt_anual]:.2f} mm)")
    for p_c, sc in scores_anual.items():
        print(f"        p = {p_c:.1f} -> RMSE = {sc:.2f} mm")
        
    # 3. Grade regular de 3 km e mascaramento IBGE
    print("\n[3/6] Configurando grade de 3 km e mascaramento vetorial (IBGE)...")
    shapes = carregar_geometria_sudeste()
    with rasterio.open(NDVI_REF_FILE) as ref:
        width = ref.width
        height = ref.height
        transform = ref.transform
        crs = ref.crs
        
    mask_ibge = rasterio.features.geometry_mask(
        shapes,
        out_shape=(height, width),
        transform=transform,
        invert=True
    )
    
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    tgt_lons, tgt_lats = rasterio.transform.xy(transform, rows, cols)
    tgt_lon = np.array(tgt_lons, dtype=np.float32).ravel()
    tgt_lat = np.array(tgt_lats, dtype=np.float32).ravel()
    n_tgt = len(tgt_lat)
    
    # 4. Pre-calcula pesos IDW sobre a grade (chunked para memoria leve)
    print(f"\n[4/6] Pre-calculando pesos IDW sobre a grade de {n_tgt:,} pixels...")
    CHUNK = 50000
    w_list = []
    w_sum_list = []
    
    for start in range(0, n_tgt, CHUNK):
        end = min(start + CHUNK, n_tgt)
        c_lat = tgt_lat[start:end]
        c_lon = tgt_lon[start:end]
        d_chunk = haversine_km(c_lat[:, None], c_lon[:, None], src_lat[None, :], src_lon[None, :])
        np.maximum(d_chunk, 1e-6, out=d_chunk)
        w_chunk = (d_chunk ** (-p_opt_anual)).astype(np.float32)
        w_sum_chunk = w_chunk.sum(axis=1)
        w_list.append(w_chunk)
        w_sum_list.append(w_sum_chunk)
        
    def predict_fast(values_arr):
        preds = np.empty(n_tgt, dtype=np.float32)
        offset = 0
        for w_chunk, w_sum in zip(w_list, w_sum_list):
            chunk_len = len(w_sum)
            preds[offset:offset+chunk_len] = (w_chunk @ values_arr) / w_sum
            offset += chunk_len
        return preds

    # Interpola Anual
    pred_anual = predict_fast(src_anual)
    mat_anual = pred_anual.reshape((height, width))
    mat_anual[~mask_ibge] = np.nan
    
    profile = {
        "driver": "GTiff",
        "dtype": np.float32,
        "nodata": np.nan,
        "width": width,
        "height": height,
        "count": 1,
        "crs": crs,
        "transform": transform,
        "compress": "lzw"
    }
    
    out_anual = SCRIPT_DIR / "chuva_uniplu_anual_sudeste.tif"
    with rasterio.open(out_anual, "w", **profile) as dst:
        dst.write(mat_anual, 1)
        dst.set_band_description(1, "precip_total_anual_clim_mm")
        dst.update_tags(
            TITLE="Climatologia da Precipitacao Total Anual - Sudeste (2008-2023)",
            SENSOR="UNIPLU-BR (Controle de Qualidade)",
            UNIT="mm/ano",
            IDW_POWER=str(p_opt_anual)
        )
    print(f"      -> Salvo: {out_anual.name} (Media Regional = {np.nanmean(mat_anual):.1f} mm/ano) [OK]")
    
    # 5. Interpolar 12 Meses Climatologicos
    print("\n[5/6] Interpolando 12 meses climatologicos de chuva...")
    meses_siglas = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    meses_extenso = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    # Agrega por mes para o mesmo conjunto de estacoes
    clim_monthly = (df_clean_mo
                    .filter(pl.col("gauge_code").is_in(stable_gauges))
                    .group_by(["gauge_code", "mo"])
                    .agg(pl.col("rain_mo").mean().alias("rain_mo_clim"))
    )
    
    monthly_bands = []
    gauge_order = clim_annual["gauge_code"].to_list()
    
    for mo in range(1, 13):
        sub_mo = clim_monthly.filter(pl.col("mo") == mo)
        # Garante alinhamento exato com src_lat / src_lon
        sub_dict = dict(zip(sub_mo["gauge_code"], sub_mo["rain_mo_clim"]))
        m_val = np.array([sub_dict.get(g, np.nan) for g in gauge_order], dtype=np.float32)
        # Se alguma estacao faltar no mes, preenche com a media
        m_val[np.isnan(m_val)] = np.nanmean(m_val)
        
        pred_mo = predict_fast(m_val)
        mat_mo = pred_mo.reshape((height, width))
        mat_mo[~mask_ibge] = np.nan
        monthly_bands.append(mat_mo)
        
        f_ind = OUT_DIR_MENSAL / f"chuva_uniplu_clim_{mo:02d}_{meses_siglas[mo-1]}.tif"
        with rasterio.open(f_ind, "w", **profile) as dst:
            dst.write(mat_mo, 1)
            dst.set_band_description(1, f"chuva_clim_{meses_siglas[mo-1]}_mm")
            dst.update_tags(
                TITLE=f"Climatologia Mensal de Precipitacao - {meses_extenso[mo-1]} (2008-2023)",
                UNIT="mm/mes"
            )
        print(f"      -> Mes {mo:02d} ({meses_siglas[mo-1]}): Media = {np.nanmean(mat_mo):.1f} mm [OK]")
        
    # Salva multibanda
    multi_profile = profile.copy()
    multi_profile["count"] = 12
    out_multi = SCRIPT_DIR / "chuva_uniplu_clim_sudeste.tif"
    with rasterio.open(out_multi, "w", **multi_profile) as dst:
        for b in range(1, 13):
            dst.write(monthly_bands[b-1], b)
            dst.set_band_description(b, f"chuva_clim_{meses_siglas[b-1]}_mm")
        dst.update_tags(
            TITLE="Climatologia Mensal de Chuva - Sudeste (2008-2023) - 12 Bandas",
            UNIT="mm/mes"
        )
    print(f"      -> Multibanda salvo: {out_multi.name} [OK]")
    
    # 6. Recorte pela mascara de pastagem MapBiomas
    print("\n[6/6] Criando raster de chuva anual na mascara de pastagem...")
    with rasterio.open(NDVI_REF_FILE) as src_ndvi:
        ndvi_band1 = src_ndvi.read(1)
        pasture_mask = mask_ibge & (ndvi_band1 > 0.05)
        
    mat_anual_pasture = mat_anual.copy()
    mat_anual_pasture[~pasture_mask] = np.nan
    out_pasture = SCRIPT_DIR / "chuva_uniplu_anual_pastagem_sudeste.tif"
    with rasterio.open(out_pasture, "w", **profile) as dst:
        dst.write(mat_anual_pasture, 1)
        dst.set_band_description(1, "chuva_anual_pastagem_mm")
        dst.update_tags(
            TITLE="Precipitacao Anual nas Pastagens do Sudeste (UNIPLU / MapBiomas)",
            UNIT="mm/ano"
        )
    print(f"      -> Salvo: {out_pasture.name} (Media Pastagens = {np.nanmean(mat_anual_pasture):.1f} mm/ano) [OK]")
    
    print("\n" + "=" * 70)
    print(f"PROCESSAMENTO CONCLUIDO COM SUCESSO EM {time.time() - t0:.1f}s!")
    print("=" * 70)

if __name__ == "__main__":
    main()

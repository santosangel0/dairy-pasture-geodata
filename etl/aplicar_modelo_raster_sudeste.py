# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy",
#     "polars",
#     "pandas",
#     "rasterio",
#     "shapely",
# ]
# ///
"""Aplica o modelo econometrico do artigo PIBIC/CNPq (Luna Filho et al., 2026) diretamente
sobre a grade raster (3 km) da Regiao Sudeste (MG, SP, RJ, ES), estritamente restrito a
mascara de pastagem do MapBiomas Colecao 9 (Classe 15).

Modelo econometrico (Tabela 1 do artigo):
  ln(Produtividade) = alpha_i + gamma_t + beta_calor * ITU + beta_chuva * Chuva
  Onde:
    beta_calor = -0.00282 (impacto do calor cronico / dias de estresse termico)
    beta_chuva = +0.000117 (impacto da precipitacao anual acumulada em mm)

Produtos gerados:
  1. produtividade_leite_base_sudeste.tif: Produtividade media municipal do IBGE-PPM (L/vaca) rasterizada
  2. modelo_impacto_calor_pct_pastagem.tif: Penalidade percentual isolada do estresse termico (%)
  3. modelo_impacto_chuva_pct_pastagem.tif: Efeito percentual da precipitacao anual (%)
  4. modelo_impacto_liquido_pct_pastagem.tif: Efeito climatico liquido combinado (%)
  5. modelo_perda_leite_l_vaca_pastagem.tif: Perda estimada de leite por vaca por ano (Litros/vaca)
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
import pandas as pd
import polars as pl
import rasterio
import rasterio.features
import shapely.geometry

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# Arquivos de entrada
PPM_CSV = SCRIPT_DIR / "produtividade_leite_media_municipal_sudeste.csv"
ITU_TIF = SCRIPT_DIR / "itu_inmet_idw_anual_sudeste.tif"
CHUVA_TIF = SCRIPT_DIR / "chuva_uniplu_anual_sudeste.tif"
NDVI_TIF = SCRIPT_DIR / "ndvi_pastagem_sudeste.tif"
MALHAS_CACHE = SCRIPT_DIR / "malhas_municipios_sudeste.geojson"

# Coeficientes do modelo econometrico (Luna Filho et al., 2026)
BETA_CALOR = -0.00282
BETA_CHUVA = +0.000117

def carregar_malhas_municipais():
    """Baixa ou carrega do cache a malha vetorial dos municipios do Sudeste do IBGE."""
    if MALHAS_CACHE.exists():
        print("  Carregando malhas municipais do cache local...")
        with open(MALHAS_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print("  Baixando malha oficial de municipios do Sudeste (IBGE)...")
        url = "https://servicodados.ibge.gov.br/api/v3/malhas/regioes/3?formato=application/vnd.geo+json&intrarregiao=municipio"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
        with open(MALHAS_CACHE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    return data.get("features", [])

def main():
    print("=" * 70)
    print("APLICACAO DO MODELO ECONOMETRICO EM RASTER - SUDESTE (2008-2023)")
    print("=" * 70)
    
    t0 = time.time()
    
    # 1. Carrega dados de produtividade do IBGE-PPM
    print("[1/5] Carregando dados da PPM/IBGE por município...")
    df_ppm = pl.read_csv(PPM_CSV)
    ppm_dict = {
        row["code"]: (row["prod_media_l_vaca"], row["log_prod_medio"])
        for row in df_ppm.iter_rows(named=True)
    }
    print(f"      Total de municípios na tabela PPM: {len(ppm_dict):,}")
    
    # 2. Carrega geometria e rasteriza a produtividade do leite
    print("\n[2/5] Rasterizando a produtividade leiteira municipal na grade 3 km...")
    features = carregar_malhas_municipais()
    
    with rasterio.open(NDVI_TIF) as ref:
        width = ref.width
        height = ref.height
        transform = ref.transform
        crs = ref.crs
        
    shapes_prod = []
    shapes_log = []
    for f in features:
        code_str = f.get("properties", {}).get("codarea")
        if not code_str:
            continue
        code = int(code_str)
        geom = shapely.geometry.shape(f["geometry"])
        if code in ppm_dict:
            prod_val, log_val = ppm_dict[code]
            if prod_val is not None and prod_val > 0:
                shapes_prod.append((geom, float(prod_val)))
                shapes_log.append((geom, float(log_val)))
                
    # Rasteriza produtividade base
    mat_prod_base = rasterio.features.rasterize(
        shapes_prod,
        out_shape=(height, width),
        transform=transform,
        fill=np.nan,
        dtype=np.float32
    )
    
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
    
    f_prod_base = SCRIPT_DIR / "produtividade_leite_base_sudeste.tif"
    with rasterio.open(f_prod_base, "w", **profile) as dst:
        dst.write(mat_prod_base, 1)
        dst.set_band_description(1, "produtividade_leite_media_l_vaca")
        dst.update_tags(
            TITLE="Produtividade Leiteira Media Municipal - Sudeste (2008-2023)",
            SOURCE="IBGE - Pesquisa da Pecuaria Municipal (PPM)",
            UNIT="Litros/vaca/ano"
        )
    print(f"      -> Salvo: {f_prod_base.name} [OK]")
    
    # 3. Carrega rasters climaticos e mascara de pastagem MapBiomas
    print("\n[3/5] Carregando rasters climaticos (ITU e Chuva) e mascara MapBiomas...")
    with rasterio.open(ITU_TIF) as src_itu:
        if (src_itu.height, src_itu.width) != (height, width):
            print(f"      Reamostrando ITU de {src_itu.shape} para {height, width} (grade de 3 km)...")
            from rasterio.warp import reproject, Resampling
            mat_itu = np.full((height, width), np.nan, dtype=np.float32)
            reproject(
                source=src_itu.read(1),
                destination=mat_itu,
                src_transform=src_itu.transform,
                src_crs=src_itu.crs,
                dst_transform=transform,
                dst_crs=crs,
                resampling=Resampling.bilinear
            )
            # Salva ITU na grade de 3 km
            f_itu_3km = SCRIPT_DIR / "itu_inmet_idw_anual_3km_sudeste.tif"
            with rasterio.open(f_itu_3km, "w", **profile) as dst:
                dst.write(mat_itu, 1)
                dst.set_band_description(1, "dias_itu79_total_anual_3km")
            print(f"      -> Salvo: {f_itu_3km.name} [OK]")
        else:
            mat_itu = src_itu.read(1)
        
    with rasterio.open(CHUVA_TIF) as src:
        mat_chuva = src.read(1)
        
    with rasterio.open(NDVI_TIF) as src:
        mat_ndvi = src.read(1)
        # Mascara estrita de pastagem: pixels com NDVI > 0.05
        pasture_mask = (mat_ndvi > 0.05) & np.isfinite(mat_prod_base) & np.isfinite(mat_itu) & np.isfinite(mat_chuva)
        
    n_pasture = pasture_mask.sum()
    print(f"      Pixels validos de pastagem com clima e producao: {n_pasture:,}")
    
    # 4. Aplica as equacoes do modelo econometrico sobre os rasters
    print("\n[4/5] Executando Algebra de Mapas Econometrica...")
    
    # 4.1 Penalidade Percentual Isolada do Calor (%): exp(beta * ITU) - 1
    # beta_calor = -0.00282 por dia de estresse
    impacto_calor_pct = np.full((height, width), np.nan, dtype=np.float32)
    impacto_calor_pct[pasture_mask] = (np.exp(BETA_CALOR * mat_itu[pasture_mask]) - 1.0) * 100.0
    
    f_calor_pct = SCRIPT_DIR / "modelo_impacto_calor_pct_pastagem.tif"
    with rasterio.open(f_calor_pct, "w", **profile) as dst:
        dst.write(impacto_calor_pct, 1)
        dst.set_band_description(1, "impacto_estresse_termico_pct")
        dst.update_tags(
            TITLE="Impacto do Estresse Termico na Produtividade Leiteira (%)",
            MODEL="ln(Y) = beta * ITU (beta = -0.00282, Luna Filho et al. 2026)",
            MASK="MapBiomas Colecao 9 - Classe 15 (Pastagem)",
            UNIT="%"
        )
    print(f"      -> [OK] {f_calor_pct.name}")
    
    # 4.2 Efeito da Chuva Anual (%): centrado na media regional de chuva
    chuva_media = np.nanmean(mat_chuva[pasture_mask])
    impacto_chuva_pct = np.full((height, width), np.nan, dtype=np.float32)
    impacto_chuva_pct[pasture_mask] = (np.exp(BETA_CHUVA * (mat_chuva[pasture_mask] - chuva_media)) - 1.0) * 100.0
    
    f_chuva_pct = SCRIPT_DIR / "modelo_impacto_chuva_pct_pastagem.tif"
    with rasterio.open(f_chuva_pct, "w", **profile) as dst:
        dst.write(impacto_chuva_pct, 1)
        dst.set_band_description(1, "impacto_chuva_anual_pct")
        dst.update_tags(
            TITLE="Efeito da Precipitacao na Produtividade Leiteira (%)",
            MODEL="beta_chuva = +0.000117 (centrado na media regional de chuva)",
            MASK="MapBiomas Colecao 9 - Classe 15 (Pastagem)",
            UNIT="%"
        )
    print(f"      -> [OK] {f_chuva_pct.name}")
    
    # 4.3 Efeito Climatico Liquido Combinado (%): Calor + Chuva
    itu_medio = np.nanmean(mat_itu[pasture_mask])
    impacto_liquido_pct = np.full((height, width), np.nan, dtype=np.float32)
    delta_log = BETA_CALOR * (mat_itu[pasture_mask] - itu_medio) + BETA_CHUVA * (mat_chuva[pasture_mask] - chuva_media)
    impacto_liquido_pct[pasture_mask] = (np.exp(delta_log) - 1.0) * 100.0
    
    f_liquido_pct = SCRIPT_DIR / "modelo_impacto_liquido_pct_pastagem.tif"
    with rasterio.open(f_liquido_pct, "w", **profile) as dst:
        dst.write(impacto_liquido_pct, 1)
        dst.set_band_description(1, "impacto_climatico_liquido_pct")
        dst.update_tags(
            TITLE="Impacto Climatico Liquido Combinado na Produtividade (%)",
            MODEL="ln(Y) = beta_calor*(ITU - ITU_med) + beta_chuva*(Chuva - Chuva_med)",
            MASK="MapBiomas Colecao 9 - Classe 15 (Pastagem)",
            UNIT="%"
        )
    print(f"      -> [OK] {f_liquido_pct.name}")
    
    # 4.4 Perda Absoluta de Leite por Calor (Litros/vaca/ano)
    # Perda = Prod_base * (1 - exp(beta_calor * ITU))
    perda_leite_l_vaca = np.full((height, width), np.nan, dtype=np.float32)
    perda_leite_l_vaca[pasture_mask] = mat_prod_base[pasture_mask] * (1.0 - np.exp(BETA_CALOR * mat_itu[pasture_mask]))
    
    f_perda_leite = SCRIPT_DIR / "modelo_perda_leite_l_vaca_pastagem.tif"
    with rasterio.open(f_perda_leite, "w", **profile) as dst:
        dst.write(perda_leite_l_vaca, 1)
        dst.set_band_description(1, "perda_estimada_leite_l_vaca_ano")
        dst.update_tags(
            TITLE="Perda Estimada de Produtividade por Estresse Termico (Litros/vaca/ano)",
            MODEL="Perda = Prod_Base * (1 - exp(beta_calor * ITU))",
            MASK="MapBiomas Colecao 9 - Classe 15 (Pastagem)",
            UNIT="L/vaca/ano"
        )
    print(f"      -> [OK] {f_perda_leite.name}")

    # 4.4b Perda Mensal de Leite por Calor (Litros/vaca/mês)
    f_perda_mes = SCRIPT_DIR / "modelo_perda_leite_mensal_l_vaca_pastagem.tif"
    with rasterio.open(f_perda_mes, "w", **profile) as dst:
        dst.write(perda_leite_l_vaca / 12.0, 1)
        dst.set_band_description(1, "perda_estimada_leite_l_vaca_mes")
        dst.update_tags(
            TITLE="Taxa Media Mensal de Perda de Produtividade por Calor (Litros/vaca/mes)",
            MODEL="Perda_Mensal = Perda_Anual / 12",
            MASK="MapBiomas Colecao 9 - Classe 15 (Pastagem)",
            UNIT="L/vaca/mes"
        )
    print(f"      -> [OK] {f_perda_mes.name}")
    
    # 4.5 Produtividade Base mascarada apenas na pastagem
    prod_base_pastagem = np.full((height, width), np.nan, dtype=np.float32)
    prod_base_pastagem[pasture_mask] = mat_prod_base[pasture_mask]
    
    f_prod_pasture = SCRIPT_DIR / "produtividade_leite_base_pastagem.tif"
    with rasterio.open(f_prod_pasture, "w", **profile) as dst:
        dst.write(prod_base_pastagem, 1)
        dst.set_band_description(1, "produtividade_leite_base_pastagem_l_vaca")
        dst.update_tags(
            TITLE="Produtividade Leiteira Base nas Pastagens do Sudeste (PPM / MapBiomas)",
            UNIT="L/vaca/ano"
        )
    print(f"      -> [OK] {f_prod_pasture.name}")
    
    # 5. Sintese Estatistica
    print("\n[5/5] Síntese dos Resultados do Modelo sobre as Pastagens:")
    val_calor = impacto_calor_pct[pasture_mask]
    val_chuva = impacto_chuva_pct[pasture_mask]
    val_liq = impacto_liquido_pct[pasture_mask]
    val_perda = perda_leite_l_vaca[pasture_mask]
    val_prod = prod_base_pastagem[pasture_mask]
    
    print("-" * 70)
    print(f"Produtividade Base:    Média = {val_prod.mean():.1f} L/vaca | Mediana = {np.median(val_prod):.1f} L/vaca")
    print(f"Penalidade do Calor:   Média = {val_calor.mean():.2f}% | Min = {val_calor.min():.2f}% | Max = {val_calor.max():.2f}%")
    print(f"Efeito da Chuva:       Média = {val_chuva.mean():.2f}% | Min = {val_chuva.min():.2f}% | Max = {val_chuva.max():.2f}%")
    print(f"Balanço Líquido:       Média = {val_liq.mean():.2f}% | Min = {val_liq.min():.2f}% | Max = {val_liq.max():.2f}%")
    print(f"Leite Perdido/Vaca:    Média = {val_perda.mean():.1f} L/vaca/ano | P90 = {np.percentile(val_perda, 90):.1f} L/vaca/ano | Max = {val_perda.max():.1f} L/vaca/ano")
    print("-" * 70)
    
    # Salva resumo em CSV
    stats_df = pd.DataFrame([
        {"Metrica": "Produtividade Base (L/vaca)", "Media": round(val_prod.mean(), 2), "Mediana": round(float(np.median(val_prod)), 2), "Min": round(val_prod.min(), 2), "Max": round(val_prod.max(), 2)},
        {"Metrica": "Penalidade Calor (%)", "Media": round(val_calor.mean(), 2), "Mediana": round(float(np.median(val_calor)), 2), "Min": round(val_calor.min(), 2), "Max": round(val_calor.max(), 2)},
        {"Metrica": "Efeito Chuva (%)", "Media": round(val_chuva.mean(), 2), "Mediana": round(float(np.median(val_chuva)), 2), "Min": round(val_chuva.min(), 2), "Max": round(val_chuva.max(), 2)},
        {"Metrica": "Balanco Liquido (%)", "Media": round(val_liq.mean(), 2), "Mediana": round(float(np.median(val_liq)), 2), "Min": round(val_liq.min(), 2), "Max": round(val_liq.max(), 2)},
        {"Metrica": "Perda Absoluta (L/vaca/ano)", "Media": round(val_perda.mean(), 2), "Mediana": round(float(np.median(val_perda)), 2), "Min": round(val_perda.min(), 2), "Max": round(val_perda.max(), 2)},
    ])
    csv_out = SCRIPT_DIR / "resumo_estatistico_modelo_raster_sudeste.csv"
    stats_df.to_csv(csv_out, index=False, encoding="utf-8")
    print(f"Tabela resumo exportada para: {csv_out.name}")
    print(f"Tempo total de execucao: {time.time() - t0:.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()

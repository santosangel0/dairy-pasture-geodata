# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy",
#     "pandas",
#     "rasterio",
#     "shapely",
# ]
# ///
"""Processa e exporta os rasters GeoTIFF mensais da climatologia do NDVI sobre pastagem (2008-2023)
para a Região Sudeste do Brasil (SP, MG, RJ, ES).

Metodologia em consonância com o artigo PIBIC/CNPq (Luna Filho et al., 2026):
  1. Base de dados: MODIS MOD13Q1 (250m) agregada mensalmente para 2008-2023.
  2. Máscara de pastagem: MapBiomas Coleção 9 (classe 15 - Pastagem).
  3. Mascaramento geográfico: Contorno oficial da Região Sudeste (IBGE Região 3).
  4. Atribuição de NoData = NaN (Float32) para transparência nativa em SIGs.
  5. Exportação de 12 rasters mensais individuais + raster multibanda + raster da estação de crescimento (out-abr) + raster anual.
  6. Geração de tabela de estatísticas descritivas (média, mediana, desvio-padrão, min, max, quartis).
"""
import gzip
import json
import os
import sys
import urllib.request
from pathlib import Path

# Remove conflitos com PROJ_LIB herdados do sistema operacional
os.environ.pop("PROJ_LIB", None)
os.environ.pop("PROJ_DATA", None)

import numpy as np
import pandas as pd
import rasterio
import rasterio.features
import shapely.geometry

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_RASTER = SCRIPT_DIR / "ndvi_pastagem_sudeste.tif"
OUT_DIR_MENSAL = SCRIPT_DIR / "ndvi_pastagem_mensal_sudeste_2008_2023"
OUT_DIR_MENSAL.mkdir(parents=True, exist_ok=True)

IBGE_CACHE_FILE = SCRIPT_DIR / "malha_sudeste_ibge.geojson"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES_EXTENSO = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def carregar_geometria_sudeste():
    """Carrega ou baixa a malha oficial da Região Sudeste do IBGE (Região 3)."""
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
    
    shapes = [shapely.geometry.shape(f["geometry"]) for f in data.get("features", [])]
    return shapes

def main():
    print("=" * 70)
    print("PROCESSAMENTO DOS RASTERS DE NDVI SOBRE PASTAGEM - SUDESTE (2008-2023)")
    print("=" * 70)
    
    if not SRC_RASTER.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {SRC_RASTER}")
        
    shapes = carregar_geometria_sudeste()
    print(f"[1/6] Geometria oficial da Região Sudeste (IBGE) carregada: {len(shapes)} polígono(s).")
    
    with rasterio.open(SRC_RASTER) as src:
        profile = src.profile.copy()
        transform = src.transform
        width = src.width
        height = src.height
        crs = src.crs
        
        # Cria máscara booleana da região Sudeste
        mask_sudeste = rasterio.features.geometry_mask(
            shapes,
            out_shape=(height, width),
            transform=transform,
            invert=True
        )
        
        print(f"[2/6] Dimensões do raster: {width} x {height} ({width * height:,} pixels).")
        print(f"      Resolução espacial: {transform.a:.6f}° (~{transform.a * 111.32:.2f} km/pixel).")
        print(f"      Sistema de Referência (CRS): {crs}.")
        
        # Lê todas as 12 bandas
        raw_bands = []
        clean_bands = []
        stats = []
        
        for b in range(1, 13):
            arr = src.read(b).astype(np.float32)
            raw_bands.append(arr)
            
            # Filtro: dentro do Sudeste e valor de pastagem válido (> 0.05)
            # Valores <= 0.05 correspondem a não-pastagem, corpos d'água ou ruídos de corte
            clean = arr.copy()
            invalid_mask = (~mask_sudeste) | (clean <= 0.05)
            clean[invalid_mask] = np.nan
            clean_bands.append(clean)
            
            valid_vals = clean[~np.isnan(clean)]
            stats.append({
                "mes_num": b,
                "mes_sigla": MESES[b-1],
                "mes_nome": MESES_EXTENSO[b-1],
                "pixels_pastagem": len(valid_vals),
                "media_ndvi": round(float(np.mean(valid_vals)), 4),
                "mediana_ndvi": round(float(np.median(valid_vals)), 4),
                "desvio_padrao": round(float(np.std(valid_vals)), 4),
                "minimo": round(float(np.min(valid_vals)), 4),
                "maximo": round(float(np.max(valid_vals)), 4),
                "p25": round(float(np.percentile(valid_vals, 25)), 4),
                "p75": round(float(np.percentile(valid_vals, 75)), 4),
            })
            
    df_stats = pd.DataFrame(stats)
    print("\n[3/6] Estatísticas Climatológicas Mensais de NDVI sobre Pastagem:")
    print(df_stats[["mes_num", "mes_sigla", "mes_nome", "pixels_pastagem", "media_ndvi", "mediana_ndvi", "minimo", "maximo"]].to_string(index=False))
    
    # Salvar tabela de estatísticas CSV
    csv_root = SCRIPT_DIR / "estatisticas_mensais_ndvi_sudeste.csv"
    csv_mensal = OUT_DIR_MENSAL / "estatisticas_mensais_ndvi_sudeste.csv"
    df_stats.to_csv(csv_root, index=False, encoding="utf-8")
    df_stats.to_csv(csv_mensal, index=False, encoding="utf-8")
    print(f"\n[4/6] Estatísticas salvas em:")
    print(f"      - {csv_root}")
    print(f"      - {csv_mensal}")
    
    # Perfil para exportação GeoTIFF Float32 com NoData = NaN
    out_profile = {
        "driver": "GTiff",
        "dtype": np.float32,
        "nodata": np.nan,
        "width": width,
        "height": height,
        "count": 1,
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
    }
    
    print("\n[5/6] Gravando 12 rasters mensais individuais em ndvi_pastagem_mensal_sudeste_2008_2023/ ...")
    for b in range(1, 13):
        out_filename = OUT_DIR_MENSAL / f"ndvi_pastagem_clim_{b:02d}_{MESES[b-1]}.tif"
        with rasterio.open(out_filename, "w", **out_profile) as dst:
            dst.write(clean_bands[b-1], 1)
            dst.set_band_description(1, f"ndvi_pastagem_clim_{MESES[b-1]}_2008_2023")
            dst.update_tags(
                TITLE=f"Climatologia Mensal do NDVI em Pastagem - {MESES_EXTENSO[b-1]} (2008-2023)",
                DESCRIPTION="Banco de dados com informacoes utilizadas para as analises econometricas e resultados do cenario de oferta de leite no sudeste do Brasil (Embrapa Gado de Leite / PIBIC CNPq)",
                SENSOR="MODIS MOD13Q1 (250m) com mascara MapBiomas Colecao 9 (classe 15)",
                PERIOD="2008-2023",
                REGION="Sudeste (SP, MG, RJ, ES)",
                METRIC="NDVI medio mensal sobre pastagem"
            )
        print(f"      -> {out_filename.name} [OK]")
        
    print("\n[6/6] Gravando rasters complementares consolidados:")
    
    # 6.1 Raster multibanda (12 bandas)
    multi_profile = out_profile.copy()
    multi_profile["count"] = 12
    multi_out = SCRIPT_DIR / "ndvi_pastagem_clim_sudeste.tif"
    with rasterio.open(multi_out, "w", **multi_profile) as dst:
        for b in range(1, 13):
            dst.write(clean_bands[b-1], b)
            dst.set_band_description(b, f"ndvi_pastagem_clim_{MESES[b-1]}")
        dst.update_tags(
            TITLE="Climatologia Mensal de NDVI sobre Pastagem - Sudeste do Brasil (12 bandas)",
            DESCRIPTION="Banco de dados com informacoes utilizadas para as analises econometricas e resultados do cenario de oferta de leite no sudeste do Brasil",
            PERIOD="2008-2023"
        )
    print(f"      -> {multi_out.name} (12 bandas mensais) [OK]")
    
    # 6.2 Raster da estação de crescimento (outubro a abril - 7 meses: out, nov, dez, jan, fev, mar, abr)
    # Bandas correspondentes: 10, 11, 12, 1, 2, 3, 4 (índices 9, 10, 11, 0, 1, 2, 3)
    growth_indices = [9, 10, 11, 0, 1, 2, 3]
    growth_stack = np.stack([clean_bands[i] for i in growth_indices], axis=0)
    growth_mean = np.nanmean(growth_stack, axis=0).astype(np.float32)
    # Garantir que onde todos eram NaN continue NaN
    growth_mean[np.all(np.isnan(growth_stack), axis=0)] = np.nan
    
    growth_out = SCRIPT_DIR / "ndvi_pastagem_crescimento_sudeste.tif"
    with rasterio.open(growth_out, "w", **out_profile) as dst:
        dst.write(growth_mean, 1)
        dst.set_band_description(1, "ndvi_pastagem_crescimento_out_abr")
        dst.update_tags(
            TITLE="NDVI Medio da Estacao de Crescimento da Pastagem (Out-Abr) - Sudeste (2008-2023)",
            DESCRIPTION="Mediador primario da vegetacao utilizado nos modelos econometricos de painel"
        )
    print(f"      -> {growth_out.name} (Estacao de crescimento Out-Abr) [OK]")
    
    # 6.3 Raster da média anual (12 meses)
    annual_stack = np.stack(clean_bands, axis=0)
    annual_mean = np.nanmean(annual_stack, axis=0).astype(np.float32)
    annual_mean[np.all(np.isnan(annual_stack), axis=0)] = np.nan
    
    annual_out = SCRIPT_DIR / "ndvi_pastagem_anual_sudeste.tif"
    with rasterio.open(annual_out, "w", **out_profile) as dst:
        dst.write(annual_mean, 1)
        dst.set_band_description(1, "ndvi_pastagem_medio_anual")
        dst.update_tags(
            TITLE="NDVI Medio Anual sobre Pastagem - Sudeste (2008-2023)",
            DESCRIPTION="Mediador de sensibilidade utilizado nos modelos econometricos de painel"
        )
    print(f"      -> {annual_out.name} (Media anual) [OK]")
    
    print("\n" + "=" * 70)
    print("PROCESSAMENTO CONCLUIDO COM SUCESSO!")
    print("=" * 70)

if __name__ == "__main__":
    main()

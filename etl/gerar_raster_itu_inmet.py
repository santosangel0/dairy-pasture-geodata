# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "polars",
#     "duckdb",
#     "pyarrow",
#     "numpy",
#     "rasterio",
#     "shapely",
# ]
# ///
"""Gera o raster GeoTIFF (12 bandas mensais) do Estresse Térmico Crítico (ITU > 79)
para a Região Sudeste via IDW de estações INMET.

Metodologia idêntica a analise/prep/prep_mapas_clima.py e analise/R/mapa_itu.R:
  1. Filtra dados diários de 2008 a 2023 com count(itu_max) >= 25 por mês.
  2. Calcula média de dias/mês com itu_max > 79 por estação e mês.
  3. Filtra núcleo estável de estações (>= 10 anos no período).
  4. IDW (P = 2.0) sobre grade regular (0.05° ~ 5km) cobrindo SP, MG, RJ e ES.
  5. Recorta com o contorno oficial do Sudeste (IBGE), mascarando o oceano e estados vizinhos.
  6. Salva GeoTIFF com 12 bandas mensais + GeoTIFF anual + rasters mensais individuais.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import urllib.request
from pathlib import Path

# Remove caminhos PROJ conflitantes herdados do sistema operacional (ex: PostgreSQL/PostGIS)
os.environ.pop("PROJ_LIB", None)
os.environ.pop("PROJ_DATA", None)

import duckdb
import numpy as np
import polars as pl
import rasterio
import rasterio.features
from rasterio.transform import from_origin
import shapely.geometry

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
try:
    from _spatial import idw_predict, choose_p_cv
except ImportError:
    print("Erro: Não foi possível importar _spatial.py da pasta build.")
    sys.exit(1)

BASE_DATA = Path(r"C:\Users\Lenovo\Documents\projects\zarc-etl\data\final")
IMP_PARQUET = BASE_DATA / "inmet_historico_diario_imputado.parquet"
DAILY_PARQUET = BASE_DATA / "inmet_historico_diario.parquet"
EST_PARQUET = BASE_DATA / "estacoes.parquet"

OUT_DIR = Path(__file__).resolve().parent
YEAR_MIN, YEAR_MAX = 2008, 2023
BUFFER_DEG = 2.5
P_IDW = 2.0  # Conforme analise/prep/prep_mapas_clima.py:117

# Bounding box do Sudeste (SP, MG, RJ, ES)
LAT_MIN, LAT_MAX = -25.5, -14.0
LON_MIN, LON_MAX = -53.5, -39.0
RES_DEG = 0.05  # ~5 km

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def get_sudeste_geometry() -> list[shapely.geometry.base.BaseGeometry]:
    """Baixa a geometria oficial da Região Sudeste (IBGE) para máscara."""
    print("Obtendo contorno oficial do Sudeste (IBGE)...")
    url = "https://servicodados.ibge.gov.br/api/v3/malhas/regioes/3?formato=application/vnd.geo+json"
    req = urllib.request.urlopen(url, timeout=30)
    raw = req.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    shapes = [shapely.geometry.shape(f["geometry"]) for f in data.get("features", [])]
    return shapes


def main():
    if IMP_PARQUET.exists():
        src_parquet = IMP_PARQUET
        where_extra = "and tipo <> 'backfill'"
    elif DAILY_PARQUET.exists():
        src_parquet = DAILY_PARQUET
        where_extra = ""
    else:
        print(f"ERRO: Nenhuma base de dados diária do INMET encontrada em {BASE_DATA}.")
        print("Execute o pipeline do zarc-etl primeiro!")
        return

    if not EST_PARQUET.exists():
        print(f"ERRO: Arquivo de estações não encontrado em {EST_PARQUET}.")
        return

    print(f"Lendo dados de: {src_parquet}")
    con = duckdb.connect()

    # 1. Agregação mensal: contagem de dias com itu_max > 79 (mínimo 25 dias válidos)
    query_monthly = f"""
        select cd_estacao,
               year(data) as yr,
               month(data) as mo,
               sum((itu_max > 79)::int) as d79,
               count(itu_max) as n
        from read_parquet('{src_parquet.as_posix()}')
        where year(data) between {YEAR_MIN} and {YEAR_MAX}
          and itu_max is not null
          {where_extra}
        group by cd_estacao, year(data), month(data)
        having count(itu_max) >= 25
    """
    m = con.execute(query_monthly).pl()
    print(f"Registros estação-ano-mês válidos: {m.height}")

    # 2. Climatologia por estação-mês: média entre anos; núcleo estável (>= 10 anos)
    clim = (
        m.group_by(["cd_estacao", "mo"])
        .agg(
            d79=pl.col("d79").mean(),
            nyr=pl.col("yr").n_unique()
        )
        .filter(pl.col("nyr") >= 10)
    )
    print(f"Estações no núcleo estável (>=10 anos): {clim['cd_estacao'].n_unique()}")

    # 3. Coordenadas das estações no Sudeste + Buffer
    lo_lon, hi_lon = LON_MIN - BUFFER_DEG, LON_MAX + BUFFER_DEG
    lo_lat, hi_lat = LAT_MIN - BUFFER_DEG, LAT_MAX + BUFFER_DEG
    est = con.execute(
        f"""
        select cd_estacao, vl_latitude as lat, vl_longitude as lon
        from read_parquet('{EST_PARQUET.as_posix()}')
        where vl_latitude is not null and vl_longitude is not null
          and vl_latitude between {lo_lat} and {hi_lat}
          and vl_longitude between {lo_lon} and {hi_lon}
        """
    ).pl()
    clim = clim.join(est, on="cd_estacao", how="inner")
    print(f"Estações válidas dentro da abrangência: {clim['cd_estacao'].n_unique()}")

    # 4. Criar grade regular
    lon_grid = np.arange(LON_MIN, LON_MAX, RES_DEG)
    lat_grid = np.arange(LAT_MAX, LAT_MIN, -RES_DEG)  # norte para sul
    grid_lon, grid_lat = np.meshgrid(lon_grid, lat_grid)
    tgt_lat = grid_lat.ravel()
    tgt_lon = grid_lon.ravel()
    transform = from_origin(LON_MIN, LAT_MAX, RES_DEG, RES_DEG)

    # 5. Validação Cruzada (LOO-CV) e Interpolação mês a mês
    print("Ajustando expoente p por Validação Cruzada Leave-One-Out (LOO-CV) para cada mês...")
    monthly_bands = []
    p_by_month = {}
    for mo in range(1, 13):
        sub = clim.filter(pl.col("mo") == mo)
        if sub.height < 3:
            print(f"Aviso: apenas {sub.height} estações para o mês {mo}")
            pred = np.zeros_like(tgt_lat)
            p_mo = 2.0
        else:
            slat = sub["lat"].to_numpy()
            slon = sub["lon"].to_numpy()
            sval = sub["d79"].to_numpy()
            p_mo, scores = choose_p_cv(
                [(slat, slon, sval)],
                candidates=(1.0, 1.5, 2.0, 2.5, 3.0, 4.0),
            )
            pred = idw_predict(slat, slon, sval, tgt_lat, tgt_lon, p_mo)
        p_by_month[mo] = p_mo
        monthly_bands.append(pred.reshape(grid_lat.shape).astype(np.float32))
        print(f"  Mês {mo:02d} ({MESES[mo-1]}): {sub.height} estações | LOO-CV p={p_mo} | min={pred.min():.1f}, max={pred.max():.1f} dias")

    # 6. Aplicar máscara com contorno do Sudeste (IBGE)
    shapes = get_sudeste_geometry()
    mask = rasterio.features.geometry_mask(
        shapes,
        out_shape=(len(lat_grid), len(lon_grid)),
        transform=transform,
        invert=True,  # True para pixels dentro da região
    )

    for i in range(12):
        monthly_bands[i][~mask] = np.nan

    # 7. Salvar GeoTIFF multibanda (12 bandas mensais mascaradas)
    out_file = OUT_DIR / "itu_inmet_idw_clim_sudeste.tif"
    with rasterio.open(
        out_file,
        "w",
        driver="GTiff",
        height=len(lat_grid),
        width=len(lon_grid),
        count=12,
        dtype=np.float32,
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
        compress="lzw",
    ) as dst:
        for b_idx, band_data in enumerate(monthly_bands, start=1):
            dst.write(band_data, b_idx)
            dst.set_band_description(b_idx, f"dias_itu79_clim_{MESES[b_idx-1]}")

    print(f"\n[SUCESSO] Raster GeoTIFF multibanda salvo em: {out_file}")

    # 8. Salvar GeoTIFF anual (soma dos 12 meses)
    anual = np.nansum(monthly_bands, axis=0).astype(np.float32)
    anual[~mask] = np.nan
    out_anual = OUT_DIR / "itu_inmet_idw_anual_sudeste.tif"
    with rasterio.open(
        out_anual,
        "w",
        driver="GTiff",
        height=len(lat_grid),
        width=len(lon_grid),
        count=1,
        dtype=np.float32,
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
        compress="lzw",
    ) as dst:
        dst.write(anual, 1)
        dst.set_band_description(1, "dias_itu79_total_anual")
    print(f"[SUCESSO] Raster GeoTIFF anual salvo em: {out_anual}")

    # 9. Salvar rasters mensais individuais para visualização rápida no QGIS
    pasta_mensal = OUT_DIR / "itu_inmet_mensal"
    pasta_mensal.mkdir(exist_ok=True)
    for mo in range(1, 13):
        f_mes = pasta_mensal / f"itu_inmet_idw_clim_{mo:02d}_{MESES[mo-1]}.tif"
        with rasterio.open(
            f_mes,
            "w",
            driver="GTiff",
            height=len(lat_grid),
            width=len(lon_grid),
            count=1,
            dtype=np.float32,
            crs="EPSG:4326",
            transform=transform,
            nodata=np.nan,
            compress="lzw",
        ) as dst:
            dst.write(monthly_bands[mo - 1], 1)
            dst.set_band_description(1, f"dias_itu79_clim_{MESES[mo-1]}")
    print(f"[SUCESSO] 12 Rasters individuais mensais salvos em: {pasta_mensal}")


if __name__ == "__main__":
    main()

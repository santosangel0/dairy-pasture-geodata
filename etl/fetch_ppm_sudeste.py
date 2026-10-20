# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "polars",
#     "numpy",
# ]
# ///
"""Baixa os dados de Produção Leiteira da PPM/IBGE (2008-2023) para o Sudeste:
  - Tabela 74, variavel 106, classificacao 80[2682]: Producao de leite (mil litros -> litros)
  - Tabela 94, variavel 107: Vacas ordenhadas (cabecas)
  - Produtividade = litros / vacas_ordenhadas (L/vaca)
  - log_prod = ln(prod_l_vaca)
UFs do Sudeste: MG (31), ES (32), RJ (33), SP (35).
Salva em:
  - rasters-sudeste/produtividade_leite_sudeste_2008_2023.parquet
  - rasters-sudeste/produtividade_leite_media_municipal_sudeste.csv
"""
import json
import time
import urllib.request
from pathlib import Path
import numpy as np
import polars as pl

OUT_DIR = Path(__file__).resolve().parents[1] / "rasters-sudeste"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UFS = [31, 32, 33, 35]
YEARS_STR = "|".join(str(y) for y in range(2008, 2024))
AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"

def _get_json(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def clean_sidra_val(v):
    if v is None or v in ("-", "...", "..", "X", ""):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def fetch_uf_milk(uf: int) -> list[dict]:
    """Tabela 74: Leite em mil litros (multiplicado por 1000 -> litros)."""
    url = f"{AGREGADOS}/74/periodos/{YEARS_STR}/variaveis/106?localidades=N6[N3[{uf}]]&classificacao=80[2682]"
    data = _get_json(url)
    rows = []
    series = data[0]["resultados"][0]["series"]
    for s in series:
        code = int(s["localidade"]["id"])
        nome = s["localidade"]["nome"]
        for yr_str, raw_val in (s.get("serie") or {}).items():
            val = clean_sidra_val(raw_val)
            if val is not None:
                rows.append({
                    "code": code,
                    "nome": nome,
                    "year": int(yr_str),
                    "litros": val * 1000.0,
                    "uf": uf
                })
    return rows

def fetch_uf_cows(uf: int) -> list[dict]:
    """Tabela 94: Vacas ordenhadas (cabecas)."""
    url = f"{AGREGADOS}/94/periodos/{YEARS_STR}/variaveis/107?localidades=N6[N3[{uf}]]"
    data = _get_json(url)
    rows = []
    series = data[0]["resultados"][0]["series"]
    for s in series:
        code = int(s["localidade"]["id"])
        for yr_str, raw_val in (s.get("serie") or {}).items():
            val = clean_sidra_val(raw_val)
            if val is not None:
                rows.append({
                    "code": code,
                    "year": int(yr_str),
                    "vacas_ordenhadas": val
                })
    return rows

def main():
    print("=" * 70)
    print("DOWNLOAD DE DADOS DE PRODUCAO LEITEIRA PPM/IBGE - SUDESTE (2008-2023)")
    print("=" * 70)
    
    t0 = time.time()
    all_milk = []
    all_cows = []
    
    uf_names = {31: "Minas Gerais (MG)", 32: "Espírito Santo (ES)", 33: "Rio de Janeiro (RJ)", 35: "São Paulo (SP)"}
    
    for uf in UFS:
        print(f"Consultando {uf_names[uf]}...", end=" ", flush=True)
        m_rows = fetch_uf_milk(uf)
        c_rows = fetch_uf_cows(uf)
        all_milk.extend(m_rows)
        all_cows.extend(c_rows)
        print(f"[{len(m_rows)} obs de leite | {len(c_rows)} obs de vacas]")
        
    df_milk = pl.DataFrame(all_milk)
    df_cows = pl.DataFrame(all_cows)
    
    print("\nConsolidando painel e calculando produtividade (L/vaca)...")
    df = (df_milk
          .join(df_cows, on=["code", "year"], how="inner")
          .with_columns(
              pl.when(pl.col("vacas_ordenhadas") > 0)
              .then(pl.col("litros") / pl.col("vacas_ordenhadas"))
              .otherwise(None)
              .alias("prod_l_vaca")
          )
          .with_columns(
              pl.when(pl.col("prod_l_vaca") > 0)
              .then(pl.col("prod_l_vaca").log())
              .otherwise(None)
              .alias("log_prod")
          )
          .sort(["code", "year"])
    )
    
    print(f"Painel municipal consolidado: {len(df):,} linhas ({df['code'].n_unique():,} municipios)")
    print(f"Produtividade media geral: {df['prod_l_vaca'].mean():.1f} L/vaca/ano "
          f"(mediana: {df['prod_l_vaca'].median():.1f} L/vaca/ano)")
    
    # Salva painel completo
    out_pq = OUT_DIR / "produtividade_leite_sudeste_2008_2023.parquet"
    df.write_parquet(out_pq)
    print(f"\nSalvo: {out_pq}")
    
    # Climatologia / Media Historica por Municipio (2008-2023)
    df_muni = (df
               .group_by(["code", "nome", "uf"])
               .agg(
                   pl.col("litros").mean().alias("litros_medio_ano"),
                   pl.col("vacas_ordenhadas").mean().alias("vacas_medio_ano"),
                   pl.col("prod_l_vaca").mean().alias("prod_media_l_vaca"),
                   pl.col("log_prod").mean().alias("log_prod_medio"),
                   pl.col("year").n_unique().alias("anos_com_producao")
               )
               .sort("code")
    )
    
    out_csv = OUT_DIR / "produtividade_leite_media_municipal_sudeste.csv"
    df_muni.write_csv(out_csv)
    print(f"Salvo resumo municipal: {out_csv}")
    print(f"Concluido em {time.time() - t0:.1f}s!")

if __name__ == "__main__":
    main()

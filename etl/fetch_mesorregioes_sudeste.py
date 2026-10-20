# /// script
# requires-python = ">=3.10"
# ///
"""Baixa a malha vetorial oficial das Mesorregiões do Sudeste do IBGE
e enriquece cada polígono com seu respectivo Nome e UF (com acentuação correta).
"""
import gzip
import json
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "vectors"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DATA_DIR / "malhas_mesorregioes_sudeste.geojson"

def main():
    print("=" * 60)
    print("EXTRAÇÃO DE MESORREGIÕES DO SUDESTE (IBGE)")
    print("=" * 60)

    # 1. Metadados (Nome, ID, UF)
    print("1. Baixando metadados das mesorregiões...")
    url_meta = "https://servicodados.ibge.gov.br/api/v1/localidades/regioes/3/mesorregioes"
    req_meta = urllib.request.Request(url_meta, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req_meta, timeout=60) as r:
        raw = r.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        # IBGE retorna latin1 nesta rota
        try:
            decoded = raw.decode("latin1")
        except Exception:
            decoded = raw.decode("utf-8")
        meso_meta = {str(item["id"]): item for item in json.loads(decoded)}
    print(f"   Metadados obtidos para {len(meso_meta)} mesorregiões.")

    # 2. Malha Geográfica (GeoJSON)
    print("2. Baixando malhas vetoriais geográficas...")
    url_geo = "https://servicodados.ibge.gov.br/api/v3/malhas/regioes/3?formato=application/vnd.geo+json&intrarregiao=mesorregiao"
    req_geo = urllib.request.Request(url_geo, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req_geo, timeout=120) as r:
        raw = r.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        geojson_data = json.loads(raw.decode("utf-8"))

    # 3. Enriquecimento dos atributos
    print("3. Enriquecendo propriedades com Nome e UF...")
    features = geojson_data.get("features", [])
    for f in features:
        props = f.setdefault("properties", {})
        cod = str(props.get("codarea", ""))
        if cod in meso_meta:
            meta = meso_meta[cod]
            props["id"] = int(cod)
            props["nome"] = meta.get("nome")
            props["uf_sigla"] = meta.get("UF", {}).get("sigla")
            props["uf_nome"] = meta.get("UF", {}).get("nome")

    # 4. Salva o arquivo final em UTF-8
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)

    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"\n[OK] Salvo com sucesso em: {OUT_FILE}")
    print(f"     Total de polígonos: {len(features)}")
    print(f"     Tamanho do arquivo: {size_kb:.1f} KB")

if __name__ == "__main__":
    main()

import json
import numpy as np
import rasterio
import rasterio.features

NOMES_OFICIAIS_MESO = {
    # Minas Gerais (31)
    3101: "Noroeste de Minas",
    3102: "Norte de Minas",
    3103: "Jequitinhonha",
    3104: "Vale do Mucuri",
    3105: "Triângulo Mineiro / Alto Paranaíba",
    3106: "Central Mineira",
    3107: "Metropolitana de Belo Horizonte",
    3108: "Vale do Rio Doce",
    3109: "Oeste de Minas",
    3110: "Sul / Sudoeste de Minas",
    3111: "Campo das Vertentes",
    3112: "Zona da Mata",
    # Espírito Santo (32)
    3201: "Noroeste Espírito-santense",
    3202: "Litoral Norte Espírito-santense",
    3203: "Central Espírito-santense",
    3204: "Sul Espírito-santense",
    # Rio de Janeiro (33)
    3301: "Noroeste Fluminense",
    3302: "Norte Fluminense",
    3303: "Centro Fluminense",
    3304: "Baixadas Litorâneas",
    3305: "Sul Fluminense",
    3306: "Metropolitana do Rio de Janeiro",
    # São Paulo (35)
    3501: "São José do Rio Preto",
    3502: "Ribeirão Preto",
    3503: "Araçatuba",
    3504: "Bauru",
    3505: "Araraquara",
    3506: "Piracicaba",
    3507: "Campinas",
    3508: "Presidente Prudente",
    3509: "Marília",
    3510: "Assis",
    3511: "Itapetininga",
    3512: "Litoral Sul Paulista",
    3513: "Vale do Paraíba Paulista",
    3514: "Macro Metropolitana Paulista",
    3515: "Metropolitana de São Paulo"
}

def main():
    with open('data/vectors/malhas_mesorregioes_sudeste.geojson', encoding='utf-8') as f:
        mesos = json.load(f)['features']

    with rasterio.open('data/rasters/modelo/modelo_impacto_liquido_pct_pastagem.tif') as src_liq, \
         rasterio.open('data/rasters/clima/itu_inmet_idw_anual_3km_sudeste.tif') as src_itu, \
         rasterio.open('data/rasters/clima/chuva_uniplu_anual_sudeste.tif') as src_chuva, \
         rasterio.open('data/rasters/modelo/modelo_perda_leite_l_vaca_pastagem.tif') as src_perda, \
         rasterio.open('data/rasters/modelo/produtividade_leite_base_pastagem.tif') as src_prod:
        
        mat_liq = src_liq.read(1)
        mat_itu = src_itu.read(1)
        mat_chuva = src_chuva.read(1)
        mat_perda = src_perda.read(1)
        mat_prod = src_prod.read(1)
        transform = src_liq.transform
        shape = mat_liq.shape

    results = []
    for f in mesos:
        geom = f['geometry']
        props = f['properties']
        m_id = int(props.get('id', props.get('codarea', 0)))
        mask = rasterio.features.geometry_mask([geom], transform=transform, out_shape=shape, invert=True)
        
        v_mask = mask & np.isfinite(mat_liq)
        if np.any(v_mask):
            liq_mean = float(np.mean(mat_liq[v_mask]))
            itu_mean = float(np.mean(mat_itu[v_mask]))
            chuva_mean = float(np.mean(mat_chuva[v_mask]))
            perda_mean = float(np.mean(mat_perda[v_mask]))
            prod_mean = float(np.mean(mat_prod[v_mask]))
            count = int(np.count_nonzero(v_mask))
        else:
            liq_mean = itu_mean = chuva_mean = perda_mean = prod_mean = None
            count = 0
            
        uf = props.get('uf_sigla', '')
        nome = NOMES_OFICIAIS_MESO.get(m_id, props.get('nome', ''))
        results.append({
            'id': m_id,
            'nome': nome,
            'uf': uf,
            'label': f"{nome} ({uf})",
            'liq_pct': round(liq_mean, 2) if liq_mean is not None else None,
            'itu_dias': round(itu_mean, 1) if itu_mean is not None else None,
            'chuva_mm': round(chuva_mean, 0) if chuva_mean is not None else None,
            'perda_l': round(perda_mean, 1) if perda_mean is not None else None,
            'prod_base': round(prod_mean, 1) if prod_mean is not None else None,
            'pixels': count
        })

    results = [r for r in results if r['liq_pct'] is not None]
    results.sort(key=lambda x: x['liq_pct'])

    with open('data/mesorregioes_impacto_climatico.json', 'w', encoding='utf-8') as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)

    # Também salva diretamente em docs/ para uso no site se necessário
    import os
    os.makedirs('assets/data', exist_ok=True)
    with open('assets/data/mesorregioes_impacto_climatico.json', 'w', encoding='utf-8') as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)

    print(f"Salvas {len(results)} mesorregiões com sucesso!")

if __name__ == '__main__':
    main()

# Repositório de Dados Geoespaciais e Climáticos - Sudeste (Embrapa)

Estrutura padronizada para armazenamento de bases tabulares (.parquet), camadas raster (.tif) e vetores (.geojson / .gpkg) referentes ao rebanho leiteiro e variáveis bioclimáticas na Região Sudeste (SP, MG, RJ, ES) no período 2008–2023.

---

## 📁 Estrutura de Diretórios

```text
data/
├── raw/                 # Dados brutos baixados (zips UNIPLU-BR, dumps temporários)
├── parquets/            # Bases tabulares consolidadas e limpas
├── rasters/
│   ├── reference/       # Raster mestre de referência (grade 3 km, WGS 84)
│   ├── clima/           # ITU (INMET), Chuva (UNIPLU-BR), SPEI (CSIC)
│   ├── sensoriamento/   # NDVI (MODIS MOD13Q1), Pastagem (MapBiomas Col. 9)
│   └── modelo/          # Projeção espacial do modelo econométrico (impacto %, perdas L/vaca)
└── vectors/             # Malhas territoriais oficiais (IBGE Sudeste Região 3)
```

---

## 📋 Conteúdo Previsto por Pasta

### 1. `parquets/`
- `inmet_historico_diario.parquet`: Registros meteorológicos diários do INMET (Tmax, URmin, precipitação).
- `inmet_estacoes_sudeste.parquet`: Metadados e coordenadas das estações INMET.
- `uniplu_sudeste_mensal.parquet`: Série mensal consolidada de precipitação por estação.
- `uniplu_sudeste_estacoes.parquet`: Cadastro e localização das estações UNIPLU-BR.
- `produtividade_leite_sudeste_2008_2023.parquet`: Painel municipal PPM/IBGE (leite, vacas ordenhadas, produtividade).

### 2. `rasters/reference/`
- `grade_referencia_sudeste_3km.tif`: Matriz base definindo dimensões, resolução e CRS padrão para garantir alinhamento exato de pixel em toda a álgebra de mapas.

### 3. `rasters/clima/`
- `itu_inmet_idw_anual_sudeste.tif`: Média anual de dias com estresse térmico crítico ($ITU > 79$).
- `itu_inmet_idw_clim_sudeste.tif`: Multibanda climatológica mensal de ITU (12 meses).
- `chuva_uniplu_anual_sudeste.tif`: Precipitação total anual (mm/ano).
- `chuva_uniplu_clim_sudeste.tif`: Multibanda de 12 meses climatológicos de chuva.
- Pastas mensais individuais (`itu_inmet_mensal_sudeste_2008_2023/`, `chuva_uniplu_mensal_sudeste_2008_2023/`).

### 4. `rasters/sensoriamento/`
- `ndvi_pastagem_sudeste.tif`: Climatologia MODIS 12 meses mascarada na Classe 15 (Pastagem) do MapBiomas.
- `ndvi_pastagem_anual_sudeste.tif`: Média anual de NDVI sobre pastagem.
- `spei12_mensal_sudeste.tif`: Multibanda de índice de seca SPEI-12.

### 5. `rasters/modelo/`
- `produtividade_leite_base_pastagem.tif`: Produtividade leiteira municipal rasterizada e restrita a pastagens.
- `modelo_impacto_calor_pct_pastagem.tif`: Penalidade percentual isolada do estresse térmico ($\beta_{\text{calor}} = -0.00282$).
- `modelo_impacto_chuva_pct_pastagem.tif`: Efeito percentual da disponibilidade hídrica ($\beta_{\text{chuva}} = +0.000117$).
- `modelo_impacto_liquido_pct_pastagem.tif`: Efeito climático líquido combinado (%).
- `modelo_perda_leite_l_vaca_pastagem.tif`: Perda estimada de leite por vaca por ano (Litros/vaca/ano).

### 6. `vectors/`
- `malhas_municipios_sudeste.geojson`: Polígonos de todos os municípios de MG, SP, RJ e ES (IBGE).
- `malhas_mesorregioes_sudeste.geojson`: Polígonos das 37 mesorregiões do Sudeste com atributos enriquecidos (id, nome, uf_sigla, uf_nome).
- `malha_sudeste_ibge.geojson`: Contorno externo oficial da Região Sudeste (Região 3).

---

## 🌐 Padrão Cartográfico e Geoespacial
- **Sistema de Referência (CRS):** WGS 84 (`EPSG:4326`)
- **Tipo de Dado Raster:** `Float32` com compressão `LZW`
- **Tratamento de NoData:** `NaN` (not-a-number) para suporte a transparência nativa em SIGs (QGIS, ArcGIS, R terra/stars, Python rasterio)
- **Bounding Box aproximada:** Oeste: -53.5°, Leste: -39.0°, Sul: -25.5°, Norte: -14.0°

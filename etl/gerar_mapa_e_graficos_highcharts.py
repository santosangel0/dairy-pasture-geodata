import json
from pathlib import Path
import shapely.geometry

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
    # 1. Carrega GeoJSON original e dados zonais calculados
    with open("data/vectors/malhas_mesorregioes_sudeste.geojson", encoding="utf-8") as f:
        raw_geo = json.load(f)

    with open("assets/data/mesorregioes_impacto_climatico.json", encoding="utf-8") as f:
        data_stats = json.load(f)
    stats_map = {d["id"]: d for d in data_stats}

    # 2. Processa geometrias:
    #    - Filtra ilhas oceânicas remotas (Trindade e Martim Vaz a longitude > -38.5°) para centralizar o mapa no continente
    #    - Simplifica polígonos com shapely (0.005) para renderização leve e rápida (~300 KB)
    features = []
    map_series_data = []
    for feat in raw_geo["features"]:
        props = feat["properties"]
        m_id = int(props.get("id", props.get("codarea", 0)))
        st = stats_map.get(m_id, {})
        nome = NOMES_OFICIAIS_MESO.get(m_id, props.get("nome", ""))
        uf = props.get("uf_sigla", st.get("uf", ""))

        geom = shapely.geometry.shape(feat["geometry"])
        
        # Filtro de ilhas oceânicas distantes (ex: Trindade e Martim Vaz no ES)
        if geom.geom_type == "MultiPolygon":
            continental_polys = [p for p in geom.geoms if p.bounds[0] < -38.5]
            if not continental_polys:
                continental_polys = list(geom.geoms)
            geom = shapely.geometry.MultiPolygon(continental_polys) if len(continental_polys) > 1 else continental_polys[0]
        elif geom.geom_type == "Polygon":
            if geom.bounds[0] >= -38.5:
                continue

        geom_simplified = geom.simplify(0.005, preserve_topology=True)

        val = st.get("liq_pct", 0.0)
        itu = st.get("itu_dias", 0.0)
        chuva = st.get("chuva_mm", 0.0)
        perda = st.get("perda_l", 0.0)
        prod = st.get("prod_base", 0.0)

        new_props = {
            "id": m_id,
            "codarea": str(m_id),
            "nome": nome,
            "uf_sigla": uf,
            "value": val,
            "itu": itu,
            "chuva": chuva,
            "perda": perda,
            "prod": prod
        }

        features.append({
            "type": "Feature",
            "id": m_id,
            "properties": new_props,
            "geometry": shapely.geometry.mapping(geom_simplified)
        })

        map_series_data.append({
            "id": m_id,
            "value": val,
            "nome": nome,
            "uf": uf,
            "itu": itu,
            "chuva": chuva,
            "perda": perda,
            "prod": prod
        })

    geo_collection = {
        "type": "FeatureCollection",
        "features": features
    }

    # 3. Salva o GeoJSON otimizado e centralizado
    geo_out = Path("assets/data/mesorregioes_sudeste_geo.json")
    geo_out.parent.mkdir(parents=True, exist_ok=True)
    with open(geo_out, "w", encoding="utf-8") as f:
        json.dump(geo_collection, f, ensure_ascii=False)

    # 4. Dados para o ranking
    data_sorted = sorted(data_stats, key=lambda x: x["liq_pct"])
    categories_ranking = [d["label"] for d in data_sorted]
    points_ranking = []
    for d in data_sorted:
        val = d["liq_pct"]
        if val <= -10:
            c = "#c53030"
        elif val < 0:
            c = "#e53e3e"
        elif val < 10:
            c = "#3182ce"
        else:
            c = "#2b6cb0"
            
        points_ranking.append({
            "y": val,
            "color": c,
            "itu": d["itu_dias"],
            "chuva": d["chuva_mm"],
            "perda": d["perda_l"],
            "prod": d["prod_base"],
            "uf": d["uf"]
        })

    # 5. Dados para o scatter plot
    ufs = {
        "MG": {"name": "Minas Gerais", "color": "#2f855a"},
        "SP": {"name": "São Paulo", "color": "#dd6b20"},
        "RJ": {"name": "Rio de Janeiro", "color": "#e53e3e"},
        "ES": {"name": "Espírito Santo", "color": "#319795"}
    }
    scatter_series = []
    for uf_code, uf_info in ufs.items():
        pts = []
        for d in data_stats:
            if d["uf"] == uf_code:
                pts.append({
                    "x": d["itu_dias"],
                    "y": d["liq_pct"],
                    "name": d["nome"],
                    "uf": d["uf"],
                    "chuva": d["chuva_mm"],
                    "perda": d["perda_l"],
                    "prod": d["prod_base"]
                })
        scatter_series.append({
            "name": uf_info["name"],
            "color": uf_info["color"],
            "data": pts,
            "marker": {
                "radius": 6,
                "symbol": "circle"
            }
        })

    # 6. Top Perdas Absolutas
    data_perda = sorted(data_stats, key=lambda x: x["perda_l"], reverse=True)[:15]
    categories_perda = [d["label"] for d in data_perda]
    points_perda = []
    for d in data_perda:
        points_perda.append({
            "y": d["perda_l"],
            "color": "#c53030" if d["liq_pct"] < 0 else "#2b6cb0",
            "liq": d["liq_pct"],
            "itu": d["itu_dias"],
            "chuva": d["chuva_mm"],
            "prod": d["prod_base"]
        })

    # 7. Gera o arquivo JavaScript consolidado
    geo_json_str = json.dumps(geo_collection, ensure_ascii=False)
    map_series_str = json.dumps(map_series_data, ensure_ascii=False)
    
    js_content = f"""// Highcharts & Highcharts Maps - Visualização Interativa do Sudeste (37 Mesorregiões)

const MESORREGIOES_GEOJSON = {geo_json_str};

document.addEventListener('DOMContentLoaded', function () {{
    Highcharts.setOptions({{
        lang: {{
            decimalPoint: ',',
            thousandsSep: '.',
            downloadPNG: 'Baixar imagem PNG',
            downloadJPEG: 'Baixar imagem JPEG',
            downloadPDF: 'Baixar documento PDF',
            downloadSVG: 'Baixar vetor SVG',
            printChart: 'Imprimir visualização',
            viewFullscreen: 'Ver em tela cheia'
        }},
        credits: {{
            enabled: false
        }}
    }});

    // ========================================================
    // 1. MAPA INTERATIVO DE MESORREGIÕES (Highcharts Maps)
    // ========================================================
    const mapEl = document.getElementById('map-mesorregioes');
    if (mapEl) {{
        Highcharts.mapChart('map-mesorregioes', {{
            chart: {{
                map: MESORREGIOES_GEOJSON,
                height: 650,
                backgroundColor: 'transparent'
            }},
            title: {{
                text: 'Mapa Bioclimático do Sudeste (37 Mesorregiões)',
                style: {{ color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }}
            }},
            subtitle: {{
                text: 'Encoste o mouse ou toque sobre qualquer mesorregião para visualizar os indicadores',
                style: {{ color: '#718096' }}
            }},
            mapNavigation: {{
                enabled: true,
                buttonOptions: {{
                    verticalAlign: 'bottom',
                    theme: {{
                        fill: '#ffffff',
                        'stroke-width': 1,
                        stroke: '#cbd5e0',
                        r: 4
                    }}
                }}
            }},
            colorAxis: {{
                min: -18,
                max: 18,
                stops: [
                    [0.0, '#9b2c2c'], // Penalidade Severa (Vermelho Escuro)
                    [0.25, '#e53e3e'], // Penalidade Moderada (Vermelho)
                    [0.5, '#ffffbf'],  // Neutro / Média Regional (Amarelo Claro / 0%)
                    [0.75, '#4299e1'], // Vantagem Moderada (Azul Claro)
                    [1.0, '#2b6cb0']   // Refúgio Térmico (Azul Escuro)
                ],
                labels: {{
                    format: '{{value}}%',
                    style: {{ fontWeight: '600', color: '#2d3748' }}
                }}
            }},
            legend: {{
                title: {{
                    text: 'Balanço Climático Líquido (Δ%)',
                    style: {{ fontSize: '0.85rem', fontWeight: 'bold', color: '#2d3748' }}
                }},
                layout: 'horizontal',
                align: 'center',
                verticalAlign: 'bottom'
            }},
            tooltip: {{
                useHTML: true,
                backgroundColor: 'rgba(255, 255, 255, 0.96)',
                borderColor: '#cbd5e0',
                borderRadius: 8,
                shadow: true,
                formatter: function () {{
                    const p = this.point;
                    const sinal = p.value >= 0 ? '+' : '';
                    const cor = p.value >= 0 ? '#2b6cb0' : '#c53030';
                    return `
                        <div style="padding: 6px 10px; font-family: sans-serif; min-width: 230px;">
                            <div style="font-size: 1.15rem; font-weight: bold; border-bottom: 2px solid #edf2f7; padding-bottom: 4px; margin-bottom: 6px; color: #1a365d;">
                                ${{p.nome}} (${{p.uf}})
                            </div>
                            <div style="margin: 6px 0; color: ${{cor}}; font-weight: bold; font-size: 1.25rem;">
                                Balanço Líquido: ${{sinal}}${{p.value.toFixed(2)}}%
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.6; color: #2d3748;">
                                • <b>Calor Crítico (&gt;79 ITU):</b> ${{p.itu}} dias/ano<br/>
                                • <b>Precipitação Anual:</b> ${{p.chuva}} mm/ano<br/>
                                • <b>Perda Térmica (vs. estresse zero):</b> ${{p.perda}} L/vaca/ano<br/>
                                • <b>Produtividade Base:</b> ${{p.prod}} L/vaca/ano
                            </div>
                        </div>
                    `;
                }}
            }},
            series: [{{
                data: {map_series_str},
                joinBy: 'id',
                name: 'Balanço Climático Líquido',
                borderColor: '#718096',
                borderWidth: 0.75,
                states: {{
                    hover: {{
                        color: '#ffffff',
                        borderColor: '#1a365d',
                        borderWidth: 2.5
                    }}
                }},
                // Rótulos estáticos desativados conforme solicitado: o nome aparece no hover/toque
                dataLabels: {{
                    enabled: false
                }}
            }}]
        }});
    }}

    // ========================================================
    // 2. RANKING DIVERGENTE DAS 37 MESORREGIÕES
    // ========================================================
    const chartRankingEl = document.getElementById('chart-ranking-mesorregioes');
    if (chartRankingEl) {{
        Highcharts.chart('chart-ranking-mesorregioes', {{
            chart: {{
                type: 'bar',
                height: 850,
                backgroundColor: 'transparent'
            }},
            title: {{
                text: 'Ranking do Balanço Climático Líquido (Δ%) por Mesorregião',
                style: {{ color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }},
                margin: 30
            }},
            subtitle: {{
                text: 'Projeção da Equação 3 ponderada nas células de pastagem (Coleção 9 MapBiomas)',
                style: {{ color: '#718096' }}
            }},
            xAxis: {{
                categories: {json.dumps(categories_ranking, ensure_ascii=False)},
                labels: {{
                    style: {{ fontSize: '0.85rem', color: '#2d3748' }}
                }}
            }},
            yAxis: {{
                title: {{
                    text: 'Variação Percentual Relativa frente à Média Regional (%)',
                    style: {{ fontWeight: '600' }}
                }},
                labels: {{
                    format: '{{value}}%'
                }},
                plotLines: [{{
                    value: 0,
                    color: '#2b6cb0',
                    width: 2,
                    zIndex: 5,
                    label: {{
                        text: 'Média Regional (0%)',
                        align: 'center',
                        verticalAlign: 'bottom',
                        y: -12,
                        style: {{
                            color: '#2b6cb0',
                            fontWeight: 'bold',
                            fontSize: '11px',
                            backgroundColor: 'rgba(255, 255, 255, 0.9)',
                            padding: '2px 5px',
                            borderRadius: '3px',
                            border: '1px solid #cbd5e0'
                        }}
                    }}
                }}]
            }},
            legend: {{
                enabled: false
            }},
            tooltip: {{
                useHTML: true,
                formatter: function () {{
                    const p = this.point;
                    const sinal = p.y >= 0 ? '+' : '';
                    const cor = p.y >= 0 ? '#2b6cb0' : '#c53030';
                    return `
                        <div style="padding: 6px 8px; font-family: sans-serif;">
                            <strong style="font-size: 1.05rem;">${{this.x}}</strong><br/>
                            <div style="margin: 6px 0; color: ${{cor}}; font-weight: bold; font-size: 1.15rem;">
                                Balanço Líquido: ${{sinal}}${{p.y.toFixed(2)}}%
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.5;">
                                • <b>Calor Crítico:</b> ${{p.itu}} dias/ano com ITU &gt; 79<br/>
                                • <b>Chuva Anual:</b> ${{p.chuva}} mm/ano<br/>
                                • <b>Perda Estimada:</b> ${{p.perda}} L/vaca/ano<br/>
                                • <b>Produtividade Base:</b> ${{p.prod}} L/vaca/ano
                            </div>
                        </div>
                    `;
                }}
            }},
            plotOptions: {{
                bar: {{
                    dataLabels: {{
                        enabled: true,
                        format: '{{point.y:+.1f}}%',
                        style: {{ fontSize: '0.75rem', fontWeight: 'bold' }}
                    }}
                }}
            }},
            series: [{{
                name: 'Balanço Líquido',
                data: {json.dumps(points_ranking, ensure_ascii=False)}
            }}]
        }});
    }}

    // ========================================================
    // 3. DISPERSÃO: CALOR CRÍTICO VS. BALANÇO LÍQUIDO
    // ========================================================
    const chartScatterEl = document.getElementById('chart-scatter-calor');
    if (chartScatterEl) {{
        Highcharts.chart('chart-scatter-calor', {{
            chart: {{
                type: 'scatter',
                height: 520,
                backgroundColor: 'transparent'
            }},
            title: {{
                text: 'Relação Bioclimática: Estresse Térmico vs. Balanço Líquido',
                style: {{ color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }}
            }},
            subtitle: {{
                text: 'Forte correspondência empírica (r ≈ -0,98) entre frequência de calor extremo e penalidade no rendimento',
                style: {{ color: '#718096' }}
            }},
            xAxis: {{
                title: {{
                    text: 'Frequência de Dias com Calor Crítico no Ano (ITU > 79)',
                    style: {{ fontWeight: '600' }}
                }},
                plotLines: [{{
                    value: 52,
                    color: '#a0aec0',
                    dashStyle: 'dash',
                    width: 1.5,
                    zIndex: 3,
                    label: {{
                        text: 'Média Sudeste (52 dias)',
                        align: 'left',
                        style: {{ color: '#718096', fontSize: '0.8rem' }}
                    }}
                }}]
            }},
            yAxis: {{
                title: {{
                    text: 'Balanço Climático Líquido (%)',
                    style: {{ fontWeight: '600' }}
                }},
                labels: {{
                    format: '{{value}}%'
                }},
                plotLines: [{{
                    value: 0,
                    color: '#2b6cb0',
                    width: 2,
                    zIndex: 4,
                    label: {{
                        text: 'Média Regional (0%)',
                        align: 'right',
                        style: {{ color: '#2b6cb0', fontWeight: 'bold' }}
                    }}
                }}]
            }},
            tooltip: {{
                useHTML: true,
                formatter: function () {{
                    const p = this.point;
                    const sinal = p.y >= 0 ? '+' : '';
                    const cor = p.y >= 0 ? '#2b6cb0' : '#c53030';
                    return `
                        <div style="padding: 6px 8px; font-family: sans-serif;">
                            <strong style="font-size: 1.05rem;">${{p.name}} (${{p.uf}})</strong><br/>
                            <div style="margin: 6px 0; color: ${{cor}}; font-weight: bold; font-size: 1.1rem;">
                                Balanço Líquido: ${{sinal}}${{p.y.toFixed(2)}}%
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.5;">
                                • <b>ITU Crítico:</b> ${{p.x}} dias/ano (&gt;79)<br/>
                                • <b>Precipitação:</b> ${{p.chuva}} mm/ano<br/>
                                • <b>Perda Média:</b> ${{p.perda}} L/vaca/ano
                            </div>
                        </div>
                    `;
                }}
            }},
            plotOptions: {{
                scatter: {{
                    marker: {{
                        radius: 7,
                        states: {{
                            hover: {{
                                enabled: true,
                                lineColor: '#2b6cb0'
                            }}
                        }}
                    }}
                }}
            }},
            series: {json.dumps(scatter_series, ensure_ascii=False)}
        }});
    }}

    // ========================================================
    // 4. COLUNAS: TOP 15 PERDAS FÍSICAS ABSOLUTAS EM LITROS
    // ========================================================
    const chartPerdaEl = document.getElementById('chart-perda-absoluta');
    if (chartPerdaEl) {{
        Highcharts.chart('chart-perda-absoluta', {{
            chart: {{
                type: 'column',
                height: 500,
                backgroundColor: 'transparent'
            }},
            title: {{
                text: 'Volume Físico Estimado de Leite Perdido por Calor Crítico',
                style: {{ color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }}
            }},
            subtitle: {{
                text: 'Top 15 Mesorregiões do Sudeste com maiores perdas físicas anuais (L/vaca/ano)',
                style: {{ color: '#718096' }}
            }},
            xAxis: {{
                categories: {json.dumps(categories_perda, ensure_ascii=False)},
                labels: {{
                    rotation: -45,
                    style: {{ fontSize: '0.8rem' }}
                }}
            }},
            yAxis: {{
                title: {{
                    text: 'Leite Perdido Anual por Calor (Litros / vaca / ano)',
                    style: {{ fontWeight: '600' }}
                }}
            }},
            legend: {{
                enabled: false
            }},
            tooltip: {{
                useHTML: true,
                formatter: function () {{
                    const p = this.point;
                    return `
                        <div style="padding: 6px 8px; font-family: sans-serif;">
                            <strong style="font-size: 1.05rem;">${{this.x}}</strong><br/>
                            <div style="margin: 6px 0; color: #c53030; font-weight: bold; font-size: 1.15rem;">
                                Perda: ${{p.y.toFixed(1)}} Litros/vaca/ano
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.5;">
                                • <b>Produtividade Base:</b> ${{p.prod}} L/vaca/ano<br/>
                                • <b>Balanço Líquido:</b> ${{p.liq >= 0 ? '+' : ''}}${{p.liq.toFixed(2)}}%<br/>
                                • <b>Calor Crítico:</b> ${{p.itu}} dias/ano<br/>
                                • <b>Chuva:</b> ${{p.chuva}} mm/ano
                            </div>
                        </div>
                    `;
                }}
            }},
            plotOptions: {{
                column: {{
                    borderRadius: 4,
                    dataLabels: {{
                        enabled: true,
                        format: '{{point.y:.0f}} L',
                        style: {{ fontSize: '0.75rem', fontWeight: 'bold' }}
                    }}
                }}
            }},
            series: [{{
                name: 'Perda Física de Leite',
                data: {json.dumps(points_perda, ensure_ascii=False)}
            }}]
        }});
    }}

    // ========================================================
    // REFLOW AUTOMÁTICO EM MUDANÇA DE ABAS DO BOOTSTRAP / QUARTO
    // ========================================================
    document.querySelectorAll('a[data-bs-toggle="tab"], button[data-bs-toggle="tab"]').forEach((tab) => {{
        tab.addEventListener('shown.bs.tab', function () {{
            if (window.Highcharts) {{
                Highcharts.charts.forEach((chart) => {{
                    if (chart) chart.reflow();
                }});
            }}
        }});
    }});
}});
"""

    out_file = Path("assets/highcharts-mesorregioes.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"Salvo {out_file} ({out_file.stat().st_size / 1024:.1f} KB) com sucesso!")

if __name__ == "__main__":
    main()

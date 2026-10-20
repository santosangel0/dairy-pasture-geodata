import json
from pathlib import Path

def main():
    json_path = Path("assets/data/mesorregioes_impacto_climatico.json")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Ranking data
    data_sorted = sorted(data, key=lambda x: x["liq_pct"])
    categories_ranking = [d["label"] for d in data_sorted]
    points_ranking = []
    for d in data_sorted:
        val = d["liq_pct"]
        if val <= -10:
            c = "#c53030"  # Vermelho escuro
        elif val < 0:
            c = "#e53e3e"  # Vermelho médio
        elif val < 10:
            c = "#3182ce"  # Azul médio
        else:
            c = "#2b6cb0"  # Azul escuro
            
        points_ranking.append({
            "y": val,
            "color": c,
            "itu": d["itu_dias"],
            "chuva": d["chuva_mm"],
            "perda": d["perda_l"],
            "prod": d["prod_base"],
            "uf": d["uf"]
        })

    # 2. Scatter data grouped by UF
    ufs = {
        "MG": {"name": "Minas Gerais", "color": "#2f855a"},
        "SP": {"name": "São Paulo", "color": "#dd6b20"},
        "RJ": {"name": "Rio de Janeiro", "color": "#e53e3e"},
        "ES": {"name": "Espírito Santo", "color": "#319795"}
    }
    scatter_series = []
    for uf_code, uf_info in ufs.items():
        pts = []
        for d in data:
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

    # 3. Top Perdas Absolutas
    data_perda = sorted(data, key=lambda x: x["perda_l"], reverse=True)[:15]
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

    js_content = f"""// Gráficos Interativos Highcharts - Projeção Bioclimática por Mesorregião (Sudeste)

document.addEventListener('DOMContentLoaded', function () {{
    Highcharts.setOptions({{
        lang: {{
            decimalPoint: ',',
            thousandsSep: '.',
            downloadPNG: 'Baixar imagem PNG',
            downloadJPEG: 'Baixar imagem JPEG',
            downloadPDF: 'Baixar documento PDF',
            downloadSVG: 'Baixar vetor SVG',
            printChart: 'Imprimir gráfico',
            viewFullscreen: 'Ver em tela cheia'
        }},
        credits: {{
            enabled: false
        }}
    }});

    // 1. Gráfico de Barras Divergente: Ranking das 37 Mesorregiões
    const chartRankingEl = document.getElementById('chart-ranking-mesorregioes');
    if (chartRankingEl) {{
        Highcharts.chart('chart-ranking-mesorregioes', {{
            chart: {{
                type: 'bar',
                height: 850,
                backgroundColor: 'transparent'
            }},
            title: {{
                text: 'Balanço Climático Líquido (Δ%) por Mesorregião do Sudeste',
                style: {{ color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }}
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
                    width: 2.5,
                    zIndex: 5,
                    label: {{
                        text: 'Média Regional (0%)',
                        align: 'right',
                        style: {{ color: '#2b6cb0', fontWeight: 'bold' }}
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

    // 2. Gráfico de Dispersão: Calor Crítico vs. Balanço Líquido
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
                text: 'Correspondência estrita (r ≈ -0,98) entre frequência de dias de calor extremo e penalidade no rendimento',
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

    // 3. Gráfico de Colunas: Top 15 Maiores Perdas Absolutas em Litros
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

    // Reflow dos gráficos quando abas do Quarto/Bootstrap forem alternadas
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
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"Salvo {out_file} com sucesso!")

if __name__ == "__main__":
    main()

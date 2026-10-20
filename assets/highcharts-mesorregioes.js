// Gráficos Interativos Highcharts - Projeção Bioclimática por Mesorregião (Sudeste)

document.addEventListener('DOMContentLoaded', function () {
    Highcharts.setOptions({
        lang: {
            decimalPoint: ',',
            thousandsSep: '.',
            downloadPNG: 'Baixar imagem PNG',
            downloadJPEG: 'Baixar imagem JPEG',
            downloadPDF: 'Baixar documento PDF',
            downloadSVG: 'Baixar vetor SVG',
            printChart: 'Imprimir gráfico',
            viewFullscreen: 'Ver em tela cheia'
        },
        credits: {
            enabled: false
        }
    });

    // 1. Gráfico de Barras Divergente: Ranking das 37 Mesorregiões
    const chartRankingEl = document.getElementById('chart-ranking-mesorregioes');
    if (chartRankingEl) {
        Highcharts.chart('chart-ranking-mesorregioes', {
            chart: {
                type: 'bar',
                height: 850,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Balanço Climático Líquido (Δ%) por Mesorregião do Sudeste',
                style: { color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }
            },
            subtitle: {
                text: 'Projeção da Equação 3 ponderada nas células de pastagem (Coleção 9 MapBiomas)',
                style: { color: '#718096' }
            },
            xAxis: {
                categories: ["Noroeste Fluminense (RJ)", "Norte Fluminense (RJ)", "Araçatuba (SP)", "Sul Espírito-santense (ES)", "Litoral Norte Espírito-santense (ES)", "São José do Rio Preto (SP)", "Noroeste Espírito-santense (ES)", "Jequitinhonha (MG)", "Presidente Prudente (SP)", "Norte de Minas (MG)", "Central Espírito-santense (ES)", "Vale do Rio Doce (MG)", "Vale do Mucuri (MG)", "Marília (SP)", "Centro Fluminense (RJ)", "Baixadas Litorâneas (RJ)", "Assis (SP)", "Sul Fluminense (RJ)", "Metropolitana do Rio de Janeiro (RJ)", "Bauru (SP)", "Triângulo Mineiro / Alto Paranaíba (MG)", "Zona da Mata (MG)", "Ribeirão Preto (SP)", "Piracicaba (SP)", "Araraquara (SP)", "Itapetininga (SP)", "Noroeste de Minas (MG)", "Macro Metropolitana Paulista (SP)", "Central Mineira (MG)", "Vale do Paraíba Paulista (SP)", "Campinas (SP)", "Litoral Sul Paulista (SP)", "Metropolitana de Belo Horizonte (MG)", "Oeste de Minas (MG)", "Sul / Sudoeste de Minas (MG)", "Metropolitana de São Paulo (SP)", "Campo das Vertentes (MG)"],
                labels: {
                    style: { fontSize: '0.85rem', color: '#2d3748' }
                }
            },
            yAxis: {
                title: {
                    text: 'Variação Percentual Relativa frente à Média Regional (%)',
                    style: { fontWeight: '600' }
                },
                labels: {
                    format: '{value}%'
                },
                plotLines: [{
                    value: 0,
                    color: '#2b6cb0',
                    width: 2.5,
                    zIndex: 5,
                    label: {
                        text: 'Média Regional (0%)',
                        align: 'right',
                        style: { color: '#2b6cb0', fontWeight: 'bold' }
                    }
                }]
            },
            legend: {
                enabled: false
            },
            tooltip: {
                useHTML: true,
                formatter: function () {
                    const p = this.point;
                    const sinal = p.y >= 0 ? '+' : '';
                    const cor = p.y >= 0 ? '#2b6cb0' : '#c53030';
                    return `
                        <div style="padding: 6px 8px; font-family: sans-serif;">
                            <strong style="font-size: 1.05rem;">${this.x}</strong><br/>
                            <div style="margin: 6px 0; color: ${cor}; font-weight: bold; font-size: 1.15rem;">
                                Balanço Líquido: ${sinal}${p.y.toFixed(2)}%
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.5;">
                                • <b>Calor Crítico:</b> ${p.itu} dias/ano com ITU &gt; 79<br/>
                                • <b>Chuva Anual:</b> ${p.chuva} mm/ano<br/>
                                • <b>Perda Estimada:</b> ${p.perda} L/vaca/ano<br/>
                                • <b>Produtividade Base:</b> ${p.prod} L/vaca/ano
                            </div>
                        </div>
                    `;
                }
            },
            plotOptions: {
                bar: {
                    dataLabels: {
                        enabled: true,
                        format: '{point.y:+.1f}%',
                        style: { fontSize: '0.75rem', fontWeight: 'bold' }
                    }
                }
            },
            series: [{
                name: 'Balanço Líquido',
                data: [{"y": -16.36, "color": "#c53030", "itu": 124.4, "chuva": 1216.0, "perda": 342.8, "prod": 1160.4, "uf": "RJ"}, {"y": -16.25, "color": "#c53030", "itu": 120.4, "chuva": 1130.0, "perda": 322.5, "prod": 1128.9, "uf": "RJ"}, {"y": -15.7, "color": "#c53030", "itu": 122.0, "chuva": 1225.0, "perda": 481.3, "prod": 1659.4, "uf": "SP"}, {"y": -14.36, "color": "#c53030", "itu": 118.7, "chuva": 1286.0, "perda": 426.5, "prod": 1504.8, "uf": "ES"}, {"y": -13.18, "color": "#c53030", "itu": 106.0, "chuva": 1087.0, "perda": 330.5, "prod": 1278.7, "uf": "ES"}, {"y": -11.02, "color": "#c53030", "itu": 104.4, "chuva": 1267.0, "perda": 299.5, "prod": 1177.6, "uf": "SP"}, {"y": -9.99, "color": "#e53e3e", "itu": 90.5, "chuva": 1030.0, "perda": 267.1, "prod": 1186.3, "uf": "ES"}, {"y": -9.41, "color": "#e53e3e", "itu": 83.8, "chuva": 878.0, "perda": 186.8, "prod": 952.1, "uf": "MG"}, {"y": -8.89, "color": "#e53e3e", "itu": 97.2, "chuva": 1295.0, "perda": 260.2, "prod": 1083.5, "uf": "SP"}, {"y": -7.84, "color": "#e53e3e", "itu": 79.2, "chuva": 931.0, "perda": 233.2, "prod": 1200.0, "uf": "MG"}, {"y": -6.09, "color": "#e53e3e", "itu": 84.4, "chuva": 1236.0, "perda": 298.8, "prod": 1441.0, "uf": "ES"}, {"y": -5.2, "color": "#e53e3e", "itu": 74.2, "chuva": 1049.0, "perda": 290.0, "prod": 1580.7, "uf": "MG"}, {"y": -4.63, "color": "#e53e3e", "itu": 69.1, "chuva": 995.0, "perda": 208.0, "prod": 1210.8, "uf": "MG"}, {"y": -4.61, "color": "#e53e3e", "itu": 83.1, "chuva": 1348.0, "perda": 274.9, "prod": 1301.2, "uf": "SP"}, {"y": -3.64, "color": "#e53e3e", "itu": 81.8, "chuva": 1375.0, "perda": 246.5, "prod": 1285.5, "uf": "RJ"}, {"y": -2.45, "color": "#e53e3e", "itu": 85.7, "chuva": 1597.0, "perda": 264.0, "prod": 1247.1, "uf": "RJ"}, {"y": -0.92, "color": "#e53e3e", "itu": 70.7, "chuva": 1366.0, "perda": 207.7, "prod": 1166.0, "uf": "SP"}, {"y": -0.13, "color": "#e53e3e", "itu": 73.4, "chuva": 1499.0, "perda": 322.5, "prod": 1751.5, "uf": "RJ"}, {"y": -0.08, "color": "#e53e3e", "itu": 74.0, "chuva": 1477.0, "perda": 232.7, "prod": 1278.5, "uf": "RJ"}, {"y": 0.91, "color": "#3182ce", "itu": 61.0, "chuva": 1280.0, "perda": 270.2, "prod": 1727.5, "uf": "SP"}, {"y": 1.94, "color": "#3182ce", "itu": 63.1, "chuva": 1365.0, "perda": 315.5, "prod": 2432.4, "uf": "MG"}, {"y": 5.51, "color": "#3182ce", "itu": 49.2, "chuva": 1362.0, "perda": 243.2, "prod": 1987.8, "uf": "MG"}, {"y": 7.67, "color": "#3182ce", "itu": 42.8, "chuva": 1387.0, "perda": 177.5, "prod": 1894.6, "uf": "SP"}, {"y": 7.8, "color": "#3182ce", "itu": 38.0, "chuva": 1306.0, "perda": 161.3, "prod": 1554.1, "uf": "SP"}, {"y": 8.9, "color": "#3182ce", "itu": 36.6, "chuva": 1334.0, "perda": 166.3, "prod": 1969.9, "uf": "SP"}, {"y": 9.46, "color": "#3182ce", "itu": 33.0, "chuva": 1318.0, "perda": 124.1, "prod": 1400.7, "uf": "SP"}, {"y": 9.58, "color": "#3182ce", "itu": 27.4, "chuva": 1181.0, "perda": 167.1, "prod": 2285.9, "uf": "MG"}, {"y": 10.24, "color": "#2b6cb0", "itu": 41.4, "chuva": 1583.0, "perda": 103.8, "prod": 965.5, "uf": "SP"}, {"y": 10.61, "color": "#2b6cb0", "itu": 23.9, "chuva": 1187.0, "perda": 162.4, "prod": 2558.5, "uf": "MG"}, {"y": 11.65, "color": "#2b6cb0", "itu": 29.6, "chuva": 1399.0, "perda": 120.3, "prod": 1599.0, "uf": "SP"}, {"y": 12.61, "color": "#2b6cb0", "itu": 24.8, "chuva": 1363.0, "perda": 140.3, "prod": 2150.7, "uf": "SP"}, {"y": 12.71, "color": "#2b6cb0", "itu": 23.0, "chuva": 1326.0, "perda": 93.6, "prod": 1504.3, "uf": "SP"}, {"y": 13.24, "color": "#2b6cb0", "itu": 19.6, "chuva": 1284.0, "perda": 118.6, "prod": 2285.1, "uf": "MG"}, {"y": 15.23, "color": "#2b6cb0", "itu": 16.4, "chuva": 1359.0, "perda": 114.5, "prod": 2521.3, "uf": "MG"}, {"y": 15.88, "color": "#2b6cb0", "itu": 15.8, "chuva": 1392.0, "perda": 104.6, "prod": 2368.2, "uf": "MG"}, {"y": 16.05, "color": "#2b6cb0", "itu": 15.6, "chuva": 1400.0, "perda": 58.5, "prod": 1417.9, "uf": "SP"}, {"y": 17.07, "color": "#2b6cb0", "itu": 12.0, "chuva": 1389.0, "perda": 96.1, "prod": 2785.8, "uf": "MG"}]
            }]
        });
    }

    // 2. Gráfico de Dispersão: Calor Crítico vs. Balanço Líquido
    const chartScatterEl = document.getElementById('chart-scatter-calor');
    if (chartScatterEl) {
        Highcharts.chart('chart-scatter-calor', {
            chart: {
                type: 'scatter',
                height: 520,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Relação Bioclimática: Estresse Térmico vs. Balanço Líquido',
                style: { color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }
            },
            subtitle: {
                text: 'Correspondência estrita (r ≈ -0,98) entre frequência de dias de calor extremo e penalidade no rendimento',
                style: { color: '#718096' }
            },
            xAxis: {
                title: {
                    text: 'Frequência de Dias com Calor Crítico no Ano (ITU > 79)',
                    style: { fontWeight: '600' }
                },
                plotLines: [{
                    value: 52,
                    color: '#a0aec0',
                    dashStyle: 'dash',
                    width: 1.5,
                    zIndex: 3,
                    label: {
                        text: 'Média Sudeste (52 dias)',
                        align: 'left',
                        style: { color: '#718096', fontSize: '0.8rem' }
                    }
                }]
            },
            yAxis: {
                title: {
                    text: 'Balanço Climático Líquido (%)',
                    style: { fontWeight: '600' }
                },
                labels: {
                    format: '{value}%'
                },
                plotLines: [{
                    value: 0,
                    color: '#2b6cb0',
                    width: 2,
                    zIndex: 4,
                    label: {
                        text: 'Média Regional (0%)',
                        align: 'right',
                        style: { color: '#2b6cb0', fontWeight: 'bold' }
                    }
                }]
            },
            tooltip: {
                useHTML: true,
                formatter: function () {
                    const p = this.point;
                    const sinal = p.y >= 0 ? '+' : '';
                    const cor = p.y >= 0 ? '#2b6cb0' : '#c53030';
                    return `
                        <div style="padding: 6px 8px; font-family: sans-serif;">
                            <strong style="font-size: 1.05rem;">${p.name} (${p.uf})</strong><br/>
                            <div style="margin: 6px 0; color: ${cor}; font-weight: bold; font-size: 1.1rem;">
                                Balanço Líquido: ${sinal}${p.y.toFixed(2)}%
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.5;">
                                • <b>ITU Crítico:</b> ${p.x} dias/ano (&gt;79)<br/>
                                • <b>Precipitação:</b> ${p.chuva} mm/ano<br/>
                                • <b>Perda Média:</b> ${p.perda} L/vaca/ano
                            </div>
                        </div>
                    `;
                }
            },
            plotOptions: {
                scatter: {
                    marker: {
                        radius: 7,
                        states: {
                            hover: {
                                enabled: true,
                                lineColor: '#2b6cb0'
                            }
                        }
                    }
                }
            },
            series: [{"name": "Minas Gerais", "color": "#2f855a", "data": [{"x": 83.8, "y": -9.41, "name": "Jequitinhonha", "uf": "MG", "chuva": 878.0, "perda": 186.8, "prod": 952.1}, {"x": 79.2, "y": -7.84, "name": "Norte de Minas", "uf": "MG", "chuva": 931.0, "perda": 233.2, "prod": 1200.0}, {"x": 74.2, "y": -5.2, "name": "Vale do Rio Doce", "uf": "MG", "chuva": 1049.0, "perda": 290.0, "prod": 1580.7}, {"x": 69.1, "y": -4.63, "name": "Vale do Mucuri", "uf": "MG", "chuva": 995.0, "perda": 208.0, "prod": 1210.8}, {"x": 63.1, "y": 1.94, "name": "Triângulo Mineiro / Alto Paranaíba", "uf": "MG", "chuva": 1365.0, "perda": 315.5, "prod": 2432.4}, {"x": 49.2, "y": 5.51, "name": "Zona da Mata", "uf": "MG", "chuva": 1362.0, "perda": 243.2, "prod": 1987.8}, {"x": 27.4, "y": 9.58, "name": "Noroeste de Minas", "uf": "MG", "chuva": 1181.0, "perda": 167.1, "prod": 2285.9}, {"x": 23.9, "y": 10.61, "name": "Central Mineira", "uf": "MG", "chuva": 1187.0, "perda": 162.4, "prod": 2558.5}, {"x": 19.6, "y": 13.24, "name": "Metropolitana de Belo Horizonte", "uf": "MG", "chuva": 1284.0, "perda": 118.6, "prod": 2285.1}, {"x": 16.4, "y": 15.23, "name": "Oeste de Minas", "uf": "MG", "chuva": 1359.0, "perda": 114.5, "prod": 2521.3}, {"x": 15.8, "y": 15.88, "name": "Sul / Sudoeste de Minas", "uf": "MG", "chuva": 1392.0, "perda": 104.6, "prod": 2368.2}, {"x": 12.0, "y": 17.07, "name": "Campo das Vertentes", "uf": "MG", "chuva": 1389.0, "perda": 96.1, "prod": 2785.8}], "marker": {"radius": 6, "symbol": "circle"}}, {"name": "São Paulo", "color": "#dd6b20", "data": [{"x": 122.0, "y": -15.7, "name": "Araçatuba", "uf": "SP", "chuva": 1225.0, "perda": 481.3, "prod": 1659.4}, {"x": 104.4, "y": -11.02, "name": "São José do Rio Preto", "uf": "SP", "chuva": 1267.0, "perda": 299.5, "prod": 1177.6}, {"x": 97.2, "y": -8.89, "name": "Presidente Prudente", "uf": "SP", "chuva": 1295.0, "perda": 260.2, "prod": 1083.5}, {"x": 83.1, "y": -4.61, "name": "Marília", "uf": "SP", "chuva": 1348.0, "perda": 274.9, "prod": 1301.2}, {"x": 70.7, "y": -0.92, "name": "Assis", "uf": "SP", "chuva": 1366.0, "perda": 207.7, "prod": 1166.0}, {"x": 61.0, "y": 0.91, "name": "Bauru", "uf": "SP", "chuva": 1280.0, "perda": 270.2, "prod": 1727.5}, {"x": 42.8, "y": 7.67, "name": "Ribeirão Preto", "uf": "SP", "chuva": 1387.0, "perda": 177.5, "prod": 1894.6}, {"x": 38.0, "y": 7.8, "name": "Piracicaba", "uf": "SP", "chuva": 1306.0, "perda": 161.3, "prod": 1554.1}, {"x": 36.6, "y": 8.9, "name": "Araraquara", "uf": "SP", "chuva": 1334.0, "perda": 166.3, "prod": 1969.9}, {"x": 33.0, "y": 9.46, "name": "Itapetininga", "uf": "SP", "chuva": 1318.0, "perda": 124.1, "prod": 1400.7}, {"x": 41.4, "y": 10.24, "name": "Macro Metropolitana Paulista", "uf": "SP", "chuva": 1583.0, "perda": 103.8, "prod": 965.5}, {"x": 29.6, "y": 11.65, "name": "Vale do Paraíba Paulista", "uf": "SP", "chuva": 1399.0, "perda": 120.3, "prod": 1599.0}, {"x": 24.8, "y": 12.61, "name": "Campinas", "uf": "SP", "chuva": 1363.0, "perda": 140.3, "prod": 2150.7}, {"x": 23.0, "y": 12.71, "name": "Litoral Sul Paulista", "uf": "SP", "chuva": 1326.0, "perda": 93.6, "prod": 1504.3}, {"x": 15.6, "y": 16.05, "name": "Metropolitana de São Paulo", "uf": "SP", "chuva": 1400.0, "perda": 58.5, "prod": 1417.9}], "marker": {"radius": 6, "symbol": "circle"}}, {"name": "Rio de Janeiro", "color": "#e53e3e", "data": [{"x": 124.4, "y": -16.36, "name": "Noroeste Fluminense", "uf": "RJ", "chuva": 1216.0, "perda": 342.8, "prod": 1160.4}, {"x": 120.4, "y": -16.25, "name": "Norte Fluminense", "uf": "RJ", "chuva": 1130.0, "perda": 322.5, "prod": 1128.9}, {"x": 81.8, "y": -3.64, "name": "Centro Fluminense", "uf": "RJ", "chuva": 1375.0, "perda": 246.5, "prod": 1285.5}, {"x": 85.7, "y": -2.45, "name": "Baixadas Litorâneas", "uf": "RJ", "chuva": 1597.0, "perda": 264.0, "prod": 1247.1}, {"x": 73.4, "y": -0.13, "name": "Sul Fluminense", "uf": "RJ", "chuva": 1499.0, "perda": 322.5, "prod": 1751.5}, {"x": 74.0, "y": -0.08, "name": "Metropolitana do Rio de Janeiro", "uf": "RJ", "chuva": 1477.0, "perda": 232.7, "prod": 1278.5}], "marker": {"radius": 6, "symbol": "circle"}}, {"name": "Espírito Santo", "color": "#319795", "data": [{"x": 118.7, "y": -14.36, "name": "Sul Espírito-santense", "uf": "ES", "chuva": 1286.0, "perda": 426.5, "prod": 1504.8}, {"x": 106.0, "y": -13.18, "name": "Litoral Norte Espírito-santense", "uf": "ES", "chuva": 1087.0, "perda": 330.5, "prod": 1278.7}, {"x": 90.5, "y": -9.99, "name": "Noroeste Espírito-santense", "uf": "ES", "chuva": 1030.0, "perda": 267.1, "prod": 1186.3}, {"x": 84.4, "y": -6.09, "name": "Central Espírito-santense", "uf": "ES", "chuva": 1236.0, "perda": 298.8, "prod": 1441.0}], "marker": {"radius": 6, "symbol": "circle"}}]
        });
    }

    // 3. Gráfico de Colunas: Top 15 Maiores Perdas Absolutas em Litros
    const chartPerdaEl = document.getElementById('chart-perda-absoluta');
    if (chartPerdaEl) {
        Highcharts.chart('chart-perda-absoluta', {
            chart: {
                type: 'column',
                height: 500,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Volume Físico Estimado de Leite Perdido por Calor Crítico',
                style: { color: '#1a365d', fontWeight: 'bold', fontSize: '1.25rem' }
            },
            subtitle: {
                text: 'Top 15 Mesorregiões do Sudeste com maiores perdas físicas anuais (L/vaca/ano)',
                style: { color: '#718096' }
            },
            xAxis: {
                categories: ["Araçatuba (SP)", "Sul Espírito-santense (ES)", "Noroeste Fluminense (RJ)", "Litoral Norte Espírito-santense (ES)", "Norte Fluminense (RJ)", "Sul Fluminense (RJ)", "Triângulo Mineiro / Alto Paranaíba (MG)", "São José do Rio Preto (SP)", "Central Espírito-santense (ES)", "Vale do Rio Doce (MG)", "Marília (SP)", "Bauru (SP)", "Noroeste Espírito-santense (ES)", "Baixadas Litorâneas (RJ)", "Presidente Prudente (SP)"],
                labels: {
                    rotation: -45,
                    style: { fontSize: '0.8rem' }
                }
            },
            yAxis: {
                title: {
                    text: 'Leite Perdido Anual por Calor (Litros / vaca / ano)',
                    style: { fontWeight: '600' }
                }
            },
            legend: {
                enabled: false
            },
            tooltip: {
                useHTML: true,
                formatter: function () {
                    const p = this.point;
                    return `
                        <div style="padding: 6px 8px; font-family: sans-serif;">
                            <strong style="font-size: 1.05rem;">${this.x}</strong><br/>
                            <div style="margin: 6px 0; color: #c53030; font-weight: bold; font-size: 1.15rem;">
                                Perda: ${p.y.toFixed(1)} Litros/vaca/ano
                            </div>
                            <div style="font-size: 0.9rem; line-height: 1.5;">
                                • <b>Produtividade Base:</b> ${p.prod} L/vaca/ano<br/>
                                • <b>Balanço Líquido:</b> ${p.liq >= 0 ? '+' : ''}${p.liq.toFixed(2)}%<br/>
                                • <b>Calor Crítico:</b> ${p.itu} dias/ano<br/>
                                • <b>Chuva:</b> ${p.chuva} mm/ano
                            </div>
                        </div>
                    `;
                }
            },
            plotOptions: {
                column: {
                    borderRadius: 4,
                    dataLabels: {
                        enabled: true,
                        format: '{point.y:.0f} L',
                        style: { fontSize: '0.75rem', fontWeight: 'bold' }
                    }
                }
            },
            series: [{
                name: 'Perda Física de Leite',
                data: [{"y": 481.3, "color": "#c53030", "liq": -15.7, "itu": 122.0, "chuva": 1225.0, "prod": 1659.4}, {"y": 426.5, "color": "#c53030", "liq": -14.36, "itu": 118.7, "chuva": 1286.0, "prod": 1504.8}, {"y": 342.8, "color": "#c53030", "liq": -16.36, "itu": 124.4, "chuva": 1216.0, "prod": 1160.4}, {"y": 330.5, "color": "#c53030", "liq": -13.18, "itu": 106.0, "chuva": 1087.0, "prod": 1278.7}, {"y": 322.5, "color": "#c53030", "liq": -16.25, "itu": 120.4, "chuva": 1130.0, "prod": 1128.9}, {"y": 322.5, "color": "#c53030", "liq": -0.13, "itu": 73.4, "chuva": 1499.0, "prod": 1751.5}, {"y": 315.5, "color": "#2b6cb0", "liq": 1.94, "itu": 63.1, "chuva": 1365.0, "prod": 2432.4}, {"y": 299.5, "color": "#c53030", "liq": -11.02, "itu": 104.4, "chuva": 1267.0, "prod": 1177.6}, {"y": 298.8, "color": "#c53030", "liq": -6.09, "itu": 84.4, "chuva": 1236.0, "prod": 1441.0}, {"y": 290.0, "color": "#c53030", "liq": -5.2, "itu": 74.2, "chuva": 1049.0, "prod": 1580.7}, {"y": 274.9, "color": "#c53030", "liq": -4.61, "itu": 83.1, "chuva": 1348.0, "prod": 1301.2}, {"y": 270.2, "color": "#2b6cb0", "liq": 0.91, "itu": 61.0, "chuva": 1280.0, "prod": 1727.5}, {"y": 267.1, "color": "#c53030", "liq": -9.99, "itu": 90.5, "chuva": 1030.0, "prod": 1186.3}, {"y": 264.0, "color": "#c53030", "liq": -2.45, "itu": 85.7, "chuva": 1597.0, "prod": 1247.1}, {"y": 260.2, "color": "#c53030", "liq": -8.89, "itu": 97.2, "chuva": 1295.0, "prod": 1083.5}]
            }]
        });
    }

    // Reflow dos gráficos quando abas do Quarto/Bootstrap forem alternadas
    document.querySelectorAll('a[data-bs-toggle="tab"], button[data-bs-toggle="tab"]').forEach((tab) => {
        tab.addEventListener('shown.bs.tab', function () {
            if (window.Highcharts) {
                Highcharts.charts.forEach((chart) => {
                    if (chart) chart.reflow();
                });
            }
        });
    });
});

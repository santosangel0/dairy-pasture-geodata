# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "earthengine-api",
#     "geemap",
# ]
# ///
import os
import ee
import geemap

def main():
    print("Inicializando o Google Earth Engine...", flush=True)
    try:
        ee.Initialize(project='503763347927')
    except Exception as e:
        print(f"Erro na inicializacao do Earth Engine: {e}", flush=True)
        return

    out_dir = "rasters-sudeste"
    os.makedirs(out_dir, exist_ok=True)
    print(f"Diretorio '{out_dir}' criado/verificado.", flush=True)

    # Definir geometria do Sudeste (SP, MG, RJ, ES)
    sudeste = ee.FeatureCollection("FAO/GAUL/2015/level1") \
        .filter(ee.Filter.inList('ADM1_NAME', ['Sao Paulo', 'Minas Gerais', 'Rio De Janeiro', 'Espirito Santo']))
    sudeste_geom = sudeste.geometry()

    # 1. NDVI sobre pastagem (2008-2023)
    print("Processando NDVI sobre pastagem (MODIS + MapBiomas Col 9)...")
    # Usa a classe de pastagem (15) do MapBiomas como máscara
    mb = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')
    pasture_mask = mb.select('classification_2023').eq(15)

    modis = ee.ImageCollection('MODIS/061/MOD13Q1') \
        .filterDate('2008-01-01', '2023-12-31') \
        .select('NDVI')
    
    # Calcular climatologia média mensal para formar 12 bandas
    months = ee.List.sequence(1, 12)
    def ndvi_by_month(m):
        return modis.filter(ee.Filter.calendarRange(m, m, 'month')) \
            .mean() \
            .multiply(0.0001) \
            .updateMask(pasture_mask) \
            .rename(ee.String('NDVI_mes_').cat(ee.Number(m).format('%02d')))

    ndvi_clim = ee.ImageCollection.fromImages(months.map(ndvi_by_month)).toBands().clip(sudeste_geom)
    
    ndvi_file = os.path.join(out_dir, "ndvi_pastagem_sudeste.tif")
    geemap.ee_export_image(ndvi_clim, filename=ndvi_file, scale=3000, region=sudeste_geom, file_per_band=False)
    print(f"NDVI salvo em: {ndvi_file}", flush=True)

    # 2. SPEI-12 mês a mês (2008-2023)
    print("Processando SPEI-12 mês a mês (CSIC)...", flush=True)
    # Usa a coleção global do SPEI como equivalente à técnica local por limitações de dados locais no GEE
    spei = ee.ImageCollection("CSIC/SPEI/2_11") \
        .filterDate('2008-01-01', '2023-12-31') \
        .select('SPEI_12_month') \
        .toBands() \
        .clip(sudeste_geom)
    
    spei_file = os.path.join(out_dir, "spei12_mensal_sudeste.tif")
    geemap.ee_export_image(spei, filename=spei_file, scale=15000, region=sudeste_geom, file_per_band=False)
    print(f"SPEI-12 salvo em: {spei_file}", flush=True)

    # 3. Estresse térmico crítico (ITU > 79)
    print("Processando Estresse térmico crítico ITU > 79 (ERA5)...")
    # Usa ERA5 para calcular ITU diariamente: ITU = T + 0.36 * Tdp + 41.2
    era5 = ee.ImageCollection("ECMWF/ERA5/DAILY") \
        .filterDate('2008-01-01', '2023-12-31')

    def calc_itu_gt_79(img):
        t_max = img.select('maximum_2m_air_temperature').subtract(273.15)
        tdp = img.select('dewpoint_2m_temperature').subtract(273.15)
        itu = t_max.add(tdp.multiply(0.36)).add(41.2)
        return itu.gt(79).rename('dias_itu79').copyProperties(img, ['system:time_start'])

    itu_gt_79 = era5.map(calc_itu_gt_79)

    # Climatologia de dias por mês com ITU > 79 (soma por mês ao longo de 16 anos / 16)
    def itu_by_month(m):
        return itu_gt_79.filter(ee.Filter.calendarRange(m, m, 'month')) \
            .sum() \
            .divide(16) \
            .rename(ee.String('dias_itu79_mes_').cat(ee.Number(m).format('%02d')))

    itu_clim = ee.ImageCollection.fromImages(months.map(itu_by_month)).toBands().clip(sudeste_geom)

    itu_file = os.path.join(out_dir, "itu_clim_sudeste.tif")
    geemap.ee_export_image(itu_clim, filename=itu_file, scale=5000, region=sudeste_geom, file_per_band=False)
    print(f"ITU > 79 salvo em: {itu_file}")
    
    print("Processamento concluído com sucesso!")

if __name__ == "__main__":
    main()

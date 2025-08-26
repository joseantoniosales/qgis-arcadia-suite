# -*- coding: utf-8 -*-
import os, configparser, requests, urllib.parse, tempfile, zipfile, shutil, json, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import *
from qgis import processing
from .configurator_dialog import get_settings_file_path

# --- NOMBRE DE CLASE ESTANDARIZADO ---
class WFSDownloaderTool(QgsProcessingAlgorithm):
    P_WFS_URL = 'WFS_BASE_URL'; P_TYPENAMES = 'TYPENAMES'; P_AOI = 'AOI'
    P_FORMAT = 'FORMAT'; P_USE_CACHE = 'USE_CACHE'; P_APPLY_STYLE = 'APPLY_STYLE'
    
    def tr(self, text): return QCoreApplication.translate('WFSDownloaderTool', text)
    def createInstance(self): return WFSDownloaderTool()
    
    # --- NOMBRES INTERNOS ESTANDARIZADOS ---
    def name(self): return 'arcadia_wfs_downloader'
    def displayName(self): return self.tr('1. Descargador WFS Avanzado')
    def group(self): return self.tr('Arcadia Suite')
    def groupId(self): return 'arcadia_suite'

    # (El resto del código del descargador no cambia)
    def initAlgorithm(self, config=None):
        self.shared_path_config = {'styles': '', 'cache': ''}
        config = configparser.ConfigParser()
        settings_file = get_settings_file_path()
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            self.shared_path_config['styles'] = config.get('Workgroup', 'StylesPath', fallback='').strip()
            self.shared_path_config['cache'] = config.get('Workgroup', 'CachePath', fallback='').strip()
        self.addParameter(QgsProcessingParameterString(self.P_WFS_URL, self.tr('URL base del servicio WFS')))
        self.addParameter(QgsProcessingParameterString(self.P_TYPENAMES, self.tr('typeName(s) a descargar')))
        self.addParameter(QgsProcessingParameterEnum(self.P_FORMAT, self.tr('Formato de Descarga'), options=['SHP (shape-zip)', 'GML', 'GeoJSON', 'GeoPackage'], defaultValue=0))
        self.addParameter(QgsProcessingParameterVectorLayer(self.P_AOI, self.tr('Capa de AOI (poligonal)'), [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterCrs('SRS', self.tr('CRS de trabajo y salida'), defaultValue='EPSG:25830'))
        self.addParameter(QgsProcessingParameterNumber('BUFFER_M', self.tr('Buffer (metros)'), type=QgsProcessingParameterNumber.Double, defaultValue=100.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterEnum('RECORTE_MODE', self.tr('Modo de máscara'), options=[self.tr('EXTENT de la AOI + Buffer'), self.tr('GEOMETRÍA de la AOI + Buffer')], defaultValue=0))
        self.addParameter(QgsProcessingParameterBoolean('ROUND_CORNERS', self.tr('Redondear esquinas del buffer'), defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean('FILTRO_ON', self.tr('Aplicar filtro por expresión'), defaultValue=False))
        self.addParameter(QgsProcessingParameterExpression('FILTRO_EXPR', self.tr('Expresión de filtro'), defaultValue='"clas_suelo" LIKE \'SNU%\'', parentLayerParameterName=self.P_AOI))
        self.addParameter(QgsProcessingParameterFileDestination('OUT_SHP', self.tr('Archivo Shapefile de Salida Principal'), fileFilter='ESRI Shapefile (*.shp)'))
        self.addParameter(QgsProcessingParameterBoolean('SAVE_MASK', self.tr('Guardar máscara de recorte'), defaultValue=False))
        self.addParameter(QgsProcessingParameterFileDestination('OUT_MASK', self.tr('Salida para la capa de máscara'), fileFilter='ESRI Shapefile (*.shp)', optional=True))
        if self.shared_path_config['cache'] or self.shared_path_config['styles']:
            if self.shared_path_config['cache']: self.addParameter(QgsProcessingParameterBoolean(self.P_USE_CACHE, self.tr('Usar y validar caché de equipo'), defaultValue=True))
            if self.shared_path_config['styles']: self.addParameter(QgsProcessingParameterFile(self.P_APPLY_STYLE, self.tr('Aplicar/Guardar archivo de estilo (.qml)'), extension='qml', optional=True))
        self.addParameter(QgsProcessingParameterBoolean('LOAD_IN_PROJECT', self.tr('Cargar capas resultantes al proyecto'), defaultValue=True))
    
    def processAlgorithm(self, parameters, context, feedback):
        wfs_base = self.parameterAsString(parameters, self.P_WFS_URL, context).strip()
        typenames_str = self.parameterAsString(parameters, self.P_TYPENAMES, context).strip()
        aoi_layer = self.parameterAsVectorLayer(parameters, self.P_AOI, context)
        format_index = self.parameterAsEnum(parameters, self.P_FORMAT, context)
        use_cache = self.parameterAsBool(parameters, self.P_USE_CACHE, context) if self.parameterDefinition(self.P_USE_CACHE) else False
        style_path_manual = self.parameterAsString(parameters, self.P_APPLY_STYLE, context) if self.parameterDefinition(self.P_APPLY_STYLE) else ''
        if not aoi_layer: raise QgsProcessingException(self.tr("Se requiere una capa AOI."))
        if not typenames_str: raise QgsProcessingException(self.tr('Debes indicar al menos un typeName.'))
        srs = self.parameterAsCrs(parameters, 'SRS', context); buffer_m = self.parameterAsDouble(parameters, 'BUFFER_M', context)
        recorte_mode = self.parameterAsEnum(parameters, 'RECORTE_MODE', context); round_corners = self.parameterAsBool(parameters, 'ROUND_CORNERS', context)
        save_mask = self.parameterAsBool(parameters, 'SAVE_MASK', context); out_mask_path = self.parameterAsFileOutput(parameters, 'OUT_MASK', context)
        filtro_on = self.parameterAsBool(parameters, 'FILTRO_ON', context); filtro_expr = self.parameterAsString(parameters, 'FILTRO_EXPR', context)
        out_shp_base = self.parameterAsFileOutput(parameters, 'OUT_SHP', context); load_project = self.parameterAsBool(parameters, 'LOAD_IN_PROJECT', context)
        typenames = [t.strip() for t in typenames_str.split(',') if t.strip()]
        feedback.pushInfo(self.tr('1. Creando máscara de recorte...'))
        reprojected_aoi = processing.run("native:reprojectlayer", { 'INPUT': aoi_layer, 'TARGET_CRS': srs, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
        mask_layer = None
        if recorte_mode == 0 and not round_corners:
            extent_layer = processing.run("native:polygonfromlayerextent", { 'INPUT': reprojected_aoi, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
            rect = extent_layer.extent(); xmin, ymin, xmax, ymax = rect.xMinimum() - buffer_m, rect.yMinimum() - buffer_m, rect.xMaximum() + buffer_m, rect.yMaximum() + buffer_m
            wkt = f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
            mask_layer = QgsVectorLayer(f"Polygon?crs={srs.authid()}", "Mascara_Recta", "memory")
            feat = QgsFeature(); feat.setGeometry(QgsGeometry.fromWkt(wkt)); mask_layer.dataProvider().addFeatures([feat])
        else:
            source_for_buffer = reprojected_aoi
            if recorte_mode == 0: source_for_buffer = processing.run("native:polygonfromlayerextent", { 'INPUT': reprojected_aoi, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
            else: source_for_buffer = processing.run("native:dissolve", { 'INPUT': reprojected_aoi, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
            buffer_params = { 'INPUT': source_for_buffer, 'DISTANCE': buffer_m, 'SEGMENTS': 5, 'DISSOLVE': True, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }
            if round_corners: buffer_params.update({'JOIN_STYLE': 1, 'END_CAP_STYLE': 0})
            else: buffer_params.update({'JOIN_STYLE': 0, 'END_CAP_STYLE': 2, 'MITER_LIMIT': 5.0})
            mask_layer = processing.run("native:buffer", buffer_params, context=context, feedback=feedback)['OUTPUT']
        if save_mask and out_mask_path:
            processing.run("gdal:convertformat", { 'INPUT': mask_layer, 'OUTPUT': out_mask_path }, context=context, feedback=feedback)
            if load_project: QgsProject.instance().addMapLayer(QgsVectorLayer(out_mask_path, 'Mascara_Guardada', 'ogr'))
        saved_any = False
        for tn in typenames:
            feedback.pushInfo(self.tr(f'\n--- Procesando typeName: {tn} ---'))
            downloaded_layer = None; cache_folder = self.shared_path_config.get('cache'); layer_name_in_cache = tn.replace(':', '_').replace('.', '_')
            cache_gpkg_path = os.path.join(cache_folder, 'wfs_cache.gpkg') if cache_folder else ''
            format_map = { 0: 'shape-zip', 1: 'application/gml+xml; version=3.2', 2: 'application/json', 3: 'application/geopackage+sqlite3' }
            format_value = format_map.get(format_index, 'shape-zip')
            if use_cache and os.path.exists(cache_gpkg_path) and not self._is_cache_stale(wfs_base, tn, format_value, feedback):
                cached_layer = QgsVectorLayer(f"{cache_gpkg_path}|layername={layer_name_in_cache}", "cached_layer", "ogr")
                if cached_layer.isValid(): downloaded_layer = cached_layer
            if not downloaded_layer:
                downloaded_layer, response_headers = self._download_and_load_wfs(wfs_base, tn, srs, format_index, feedback)
                if not downloaded_layer: continue
                if use_cache and cache_gpkg_path:
                    feedback.pushInfo("Guardando/Actualizando capa en la caché del equipo...")
                    processing.run("gdal:convertformat", { 'INPUT': downloaded_layer, 'OUTPUT': cache_gpkg_path, 'OPTIONS': f'-lco OVERWRITE=YES -nln {layer_name_in_cache}' }, context=context, feedback=feedback)
                    self._update_cache_manifest(tn, response_headers)
            feedback.pushInfo(self.tr('2a. Asignando CRS...')); assigned_crs_layer = processing.run("native:assignprojection", { 'INPUT': downloaded_layer, 'CRS': srs, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
            feedback.pushInfo(self.tr('2b. Reparando geometrías...')); fixed_data = processing.run("native:fixgeometries", {'INPUT': assigned_crs_layer, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT}, context=context, feedback=feedback)['OUTPUT']
            feedback.pushInfo(self.tr('2c. Creando índice espacial...')); processing.run("native:createspatialindex", {'INPUT': fixed_data}, context=context, feedback=feedback)
            feedback.pushInfo(self.tr('3. Recortando datos...')); clipped_layer = processing.run("native:clip", { 'INPUT': fixed_data, 'OVERLAY': mask_layer, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
            if clipped_layer.featureCount() == 0: continue
            final_layer = clipped_layer
            if filtro_on and filtro_expr:
                feedback.pushInfo(self.tr('4. Aplicando filtro...')); final_layer = processing.run("native:extractbyexpression", { 'INPUT': clipped_layer, 'EXPRESSION': filtro_expr, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT }, context=context, feedback=feedback)['OUTPUT']
                if final_layer.featureCount() == 0: continue
            feedback.pushInfo(self.tr('5. Guardando resultado...'))
            save_path = out_shp_base;
            if len(typenames) > 1: base, ext = os.path.splitext(out_shp_base); clean_tn = tn.replace(':', '_').replace('.', '_'); save_path = f"{base}_{clean_tn}{ext}"
            processing.run("gdal:convertformat", { 'INPUT': final_layer, 'OUTPUT': save_path }, context=context, feedback=feedback)
            saved_any = True
            if load_project and os.path.exists(save_path):
                result_layer = QgsVectorLayer(save_path, os.path.basename(save_path), 'ogr')
                result_layer.setCustomProperty("wfs_typeName", tn); result_layer.setCustomProperty("wfs_url", wfs_base)
                styles_folder = self.shared_path_config.get('styles'); clean_tn_style = tn.replace(':', '_').replace('.', '_')
                style_path_auto = os.path.join(styles_folder, f"{clean_tn_style}.qml") if styles_folder else ''
                if style_path_manual and os.path.exists(style_path_manual):
                    feedback.pushInfo(f"Aplicando estilo manual: {os.path.basename(style_path_manual)}")
                    result_layer.loadNamedStyle(style_path_manual)
                    if styles_folder and not os.path.exists(style_path_auto):
                        try: shutil.copy(style_path_manual, style_path_auto); feedback.pushInfo(f"Estilo guardado en carpeta compartida como '{os.path.basename(style_path_auto)}'.")
                        except Exception as e: feedback.reportError(f"No se pudo guardar el estilo: {e}")
                elif os.path.exists(style_path_auto):
                    feedback.pushInfo(f"Aplicando estilo automático: {os.path.basename(style_path_auto)}")
                    result_layer.loadNamedStyle(style_path_auto)
                result_layer.triggerRepaint(); QgsProject.instance().addMapLayer(result_layer)
        if not saved_any: feedback.reportError(self.tr('Proceso finalizado, pero no se guardó ninguna capa.'))
        return {'OUT_SHP': out_shp_base}

    def _http_get(self, url, timeout=90):
        headers = { 'User-Agent': 'QGIS-PyQGIS/V65', 'Accept': '*/*' }; r = requests.get(url, headers=headers, stream=True, timeout=timeout, allow_redirects=True); r.raise_for_status(); return r

    def _write_stream_with_progress(self, resp, out_path, feedback):
        chunk_size, total_dl, mb_marker = 8192, 0, 0
        with open(out_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk: f.write(chunk); total_dl += len(chunk)
                if total_dl // (5 * 1024 * 1024) > mb_marker: mb_marker = total_dl // (5 * 1024 * 1024); feedback.pushInfo(f"... {mb_marker * 5} MB descargados ...")
        return total_dl, resp.headers
    
    def _download_and_load_wfs(self, base_url, typename, srs, format_index, feedback):
        format_map = { 0: ('SHP (shape-zip)', 'shape-zip', 'zip'), 1: ('GML', 'application/gml+xml; version=3.2', 'gml'), 2: ('GeoJSON', 'application/json', 'json'), 3: ('GeoPackage', 'application/geopackage+sqlite3', 'gpkg') }
        label, output_format, extension = format_map.get(format_index, format_map[0])
        base_params = { 'service': 'WFS', 'version': '1.1.0', 'request': 'GetFeature', 'typeName': typename, 'srsName': srs.authid(), 'outputFormat': output_format }
        url = f"{base_url.split('?')[0]}?{urllib.parse.urlencode(base_params)}"
        tmp_dir = tempfile.mkdtemp(prefix='icv_v65_')
        out_file = os.path.join(tmp_dir, f"download.{extension}")
        response_headers = {}
        try:
            feedback.pushInfo(self.tr(f"Descargando capa en formato {label}..."))
            r = self._http_get(url); size, response_headers = self._write_stream_with_progress(r, out_file, feedback)
            if size < 2048: feedback.reportError(self.tr(f"Respuesta demasiado pequeña ({size} bytes).")); return None, None
            feedback.pushInfo(self.tr(f"Descarga finalizada ({round(size/1024/1024,2)} MB)"))
        except Exception as e: feedback.reportError(self.tr(f"Fallo en la descarga: {e}")); return None, None
        if extension == 'zip':
            out_folder = os.path.join(tmp_dir, 'unzipped'); os.makedirs(out_folder, exist_ok=True)
            try:
                with zipfile.ZipFile(out_file, 'r') as zf: zf.extractall(out_folder)
            except zipfile.BadZipFile: feedback.reportError("El archivo descargado no es un ZIP válido."); return None, None
            for fn in os.listdir(out_folder):
                if fn.lower().endswith('.shp'):
                    shp_path = os.path.join(out_folder, fn)
                    layer = QgsVectorLayer(shp_path, os.path.basename(shp_path), 'ogr')
                    if layer.isValid(): return layer, response_headers
            feedback.reportError("El ZIP no contenía un archivo .shp válido."); return None, None
        else:
            layer = QgsVectorLayer(out_file, typename, "ogr")
            if layer.isValid(): return layer, response_headers
            else: feedback.reportError(f"El archivo {extension.upper()} no es una capa vectorial válida."); return None, None

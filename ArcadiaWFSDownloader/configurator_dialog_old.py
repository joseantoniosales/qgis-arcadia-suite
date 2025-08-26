# -*- coding: utf-8 -*-
import os
import configparser
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QFileDialog
)
from qgis.PyQt.QtCore import Qt
from .settings_utils import get_settings_file_path

class ConfiguratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurador de Arcadia WFS Downloader")
        self.setMinimumWidth(600)
        
        # Crear el diseño principal
        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Campos de entrada
        self.config_path_edit = QLineEdit(self)
        self.styles_path_edit = QLineEdit(self)
        self.cache_path_edit = QLineEdit(self)
        
        # Botones para explorar
        config_browse = QPushButton("Explorar...", self)
        styles_browse = QPushButton("Explorar...", self)
        cache_browse = QPushButton("Explorar...", self)
        
        # Conectar eventos de los botones
        config_browse.clicked.connect(lambda: self.browse_folder(self.config_path_edit))
        styles_browse.clicked.connect(lambda: self.browse_folder(self.styles_path_edit))
        cache_browse.clicked.connect(lambda: self.browse_folder(self.cache_path_edit))
        
        # Añadir widgets al diseño
        layout.addRow("Carpeta de Configuración:", self.config_path_edit)
        layout.addWidget(config_browse)
        layout.addRow("Carpeta de Estilos:", self.styles_path_edit)
        layout.addWidget(styles_browse)
        layout.addRow("Carpeta de Caché:", self.cache_path_edit)
        layout.addWidget(cache_browse)
        
        # Botones OK/Cancelar
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Cargar configuración actual
        self.load_settings()
    
    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", line_edit.text())
        if folder:
            line_edit.setText(folder)
    
    def load_settings(self):
        config = configparser.ConfigParser()
        settings_file = get_settings_file_path()
        local_path = os.path.dirname(os.path.realpath(__file__))
        
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            self.config_path_edit.setText(config.get('Workgroup', 'ConfigPath', fallback=local_path))
            self.styles_path_edit.setText(config.get('Workgroup', 'StylesPath', fallback=local_path))
            self.cache_path_edit.setText(config.get('Workgroup', 'CachePath', fallback=local_path))
        else:
            self.config_path_edit.setText(local_path)
            self.styles_path_edit.setText(local_path)
            self.cache_path_edit.setText(local_path)
    
    def save_settings(self):
        config = configparser.ConfigParser()
        config['Workgroup'] = {
            'ConfigPath': self.config_path_edit.text().strip(),
            'StylesPath': self.styles_path_edit.text().strip(),
            'CachePath': self.cache_path_edit.text().strip()
        }
        
        settings_file = get_settings_file_path()
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                config.write(f)
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración:\n{e}")

class WFSEditDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir/Editar Servidor WFS")
        self.setMinimumWidth(600)
        layout = QFormLayout(self); layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.name_edit = QLineEdit(self); self.url_edit = QLineEdit(self)
        self.typenames_edit = QLineEdit(self); self.format_combo = QComboBox(self)
        self.format_options = ['Automático (SHP por defecto)', 'SHP (shape-zip)', 'GML', 'GeoJSON', 'GeoPackage']
        self.format_combo.addItems(self.format_options)
        typenames_layout = QHBoxLayout(); typenames_layout.addWidget(self.typenames_edit)
        detect_button = QPushButton("Detectar TypeNames y Formatos", self)
        typenames_layout.addWidget(detect_button)
        layout.addRow("Nombre Descriptivo:", self.name_edit); layout.addRow("URL Base:", self.url_edit)
        layout.addRow("TypeNames (detectados o manuales):", typenames_layout)
        layout.addRow("Formato Preferido:", self.format_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        detect_button.clicked.connect(self.detect_all)
        if data:
            self.name_edit.setText(data.get('name', ''))
            self.url_edit.setText(data.get('url', ''))
            self.typenames_edit.setText(data.get('typenames', ''))
            saved_format = data.get('format', self.format_options[0])
            if saved_format in self.format_options: self.format_combo.setCurrentText(saved_format)

    def get_data(self):
        raw_url = self.url_edit.text().strip(); clean_url = raw_url.split('?')[0]
        return { 'name': self.name_edit.text().strip(), 'url': clean_url, 'typenames': self.typenames_edit.text().strip(), 'format': self.format_combo.currentText() }

    def detect_all(self):
        url = self.url_edit.text().strip()
        if not url: QMessageBox.warning(self, "URL Vacía", "Introduce una URL base."); return
        self.progress_dialog = QProgressDialog("Conectando y analizando...", "Cancelar", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal); self.progress_dialog.show()
        network_manager = QgsNetworkAccessManager.instance()
        request = QNetworkRequest(QUrl(f"{url.split('?')[0]}?service=WFS&request=GetCapabilities"))
        reply = network_manager.get(request)
        self.progress_dialog.canceled.connect(reply.abort)
        reply.finished.connect(lambda: self.handle_network_reply(reply))

    def handle_network_reply(self, reply):
        self.progress_dialog.close()
        if reply.error() != 0:
            if reply.error() != 6: QMessageBox.critical(self, "Fallo de Conexión", f"No se pudo conectar:\n{reply.errorString()}")
            reply.deleteLater(); return
        try:
            content = reply.readAll(); root = ET.fromstring(content)
            namespaces = {'wfs': 'http://www.opengis.net/wfs/2.0', 'ows': 'http://www.opengis.net/ows/1.1'}
            feature_types = root.findall('.//wfs:FeatureType', namespaces)
            if not feature_types:
                namespaces = {'wfs': 'http://www.opengis.net/wfs', 'ows': 'http://www.opengis.net/ows'}
                feature_types = root.findall('.//wfs:FeatureType', namespaces)
            names = sorted([ft.find('wfs:Name', namespaces).text.strip() for ft in feature_types if ft.find('wfs:Name', namespaces) is not None])
            if not names: QMessageBox.warning(self, "Sin Resultados", "Conexión OK pero no se encontraron typeNames."); return
            self.typenames_edit.setText(",".join(names))
            first_ft = feature_types[0]; formats_xml = first_ft.findall('wfs:OutputFormats/wfs:Format', namespaces)
            if not formats_xml: formats_xml = root.findall('.//ows:Parameter[@name="outputFormat"]/ows:Value', namespaces)
            supported_formats = {fmt.text.lower() for fmt in formats_xml}
            best_format = 'Automático (SHP por defecto)'
            format_map = { 'geopackage': 'GeoPackage', 'shape-zip': 'SHP (shape-zip)', 'geojson': 'GeoJSON', 'gml': 'GML' }
            priority = ['geopackage', 'shape-zip', 'geojson', 'gml']
            for key in priority:
                if any(key in s for s in supported_formats): best_format = format_map[key]; break
            if best_format in self.format_options: self.format_combo.setCurrentText(best_format)
            size_info = self.estimate_download_size(names[0])
            QMessageBox.information(self, "Éxito", f"Se detectaron {len(names)} capas.\n\nFormato preferido: {best_format}\nTamaño estimado (1ª capa): {size_info}")
        except Exception as e: QMessageBox.critical(self, "Error de Procesamiento", f"No se pudo procesar la respuesta del servidor:\n{e}")
        finally: reply.deleteLater()

    def estimate_download_size(self, typename):
        try:
            base_url = self.url_edit.text().strip().split('?')[0]
            format_value = "application/geopackage+sqlite3"
            params = { 'service': 'WFS', 'version': '1.1.0', 'request': 'GetFeature', 'typeName': typename, 'outputFormat': format_value }
            url = f"{base_url}?{'&'.join([f'{k}={v}' for k,v in params.items()])}"
            headers = {'User-Agent': 'ArcadiaSuite-SourceManager/1.0'}
            response = requests.head(url, headers=headers, timeout=15, allow_redirects=True); response.raise_for_status()
            size_in_bytes = response.headers.get('Content-Length')
            if size_in_bytes: return f"{round(int(size_in_bytes) / (1024 * 1024), 2)} MB"
            return "No disponible"
        except Exception: return "No disponible"

class WFSSourceManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrador de Fuentes WFS")
        self.setMinimumSize(800, 500)
        self.config_path, self.styles_path, self.cache_path = self._get_paths()
        self.dat_file_path = os.path.join(self.config_path, 'wfs_servers.dat')
        self.sources = []
        self.current_update_index = 0
        self.progress_dialog = None
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4, self); self.table.setHorizontalHeaderLabels(["Nombre", "URL Base", "TypeNames Sugeridos", "Formato Preferido"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        add_button = QPushButton("Añadir...", self); edit_button = QPushButton("Editar...", self); delete_button = QPushButton("Eliminar", self)
        update_cache_button = QPushButton("Actualizar Caché", self)
        button_layout.addWidget(add_button); button_layout.addWidget(edit_button); button_layout.addWidget(delete_button)
        button_layout.addStretch(); button_layout.addWidget(update_cache_button)
        layout.addLayout(button_layout)
        adv_button_layout = QHBoxLayout()
        import_button = QPushButton("Importar...", self); export_button = QPushButton("Exportar...", self)
        open_styles_button = QPushButton("Abrir Carpeta de Estilos", self)
        adv_button_layout.addWidget(import_button); adv_button_layout.addWidget(export_button)
        adv_button_layout.addStretch(); adv_button_layout.addWidget(open_styles_button)
        layout.addLayout(adv_button_layout)
        main_buttons_layout = QHBoxLayout()
        about_button = QPushButton("Acerca de...", self)
        main_buttons_layout.addWidget(about_button); main_buttons_layout.addStretch()
        close_button_box = QDialogButtonBox(QDialogButtonBox.Close, self)
        main_buttons_layout.addWidget(close_button_box)
        layout.addLayout(main_buttons_layout)
        add_button.clicked.connect(self.add_source); edit_button.clicked.connect(self.edit_source)
        delete_button.clicked.connect(self.delete_source); update_cache_button.clicked.connect(self.update_cache)
        import_button.clicked.connect(self.import_sources); export_button.clicked.connect(self.export_sources)
        open_styles_button.clicked.connect(self.open_styles_folder)
        about_button.clicked.connect(self.show_about_dialog); close_button_box.rejected.connect(self.reject)
        self.load_sources()

    def _get_paths(self):
        config = configparser.ConfigParser(); settings_file = get_settings_file_path()
        local_path = os.path.dirname(os.path.realpath(__file__))
        config_path, styles_path, cache_path = local_path, local_path, local_path
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            config_path = config.get('Workgroup', 'ConfigPath', fallback=local_path).strip() or local_path
            styles_path = config.get('Workgroup', 'StylesPath', fallback=local_path).strip() or local_path
            cache_path = config.get('Workgroup', 'CachePath', fallback=local_path).strip() or local_path
        return config_path, styles_path, cache_path

    def load_sources(self, path=None):
        self.sources = []; file_to_load = path if path else self.dat_file_path
        if not os.path.exists(file_to_load): return
        try:
            with open(file_to_load, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        self.sources.append({ 'name': parts[0].strip(), 'url': parts[1].strip(), 'typenames': parts[2].strip() if len(parts) > 2 else '', 'format': parts[3].strip() if len(parts) > 3 else 'Automático (SHP por defecto)'})
            self.populate_table()
        except Exception as e: QMessageBox.critical(self, "Error de Lectura", f"No se pudo leer '{file_to_load}':\n{e}")

    def save_sources(self, path=None):
        file_to_save = path if path else self.dat_file_path
        try:
            with open(file_to_save, 'w', encoding='utf-8') as f:
                f.write("# Formato: Nombre (TAB) URL Base (TAB) TypeNames (TAB) Formato Preferido\n")
                for source in self.sources: f.write(f"{source['name']}\t{source['url']}\t{source['typenames']}\t{source['format']}\n")
            QMessageBox.information(self, "Guardado", f"Cambios guardados en:\n{os.path.basename(file_to_save)}")
        except Exception as e: QMessageBox.critical(self, "Error de Guardado", f"No se pudo escribir en '{file_to_save}':\n{e}")

    def import_sources(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar archivo de servidores", "", "Archivos DAT (*.dat);;Todos los archivos (*)")
        if path: self.load_sources(path); self.save_sources()

    def export_sources(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar archivo de servidores", "wfs_servers_backup.dat", "Archivos DAT (*.dat);;Todos los archivos (*)")
        if path: self.save_sources(path)

    def open_styles_folder(self):
        if self.styles_path and os.path.isdir(self.styles_path): webbrowser.open(os.path.realpath(self.styles_path))
        else: QMessageBox.warning(self, "Ruta no Definida", "La carpeta de estilos no está configurada o no es válida.")

    def populate_table(self):
        self.table.setRowCount(0)
        for i, source in enumerate(self.sources):
            self.table.insertRow(i); self.table.setItem(i, 0, QTableWidgetItem(source['name'])); self.table.setItem(i, 1, QTableWidgetItem(source['url']))
            self.table.setItem(i, 2, QTableWidgetItem(source['typenames'])); self.table.setItem(i, 3, QTableWidgetItem(source['format']))
        self.table.resizeColumnsToContents(); self.table.horizontalHeader().setStretchLastSection(True)

    def add_source(self):
        dialog = WFSEditDialog(self)
        if dialog.exec_():
            new_data = dialog.get_data()
            if new_data['name'] and new_data['url']: self.sources.append(new_data); self.populate_table(); self.save_sources()
            else: QMessageBox.warning(self, "Datos Incompletos", "El Nombre y la URL no pueden estar vacíos.")

    def edit_source(self):
        current_row = self.table.currentRow()
        if current_row < 0: return
        dialog = WFSEditDialog(self, data=self.sources[current_row])
        if dialog.exec_():
            updated_data = dialog.get_data()
            if updated_data['name'] and updated_data['url']: self.sources[current_row] = updated_data; self.populate_table(); self.save_sources()
            else: QMessageBox.warning(self, "Datos Incompletos", "El Nombre y la URL no pueden estar vacíos.")
    
    def delete_source(self):
        current_row = self.table.currentRow()
        if current_row < 0: return
        reply = QMessageBox.question(self, "Confirmar", f"¿Seguro que quieres eliminar '{self.sources[current_row]['name']}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes: del self.sources[current_row]; self.populate_table(); self.save_sources()

    def test_connection(self):
        current_row = self.table.currentRow()
        if current_row < 0: QMessageBox.information(self, "Sin Selección", "Selecciona un servidor para probar."); return
        temp_dialog = WFSEditDialog(self, data=self.sources[current_row]); temp_dialog.detect_all()
        
    def show_about_dialog(self): AboutDialog(self).exec_()
    
    def update_cache(self):
        current_row = self.table.currentRow()
        if current_row < 0: QMessageBox.information(self, "Sin Selección", "Selecciona un servidor para actualizar su caché."); return
        if not self.cache_path or not os.path.isdir(self.cache_path): QMessageBox.warning(self, "Ruta no Definida", "La carpeta de caché no está configurada o no es válida."); return
        source = self.sources[current_row]
        self.typenames_to_cache = [tn.strip() for tn in source['typenames'].split(',') if tn.strip()]
        if not self.typenames_to_cache: QMessageBox.warning(self, "Sin Capas", "El servidor no tiene typeNames definidos."); return
        reply = QMessageBox.question(self, "Confirmar", f"Se descargarán/actualizarán {len(self.typenames_to_cache)} capa(s) en la caché. El proceso puede tardar.\n\n¿Quieres continuar?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No: return
        self.cache_progress = QProgressDialog(f"Actualizando caché para {source['name']}...", "Cancelar", 0, len(self.typenames_to_cache), self)
        self.cache_progress.setWindowModality(Qt.WindowModal); self.cache_progress.show()
        self.current_cache_index = 0; self.cache_source = source
        self._process_next_cache_layer()

    def _process_next_cache_layer(self):
        if self.current_cache_index >= len(self.typenames_to_cache) or self.cache_progress.wasCanceled():
            self.cache_progress.close(); QMessageBox.information(self, "Finalizado", "Actualización de caché completada."); self.save_sources(); return
        typename = self.typenames_to_cache[self.current_cache_index]
        self.cache_progress.setValue(self.current_cache_index); self.cache_progress.setLabelText(f"Descargando: {typename}")
        self._download_layer_for_cache(self.cache_source, typename)
    
    def _download_layer_for_cache(self, source, typename):
        try:
            format_map = {'SHP (shape-zip)': 'shape-zip', 'GML': 'application/gml+xml; version=3.2', 'GeoJSON': 'application/json', 'GeoPackage': 'application/geopackage+sqlite3'}
            output_format = format_map.get(source.get('format', 'GeoPackage'), 'application/geopackage+sqlite3')
            extension = 'gpkg' if 'geopackage' in output_format else 'zip' if 'zip' in output_format else 'gml' if 'gml' in output_format else 'json'
            params = { 'service': 'WFS', 'version': '1.1.0', 'request': 'GetFeature', 'typeName': typename, 'outputFormat': output_format }
            url = f"{source['url'].split('?')[0]}?{urllib.parse.urlencode(params)}"
            headers = {'User-Agent': 'ArcadiaSuite-CacheManager/1.0'}
            response = requests.get(url, headers=headers, timeout=300, stream=True); response.raise_for_status()
            temp_file = os.path.join(tempfile.gettempdir(), f"cache_download.{extension}")
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            cache_gpkg_path = os.path.join(self.cache_path, 'wfs_cache.gpkg')
            layer_name_in_cache = typename.replace(':', '_').replace('.', '_')
            processing.run("gdal:convertformat", { 'INPUT': temp_file, 'OUTPUT': cache_gpkg_path, 'OPTIONS': f'-lco OVERWRITE=YES -nln {layer_name_in_cache}' }, is_child_algorithm=False)
            etag = response.headers.get('ETag'); last_modified = response.headers.get('Last-Modified')
            self._update_cache_manifest(typename, etag, last_modified)
        except Exception as e:
            print(f"Fallo al cachear {typename}: {e}")
        self.current_cache_index += 1
        QTimer.singleShot(1000, self._process_next_cache_layer)

    def _update_cache_manifest(self, typename, etag, last_modified):
        manifest_path = os.path.join(self.cache_path, 'wfs_cache_manifest.json')
        manifest = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f: manifest = json.load(f)
        manifest[typename] = {'etag': etag, 'last_modified': last_modified, 'cached_at': datetime.now(timezone.utc).isoformat()}
        with open(manifest_path, 'w') as f: json.dump(manifest, f, indent=4)
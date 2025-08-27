# -*- coding: utf-8 -*-
import os
import configparser
import os
from .settings_utils import get_wfs_servers_path
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QPushButton, QDialogButtonBox, QMessageBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsApplication
from qgis import processing
from .configurator_dialog import get_settings_file_path

class WFSLauncherDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lanzador WFS")
        self.setMinimumWidth(400)
        self.sources = []
        self.dat_file_path = get_wfs_servers_path()
        self.load_sources()

    def _get_work_path(self):
        config = configparser.ConfigParser()
        settings_file = get_settings_file_path()
        work_path = os.path.dirname(os.path.realpath(__file__))
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            config_path = config.get('Workgroup', 'ConfigPath', fallback='').strip()
            if config_path and os.path.isdir(config_path):
                return config_path
        return work_path

    def load_sources(self):
        if not os.path.exists(self.dat_file_path):
            QMessageBox.critical(self, "Archivo no Encontrado", f"No se encontró 'wfs_servers.dat' en:\n{self.dat_file_path}")
            return
        try:
            with open(self.dat_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        source = {
                            'name': parts[0].strip(), 'url': parts[1].strip(),
                            'typenames': parts[2].strip() if len(parts) > 2 else '',
                            'format': parts[3].strip() if len(parts) > 3 else 'Automático (SHP por defecto)'
                        }
                        self.sources.append(source)
                        self.server_list.addItem(source['name'])
        except Exception as e:
            QMessageBox.critical(self, "Error de Lectura", f"No se pudo leer el archivo:\n{e}")

    def update_typenames_list(self, row):
        self.typenames_list.clear()
        if 0 <= row < len(self.sources):
            typenames_str = self.sources[row]['typenames']
            if typenames_str:
                for tn in typenames_str.split(','):
                    item = QListWidgetItem(tn.strip(), self.typenames_list)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)

    def launch_tool(self):
        current_row = self.server_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona un servidor de la lista.")
            return
        selected_source = self.sources[current_row]
        selected_typenames = []
        for i in range(self.typenames_list.count()):
            item = self.typenames_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_typenames.append(item.text())
        if not selected_typenames:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona al menos una capa (typeName) para descargar.")
            return
        format_map = {'SHP (shape-zip)': 0, 'GML': 1, 'GeoJSON': 2, 'GeoPackage': 3}
        preferred_format_text = selected_source.get('format', 'SHP (shape-zip)')
        format_index = format_map.get(preferred_format_text, 0)
        params = {
            'WFS_BASE_URL': selected_source['url'],
            'TYPENAMES': ",".join(selected_typenames),
            'FORMAT': format_index
        }
        tool_name = None
        target_display_name = 'Descargador WFS Avanzado' 
        for alg in QgsApplication.processingRegistry().algorithms():
            if target_display_name in alg.displayName():
                tool_name = alg.id()
                break
        if not tool_name:
            QMessageBox.critical(self, "Error", f"No se encontró el script principal '{target_display_name}'.")
            return
        self.accept()
        processing.execAlgorithmDialog(tool_name, params)

wfs_launcher_dialog = None
def run_wfs_launcher():
    global wfs_launcher_dialog
    wfs_launcher_dialog = WFSLauncherDialog(QgsApplication.activeWindow())
    wfs_launcher_dialog.show()
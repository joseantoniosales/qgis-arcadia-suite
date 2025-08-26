# -*- coding: utf-8 -*-
import configparser
import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton, QLineEdit,
    QFileDialog, QMessageBox, QLabel, QDialogButtonBox, QWidget
)
from qgis.core import QgsApplication

def get_settings_file_path():
    try:
        profile_path = QgsApplication.instance().activeUserProfilePath()
    except AttributeError:
        home = os.path.expanduser("~")
        profile_path = os.path.join(home, 'Library/Application Support/QGIS/QGIS3/profiles/default')
    return os.path.join(profile_path, 'python', 'wfs_suite_settings.ini')

class WFSConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurador de la Suite WFS")
        self.setMinimumWidth(600)
        
        layout = QFormLayout(self)
        self.config_path_edit = QLineEdit(self)
        self.styles_path_edit = QLineEdit(self)
        self.cache_path_edit = QLineEdit(self)
        
        layout.addRow(QLabel("Ruta a la carpeta de Configuración (wfs_servers.dat):"), self._create_browse_row(self.config_path_edit))
        layout.addRow(QLabel("Ruta a la carpeta de Estilos (.qml):"), self._create_browse_row(self.styles_path_edit))
        layout.addRow(QLabel("Ruta a la carpeta de Caché (wfs_cache.gpkg):"), self._create_browse_row(self.cache_path_edit))
        
        self.config_path_edit.textChanged.connect(self._suggest_paths)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        
        self.load_settings()

    def _create_browse_row(self, line_edit):
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit)
        browse_button = QPushButton("...", self)
        browse_button.setFixedWidth(40)
        browse_button.clicked.connect(lambda: self.browse_folder(line_edit))
        layout.addWidget(browse_button)
        return widget

    def _suggest_paths(self, base_path):
        if base_path and not self.styles_path_edit.text():
            self.styles_path_edit.setText(os.path.join(base_path, 'estilos'))
        if base_path and not self.cache_path_edit.text():
            self.cache_path_edit.setText(os.path.join(base_path, 'cache'))

    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "Selecciona una carpeta")
        if folder:
            line_edit.setText(folder)

    def load_settings(self):
        config = configparser.ConfigParser()
        settings_file = get_settings_file_path()
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            self.config_path_edit.setText(config.get('Workgroup', 'ConfigPath', fallback=''))
            self.styles_path_edit.setText(config.get('Workgroup', 'StylesPath', fallback=''))
            self.cache_path_edit.setText(config.get('Workgroup', 'CachePath', fallback=''))

    def save_settings(self):
        config = configparser.ConfigParser()
        config['Workgroup'] = {
            'ConfigPath': self.config_path_edit.text(),
            'StylesPath': self.styles_path_edit.text(),
            'CachePath': self.cache_path_edit.text()
        }
        try:
            with open(get_settings_file_path(), 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            QMessageBox.information(self, "Guardado", "La configuración se ha guardado.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración:\n{e}")

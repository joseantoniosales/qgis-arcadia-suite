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
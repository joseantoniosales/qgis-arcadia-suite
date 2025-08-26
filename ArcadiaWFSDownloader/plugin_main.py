# -*- coding: utf-8 -*-
"""
================================================================================
Cerebro Principal del Complemento - Arcadia Suite
================================================================================
Autor: IA y José A. Sales

Descripción:
    Este script actúa como el punto de entrada principal para QGIS. Se encarga de:
    - Registrar las herramientas de geoproceso en la Caja de Herramientas.
    - Crear el menú "Arcadia Suite" y los botones en la barra de herramientas.
    - Conectar los botones con las ventanas del Configurador y el Administrador.
"""

import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProcessingProvider

# Importamos las clases de nuestras herramientas desde los otros archivos
from .downloader_tool import AdvancedWFSDownloader_V64
from .manager_dialog import WFSSourceManager
from .configurator_dialog import WFSConfigDialog
# Importamos el lanzador para poder añadirlo también al menú
from .launcher_dialog import WFSLauncherDialog

class ArcadiaSuitePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []
        self.menu = self.tr("&Arcadia Suite")
        self.toolbar = self.iface.addToolBar("Arcadia Suite Toolbar")
        self.toolbar.setObjectName("ArcadiaSuiteToolbar")
        
        # Variables para mantener las ventanas vivas
        self.manager_dialog = None
        self.config_dialog = None
        self.launcher_dialog = None

    def tr(self, message):
        return QCoreApplication.translate("ArcadiaSuitePlugin", message)

    def initGui(self):
        # 1. Registrar el algoritmo de geoproceso en la Caja de Herramientas
        self.provider = WFSProcessingProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        # 2. Crear los botones para el menú y la barra de herramientas
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        
        # Acción para el Lanzador de Descargas
        launcher_action = QAction(QIcon(icon_path), "Lanzador de Descargas WFS", self.iface.mainWindow())
        launcher_action.triggered.connect(self.run_launcher)
        
        # Acción para el Administrador de Fuentes
        manager_action = QAction("Administrador de Fuentes WFS...", self.iface.mainWindow())
        manager_action.triggered.connect(self.run_source_manager)

        # Acción para el Configurador
        config_action = QAction("Configurar Suite...", self.iface.mainWindow())
        config_action.triggered.connect(self.run_configurator)
        
        # Añadir a la barra de herramientas y crear un menú propio
        self.toolbar.addAction(launcher_action)
        self.iface.addPluginToMenu(self.menu, launcher_action)
        self.iface.addPluginToMenu(self.menu, manager_action)
        self.iface.addPluginToMenu(self.menu, config_action)
        
        self.actions.extend([launcher_action, manager_action, config_action])

    def unload(self):
        # Limpieza al desactivar el complemento
        QgsApplication.processingRegistry().removeProvider(self.provider)
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
        del self.toolbar

    def run_launcher(self):
        self.launcher_dialog = WFSLauncherDialog(self.iface.mainWindow())
        self.launcher_dialog.show()

    def run_source_manager(self):
        self.manager_dialog = WFSSourceManager(self.iface.mainWindow())
        self.manager_dialog.exec_()

    def run_configurator(self):
        self.config_dialog = WFSConfigDialog(self.iface.mainWindow())
        self.config_dialog.exec_()

# Clase para que el descargador aparezca en la Caja de Herramientas
class WFSProcessingProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()

    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(AdvancedWFSDownloader_V64())
        # Aquí podrías añadir también el 'wfs_batch_processor.py' si lo creas

    def id(self, *args, **kwargs):
        return 'arcadia_suite_provider'

    def name(self, *args, **kwargs):
        return 'Arcadia Suite'

    def longName(self, *args, **kwargs):
        return self.name()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.svg'))

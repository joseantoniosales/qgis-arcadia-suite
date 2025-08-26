# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProcessingProvider

# --- IMPORTACIONES CORREGIDAS ---
# Se usan los nombres de clase correctos de cada archivo
from .downloader_tool import WFSDownloaderTool
from .manager_dialog import WFSSourceManager
from .configurator_dialog import WFSConfigDialog

class ArcadiaSuitePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []
        self.menu = QCoreApplication.translate("ArcadiaSuitePlugin", "&Arcadia Suite")
        self.toolbar = self.iface.addToolBar("Arcadia Suite Toolbar")
        self.toolbar.setObjectName("ArcadiaSuiteToolbar")
        
        self.manager_dialog = None
        self.config_dialog = None

    def initGui(self):
        self.provider = WFSProcessingProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        
        # Acción para el Administrador de Fuentes (ahora es el lanzador principal)
        manager_action = QAction(QIcon(icon_path), "Administrador de Fuentes WFS", self.iface.mainWindow())
        manager_action.triggered.connect(self.run_source_manager)
        
        # Acción para el Configurador
        config_action = QAction("Configurar Suite...", self.iface.mainWindow())
        config_action.triggered.connect(self.run_configurator)
        
        self.toolbar.addAction(manager_action)
        self.iface.addPluginToMenu(self.menu, manager_action)
        self.iface.addPluginToMenu(self.menu, config_action)
        
        self.actions.extend([manager_action, config_action])

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
        del self.toolbar

    def run_source_manager(self):
        # El Administrador ahora actúa como el punto de entrada principal
        # Desde él se pueden lanzar las descargas si se implementa esa funcionalidad
        self.manager_dialog = WFSSourceManager(self.iface.mainWindow())
        self.manager_dialog.exec_()

    def run_configurator(self):
        # --- LÍNEA CORREGIDA ---
        self.config_dialog = WFSConfigDialog(self.iface.mainWindow())
        self.config_dialog.exec_()

class WFSProcessingProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()

    def loadAlgorithms(self, *args, **kwargs):
        # --- LÍNEA CORREGIDA ---
        self.addAlgorithm(WFSDownloaderTool())

    def id(self, *args, **kwargs):
        return 'arcadia_suite_provider'

    def name(self, *args, **kwargs):
        return 'Arcadia Suite'

    def longName(self, *args, **kwargs):
        return self.name()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.svg'))

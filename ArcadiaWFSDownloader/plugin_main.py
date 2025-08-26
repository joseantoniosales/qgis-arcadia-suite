# -*- coding: utf-8 -*-
"""
================================================================================
Cerebro Principal del Complemento - Arcadia Suite (Corregido)
================================================================================
Autor: IA y José A. Sales

Descripción:
    Versión que corrige un ImportError al no coincidir el nombre de la clase
    importada con la definida en el archivo de la herramienta.
"""

import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProcessingProvider

# --- IMPORTACIONES CORREGIDAS ---
# Se importa la clase con su nombre final y correcto
from .downloader_tool import AdvancedWFSDownloader_V64
from .manager_dialog import WFSSourceManager
from .configurator_dialog import ConfigDialog
from .launcher_dialog import WFSLauncherDialog

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
        self.launcher_dialog = None

    def initGui(self):
        self.provider = WFSProcessingProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        
        launcher_action = QAction(QIcon(icon_path), "Lanzador de Descargas WFS", self.iface.mainWindow())
        launcher_action.triggered.connect(self.run_launcher)
        
        manager_action = QAction("Administrador de Fuentes WFS...", self.iface.mainWindow())
        manager_action.triggered.connect(self.run_source_manager)

        config_action = QAction("Configurar Suite...", self.iface.mainWindow())
        config_action.triggered.connect(self.run_configurator)
        
        self.toolbar.addAction(launcher_action)
        self.iface.addPluginToMenu(self.menu, launcher_action)
        self.iface.addPluginToMenu(self.menu, manager_action)
        self.iface.addPluginToMenu(self.menu, config_action)
        
        self.actions.extend([launcher_action, manager_action, config_action])

    def unload(self):
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
        self.config_dialog = ConfigDialog(self.iface.mainWindow())
        self.config_dialog.exec_()

class WFSProcessingProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()

    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(AdvancedWFSDownloader_V64())

    def id(self, *args, **kwargs):
        return 'arcadia_suite_provider'

    def name(self, *args, **kwargs):
        return 'Arcadia Suite'

    def longName(self, *args, **kwargs):
        return self.name()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.svg'))

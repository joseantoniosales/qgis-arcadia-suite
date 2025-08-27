# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProcessingProvider

# Importamos los algoritmos de procesamiento y diálogos
from .downloader_tool import WFSDownloaderTool
from .manager_dialog import WFSSourceManager
from .launcher_dialog import WFSLauncherDialog
from .configurator_dialog import ConfiguratorDialog

class ArcadiaWFSDownloaderPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []
        
        # Asegurar que existan los directorios necesarios
        from .settings_utils import ensure_plugin_directories
        ensure_plugin_directories()
        
        # Definir la jerarquía de menús
        self.menu_arcadia = QCoreApplication.translate("ArcadiaSuitePlugin", "&Arcadia Suite")
        self.menu_wfs = self.menu_arcadia + "/" + QCoreApplication.translate("ArcadiaSuitePlugin", "Advanced WFS Downloader")
        
        # Crear la barra de herramientas
        self.toolbar = self.iface.addToolBar("Arcadia Suite Toolbar")
        self.toolbar.setObjectName("ArcadiaSuiteToolbar")
        
        # Variables para mantener las ventanas vivas
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

        config_action = QAction("Configurador de descarga", self.iface.mainWindow())
        config_action.triggered.connect(self.run_configurator)
        
        # Añadir acciones a la barra de herramientas
        self.toolbar.addAction(launcher_action)
        
        # Añadir acciones al menú
        self.iface.addPluginToMenu(self.menu_wfs, launcher_action)
        self.iface.addPluginToMenu(self.menu_wfs, manager_action)
        self.iface.addPluginToMenu(self.menu_wfs, config_action)
        
        # Guardar las acciones para poder eliminarlas después
        self.actions.extend([launcher_action, manager_action, config_action])

    def unload(self):
        # Eliminar el proveedor de procesamiento
        QgsApplication.processingRegistry().removeProvider(self.provider)
        
        # Eliminar las acciones del menú
        for action in self.actions:
            self.iface.removePluginMenu(self.menu_wfs, action)
        
        # Eliminar la barra de herramientas
        del self.toolbar

    def run_launcher(self):
        self.launcher_dialog = WFSLauncherDialog(self.iface.mainWindow())
        self.launcher_dialog.show()

    def run_source_manager(self):
        self.manager_dialog = WFSSourceManager(self.iface.mainWindow())
        self.manager_dialog.exec_()

    def run_configurator(self):
        self.config_dialog = ConfiguratorDialog(self.iface.mainWindow())
        self.config_dialog.exec_()

class WFSProcessingProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()
        self.downloader_tool = None
        self.launcher_tool = None
        self.manager_tool = None

    def loadAlgorithms(self, *args, **kwargs):
        # Cargar herramientas principales
        self.downloader_tool = WFSDownloaderTool()
        self.addAlgorithm(self.downloader_tool)

        # También añadimos las herramientas del menú como algoritmos
        from .launcher_launcher import WFSLauncherAlgorithm
        self.launcher_tool = WFSLauncherAlgorithm()
        self.addAlgorithm(self.launcher_tool)

    def id(self, *args, **kwargs):
        return 'arcadia_wfs_downloader'

    def name(self, *args, **kwargs):
        return 'Arcadia Suite'

    def longName(self, *args, **kwargs):
        return 'Arcadia Suite for QGIS'

    def icon(self, *args, **kwargs):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icono_wfs_64.png'))

    def groupId(self, *args, **kwargs):
        return 'arcadia_suite'

    def group(self, *args, **kwargs):
        return QCoreApplication.translate("ArcadiaSuitePlugin", "Arcadia Suite")
        
    def subGroupId(self, *args, **kwargs):
        return 'advanced_wfs_downloader'
        
    def subGroup(self, *args, **kwargs):
        return QCoreApplication.translate("ArcadiaSuitePlugin", "Advanced WFS Downloader")
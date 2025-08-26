# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterBoolean, QgsProcessingContext
from .launcher_dialog import WFSLauncherDialog

class WFSLauncherAlgorithm(QgsProcessingAlgorithm):
    def tr(self, text):
        return QCoreApplication.translate('WFSLauncherAlgorithm', text)

    def createInstance(self):
        return WFSLauncherAlgorithm()

    def name(self):
        return 'wfs_launcher'

    def displayName(self):
        return self.tr('Lanzador de Descargas WFS')

    def group(self):
        return self.tr('Arcadia Suite')

    def groupId(self):
        return 'arcadia_suite'

    def subGroup(self):
        return self.tr('Advanced WFS Downloader')

    def subGroupId(self):
        return 'advanced_wfs_downloader'

    def shortHelpString(self):
        return self.tr('Lanza el diálogo de selección de servidor WFS y capas.')

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterBoolean(
                'RUN',
                self.tr('Ejecutar Configurador de descarga'),
                defaultValue=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        iface = context.project().mainWindow()
        dialog = WFSLauncherDialog(iface)
        result = dialog.exec_()
        
        return {
            'WAS_CANCELLED': not bool(result)
        }

 # -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterBoolean, QgsProcessingContext
from .launcher_dialog import WFSLauncherDialog


class WFSLauncherAlgorithm(QgsProcessingAlgorithm):


    def tr(self, text):
        return QCoreApplication.translate('WFSLauncherAlgorithm', text)

        self.addParameter(QgsProcessingParameterBoolean('RUN', self.tr('Ejecutar Configurador de descarga'), defaultValue=True))

    def createInstance(self):
        return WFSLauncherAlgorithm()

    def name(self):
        return 'wfs_launcher'

    def displayName(self):
        return self.tr('Configurador de descarga')
    def processAlgorithm(self, parameters, context, feedback):

        iface = QgsProcessingContext.instance().mainWindow()
        dialog = WFSLauncherDialog(iface)
        dialog.exec_()

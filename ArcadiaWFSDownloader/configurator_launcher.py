# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterBoolean, QgsProcessingContext
from .configurator_dialog import WFSSourceManager

from qgis import processing

class WFSSourceManagerAlgorithm(QgsProcessingAlgorithm):


    def tr(self, text):
        return QCoreApplication.translate('WFSSourceManagerAlgorithm', text)


    def createInstance(self):
        return WFSSourceManagerAlgorithm()

    def name(self):
        return 'wfs_source_manager'

    def displayName(self):
        return self.tr('Administrador de Fuentes WFS')

    def group(self): return self.tr('Arcadia Suite')
    def groupId(self): return 'arcadia_suite'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterBoolean('RUN', self.tr('Ejecutar Administrador de Fuentes'), defaultValue=True))

    def processAlgorithm(self, parameters, context, feedback):

         iface = QgsProcessingContext.instance().mainWindow()
         dialog = WFSSourceManager(iface)
         dialog.exec_()
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterBoolean('RUN', self.tr('Ejecutar Administrador de Fuentes'), defaultValue=True))

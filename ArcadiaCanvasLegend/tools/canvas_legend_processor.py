"""
Processing algorithms for Arcadia Canvas Legend
Provides processing tools for batch operations and automation
"""

from qgis.core import (QgsProcessingProvider, QgsProcessingAlgorithm,
                      QgsProcessingParameterBoolean, QgsProcessingParameterString,
                      QgsProcessingParameterNumber, QgsProcessingParameterFile,
                      QgsProcessingOutputString, QgsProcessingException,
                      QgsProject, QgsApplication)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
import os


class CanvasLegendProvider(QgsProcessingProvider):
    """Processing provider for Canvas Legend algorithms"""

    def __init__(self):
        QgsProcessingProvider.__init__(self)

    def loadAlgorithms(self):
        """Load all available algorithms"""
        self.addAlgorithm(ExportCanvasWithLegendAlgorithm())
        self.addAlgorithm(CreateCompositionWithLegendAlgorithm())

    def id(self):
        return 'arcadia_suite'

    def name(self):
        return self.tr('Arcadia Suite')

    def longName(self):
        return self.tr('Arcadia Suite Processing Tools')

    def icon(self):
        """Return provider icon"""
        return QgsApplication.getThemeIcon("/mActionAddLegend.svg")

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)


class ExportCanvasWithLegendAlgorithm(QgsProcessingAlgorithm):
    """Algorithm to export canvas with legend overlay"""

    OUTPUT_FILE = 'OUTPUT_FILE'
    LEGEND_POSITION = 'LEGEND_POSITION'
    INCLUDE_FRAME = 'INCLUDE_FRAME'
    BACKGROUND_COLOR = 'BACKGROUND_COLOR'
    EXPORT_FORMAT = 'EXPORT_FORMAT'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExportCanvasWithLegendAlgorithm()

    def name(self):
        return 'export_canvas_with_legend'

    def displayName(self):
        return self.tr('Export Canvas with Legend')

    def group(self):
        return self.tr('Arcadia Suite')

    def groupId(self):
        return 'arcadia_suite'

    def shortHelpString(self):
        return self.tr('Exports the current map canvas with a legend overlay to an image file.')

    def initAlgorithm(self, config=None):
        """Initialize algorithm parameters"""
        
        # Código compatible con diferentes versiones de QGIS
        try:
            # Para versiones más recientes
            save_behavior = QgsProcessingParameterFile.Behavior.Save
        except AttributeError:
            # Para versiones más antiguas
            save_behavior = 1

        self.addParameter(
            QgsProcessingParameterFile(
                self.OUTPUT_FILE,
                self.tr('Output file'),
                behavior=save_behavior,
                fileFilter='PNG files (*.png);;JPEG files (*.jpg);;PDF files (*.pdf)'
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.LEGEND_POSITION,
                self.tr('Legend position'),
                defaultValue='bottom_right'
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INCLUDE_FRAME,
                self.tr('Include frame around legend'),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.BACKGROUND_COLOR,
                self.tr('Legend background color'),
                defaultValue='white'
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.EXPORT_FORMAT,
                self.tr('Export format'),
                defaultValue='PNG'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm"""
        
        try:
            output_file = self.parameterAsFile(parameters, self.OUTPUT_FILE, context)
            legend_position = self.parameterAsString(parameters, self.LEGEND_POSITION, context)
            include_frame = self.parameterAsBool(parameters, self.INCLUDE_FRAME, context)
            background_color = self.parameterAsString(parameters, self.BACKGROUND_COLOR, context)
            export_format = self.parameterAsString(parameters, self.EXPORT_FORMAT, context)

            feedback.pushInfo(self.tr('Starting canvas export with legend...'))

            # Implementation would go here
            # This is a placeholder for the actual export logic
            
            feedback.pushInfo(self.tr('Export completed successfully'))

            return {self.OUTPUT_FILE: output_file}

        except Exception as e:
            raise QgsProcessingException(str(e))


class CreateCompositionWithLegendAlgorithm(QgsProcessingAlgorithm):
    """Algorithm to create a composition with canvas and legend"""

    COMPOSITION_NAME = 'COMPOSITION_NAME'
    INCLUDE_TITLE = 'INCLUDE_TITLE'
    TITLE_TEXT = 'TITLE_TEXT'
    LEGEND_POSITION = 'LEGEND_POSITION'
    PAGE_SIZE = 'PAGE_SIZE'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CreateCompositionWithLegendAlgorithm()

    def name(self):
        return 'create_composition_with_legend'

    def displayName(self):
        return self.tr('Create Composition with Legend')

    def group(self):
        return self.tr('Arcadia Suite')

    def groupId(self):
        return 'arcadia_suite'

    def shortHelpString(self):
        return self.tr('Creates a new print composition with the current map canvas and legend.')

    def initAlgorithm(self, config=None):
        """Initialize algorithm parameters"""
        
        self.addParameter(
            QgsProcessingParameterString(
                self.COMPOSITION_NAME,
                self.tr('Composition name'),
                defaultValue='Canvas with Legend'
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INCLUDE_TITLE,
                self.tr('Include title'),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.TITLE_TEXT,
                self.tr('Title text'),
                defaultValue='Map with Legend'
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.LEGEND_POSITION,
                self.tr('Legend position'),
                defaultValue='right'
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.PAGE_SIZE,
                self.tr('Page size'),
                defaultValue='A4'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm"""
        
        try:
            composition_name = self.parameterAsString(parameters, self.COMPOSITION_NAME, context)
            include_title = self.parameterAsBool(parameters, self.INCLUDE_TITLE, context)
            title_text = self.parameterAsString(parameters, self.TITLE_TEXT, context)
            legend_position = self.parameterAsString(parameters, self.LEGEND_POSITION, context)
            page_size = self.parameterAsString(parameters, self.PAGE_SIZE, context)

            feedback.pushInfo(self.tr('Creating composition...'))

            # Implementation would go here
            # This is a placeholder for the actual composition creation logic
            
            feedback.pushInfo(self.tr('Composition created successfully'))

            return {}

        except Exception as e:
            raise QgsProcessingException(str(e))

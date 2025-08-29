"""
Main plugin class for Arcadia Canvas Legend
Handles plugin initialization, menu creation, and main functionality
"""

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.core import QgsProcessingAlgorithm, QgsApplication
import os.path

from .dialogs.canvas_legend_dialog import CanvasLegendDialog
from .tools.canvas_legend_processor import CanvasLegendProvider
from .utils import get_settings_file_path


class ArcadiaCanvasLegendPlugin:
    """QGIS Plugin Implementation for Arcadia Canvas Legend."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ArcadiaCanvasLegend_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr('&Arcadia Suite')
        
        # Keep dialog references to prevent garbage collection
        self.canvas_legend_dialog = None
        
        # Processing provider
        self.provider = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('ArcadiaCanvasLegend', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        """Add a toolbar icon to the toolbar."""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir, 'icon.svg')
        
        self.add_action(
            icon_path,
            text=self.tr('Canvas Legend Overlay'),
            callback=self.run,
            parent=self.iface.mainWindow(),
            status_tip=self.tr('Configure and display legend overlay on canvas'),
            whats_this=self.tr('Opens the Canvas Legend configuration dialog')
        )
        
        # Initialize the processing provider
        self.initProcessing()

    def initProcessing(self):
        """Create the processing provider and add algorithms."""
        try:
            self.provider = CanvasLegendProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)
        except Exception as e:
            print(f"Error initializing processing provider: {e}")

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        
        # Remove processing provider
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('&Arcadia Suite'),
                action)
            self.iface.removeToolBarIcon(action)
            
        # Clean up dialog references
        if self.canvas_legend_dialog:
            self.canvas_legend_dialog.close()
            self.canvas_legend_dialog = None

    def run(self):
        """Run method that performs all the real work"""
        try:
            # Create dialog if it doesn't exist
            if not self.canvas_legend_dialog:
                self.canvas_legend_dialog = CanvasLegendDialog(self.iface)
                
            # Show the dialog
            self.canvas_legend_dialog.show()
            
        except Exception as e:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr('Error'),
                self.tr('Error opening Canvas Legend dialog: {}').format(str(e))
            )
            print(f"Error in ArcadiaCanvasLegend.run(): {e}")

"""
Dialog for configuring canvas legend overlay
Handles all user interface interactions for legend configuration
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer, QRect
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QPushButton, QComboBox, QSpinBox, 
                                QCheckBox, QGroupBox, QTabWidget, QWidget, 
                                QSlider, QFrame, QMessageBox, QApplication, 
                                QFileDialog, QTextEdit, QLineEdit)
from qgis.PyQt.QtGui import QFont, QPixmap, QPainter, QColor
from qgis.core import (QgsProject, QgsLayoutExporter, QgsLayoutItemMap, 
                      QgsLayoutItemLegend, QgsPrintLayout, QgsLayoutPoint,
                      QgsLayoutSize, QgsUnitTypes)
from qgis.gui import QgsColorButton, QgsFontButton

import os
from ..utils import get_arcadia_setting, set_arcadia_setting


class CanvasLegendOverlay(QWidget):
    """Widget for displaying legend overlay on canvas"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.legend_items = []
        self.settings = {}
        
    def update_legend_content(self, legend_items, settings):
        """Update legend content and settings"""
        self.legend_items = legend_items
        self.settings = settings
        self.update()
        
    def paintEvent(self, event):
        """Paint the legend overlay"""
        if not self.legend_items:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background if enabled
        if self.settings.get('show_background', True):
            bg_color = QColor(self.settings.get('background_color', 'white'))
            bg_color.setAlpha(self.settings.get('background_alpha', 200))
            painter.fillRect(self.rect(), bg_color)
            
        # Draw frame if enabled
        if self.settings.get('show_frame', True):
            frame_color = QColor(self.settings.get('frame_color', 'black'))
            frame_width = self.settings.get('frame_width', 1)
            painter.setPen(frame_color)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            
        # Draw legend items
        y_offset = 10
        for item in self.legend_items:
            self.draw_legend_item(painter, item, y_offset)
            y_offset += 25  # Adjust based on item height
            
    def draw_legend_item(self, painter, item, y_offset):
        """Draw individual legend item"""
        # Simple implementation - would be expanded for real use
        painter.drawText(10, y_offset, item.get('name', 'Unknown'))


class CanvasLegendDialog(QDialog):
    """Main dialog for canvas legend configuration"""
    
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.legend_overlay = None
        
        self.setupUi()
        self.load_settings()
        self.connect_signals()
        
    def setupUi(self):
        """Set up the user interface"""
        self.setWindowTitle(self.tr('Arcadia Canvas Legend Configuration'))
        self.setMinimumSize(400, 600)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Position and Size Tab
        self.setup_position_tab()
        
        # Style Tab
        self.setup_style_tab()
        
        # Content Tab
        self.setup_content_tab()
        
        # Export Tab
        self.setup_export_tab()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton(self.tr('Preview'))
        self.apply_btn = QPushButton(self.tr('Apply'))
        self.export_btn = QPushButton(self.tr('Export'))
        self.close_btn = QPushButton(self.tr('Close'))
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def setup_position_tab(self):
        """Set up position and size configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Position group
        pos_group = QGroupBox(self.tr('Position'))
        pos_layout = QGridLayout(pos_group)
        
        pos_layout.addWidget(QLabel(self.tr('Position:')), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            self.tr('Top Left'), self.tr('Top Right'),
            self.tr('Bottom Left'), self.tr('Bottom Right'),
            self.tr('Custom')
        ])
        pos_layout.addWidget(self.position_combo, 0, 1)
        
        pos_layout.addWidget(QLabel(self.tr('X Offset:')), 1, 0)
        self.x_offset_spin = QSpinBox()
        self.x_offset_spin.setRange(-9999, 9999)
        self.x_offset_spin.setValue(10)
        pos_layout.addWidget(self.x_offset_spin, 1, 1)
        
        pos_layout.addWidget(QLabel(self.tr('Y Offset:')), 2, 0)
        self.y_offset_spin = QSpinBox()
        self.y_offset_spin.setRange(-9999, 9999)
        self.y_offset_spin.setValue(10)
        pos_layout.addWidget(self.y_offset_spin, 2, 1)
        
        layout.addWidget(pos_group)
        
        # Size group
        size_group = QGroupBox(self.tr('Size'))
        size_layout = QGridLayout(size_group)
        
        size_layout.addWidget(QLabel(self.tr('Width:')), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(50, 1000)
        self.width_spin.setValue(200)
        size_layout.addWidget(self.width_spin, 0, 1)
        
        size_layout.addWidget(QLabel(self.tr('Height:')), 1, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 1000)
        self.height_spin.setValue(300)
        size_layout.addWidget(self.height_spin, 1, 1)
        
        self.auto_size_check = QCheckBox(self.tr('Auto-size to content'))
        self.auto_size_check.setChecked(True)
        size_layout.addWidget(self.auto_size_check, 2, 0, 1, 2)
        
        layout.addWidget(size_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, self.tr('Position & Size'))
        
    def setup_style_tab(self):
        """Set up style configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Background group
        bg_group = QGroupBox(self.tr('Background'))
        bg_layout = QGridLayout(bg_group)
        
        self.show_bg_check = QCheckBox(self.tr('Show Background'))
        self.show_bg_check.setChecked(True)
        bg_layout.addWidget(self.show_bg_check, 0, 0, 1, 2)
        
        bg_layout.addWidget(QLabel(self.tr('Background Color:')), 1, 0)
        self.bg_color_btn = QgsColorButton()
        self.bg_color_btn.setColor(QColor('white'))
        bg_layout.addWidget(self.bg_color_btn, 1, 1)
        
        bg_layout.addWidget(QLabel(self.tr('Opacity:')), 2, 0)
        self.bg_opacity_slider = QSlider(Qt.Horizontal)
        self.bg_opacity_slider.setRange(0, 255)
        self.bg_opacity_slider.setValue(200)
        bg_layout.addWidget(self.bg_opacity_slider, 2, 1)
        
        layout.addWidget(bg_group)
        
        # Frame group
        frame_group = QGroupBox(self.tr('Frame'))
        frame_layout = QGridLayout(frame_group)
        
        self.show_frame_check = QCheckBox(self.tr('Show Frame'))
        self.show_frame_check.setChecked(True)
        frame_layout.addWidget(self.show_frame_check, 0, 0, 1, 2)
        
        frame_layout.addWidget(QLabel(self.tr('Frame Color:')), 1, 0)
        self.frame_color_btn = QgsColorButton()
        self.frame_color_btn.setColor(QColor('black'))
        frame_layout.addWidget(self.frame_color_btn, 1, 1)
        
        frame_layout.addWidget(QLabel(self.tr('Frame Width:')), 2, 0)
        self.frame_width_spin = QSpinBox()
        self.frame_width_spin.setRange(1, 10)
        self.frame_width_spin.setValue(1)
        frame_layout.addWidget(self.frame_width_spin, 2, 1)
        
        layout.addWidget(frame_group)
        
        # Font group
        font_group = QGroupBox(self.tr('Text Style'))
        font_layout = QGridLayout(font_group)
        
        font_layout.addWidget(QLabel(self.tr('Font:')), 0, 0)
        self.font_btn = QgsFontButton()
        font_layout.addWidget(self.font_btn, 0, 1)
        
        layout.addWidget(font_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, self.tr('Style'))
        
    def setup_content_tab(self):
        """Set up content configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title group
        title_group = QGroupBox(self.tr('Legend Title'))
        title_layout = QGridLayout(title_group)
        
        self.show_title_check = QCheckBox(self.tr('Show Title'))
        self.show_title_check.setChecked(True)
        title_layout.addWidget(self.show_title_check, 0, 0, 1, 2)
        
        title_layout.addWidget(QLabel(self.tr('Title Text:')), 1, 0)
        self.title_text = QLineEdit()
        self.title_text.setText(self.tr('Map Legend'))
        title_layout.addWidget(self.title_text, 1, 1)
        
        layout.addWidget(title_group)
        
        # Layers group
        layers_group = QGroupBox(self.tr('Layer Selection'))
        layers_layout = QVBoxLayout(layers_group)
        
        self.all_layers_check = QCheckBox(self.tr('Include all visible layers'))
        self.all_layers_check.setChecked(True)
        layers_layout.addWidget(self.all_layers_check)
        
        layout.addWidget(layers_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, self.tr('Content'))
        
    def setup_export_tab(self):
        """Set up export options tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export group
        export_group = QGroupBox(self.tr('Export Options'))
        export_layout = QVBoxLayout(export_group)
        
        self.export_clipboard_btn = QPushButton(self.tr('Copy to Clipboard'))
        self.export_png_btn = QPushButton(self.tr('Export as PNG'))
        self.create_composition_btn = QPushButton(self.tr('Create Composition'))
        
        export_layout.addWidget(self.export_clipboard_btn)
        export_layout.addWidget(self.export_png_btn)
        export_layout.addWidget(self.create_composition_btn)
        
        layout.addWidget(export_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, self.tr('Export'))
        
    def connect_signals(self):
        """Connect UI signals to slots"""
        self.preview_btn.clicked.connect(self.preview_legend)
        self.apply_btn.clicked.connect(self.apply_legend)
        self.export_btn.clicked.connect(self.export_current_view)
        self.close_btn.clicked.connect(self.close)
        
        self.export_clipboard_btn.clicked.connect(self.export_to_clipboard)
        self.export_png_btn.clicked.connect(self.export_to_png)
        self.create_composition_btn.clicked.connect(self.create_composition)
        
    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('CanvasLegendDialog', message)
        
    def load_settings(self):
        """Load settings from Arcadia Suite configuration"""
        try:
            position = get_arcadia_setting('CANVAS_LEGEND', 'default_position', 'bottom_right')
            self.position_combo.setCurrentText(position.replace('_', ' ').title())
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            
    def save_settings(self):
        """Save current settings to Arcadia Suite configuration"""
        try:
            position = self.position_combo.currentText().lower().replace(' ', '_')
            set_arcadia_setting('CANVAS_LEGEND', 'default_position', position)
                              
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def preview_legend(self):
        """Preview the legend overlay on canvas"""
        try:
            self.apply_legend()
        except Exception as e:
            QMessageBox.warning(self, self.tr('Warning'), 
                              self.tr('Error creating preview: {}').format(str(e)))
            
    def apply_legend(self):
        """Apply the legend overlay to canvas"""
        try:
            # Create or update legend overlay
            if not self.legend_overlay:
                self.legend_overlay = CanvasLegendOverlay(self.canvas)
                
            # Get current settings
            settings = self.get_current_settings()
            
            # Get legend items from current layers
            legend_items = self.get_legend_items()
            
            # Update overlay
            self.legend_overlay.update_legend_content(legend_items, settings)
            
            # Position overlay
            self.position_overlay()
            
            # Show overlay
            self.legend_overlay.show()
            
            self.save_settings()
            
        except Exception as e:
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error applying legend: {}').format(str(e)))
            
    def get_current_settings(self):
        """Get current settings from UI"""
        return {
            'position': self.position_combo.currentText(),
            'x_offset': self.x_offset_spin.value(),
            'y_offset': self.y_offset_spin.value(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'auto_size': self.auto_size_check.isChecked(),
            'show_background': self.show_bg_check.isChecked(),
            'background_color': self.bg_color_btn.color().name(),
            'background_alpha': self.bg_opacity_slider.value(),
            'show_frame': self.show_frame_check.isChecked(),
            'frame_color': self.frame_color_btn.color().name(),
            'frame_width': self.frame_width_spin.value(),
            'show_title': self.show_title_check.isChecked(),
            'title_text': self.title_text.text()
        }
        
    def get_legend_items(self):
        """Get legend items from current map layers"""
        items = []
        try:
            layers = QgsProject.instance().layerTreeRoot().children()
            for layer_node in layers:
                if layer_node.isVisible():
                    items.append({
                        'name': layer_node.name(),
                        'type': 'layer'
                    })
        except Exception as e:
            print(f"Error getting legend items: {e}")
        return items
        
    def position_overlay(self):
        """Position the legend overlay on canvas"""
        if not self.legend_overlay:
            return
            
        canvas_size = self.canvas.size()
        self.legend_overlay.resize(self.width_spin.value(), self.height_spin.value())
        overlay_size = self.legend_overlay.size()
        
        position = self.position_combo.currentText().lower()
        x_offset = self.x_offset_spin.value()
        y_offset = self.y_offset_spin.value()
        
        if 'top' in position and 'left' in position:
            x, y = x_offset, y_offset
        elif 'top' in position and 'right' in position:
            x = canvas_size.width() - overlay_size.width() - x_offset
            y = y_offset
        elif 'bottom' in position and 'left' in position:
            x = x_offset
            y = canvas_size.height() - overlay_size.height() - y_offset
        elif 'bottom' in position and 'right' in position:
            x = canvas_size.width() - overlay_size.width() - x_offset
            y = canvas_size.height() - overlay_size.height() - y_offset
        else:  # Custom position
            x, y = x_offset, y_offset
            
        self.legend_overlay.move(x, y)
        
    def export_current_view(self):
        """Export current canvas view with legend"""
        try:
            self.export_to_png()
        except Exception as e:
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error exporting view: {}').format(str(e)))
            
    def export_to_clipboard(self):
        """Export canvas with legend to clipboard"""
        try:
            pixmap = self.capture_canvas_with_legend()
            QApplication.clipboard().setPixmap(pixmap)
            
            QMessageBox.information(self, self.tr('Success'), 
                                  self.tr('Canvas exported to clipboard successfully.'))
                                  
        except Exception as e:
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error exporting to clipboard: {}').format(str(e)))
            
    def export_to_png(self):
        """Export canvas with legend to PNG file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, self.tr('Export as PNG'), 
                'canvas_with_legend.png', 
                'PNG Files (*.png)'
            )
            
            if filename:
                pixmap = self.capture_canvas_with_legend()
                pixmap.save(filename, 'PNG')
                
                QMessageBox.information(self, self.tr('Success'), 
                                      self.tr('Canvas exported to {} successfully.').format(filename))
                                      
        except Exception as e:
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error exporting to PNG: {}').format(str(e)))
            
    def create_composition(self):
        """Create a QGIS composition with canvas and legend"""
        try:
            # Create new print layout
            project = QgsProject.instance()
            layout = QgsPrintLayout(project)
            layout.initializeDefaults()
            layout.setName(self.tr('Canvas with Legend'))
            
            # Add map item
            map_item = QgsLayoutItemMap(layout)
            map_item.attemptResize(QgsLayoutSize(200, 200))
            map_item.setExtent(self.canvas.extent())
            layout.addLayoutItem(map_item)
            
            # Add legend item
            legend_item = QgsLayoutItemLegend(layout)
            legend_item.setLinkedMap(map_item)
            legend_item.setAutoUpdateModel(True)
            layout.addLayoutItem(legend_item)
            
            # Add to project
            project.layoutManager().addLayout(layout)
            
            QMessageBox.information(self, self.tr('Success'), 
                                  self.tr('Composition created successfully.'))
                                  
        except Exception as e:
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error creating composition: {}').format(str(e)))
            
    def capture_canvas_with_legend(self):
        """Capture canvas with legend overlay as pixmap"""
        canvas_pixmap = self.canvas.grab()
        return canvas_pixmap
        
    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.legend_overlay:
            self.legend_overlay.close()
        event.accept()

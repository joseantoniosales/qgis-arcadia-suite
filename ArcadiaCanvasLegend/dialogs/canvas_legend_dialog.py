"""
Dialog for configuring canvas legend overlay
Handles all user interface interactions for legend configuration
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer, QRect, QPointF, QSize
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QPushButton, QComboBox, QSpinBox, 
                                QCheckBox, QGroupBox, QTabWidget, QWidget, 
                                QSlider, QFrame, QMessageBox, QApplication, 
                                QFileDialog, QTextEdit, QLineEdit)
from qgis.PyQt.QtGui import QFont, QPixmap, QPainter, QColor
from qgis.core import (QgsProject, QgsLayoutExporter, QgsLayoutItemMap, 
                      QgsLayoutItemLegend, QgsPrintLayout, QgsLayoutPoint,
                      QgsLayoutSize, QgsUnitTypes, QgsSymbolLayerUtils,
                      QgsRenderContext, QgsMapSettings)
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
        self.symbol_size = 16  # Size for legend symbols
        
    def update_legend_content(self, legend_items, settings):
        """Update legend content and settings"""
        self.legend_items = legend_items
        self.settings = settings
        
        # Auto-size if enabled
        if settings.get('auto_size', True):
            self.calculate_optimal_size()
        
        self.update()
        
    def calculate_optimal_size(self):
        """Calculate optimal size based on content"""
        if not self.legend_items:
            return
            
        # Basic calculation - would be refined based on actual content
        line_height = 20
        padding = 10
        symbol_width = 30
        text_width = 150  # Estimated
        
        height = padding * 2
        if self.settings.get('show_title', True):
            height += 25  # Title height
            
        # Count visible items
        total_items = 0
        for item in self.legend_items:
            if item.get('type') == 'group':
                total_items += 1  # Group title
                total_items += len(item.get('children', []))
            else:
                symbols = item.get('symbols', [])
                if symbols:
                    total_items += len(symbols)
                else:
                    total_items += 1
                    
        height += total_items * line_height
        width = symbol_width + text_width + padding * 2
        
        self.resize(width, height)
        
    def paintEvent(self, event):
        """Paint the legend overlay"""
        if not self.legend_items:
            return
            
        painter = QPainter()
        if not painter.begin(self):
            print("Error: Failed to begin painting on legend overlay")
            return
            
        try:
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
                
            # Draw title if enabled
            y_offset = 10
            if self.settings.get('show_title', True):
                title_text = self.settings.get('title_text', 'Map Legend')
                painter.setPen(QColor('black'))
                painter.setFont(QFont('Arial', 12, QFont.Bold))
                painter.drawText(10, y_offset + 15, title_text)
                y_offset += 25
                
            # Draw legend items
            painter.setFont(QFont('Arial', 10))
            for item in self.legend_items:
                y_offset = self.draw_legend_item(painter, item, y_offset)
                
        except Exception as e:
            print(f"Error in paintEvent: {e}")
        finally:
            painter.end()
            
    def draw_legend_item(self, painter, item, y_offset):
        """Draw individual legend item"""
        line_height = 20
        symbol_width = 20
        padding = 10
        
        if item.get('type') == 'group':
            # Draw group name
            painter.setPen(QColor('black'))
            painter.setFont(QFont('Arial', 10, QFont.Bold))
            painter.drawText(padding, y_offset + 15, item.get('name', 'Unknown Group'))
            y_offset += line_height
            
            # Draw children
            painter.setFont(QFont('Arial', 9))
            for child in item.get('children', []):
                y_offset = self.draw_legend_item(painter, child, y_offset)
                
        else:
            # Draw layer
            symbols = item.get('symbols', [])
            if symbols:
                # Draw each symbol
                for symbol_info in symbols:
                    symbol_rect = QRect(padding + 5, y_offset + 2, symbol_width, self.symbol_size)
                    
                    # Try to render actual symbol
                    symbol = symbol_info.get('symbol')
                    symbol_color = symbol_info.get('color')
                    
                    if symbol:
                        try:
                            # Method 1: Try to use drawPreviewIcon (most reliable)
                            if hasattr(symbol, 'drawPreviewIcon'):
                                try:
                                    icon_pixmap = symbol.drawPreviewIcon(None, QSize(symbol_width, self.symbol_size))
                                    if icon_pixmap and not icon_pixmap.isNull():
                                        painter.drawPixmap(symbol_rect, icon_pixmap)
                                        continue
                                except Exception:
                                    pass
                            
                            # Method 2: Try direct color rendering
                            if hasattr(symbol, 'color'):
                                try:
                                    color = symbol.color()
                                    if color.isValid():
                                        painter.fillRect(symbol_rect, color)
                                        continue
                                except Exception:
                                    pass
                            
                            # Method 3: Create separate pixmap for complex rendering
                            pixmap = QPixmap(symbol_width, self.symbol_size)
                            pixmap.fill(Qt.transparent)
                            
                            symbol_painter = QPainter()
                            if symbol_painter.begin(pixmap):
                                try:
                                    symbol_painter.setRenderHint(QPainter.Antialiasing)
                                    
                                    # Try renderPoint method
                                    if hasattr(symbol, 'startRender') and hasattr(symbol, 'renderPoint'):
                                        symbol.startRender(symbol_painter)
                                        center_point = QPointF(symbol_width/2, self.symbol_size/2)
                                        symbol.renderPoint(center_point, symbol_painter)
                                        symbol.stopRender(symbol_painter)
                                    else:
                                        # Simple fallback - fill with color
                                        if hasattr(symbol, 'color'):
                                            symbol_painter.fillRect(0, 0, symbol_width, self.symbol_size, symbol.color())
                                        else:
                                            symbol_painter.fillRect(0, 0, symbol_width, self.symbol_size, QColor('lightblue'))
                                            
                                except Exception as render_error:
                                    print(f"Error in symbol rendering: {render_error}")
                                    # Emergency fallback within the painter context
                                    symbol_painter.fillRect(0, 0, symbol_width, self.symbol_size, QColor('lightgray'))
                                finally:
                                    symbol_painter.end()
                                    
                                # Draw the rendered symbol
                                painter.drawPixmap(symbol_rect, pixmap)
                            else:
                                # Failed to begin painting - use direct color fallback
                                raise Exception("Failed to begin symbol painter")
                                
                        except Exception as e:
                            # Fallback to colored rectangle if all symbol rendering fails
                            print(f"Error rendering symbol: {e}")
                            if symbol_color:
                                painter.fillRect(symbol_rect, symbol_color)
                            elif hasattr(symbol, 'color'):
                                try:
                                    painter.fillRect(symbol_rect, symbol.color())
                                except:
                                    painter.fillRect(symbol_rect, QColor('lightblue'))
                            else:
                                painter.fillRect(symbol_rect, QColor('lightblue'))
                    elif symbol_color:
                        # Use the stored color
                        painter.fillRect(symbol_rect, symbol_color)
                    else:
                        # Final fallback
                        painter.fillRect(symbol_rect, QColor('lightgray'))
                    
                    # Draw label
                    painter.setPen(QColor('black'))
                    text_x = padding + symbol_width + 10
                    painter.drawText(text_x, y_offset + 15, symbol_info.get('label', 'Unknown'))
                    y_offset += line_height
            else:
                # Simple layer item without symbols - draw layer color or default
                symbol_rect = QRect(padding + 5, y_offset + 2, symbol_width, self.symbol_size)
                
                # Try to get layer color from renderer
                layer = item.get('layer')
                if layer and hasattr(layer, 'renderer') and layer.renderer():
                    renderer = layer.renderer()
                    if hasattr(renderer, 'symbol') and renderer.symbol():
                        symbol = renderer.symbol()
                        if hasattr(symbol, 'color'):
                            painter.fillRect(symbol_rect, symbol.color())
                        else:
                            painter.fillRect(symbol_rect, QColor('lightblue'))
                    else:
                        painter.fillRect(symbol_rect, QColor('lightblue'))
                else:
                    painter.fillRect(symbol_rect, QColor('lightgray'))
                
                painter.setPen(QColor('black'))
                text_x = padding + symbol_width + 10
                painter.drawText(text_x, y_offset + 15, item.get('name', 'Unknown'))
                y_offset += line_height
                
        return y_offset


class CanvasLegendDialog(QDialog):
    """Main dialog for canvas legend configuration"""
    
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.legend_overlay = None
        self.auto_update_enabled = True
        
        self.setupUi()
        self.load_settings()
        self.connect_signals()
        self.connect_layer_signals()
        
    def connect_layer_signals(self):
        """Connect signals to detect layer changes"""
        try:
            # Connect to layer tree changes
            root = QgsProject.instance().layerTreeRoot()
            root.visibilityChanged.connect(self.on_layer_visibility_changed)
            
            # Connect to project signals for layer addition/removal
            QgsProject.instance().layersAdded.connect(self.on_layers_changed)
            QgsProject.instance().layersRemoved.connect(self.on_layers_changed)
            
            # Connect to layer style changes
            QgsProject.instance().layerStyleChanged.connect(self.on_layer_style_changed)
            
        except Exception as e:
            print(f"Error connecting layer signals: {e}")
            
    def on_layer_visibility_changed(self, node):
        """Handle layer visibility changes"""
        if self.auto_update_enabled and self.legend_overlay and self.legend_overlay.isVisible():
            # Small delay to allow QGIS to process the change
            QTimer.singleShot(100, self.update_legend_auto)
            
    def on_layers_changed(self):
        """Handle layer addition/removal"""
        if self.auto_update_enabled and self.legend_overlay and self.legend_overlay.isVisible():
            QTimer.singleShot(100, self.update_legend_auto)
            
    def on_layer_style_changed(self, layer_id):
        """Handle layer style changes"""
        if self.auto_update_enabled and self.legend_overlay and self.legend_overlay.isVisible():
            QTimer.singleShot(100, self.update_legend_auto)
            
    def update_legend_auto(self):
        """Update legend automatically without user interaction"""
        try:
            if self.legend_overlay and self.legend_overlay.isVisible():
                # Get current settings
                settings = self.get_current_settings()
                
                # Get updated legend items
                legend_items = self.get_legend_items()
                
                # Update overlay
                self.legend_overlay.update_legend_content(legend_items, settings)
                
                # Reposition overlay if needed
                self.position_overlay()
                
        except Exception as e:
            print(f"Error auto-updating legend: {e}")
        
    def setupUi(self):
        """Set up the user interface"""
        self.setWindowTitle(self.tr('Arcadia Canvas Legend Configuration - Beta 03'))
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
        self.hide_legend_btn = QPushButton(self.tr('Hide Legend'))
        self.export_btn = QPushButton(self.tr('Export'))
        self.close_btn = QPushButton(self.tr('Close'))
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.hide_legend_btn)
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
        
        self.auto_update_check = QCheckBox(self.tr('Auto-update when layers change'))
        self.auto_update_check.setChecked(True)
        self.auto_update_check.toggled.connect(self.toggle_auto_update)
        layers_layout.addWidget(self.auto_update_check)
        
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
        self.hide_legend_btn.clicked.connect(self.hide_legend)
        self.export_btn.clicked.connect(self.export_current_view)
        self.close_btn.clicked.connect(self.close_dialog_only)
        
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
            # Get layer tree root
            root = QgsProject.instance().layerTreeRoot()
            
            # Process each layer or group
            for child in root.children():
                if hasattr(child, 'layer') and child.layer() is not None:
                    # Single layer
                    layer = child.layer()
                    if child.isVisible() and layer.isValid():
                        layer_item = {
                            'name': layer.name(),
                            'type': 'layer',
                            'layer': layer,
                            'visible': child.isVisible()
                        }
                        
                        # Get symbols if it's a vector layer
                        if hasattr(layer, 'renderer') and layer.renderer():
                            layer_item['symbols'] = self.get_layer_symbols(layer)
                        
                        items.append(layer_item)
                        
                elif hasattr(child, 'children'):
                    # Group
                    if child.isVisible():
                        group_item = {
                            'name': child.name(),
                            'type': 'group',
                            'visible': child.isVisible(),
                            'children': []
                        }
                        
                        # Process children of the group
                        for group_child in child.children():
                            if hasattr(group_child, 'layer') and group_child.layer() is not None:
                                layer = group_child.layer()
                                if group_child.isVisible() and layer.isValid():
                                    layer_item = {
                                        'name': layer.name(),
                                        'type': 'layer',
                                        'layer': layer,
                                        'visible': group_child.isVisible()
                                    }
                                    
                                    # Get symbols if it's a vector layer
                                    if hasattr(layer, 'renderer') and layer.renderer():
                                        layer_item['symbols'] = self.get_layer_symbols(layer)
                                    
                                    group_item['children'].append(layer_item)
                        
                        if group_item['children']:  # Only add groups that have visible children
                            items.append(group_item)
                            
        except Exception as e:
            print(f"Error getting legend items: {e}")
        return items
    
    def get_layer_symbols(self, layer):
        """Get symbols for a layer"""
        symbols = []
        try:
            renderer = layer.renderer()
            if renderer:
                # Handle different renderer types
                renderer_type = renderer.type()
                
                if renderer_type == 'singleSymbol':
                    # Single symbol renderer
                    symbol = renderer.symbol()
                    if symbol:
                        symbols.append({
                            'label': layer.name(),
                            'symbol': symbol,
                            'color': symbol.color() if hasattr(symbol, 'color') else None
                        })
                        
                elif renderer_type == 'categorizedSymbol':
                    # Categorized renderer
                    for category in renderer.categories():
                        if category.renderState():  # Only include enabled categories
                            symbols.append({
                                'label': category.label() if category.label() else category.value(),
                                'symbol': category.symbol(),
                                'color': category.symbol().color() if hasattr(category.symbol(), 'color') else None
                            })
                            
                elif renderer_type == 'graduatedSymbol':
                    # Graduated renderer
                    for range_item in renderer.ranges():
                        symbols.append({
                            'label': range_item.label(),
                            'symbol': range_item.symbol(),
                            'color': range_item.symbol().color() if hasattr(range_item.symbol(), 'color') else None
                        })
                        
                elif renderer_type == 'RuleRenderer':
                    # Rule-based renderer
                    root_rule = renderer.rootRule()
                    if root_rule:
                        for rule in root_rule.children():
                            if rule.isActive() and rule.symbol():
                                symbols.append({
                                    'label': rule.label() or rule.filterExpression() or 'Rule',
                                    'symbol': rule.symbol(),
                                    'color': rule.symbol().color() if hasattr(rule.symbol(), 'color') else None
                                })
                else:
                    # Fallback for other renderer types
                    symbol = getattr(renderer, 'symbol', lambda: None)()
                    if symbol:
                        symbols.append({
                            'label': layer.name(),
                            'symbol': symbol,
                            'color': symbol.color() if hasattr(symbol, 'color') else None
                        })
                        
        except Exception as e:
            print(f"Error getting symbols for layer {layer.name()}: {e}")
            # Fallback: create a basic symbol representation
            symbols.append({
                'label': layer.name(),
                'symbol': None,
                'color': QColor('lightblue')
            })
        return symbols
        
    def position_overlay(self):
        """Position the legend overlay on canvas"""
        if not self.legend_overlay:
            return
            
        # Get canvas geometry in global coordinates
        canvas_global_pos = self.canvas.mapToGlobal(self.canvas.rect().topLeft())
        canvas_size = self.canvas.size()
        
        self.legend_overlay.resize(self.width_spin.value(), self.height_spin.value())
        overlay_size = self.legend_overlay.size()
        
        position = self.position_combo.currentText().lower()
        x_offset = self.x_offset_spin.value()
        y_offset = self.y_offset_spin.value()
        
        # Calculate position relative to canvas, not main window
        if 'top' in position and 'left' in position:
            x = canvas_global_pos.x() + x_offset
            y = canvas_global_pos.y() + y_offset
        elif 'top' in position and 'right' in position:
            x = canvas_global_pos.x() + canvas_size.width() - overlay_size.width() - x_offset
            y = canvas_global_pos.y() + y_offset
        elif 'bottom' in position and 'left' in position:
            x = canvas_global_pos.x() + x_offset
            y = canvas_global_pos.y() + canvas_size.height() - overlay_size.height() - y_offset
        elif 'bottom' in position and 'right' in position:
            x = canvas_global_pos.x() + canvas_size.width() - overlay_size.width() - x_offset
            y = canvas_global_pos.y() + canvas_size.height() - overlay_size.height() - y_offset
        else:  # Custom position
            x = canvas_global_pos.x() + x_offset
            y = canvas_global_pos.y() + y_offset
            
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
            
    def toggle_auto_update(self, enabled):
        """Toggle automatic legend updates"""
        self.auto_update_enabled = enabled
        
    def hide_legend(self):
        """Hide the legend overlay without closing the dialog"""
        try:
            if self.legend_overlay:
                self.legend_overlay.hide()
        except Exception as e:
            QMessageBox.warning(self, self.tr('Warning'), 
                              self.tr('Error hiding legend: {}').format(str(e)))
            
    def close_dialog_only(self):
        """Close only the dialog, keep legend visible if active"""
        self.hide()
        
    def capture_canvas_with_legend(self):
        """Capture canvas with legend overlay as pixmap"""
        try:
            # Get canvas pixmap safely
            canvas_pixmap = self.canvas.grab()
            
            if self.legend_overlay and self.legend_overlay.isVisible():
                # Create combined pixmap
                combined_pixmap = QPixmap(canvas_pixmap.size())
                combined_pixmap.fill(Qt.transparent)
                
                painter = QPainter()
                if painter.begin(combined_pixmap):
                    try:
                        # Draw canvas
                        painter.drawPixmap(0, 0, canvas_pixmap)
                        
                        # Draw legend overlay at its position
                        legend_pixmap = self.legend_overlay.grab()
                        legend_pos = self.legend_overlay.pos()
                        canvas_pos = self.canvas.mapToGlobal(self.canvas.rect().topLeft())
                        
                        # Calculate relative position
                        relative_x = legend_pos.x() - canvas_pos.x()
                        relative_y = legend_pos.y() - canvas_pos.y()
                        
                        painter.drawPixmap(relative_x, relative_y, legend_pixmap)
                        
                    except Exception as e:
                        print(f"Error combining pixmaps: {e}")
                    finally:
                        painter.end()
                        
                return combined_pixmap
            else:
                return canvas_pixmap
                
        except Exception as e:
            print(f"Error capturing canvas: {e}")
            # Return a simple canvas grab as fallback
            return self.canvas.grab()
        
    def cleanup(self):
        """Clean up resources when plugin is unloaded"""
        try:
            # Disconnect layer signals
            root = QgsProject.instance().layerTreeRoot()
            root.visibilityChanged.disconnect(self.on_layer_visibility_changed)
            
            QgsProject.instance().layersAdded.disconnect(self.on_layers_changed)
            QgsProject.instance().layersRemoved.disconnect(self.on_layers_changed)
            QgsProject.instance().layerStyleChanged.disconnect(self.on_layer_style_changed)
            
        except Exception as e:
            print(f"Error disconnecting signals: {e}")
            
        if self.legend_overlay:
            self.legend_overlay.close()
            self.legend_overlay = None
    
    def closeEvent(self, event):
        """Handle dialog close event - don't close legend overlay"""
        # Don't close the legend overlay when dialog closes
        # User must explicitly use "Hide Legend" button
        event.accept()

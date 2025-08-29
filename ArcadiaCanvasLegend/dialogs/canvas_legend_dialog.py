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
from qgis.PyQt.QtGui import QFont, QPixmap, QPainter, QColor, QPen
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
        # Set canvas as parent to limit overlay to canvas area only
        super().__init__(canvas)  # Canvas as parent instead of generic parent
        self.canvas = canvas
        # Removed WindowStaysOnTopHint to prevent overlay on composer/other windows
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.legend_items = []
        self.settings = {}
        self.symbol_size = 16  # Size for legend symbols
        self.debug_mode = False  # Debug mode off by default
        
    def debug_print(self, message):
        """Print debug message only if debug mode is enabled"""
        if self.debug_mode:
            print(message)
        
    def update_legend_content(self, legend_items, settings):
        """Update legend content and settings"""
        self.legend_items = legend_items
        self.settings = settings
        
        # Update debug mode from settings
        self.debug_mode = settings.get('debug_mode', False)
        
        # Auto-size if enabled
        if settings.get('auto_size', True):
            self.calculate_optimal_size()
        
        self.update()
        
    def calculate_optimal_size(self):
        """Calculate optimal size based on content"""
        if not self.legend_items:
            self.resize(200, 100)  # Minimum size
            return
            
        # Basic calculation - refined based on actual content
        line_height = 22  # Increased for better spacing
        padding = 15
        symbol_width = 25
        text_width = 200  # Increased for longer names
        min_width = 150
        
        height = padding * 2
        max_text_width = 0
        
        # Add title height if enabled
        if self.settings.get('show_title', True):
            height += 30  # Title height with spacing
            title_text = self.settings.get('title_text', 'Map Legend')
            # Estimate title width (rough calculation)
            title_width = len(title_text) * 8  # Approximate
            max_text_width = max(max_text_width, title_width)
            
        # Count visible items and calculate text width needs
        total_items = 0
        for item in self.legend_items:
            if item.get('type') == 'group':
                total_items += 1  # Group title
                group_name_width = len(item.get('name', '')) * 7
                max_text_width = max(max_text_width, group_name_width)
                
                children = item.get('children', [])
                for child in children:
                    total_items += 1
                    child_name_width = len(child.get('name', '')) * 6
                    max_text_width = max(max_text_width, child_name_width)
                    
            else:
                symbols = item.get('symbols', [])
                if symbols:
                    for symbol_info in symbols:
                        total_items += 1
                        label_width = len(symbol_info.get('label', '')) * 6
                        max_text_width = max(max_text_width, label_width)
                else:
                    total_items += 1
                    layer_name_width = len(item.get('name', '')) * 6
                    max_text_width = max(max_text_width, layer_name_width)
                    
        height += total_items * line_height
        
        # Calculate width based on content
        content_width = symbol_width + max(max_text_width, text_width) + padding * 3
        width = max(min_width, content_width)
        
        self.debug_print(f"Calculated size: {width}x{height} for {total_items} items")
        self.resize(int(width), int(height))
        
    def paintEvent(self, event):
        """Paint the legend overlay"""
        if not self.legend_items:
            return
            
        painter = QPainter()
        if not painter.begin(self):
            self.debug_print("Error: Failed to begin painting on legend overlay")
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
            self.debug_print(f"Error in paintEvent: {e}")
        finally:
            painter.end()
            
    def draw_legend_item(self, painter, item, y_offset):
        """Draw individual legend item"""
        line_height = 22  # Increased spacing
        symbol_width = 20
        padding = 15
        
        if item.get('type') == 'group':
            # Draw group name
            painter.setPen(QColor('black'))
            painter.setFont(QFont('Arial', 10, QFont.Bold))
            group_name = item.get('name', 'Unknown Group')
            painter.drawText(padding, y_offset + 15, group_name)
            self.debug_print(f"Drawing group: {group_name}")
            y_offset += line_height
            
            # Draw children
            painter.setFont(QFont('Arial', 9))
            for child in item.get('children', []):
                y_offset = self.draw_legend_item(painter, child, y_offset)
                
        else:
            # Draw layer
            layer_name = item.get('name', 'Unknown Layer')
            symbols = item.get('symbols', [])
            
            self.debug_print(f"Drawing layer: {layer_name}, symbols: {len(symbols)}")
            
            if symbols:
                # Draw each symbol
                for i, symbol_info in enumerate(symbols):
                    symbol_rect = QRect(padding + 5, y_offset + 3, symbol_width, 16)
                    
                    # Get symbol and color info
                    symbol = symbol_info.get('symbol')
                    symbol_color = symbol_info.get('color', QColor('lightgray'))
                    layer_type = symbol_info.get('layer_type', 'unknown')
                    geometry_type = symbol_info.get('geometry_type', 'unknown')
                    label = symbol_info.get('label', layer_name)
                    text_only = symbol_info.get('text_only', False)
                    
                    self.debug_print(f"  Drawing symbol {i} for {layer_name}: type={layer_type}, geom={geometry_type}, has_symbol={symbol is not None}, text_only={text_only}")
                    
                    # Draw symbol only if not text_only
                    if not text_only:
                        self.draw_symbol_safe(painter, symbol_rect, symbol, symbol_color, layer_type, geometry_type)
                    else:
                        self.debug_print(f"  - Skipping symbol draw for text-only layer: {label}")
                    
                    # Draw label with better positioning
                    painter.setPen(QColor('black'))
                    painter.setFont(QFont('Arial', 9))
                    # Adjust text position for text-only items (no symbol space needed)
                    text_x = padding + (symbol_width + 15 if not text_only else 5)
                    painter.drawText(text_x, y_offset + 15, label)
                    self.debug_print(f"  - Symbol drawn for: {label}")
                    y_offset += line_height
            else:
                # Layer without symbols - draw simple representation
                symbol_rect = QRect(padding + 5, y_offset + 3, symbol_width, 16)
                
                # Try to get layer color from renderer or use default
                layer = item.get('layer')
                default_color = QColor('lightgray')
                
                if layer:
                    try:
                        if hasattr(layer, 'renderer') and layer.renderer():
                            renderer = layer.renderer()
                            if hasattr(renderer, 'symbol') and renderer.symbol():
                                symbol = renderer.symbol()
                                if hasattr(symbol, 'color'):
                                    default_color = symbol.color()
                    except:
                        pass
                
                painter.fillRect(symbol_rect, default_color)
                
                # Draw layer name
                painter.setPen(QColor('black'))
                painter.setFont(QFont('Arial', 9))
                text_x = padding + symbol_width + 15
                painter.drawText(text_x, y_offset + 15, layer_name)
                self.debug_print(f"  - Simple rect drawn for: {layer_name}")
                y_offset += line_height
                
        return y_offset
    
    def draw_symbol_safe(self, painter, symbol_rect, symbol, symbol_color, layer_type, geometry_type='unknown'):
        """Draw symbol with multiple fallback methods and crash protection"""
        method_used = "none"
        try:
            self.debug_print(f"    draw_symbol_safe: layer_type={layer_type}, geometry_type={geometry_type}, has_symbol={symbol is not None}")
            
            # CRITICAL: Validate symbol before ANY operation to prevent crashes
            if symbol and layer_type != 'raster':
                # Pre-validate symbol to catch corrupted symbols that cause crashes
                try:
                    # Test basic symbol properties that might crash
                    _ = symbol.type()  # This can crash with corrupted symbols
                    _ = hasattr(symbol, 'asImage')  # Safe property check
                    self.debug_print(f"    -> Symbol validation passed")
                except Exception as validation_error:
                    self.debug_print(f"    -> CRITICAL: Symbol validation failed: {validation_error}")
                    # Corrupt symbol detected - use color fallback immediately
                    painter.fillRect(symbol_rect, symbol_color or QColor('red'))
                    return
                
                # Method 1: Try asImage (best for getting actual rendered symbol)
                if hasattr(symbol, 'asImage'):
                    try:
                        size = symbol_rect.size()
                        # Additional safety check before calling asImage
                        if size.width() > 0 and size.height() > 0:
                            image = symbol.asImage(size)
                            if image and not image.isNull():
                                pixmap = QPixmap.fromImage(image)
                                painter.drawPixmap(symbol_rect, pixmap)
                                method_used = "asImage"
                                self.debug_print(f"    -> SUCCESS: Used asImage method")
                                return
                    except Exception as e:
                        self.debug_print(f"    -> asImage failed: {e}")
                
                # Method 2: Try exportImage
                if hasattr(symbol, 'exportImage'):
                    try:
                        size = symbol_rect.size()
                        image = symbol.exportImage(size.width(), size.height())
                        if image and not image.isNull():
                            pixmap = QPixmap.fromImage(image)
                            painter.drawPixmap(symbol_rect, pixmap)
                            method_used = "exportImage"
                            self.debug_print(f"    -> SUCCESS: Used exportImage method")
                            return
                    except Exception as e:
                        self.debug_print(f"    -> exportImage failed: {e}")
                
                # Method 3: Custom rendering based on geometry type
                pixmap = QPixmap(symbol_rect.width(), symbol_rect.height())
                pixmap.fill(Qt.transparent)
                
                symbol_painter = QPainter()
                if symbol_painter.begin(pixmap):
                    try:
                        symbol_painter.setRenderHint(QPainter.Antialiasing)
                        
                        # Get symbol color
                        symbol_color_to_use = symbol.color() if hasattr(symbol, 'color') else symbol_color
                        self.debug_print(f"    -> Custom rendering with color: {symbol_color_to_use.name() if symbol_color_to_use else 'None'}")
                        
                        # Different rendering based on geometry type
                        if geometry_type == 'point':
                            # Draw circle for points
                            symbol_painter.setBrush(symbol_color_to_use)
                            symbol_painter.setPen(QPen(symbol_color_to_use.darker(120), 1))
                            center = QPointF(symbol_rect.width()/2, symbol_rect.height()/2)
                            radius = min(symbol_rect.width(), symbol_rect.height()) // 3
                            symbol_painter.drawEllipse(center, radius, radius)
                            method_used = "custom_point"
                            
                        elif geometry_type == 'line':
                            # Draw line
                            pen = QPen(symbol_color_to_use, 2)
                            symbol_painter.setPen(pen)
                            symbol_painter.drawLine(2, symbol_rect.height()//2, 
                                                  symbol_rect.width()-2, symbol_rect.height()//2)
                            method_used = "custom_line"
                                                  
                        elif geometry_type == 'polygon':
                            # Draw filled rectangle for polygons
                            symbol_painter.setBrush(symbol_color_to_use)
                            symbol_painter.setPen(QPen(symbol_color_to_use.darker(120), 1))
                            symbol_painter.drawRect(2, 2, symbol_rect.width()-4, symbol_rect.height()-4)
                            method_used = "custom_polygon"
                            
                        else:
                            # Default: filled rectangle
                            symbol_painter.fillRect(0, 0, symbol_rect.width(), symbol_rect.height(), symbol_color_to_use)
                            method_used = "custom_default"
                            
                        self.debug_print(f"    -> SUCCESS: Used {method_used} method")
                            
                    except Exception as render_error:
                        self.debug_print(f"    -> Custom rendering failed: {render_error}")
                        # Emergency fallback within the painter context
                        color = symbol.color() if hasattr(symbol, 'color') else symbol_color or QColor('lightgray')
                        symbol_painter.fillRect(0, 0, symbol_rect.width(), symbol_rect.height(), color)
                        method_used = "custom_fallback"
                    finally:
                        symbol_painter.end()
                        
                    # Draw the rendered symbol
                    painter.drawPixmap(symbol_rect, pixmap)
                    return
                
                # Method 4: Try direct color rendering
                if hasattr(symbol, 'color'):
                    try:
                        color = symbol.color()
                        if color.isValid():
                            # Apply geometry-specific rendering even for fallback
                            if geometry_type == 'point':
                                painter.setBrush(color)
                                painter.setPen(QPen(color.darker(120), 1))
                                center = QPointF(symbol_rect.center())
                                radius = min(symbol_rect.width(), symbol_rect.height()) // 3
                                painter.drawEllipse(center, radius, radius)
                                method_used = "direct_point"
                            elif geometry_type == 'line':
                                pen = QPen(color, 2)
                                painter.setPen(pen)
                                painter.drawLine(symbol_rect.left()+2, symbol_rect.center().y(), 
                                               symbol_rect.right()-2, symbol_rect.center().y())
                                method_used = "direct_line"
                            else:
                                painter.fillRect(symbol_rect, color)
                                method_used = "direct_fill"
                            self.debug_print(f"    -> SUCCESS: Used {method_used} method")
                            return
                    except Exception as e:
                        self.debug_print(f"    -> Direct color failed: {e}")
            
            # Method 5: Use provided symbol_color with geometry awareness
            if symbol_color and symbol_color.isValid():
                self.debug_print(f"    -> Using provided symbol_color: {symbol_color.name()}")
                if geometry_type == 'point':
                    painter.setBrush(symbol_color)
                    painter.setPen(QPen(symbol_color.darker(120), 1))
                    center = QPointF(symbol_rect.center())
                    radius = min(symbol_rect.width(), symbol_rect.height()) // 3
                    painter.drawEllipse(center, radius, radius)
                    method_used = "provided_point"
                elif geometry_type == 'line':
                    pen = QPen(symbol_color, 2)
                    painter.setPen(pen)
                    painter.drawLine(symbol_rect.left()+2, symbol_rect.center().y(), 
                                   symbol_rect.right()-2, symbol_rect.center().y())
                    method_used = "provided_line"
                else:
                    painter.fillRect(symbol_rect, symbol_color)
                    method_used = "provided_fill"
                self.debug_print(f"    -> SUCCESS: Used {method_used} method")
                return
                
            # Method 6: Default colors by layer type and geometry
            self.debug_print(f"    -> Using default colors for {layer_type}/{geometry_type}")
            if layer_type == 'raster':
                painter.fillRect(symbol_rect, QColor(200, 200, 200))  # Light gray for rasters
                method_used = "default_raster"
            else:
                # Default colors based on geometry type
                if geometry_type == 'point':
                    default_color = QColor(255, 100, 100)  # Red for points
                    painter.setBrush(default_color)
                    painter.setPen(QPen(default_color.darker(120), 1))
                    center = QPointF(symbol_rect.center())
                    radius = min(symbol_rect.width(), symbol_rect.height()) // 3
                    painter.drawEllipse(center, radius, radius)
                    method_used = "default_point"
                elif geometry_type == 'line':
                    default_color = QColor(100, 255, 100)  # Green for lines
                    pen = QPen(default_color, 2)
                    painter.setPen(pen)
                    painter.drawLine(symbol_rect.left()+2, symbol_rect.center().y(), 
                                   symbol_rect.right()-2, symbol_rect.center().y())
                    method_used = "default_line"
                elif geometry_type == 'polygon':
                    default_color = QColor(100, 100, 255)  # Blue for polygons
                    painter.fillRect(symbol_rect, default_color)
                    method_used = "default_polygon"
                else:
                    painter.fillRect(symbol_rect, QColor(180, 180, 180))  # Gray for unknown
                    method_used = "default_unknown"
            print(f"    -> SUCCESS: Used {method_used} method")
                
        except Exception as e:
            print(f"    -> ERROR in draw_symbol_safe: {e}")
            # Emergency fallback
            painter.fillRect(symbol_rect, QColor('lightgray'))
            method_used = "emergency_fallback"
            
        print(f"    -> Final method used: {method_used}")


class CanvasLegendDialog(QDialog):
    """Main dialog for canvas legend configuration"""
    
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.legend_overlay = None
        self.auto_update_enabled = True
        self.debug_mode = False  # Debug mode disabled by default
        
        self.setupUi()
        self.load_settings()
        self.connect_signals()
        self.connect_layer_signals()
        
    def debug_print(self, message):
        """Print debug message only if debug mode is enabled"""
        if self.debug_mode:
            print(message)
        
    def connect_layer_signals(self):
        """Connect signals to detect layer changes"""
        try:
            # Connect to layer tree changes
            root = QgsProject.instance().layerTreeRoot()
            root.visibilityChanged.connect(self.on_layer_visibility_changed)
            
            # Connect to project signals for layer addition/removal
            QgsProject.instance().layersAdded.connect(self.on_layers_changed)
            QgsProject.instance().layersRemoved.connect(self.on_layers_changed)
            
            # Connect to layer style changes (use different signal)
            # QgsProject.instance().layerStyleChanged.connect(self.on_layer_style_changed)
            # Use legendLayersAdded instead as it's more reliable
            QgsProject.instance().legendLayersAdded.connect(self.on_layers_changed)
            
        except Exception as e:
            self.debug_print(f"Error connecting layer signals: {e}")
            
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
            self.debug_print(f"Error auto-updating legend: {e}")
        
    def setupUi(self):
        """Set up the user interface"""
        self.setWindowTitle(self.tr('Arcadia Canvas Legend Configuration - Beta 09'))
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
        
        self.debug_mode_check = QCheckBox(self.tr('Debug mode (for development)'))
        self.debug_mode_check.setChecked(False)
        self.debug_mode_check.toggled.connect(self.toggle_debug_mode)
        layers_layout.addWidget(self.debug_mode_check)
        
        layout.addWidget(layers_group)
        
        # Raster styling group
        raster_group = QGroupBox(self.tr('Raster Styling'))
        raster_layout = QGridLayout(raster_group)
        
        raster_layout.addWidget(QLabel(self.tr('Pseudocolor decimals:')), 0, 0)
        self.pseudocolor_decimals_spin = QSpinBox()
        self.pseudocolor_decimals_spin.setRange(0, 6)
        self.pseudocolor_decimals_spin.setValue(2)
        self.pseudocolor_decimals_spin.setToolTip(self.tr('Number of decimal places for pseudocolor raster values'))
        raster_layout.addWidget(self.pseudocolor_decimals_spin, 0, 1)
        
        layout.addWidget(raster_group)
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
            
            # Load pseudocolor decimals setting
            decimals = get_arcadia_setting('CANVAS_LEGEND', 'pseudocolor_decimals', 2)
            if hasattr(self, 'pseudocolor_decimals_spin'):
                self.pseudocolor_decimals_spin.setValue(int(decimals))
            
        except Exception as e:
            self.debug_print(f"Error loading settings: {e}")
            
    def save_settings(self):
        """Save current settings to Arcadia Suite configuration"""
        try:
            position = self.position_combo.currentText().lower().replace(' ', '_')
            set_arcadia_setting('CANVAS_LEGEND', 'default_position', position)
            
            # Save pseudocolor decimals setting
            if hasattr(self, 'pseudocolor_decimals_spin'):
                set_arcadia_setting('CANVAS_LEGEND', 'pseudocolor_decimals', self.pseudocolor_decimals_spin.value())
                              
        except Exception as e:
            self.debug_print(f"Error saving settings: {e}")
            
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
            'title_text': self.title_text.text(),
            'debug_mode': self.debug_mode,
            'pseudocolor_decimals': self.pseudocolor_decimals_spin.value()
        }
        
    def get_legend_items(self):
        """Get legend items from current map layers"""
        items = []
        try:
            # Get layer tree root
            root = QgsProject.instance().layerTreeRoot()
            
            # Process all visible layers directly (simpler approach)
            def process_node(node, is_group_child=False):
                nonlocal items
                
                if hasattr(node, 'layer') and node.layer() is not None:
                    # Single layer
                    layer = node.layer()
                    if node.isVisible() and layer.isValid():
                        self.debug_print(f"Processing layer: {layer.name()}, visible: {node.isVisible()}, type: {layer.type()}")
                        
                        layer_item = {
                            'name': layer.name(),
                            'type': 'layer',
                            'layer': layer,
                            'visible': node.isVisible(),
                            'is_group_child': is_group_child
                        }
                        
                        # Get symbols for all layer types
                        symbols = self.get_layer_symbols(layer)
                        layer_item['symbols'] = symbols
                        self.debug_print(f"  -> Found {len(symbols)} symbols for {layer.name()}")
                        for i, sym in enumerate(symbols):
                            self.debug_print(f"    Symbol {i}: label='{sym.get('label')}', type='{sym.get('layer_type')}', geom='{sym.get('geometry_type')}'")
                        items.append(layer_item)
                        
                elif hasattr(node, 'children'):
                    # Group - process children individually
                    group_visible = node.isVisible()
                    self.debug_print(f"Processing group: {node.name()}, visible: {group_visible}")
                    
                    if group_visible:
                        # Add group header if it has visible children
                        has_visible_children = False
                        group_children = []
                        
                        for child in node.children():
                            if hasattr(child, 'layer') and child.layer() is not None:
                                layer = child.layer()
                                child_visible = child.isVisible() and group_visible
                                if child_visible and layer.isValid():
                                    has_visible_children = True
                                    layer_item = {
                                        'name': layer.name(),
                                        'type': 'layer',
                                        'layer': layer,
                                        'visible': child_visible,
                                        'is_group_child': True
                                    }
                                    layer_item['symbols'] = self.get_layer_symbols(layer)
                                    group_children.append(layer_item)
                            else:
                                # Nested group
                                process_node(child, True)
                        
                        if has_visible_children:
                            # Add group header
                            group_item = {
                                'name': node.name(),
                                'type': 'group',
                                'visible': group_visible,
                                'children': group_children
                            }
                            items.append(group_item)
            
            # Process all root children
            for child in root.children():
                process_node(child)
                            
        except Exception as e:
            self.debug_print(f"Error getting legend items: {e}")
            import traceback
            if self.debug_mode:
                traceback.print_exc()
        
        self.debug_print(f"Total legend items found: {len(items)}")
        return items
    
    def get_layer_symbols(self, layer):
        """Get symbols for a layer"""
        symbols = []
        try:
            self.debug_print(f"=== get_layer_symbols for {layer.name()} ===")
            layer_type_int = layer.type()
            self.debug_print(f"Layer type: {layer_type_int} (0=Raster, 1=Vector, 2=Plugin)")
            self.debug_print(f"Layer class: {layer.__class__.__name__}")
            
            # More robust layer type detection
            layer_type_name = layer.__class__.__name__
            is_vector = 'Vector' in layer_type_name or hasattr(layer, 'geometryType')
            is_raster = 'Raster' in layer_type_name or hasattr(layer, 'bandCount')
            
            self.debug_print(f"-> is_vector: {is_vector}, is_raster: {is_raster}")
            
            # Handle raster layers
            if is_raster and not is_vector:
                self.debug_print(f"-> Raster layer detected (class-based)")
                
                # Analyze raster renderer type
                renderer = layer.renderer() if hasattr(layer, 'renderer') else None
                renderer_type = renderer.type() if renderer else 'unknown'
                band_count = layer.bandCount() if hasattr(layer, 'bandCount') else 1
                
                self.debug_print(f"-> Raster renderer type: {renderer_type}")
                self.debug_print(f"-> Band count: {band_count}")
                
                # Handle different raster types
                if renderer_type == 'singlebandpseudocolor':
                    # Pseudocolor raster - show color ramp
                    self.debug_print(f"-> Pseudocolor raster - generating color ramp")
                    if hasattr(renderer, 'shader') and renderer.shader():
                        shader = renderer.shader()
                        if hasattr(shader, 'rasterShaderFunction'):
                            ramp_function = shader.rasterShaderFunction()
                            if hasattr(ramp_function, 'colorRampItemList'):
                                color_items = ramp_function.colorRampItemList()
                                if color_items:
                                    # Get decimal places from UI control
                                    decimals = self.pseudocolor_decimals_spin.value() if hasattr(self, 'pseudocolor_decimals_spin') else 2
                                    
                                    # Create multiple symbols for the color ramp
                                    for i, item in enumerate(color_items[:5]):  # Max 5 colors to avoid overcrowding
                                        # Format value with specified decimal places
                                        if hasattr(item, 'value'):
                                            value_text = f"{item.value:.{decimals}f}"
                                        else:
                                            value_text = f"Color {i+1}"
                                            
                                        label = f"{item.label}" if hasattr(item, 'label') and item.label else f"Value {value_text}"
                                        
                                        symbols.append({
                                            'label': label,
                                            'symbol': None,
                                            'color': item.color if hasattr(item, 'color') else QColor('gray'),
                                            'layer_type': 'raster_pseudocolor',
                                            'geometry_type': 'raster'
                                        })
                                    return symbols
                    
                    # Fallback for pseudocolor without detailed ramp info
                    symbols.append({
                        'label': f"{layer.name()} (Pseudocolor)",
                        'symbol': None,
                        'color': QColor('blue'),
                        'layer_type': 'raster_pseudocolor',
                        'geometry_type': 'raster'
                    })
                    
                elif renderer_type == 'multibandcolor' or band_count >= 3:
                    # RGB/Multiband raster - no symbol, just text
                    self.debug_print(f"-> RGB/Multiband raster - text only")
                    symbols.append({
                        'label': layer.name(),
                        'symbol': None,
                        'color': None,  # No color = no symbol drawn
                        'layer_type': 'raster_rgb',
                        'geometry_type': 'raster',
                        'text_only': True  # Special flag for text-only display
                    })
                    
                else:
                    # Single band grayscale or other - simple symbol
                    self.debug_print(f"-> Other raster type - simple symbol")
                    symbols.append({
                        'label': layer.name(),
                        'symbol': None,
                        'color': QColor('lightgray'),
                        'layer_type': 'raster_other',
                        'geometry_type': 'raster'
                    })
                
                return symbols
            
            # Handle vector layers
            if is_vector:
                self.debug_print(f"-> Vector layer detected (class-based)")
                # Get geometry type
                geometry_type = 'unknown'
                if hasattr(layer, 'geometryType'):
                    try:
                        geom_type = layer.geometryType()
                        self.debug_print(f"-> Raw geometry type: {geom_type}")
                        if geom_type == 0:  # Point
                            geometry_type = 'point'
                        elif geom_type == 1:  # Line
                            geometry_type = 'line'
                        elif geom_type == 2:  # Polygon
                            geometry_type = 'polygon'
                    except Exception as e:
                        self.debug_print(f"-> Error getting geometry type: {e}")
                
                self.debug_print(f"-> Geometry type: {geometry_type}")
                
                if not hasattr(layer, 'renderer') or not layer.renderer():
                    self.debug_print(f"-> Layer {layer.name()} has no renderer")
                    symbols.append({
                        'label': layer.name(),
                        'symbol': None,
                        'color': QColor('lightblue'),
                        'layer_type': 'vector_no_renderer',
                        'geometry_type': geometry_type
                    })
                    return symbols
                    
                renderer = layer.renderer()
                renderer_type = renderer.type()
                self.debug_print(f"-> Renderer type: {renderer_type}")
                
                if renderer_type == 'singleSymbol':
                    self.debug_print(f"-> Processing singleSymbol renderer")
                    # Single symbol renderer
                    symbol = renderer.symbol()
                    if symbol:
                        symbol_color = symbol.color() if hasattr(symbol, 'color') else QColor('blue')
                        self.debug_print(f"-> Symbol found, color: {symbol_color.name()}")
                        symbols.append({
                            'label': layer.name(),
                            'symbol': symbol,
                            'color': symbol_color,
                            'layer_type': 'vector',
                            'geometry_type': geometry_type
                        })
                    else:
                        self.debug_print(f"-> No symbol in singleSymbol renderer")
                        
                elif renderer_type == 'categorizedSymbol':
                    # Categorized renderer - with crash protection
                    self.debug_print(f"-> Processing categorizedSymbol renderer")
                    try:
                        categories = renderer.categories()
                        self.debug_print(f"-> Found {len(categories)} categories")
                        
                        for i, category in enumerate(categories):
                            try:
                                if not category.renderState():  # Skip disabled categories
                                    continue
                                    
                                # Safely get symbol with validation
                                symbol = None
                                try:
                                    symbol = category.symbol()
                                    if symbol is None:
                                        self.debug_print(f"-> Category {i}: symbol is None")
                                        continue
                                        
                                    # Test if symbol is valid by checking basic properties
                                    _ = symbol.type()  # This might crash if symbol is invalid
                                    self.debug_print(f"-> Category {i}: symbol is valid")
                                    
                                except Exception as symbol_error:
                                    self.debug_print(f"-> Category {i}: Invalid symbol detected: {symbol_error}")
                                    symbol = None
                                    continue
                                
                                label = category.label() if category.label() else str(category.value())
                                
                                # Safely get color
                                symbol_color = QColor('green')  # Default
                                try:
                                    if symbol and hasattr(symbol, 'color'):
                                        symbol_color = symbol.color()
                                except:
                                    self.debug_print(f"-> Category {i}: Failed to get symbol color")
                                
                                symbols.append({
                                    'label': label,
                                    'symbol': symbol,
                                    'color': symbol_color,
                                    'layer_type': 'vector',
                                    'geometry_type': geometry_type
                                })
                                self.debug_print(f"-> Category {i}: Added '{label}' successfully")
                                
                            except Exception as cat_error:
                                self.debug_print(f"-> Category {i}: Error processing category: {cat_error}")
                                continue
                                
                    except Exception as renderer_error:
                        self.debug_print(f"-> Error processing categorized renderer: {renderer_error}")
                        # Fallback: create simple symbol
                        symbols.append({
                            'label': f"{layer.name()} (Categorized - Error)",
                            'symbol': None,
                            'color': QColor('red'),
                            'layer_type': 'vector_error',
                            'geometry_type': geometry_type
                        })
                            
                elif renderer_type == 'graduatedSymbol':
                    # Graduated renderer
                    for range_item in renderer.ranges():
                        symbols.append({
                            'label': range_item.label(),
                            'symbol': range_item.symbol(),
                            'color': range_item.symbol().color() if hasattr(range_item.symbol(), 'color') else QColor('orange'),
                            'layer_type': 'vector',
                            'geometry_type': geometry_type
                        })
                        
                elif renderer_type == 'RuleRenderer':
                    # Rule-based renderer
                    root_rule = renderer.rootRule()
                    if root_rule:
                        for rule in root_rule.children():
                            if rule.isActive() and rule.symbol():
                                label = rule.label() or rule.filterExpression() or 'Rule'
                                symbols.append({
                                    'label': label,
                                    'symbol': rule.symbol(),
                                    'color': rule.symbol().color() if hasattr(rule.symbol(), 'color') else QColor('purple'),
                                    'layer_type': 'vector',
                                    'geometry_type': geometry_type
                                })
                else:
                    # Fallback for other renderer types
                    symbol = getattr(renderer, 'symbol', lambda: None)()
                    if symbol:
                        symbols.append({
                            'label': layer.name(),
                            'symbol': symbol,
                            'color': symbol.color() if hasattr(symbol, 'color') else QColor('red'),
                            'layer_type': 'vector',
                            'geometry_type': geometry_type
                        })
                    else:
                        symbols.append({
                            'label': layer.name(),
                            'symbol': None,
                            'color': QColor('gray'),
                            'layer_type': 'vector',
                            'geometry_type': geometry_type
                        })
            else:
                # Other layer types (mesh, plugin, etc.)
                symbols.append({
                    'label': layer.name(),
                    'symbol': None,
                    'color': QColor('lightcyan'),
                    'layer_type': 'other',
                    'geometry_type': 'other'
                })
                        
        except Exception as e:
            self.debug_print(f"Error getting symbols for layer {layer.name()}: {e}")
            # Fallback: create a basic symbol representation
            symbols.append({
                'label': layer.name(),
                'symbol': None,
                'color': QColor('lightblue'),
                'layer_type': 'unknown',
                'geometry_type': 'unknown'
            })
        
        self.debug_print(f"Found {len(symbols)} symbols for layer {layer.name()}")
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
        
    def toggle_debug_mode(self, enabled):
        """Toggle debug mode"""
        self.debug_mode = enabled
        self.debug_print(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
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
            QgsProject.instance().legendLayersAdded.disconnect(self.on_layers_changed)
            
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

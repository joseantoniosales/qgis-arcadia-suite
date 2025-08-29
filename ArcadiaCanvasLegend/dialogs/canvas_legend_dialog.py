"""
Dialog for configuring canvas legend overlay
Handles all user interface interactions for legend configuration
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer, QRect, QPointF, QSize
from qgis.PyQt.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
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
    """Widget for displaying legend overlay on canvas ONLY"""
    
    def __init__(self, canvas, parent=None):
        # CRITICAL: Set canvas as parent and configure for canvas-only overlay
        super().__init__(canvas)  # Canvas as direct parent
        self.canvas = canvas
        
        # Configure widget to be canvas-only overlay
        self.setWindowFlags(Qt.Widget)  # Use Widget instead of Tool to limit to parent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        
        # Ensure widget stays within canvas bounds
        self.setParent(canvas)
        
        self.legend_items = []
        self.settings = {}
        self.symbol_size = 16  # Size for legend symbols
        self.debug_mode = False  # Debug mode off by default
        self._painting = False  # Flag to prevent recursive painting
        self._resizing = False  # Flag to prevent painting during resize
        self._update_scheduled = False  # Flag to prevent multiple update calls
        
    def debug_print(self, message):
        """Print debug message only if debug mode is enabled"""
        if self.debug_mode:
            print(message)
        
    def update_legend_content(self, legend_items, settings):
        """Update legend content and settings with crash protection"""
        if self._painting or self._resizing:
            # Schedule update for later if we're in a sensitive operation
            QTimer.singleShot(100, lambda: self.update_legend_content(legend_items, settings))
            return
            
        self.legend_items = legend_items
        self.settings = settings
        
        # Update debug mode from settings
        self.debug_mode = settings.get('debug_mode', False)
        
        # Auto-size if enabled
        if settings.get('auto_size', True):
            self.calculate_optimal_size()
        
        # Schedule safe update
        if not self._update_scheduled:
            self._update_scheduled = True
            QTimer.singleShot(10, self._delayed_update)
        
    def calculate_optimal_size(self):
        """Calculate optimal size based on content with crash protection"""
        if self._resizing:
            # Don't resize while already resizing
            return
            
        if not self.legend_items:
            self._safe_resize(200, 100)  # Minimum size
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
        self._safe_resize(int(width), int(height))
        
    def _safe_resize(self, width, height):
        """Safely resize widget with crash protection"""
        if self._painting or self._resizing:
            # Schedule resize for later
            QTimer.singleShot(50, lambda: self._safe_resize(width, height))
            return
            
        self._resizing = True
        try:
            self.resize(width, height)
        except Exception as e:
            self.debug_print(f"Error in safe resize: {e}")
        finally:
            QTimer.singleShot(10, lambda: setattr(self, '_resizing', False))
        
    def paintEvent(self, event):
        """Paint the legend overlay with crash protection"""
        # Prevent recursive painting
        if self._painting or self._resizing:
            self.debug_print("Skipping paintEvent: already painting or resizing")
            return
            
        if not self.legend_items:
            return
            
        self._painting = True
        painter = QPainter()
        
        try:
            if not painter.begin(self):
                self.debug_print("Error: Failed to begin painting on legend overlay")
                return
                
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
            if painter.isActive():
                painter.end()
            self._painting = False
            
    def resizeEvent(self, event):
        """Handle resize events with crash protection"""
        self._resizing = True
        try:
            super().resizeEvent(event)
            # Schedule update after resize is complete
            if not self._update_scheduled:
                self._update_scheduled = True
                QTimer.singleShot(50, self._delayed_update)
        except Exception as e:
            self.debug_print(f"Error in resizeEvent: {e}")
        finally:
            self._resizing = False
            
    def _delayed_update(self):
        """Delayed update after resize"""
        try:
            self._update_scheduled = False
            if not self._painting and not self._resizing:
                self.update()
        except Exception as e:
            self.debug_print(f"Error in delayed update: {e}")
            
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
                    is_header = symbol_info.get('is_header', False)
                    
                    self.debug_print(f"  Drawing symbol {i} for {layer_name}: type={layer_type}, geom={geometry_type}, has_symbol={symbol is not None}, text_only={text_only}, is_header={is_header}")
                    
                    # Handle header items (layer names for categorized/graduated/rules)
                    if is_header:
                        painter.setPen(QColor('black'))
                        painter.setFont(QFont('Arial', 10, QFont.Bold))
                        painter.drawText(padding, y_offset + 15, label)
                        self.debug_print(f"  - Header drawn for: {label}")
                        y_offset += line_height
                        continue
                    
                    # Draw symbol only if not text_only and not header
                    if not text_only and not is_header:
                        self.draw_symbol_safe(painter, symbol_rect, symbol, symbol_color, layer_type, geometry_type)
                    else:
                        self.debug_print(f"  - Skipping symbol draw for text-only/header layer: {label}")
                    
                    # Draw label with better positioning
                    painter.setPen(QColor('black'))
                    painter.setFont(QFont('Arial', 9))
                    # Adjust text position for text-only items (no symbol space needed)
                    text_x = padding + (symbol_width + 15 if not text_only and not is_header else 5)
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
        # Only skip if we're in a dangerous resize operation, not during normal painting
        if hasattr(self, '_resizing') and self._resizing:
            self.debug_print("    -> Skipping symbol draw: resizing in progress")
            painter.fillRect(symbol_rect, QColor('lightgray'))
            return
            
        method_used = "none"
        try:
            self.debug_print(f"    draw_symbol_safe: layer_type={layer_type}, geometry_type={geometry_type}, has_symbol={symbol is not None}")
            
            # CRITICAL: Advanced symbol validation with timeout protection
            if symbol and layer_type != 'raster':
                # Multi-level validation to catch ALL types of corrupted symbols
                is_symbol_safe = False
                try:
                    # Level 1: Basic existence and type check
                    if symbol is None:
                        self.debug_print(f"    -> Symbol is None")
                        raise Exception("Symbol is None")
                    
                    # Level 2: Test critical properties that can crash
                    symbol_type = symbol.type()  # Can crash
                    symbol_layer_count = symbol.symbolLayerCount() if hasattr(symbol, 'symbolLayerCount') else 0
                    
                    # Level 3: Test color access (another crash point)
                    test_color = symbol.color() if hasattr(symbol, 'color') else QColor('gray')
                    
                    # Level 4: Test size access
                    if hasattr(symbol, 'size'):
                        test_size = symbol.size()
                    
                    # Level 5: Check if symbol has any symbol layers (empty symbols crash)
                    if symbol_layer_count == 0:
                        self.debug_print(f"    -> Symbol has no layers, treating as unsafe")
                        raise Exception("Symbol has no layers")
                    
                    self.debug_print(f"    -> Symbol validation passed: type={symbol_type}, layers={symbol_layer_count}")
                    is_symbol_safe = True
                    
                except Exception as validation_error:
                    self.debug_print(f"    -> CRITICAL: Advanced symbol validation failed: {validation_error}")
                    is_symbol_safe = False
                
                # If symbol failed validation, use safe fallback
                if not is_symbol_safe:
                    self.debug_print(f"    -> Using safe color fallback for corrupted symbol")
                    painter.fillRect(symbol_rect, symbol_color or QColor('lightgray'))
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


class CanvasLegendDockWidget(QDockWidget):
    """Main dock widget for canvas legend configuration"""
    
    def __init__(self, iface, parent=None):
        super().__init__("Arcadia Canvas Legend", parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.legend_overlay = None
        self.auto_update_enabled = True
        self.debug_mode = False  # Debug mode disabled by default
        
        # Create central widget
        self.central_widget = QWidget()
        self.setWidget(self.central_widget)
        
        # Configure dock widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        
        self.setupUi()
        self.load_settings()
        self.connect_signals()
        self.connect_layer_signals()
        
        # Connect close event to cleanup
        self.closeEvent = self.custom_close_event
        
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
        self.setWindowTitle('Arcadia Canvas Legend - Beta 13 (Dock)')
        
        # Main layout for central widget
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Smaller margins for dock
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Position and Size Tab
        self.setup_position_tab()
        
        # Style Tab
        self.setup_style_tab()
        
        # Content Tab
        self.setup_content_tab()
        
        # Export Tab
        self.setup_export_tab()
        
        # Control buttons (more compact for dock)
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton(self.tr('Preview'))
        self.apply_btn = QPushButton(self.tr('Apply'))
        self.hide_legend_btn = QPushButton(self.tr('Hide'))
        
        # Make buttons smaller for dock
        for btn in [self.preview_btn, self.apply_btn, self.hide_legend_btn]:
            btn.setMaximumHeight(30)
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.hide_legend_btn)
        
        main_layout.addLayout(button_layout)
        
        # Set minimum width for dock
        self.setMinimumWidth(280)
        
    def custom_close_event(self, event):
        """Custom close event to cleanup overlay"""
        self.cleanup_overlay()
        event.accept()
        
    def cleanup_overlay(self):
        """Safely cleanup overlay"""
        try:
            if self.legend_overlay:
                self.legend_overlay.hide()
                self.legend_overlay.deleteLater()
                self.legend_overlay = None
        except Exception as e:
            self.debug_print(f"Error cleaning up overlay: {e}")
        
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
                    # Categorized renderer - with crash protection and layer name
                    self.debug_print(f"-> Processing categorizedSymbol renderer")
                    try:
                        categories = renderer.categories()
                        self.debug_print(f"-> Found {len(categories)} categories")
                        
                        # Add layer name as header for categorized symbols
                        symbols.append({
                            'label': f"{layer.name()} (Categories)",
                            'symbol': None,
                            'color': QColor('darkblue'),
                            'layer_type': 'vector_header',
                            'geometry_type': geometry_type,
                            'is_header': True
                        })
                        
                        for i, category in enumerate(categories):
                            try:
                                if not category.renderState():  # Skip disabled categories
                                    continue
                                    
                                # Safely get symbol with advanced validation
                                symbol = self._safe_get_symbol(category.symbol, f"Category {i}")
                                if symbol is None:
                                    continue
                                
                                label = category.label() if category.label() else str(category.value())
                                symbol_color = self._safe_get_symbol_color(symbol, QColor('green'))
                                
                                symbols.append({
                                    'label': f"  └ {label}",  # Indent category items
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
                    # Graduated renderer - with layer name header
                    self.debug_print(f"-> Processing graduatedSymbol renderer")
                    try:
                        ranges = renderer.ranges()
                        self.debug_print(f"-> Found {len(ranges)} ranges")
                        
                        # Add layer name as header
                        symbols.append({
                            'label': f"{layer.name()} (Graduated)",
                            'symbol': None,
                            'color': QColor('darkorange'),
                            'layer_type': 'vector_header',
                            'geometry_type': geometry_type,
                            'is_header': True
                        })
                        
                        for i, range_item in enumerate(ranges):
                            try:
                                symbol = self._safe_get_symbol(range_item.symbol, f"Range {i}")
                                if symbol is None:
                                    continue
                                    
                                label = range_item.label() if range_item.label() else f"Range {i+1}"
                                symbol_color = self._safe_get_symbol_color(symbol, QColor('orange'))
                                
                                symbols.append({
                                    'label': f"  └ {label}",
                                    'symbol': symbol,
                                    'color': symbol_color,
                                    'layer_type': 'vector',
                                    'geometry_type': geometry_type
                                })
                                
                            except Exception as range_error:
                                self.debug_print(f"-> Range {i}: Error processing range: {range_error}")
                                continue
                                
                    except Exception as renderer_error:
                        self.debug_print(f"-> Error processing graduated renderer: {renderer_error}")
                        symbols.append({
                            'label': f"{layer.name()} (Graduated - Error)",
                            'symbol': None,
                            'color': QColor('red'),
                            'layer_type': 'vector_error',
                            'geometry_type': geometry_type
                        })
                        
                elif renderer_type == 'RuleRenderer':
                    # Rule-based renderer - with layer name header
                    self.debug_print(f"-> Processing RuleRenderer")
                    try:
                        root_rule = renderer.rootRule()
                        if root_rule:
                            # Add layer name as header
                            symbols.append({
                                'label': f"{layer.name()} (Rules)",
                                'symbol': None,
                                'color': QColor('purple'),
                                'layer_type': 'vector_header',
                                'geometry_type': geometry_type,
                                'is_header': True
                            })
                            
                            rules = root_rule.children()
                            for i, rule in enumerate(rules):
                                try:
                                    if rule.isActive() and rule.symbol():
                                        symbol = self._safe_get_symbol(rule.symbol, f"Rule {i}")
                                        if symbol is None:
                                            continue
                                            
                                        label = rule.label() or rule.filterExpression() or f'Rule {i+1}'
                                        symbol_color = self._safe_get_symbol_color(symbol, QColor('purple'))
                                        
                                        symbols.append({
                                            'label': f"  └ {label}",
                                            'symbol': symbol,
                                            'color': symbol_color,
                                            'layer_type': 'vector',
                                            'geometry_type': geometry_type
                                        })
                                        
                                except Exception as rule_error:
                                    self.debug_print(f"-> Rule {i}: Error processing rule: {rule_error}")
                                    continue
                                    
                    except Exception as renderer_error:
                        self.debug_print(f"-> Error processing rule renderer: {renderer_error}")
                        symbols.append({
                            'label': f"{layer.name()} (Rules - Error)",
                            'symbol': None,
                            'color': QColor('red'),
                            'layer_type': 'vector_error',
                            'geometry_type': geometry_type
                        })
                else:
                    # Fallback for other renderer types (pointDisplacement, heatmapRenderer, etc.)
                    self.debug_print(f"-> Processing unknown renderer type: {renderer_type}")
                    try:
                        # Try to get symbol from renderer using different methods
                        symbol = None
                        
                        # Method 1: Direct symbol() method with safe getter
                        if hasattr(renderer, 'symbol'):
                            symbol = self._safe_get_symbol(renderer.symbol, f"Renderer {renderer_type}")
                        
                        # Method 2: Try sourceSymbol() for some renderer types
                        elif hasattr(renderer, 'sourceSymbol'):
                            symbol = self._safe_get_symbol(renderer.sourceSymbol, f"Renderer {renderer_type}")
                        
                        if symbol:
                            symbol_color = self._safe_get_symbol_color(symbol, QColor('gray'))
                            symbols.append({
                                'label': f"{layer.name()} ({renderer_type})",
                                'symbol': symbol,
                                'color': symbol_color,
                                'layer_type': 'vector',
                                'geometry_type': geometry_type
                            })
                        else:
                            # No symbol found, create simple representation
                            symbols.append({
                                'label': f"{layer.name()} ({renderer_type})",
                                'symbol': None,
                                'color': QColor('lightgray'),
                                'layer_type': 'vector_simple',
                                'geometry_type': geometry_type
                            })
                            
                    except Exception as renderer_error:
                        self.debug_print(f"-> Error processing unknown renderer: {renderer_error}")
                        # Ultimate fallback: gray rectangle
                        symbols.append({
                            'label': f"{layer.name()} (Unknown Renderer)",
                            'symbol': None,
                            'color': QColor('lightgray'),
                            'layer_type': 'vector_fallback',
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
        """Position the legend overlay on canvas with crash protection"""
        if not self.legend_overlay:
            return
            
        # Get canvas size (local coordinates since overlay is child of canvas)
        canvas_size = self.canvas.size()
        
        # Use safe resize method
        target_width = self.width_spin.value()
        target_height = self.height_spin.value()
        self.legend_overlay._safe_resize(target_width, target_height)
        
        # Wait a moment for resize to complete before positioning
        QTimer.singleShot(20, lambda: self._complete_positioning_canvas_local(canvas_size))
        
    def _complete_positioning_canvas_local(self, canvas_size):
        """Complete the positioning in canvas local coordinates"""
        if not self.legend_overlay:
            return
            
        overlay_size = self.legend_overlay.size()
        
        position = self.position_combo.currentText().lower()
        x_offset = self.x_offset_spin.value()
        y_offset = self.y_offset_spin.value()
        
        # Calculate position relative to canvas (local coordinates)
        if 'top' in position and 'left' in position:
            x = x_offset
            y = y_offset
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
            x = x_offset
            y = y_offset
            
        # Ensure overlay stays within canvas bounds
        x = max(0, min(x, canvas_size.width() - overlay_size.width()))
        y = max(0, min(y, canvas_size.height() - overlay_size.height()))
        
        self.legend_overlay.move(x, y)
        self.debug_print(f"Overlay positioned at canvas coordinates: ({x}, {y})")
        
    def export_current_view(self):
        """Export current canvas view with legend"""
        try:
            self.export_to_png()
        except Exception as e:
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error exporting view: {}').format(str(e)))
    
    def _safe_get_symbol(self, symbol_func, context="unknown"):
        """Safely get symbol with comprehensive validation"""
        try:
            if callable(symbol_func):
                symbol = symbol_func()
            else:
                symbol = symbol_func
                
            if symbol is None:
                self.debug_print(f"-> {context}: symbol is None")
                return None
                
            # Multi-level validation
            # Level 1: Type check (can crash)
            symbol_type = symbol.type()
            
            # Level 2: Layer count check (empty symbols crash)
            if hasattr(symbol, 'symbolLayerCount'):
                layer_count = symbol.symbolLayerCount()
                if layer_count == 0:
                    self.debug_print(f"-> {context}: symbol has no layers")
                    return None
            
            # Level 3: Test color access
            if hasattr(symbol, 'color'):
                test_color = symbol.color()
            
            self.debug_print(f"-> {context}: symbol validation passed")
            return symbol
            
        except Exception as symbol_error:
            self.debug_print(f"-> {context}: Invalid symbol detected: {symbol_error}")
            return None
    
    def _safe_get_symbol_color(self, symbol, default_color):
        """Safely get symbol color with fallback"""
        try:
            if symbol and hasattr(symbol, 'color'):
                return symbol.color()
        except Exception as e:
            self.debug_print(f"-> Failed to get symbol color: {e}")
        return default_color
            
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
        """Hide the legend overlay"""
        try:
            if self.legend_overlay:
                self.legend_overlay.hide()
                self.save_settings()  # Save settings when hiding
        except Exception as e:
            QMessageBox.warning(self, self.tr('Warning'), 
                              self.tr('Error hiding legend: {}').format(str(e)))
        
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

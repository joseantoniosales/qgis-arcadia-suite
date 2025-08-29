"""
Dialog for configuring canvas legend overlay
BETA 21 ENHANCED - Emergency crash protection and progressive degradation
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

# PLUGIN VERSION CONTROL - Single source of truth
PLUGIN_VERSION = "1.0.22"
PLUGIN_VERSION_NAME = "Beta 22"

# BETA 20: Import new architecture modules
try:
    from ..tools.symbol_cache_manager import SymbolCacheManager
    from ..tools.symbol_data_extractor import SymbolDataExtractor, LayerSymbolInfo
    BETA20_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"BETA 20: Failed to import new modules: {e}")
    BETA20_MODULES_AVAILABLE = False


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
        self._destroyed = False  # CRITICAL: Flag to prevent access after destruction
        
        # BETA 20: Initialize cache tracking
        self._current_cache_keys = set()
        self._symbol_cache = None  # Will be set by parent dialog
        self._beta20_enabled = False  # Will be enabled by parent dialog
        
    def closeEvent(self, event):
        """Override close event to set destroyed flag"""
        self._destroyed = True
        super().closeEvent(event)
        
    def hideEvent(self, event):
        """Override hide event to set destroyed flag"""
        self._destroyed = True
        super().hideEvent(event)
        
    def deleteLater(self):
        """Override deleteLater to set destroyed flag immediately"""
        self._destroyed = True
        super().deleteLater()
        
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
        """Paint the legend overlay - BETA 20 SIMPLIFIED with cache system"""
        # CRITICAL: Ultimate crash protection - multiple safety checks
        if getattr(self, '_destroyed', False):
            self.debug_print("ABORT: Overlay marked as destroyed")
            return
        
        # EMERGENCY SAFETY: Check if we should even attempt painting
        if getattr(self, '_emergency_disable_painting', False):
            self.debug_print("EMERGENCY: Painting completely disabled")
            return
            
        # BETA 20: Check for cache-based system availability
        beta20_enabled = getattr(self, '_beta20_enabled', False)
        symbol_cache = getattr(self, '_symbol_cache', None)
        
        self.debug_print(f"PAINT: Beta20={beta20_enabled}, Cache={symbol_cache is not None}")
        
        # BETA 20: Use simplified cache-based painting if available
        if beta20_enabled and symbol_cache is not None:
            try:
                self.debug_print("USING BETA 20 CACHE-BASED SYSTEM")
                self._paint_with_cache_beta20(event)
                return
            except Exception as e:
                self.debug_print(f"BETA 20 FAILED: {e}")
                # Force emergency mode
                self._emergency_disable_painting = True
                return
            
        # Fallback to legacy system with all protections
        self.debug_print("USING LEGACY SYSTEM")
        self._paint_legacy_system(event)
    
    def _paint_with_cache_beta20(self, event):
        """BETA 20: Simplified painting using cache system"""
        if getattr(self, '_destroyed', False):
            return
            
        # CRITICAL: Prevent recursive painting
        if getattr(self, '_painting', False) or getattr(self, '_resizing', False):
            self.debug_print("BETA 20: Skipping paint - already painting or resizing")
            return
            
        # EMERGENCY: Check for emergency disable
        if getattr(self, '_emergency_disable_painting', False):
            self._paint_emergency_mode()
            return
            
        if not self.legend_items:
            self.debug_print("BETA 20: No legend items to paint")
            return
            
        # Set painting flag
        self._painting = True
        painter = QPainter()
        
        try:
            self.debug_print("BETA 20: Starting cache-based painting")
            
            if not painter.begin(self):
                self.debug_print("BETA 20: Failed to begin painting")
                return
                
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw background and frame (no API access needed)
            self._draw_background_and_frame_beta20(painter)
            
            # Draw legend items using cache
            y_offset = self._draw_title_beta20(painter)
            
            for item in self.legend_items:
                y_offset = self._draw_legend_item_beta20(painter, item, y_offset)
            
            self.debug_print("BETA 20: Cache-based painting completed successfully")
                
        except Exception as e:
            self.debug_print(f"BETA 20: Error in cache-based painting: {e}")
            import traceback
            traceback.print_exc()
            # Force emergency mode for future paints
            self._emergency_disable_painting = True
        finally:
            if painter.isActive():
                painter.end()
            self._painting = False
    
    def _paint_emergency_mode(self):
        """Ultra-safe emergency painting mode"""
        try:
            self.debug_print("EMERGENCY MODE: Using crash-proof rendering")
            painter = QPainter()
            if painter.begin(self):
                # Ultra-simple rendering that should never crash
                painter.fillRect(self.rect(), QColor(240, 240, 240, 200))  # Light gray background
                painter.setPen(QColor(100, 100, 100))
                painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
                
                # Simple text
                painter.setPen(QColor(0, 0, 0))
                painter.setFont(QFont('Arial', 10))
                painter.drawText(10, 20, "Legend (Safe Mode)")
                painter.drawText(10, 40, "Restart QGIS to restore")
                painter.drawText(10, 60, "full functionality")
                
                painter.end()
        except Exception as e:
            self.debug_print(f"EMERGENCY MODE: Even emergency painting failed: {e}")
            # At this point, just give up gracefully
    
    def _paint_legacy_system(self, event):
        """Legacy painting system with all Beta 19 protections"""
            
        # BETA 19: Multi-layer protection against QML style loading crashes
        # Protection Layer 1: Check our own style loading flag
        if getattr(self, '_style_loading_detected', False):
            self.debug_print("BETA 19: ABORT: Style loading detected (self) - skipping paint")
            return
            
        # Protection Layer 2: Check parent dialog for style loading
        dialog = self.parent()
        while dialog and not hasattr(dialog, '_style_loading_detected'):
            dialog = dialog.parent()
        
        if dialog and getattr(dialog, '_style_loading_detected', False):
            self.debug_print("BETA 19: ABORT: Style loading detected (parent) - skipping paint")
            return
            
        # Protection Layer 3: Global layer renderer stability check
        try:
            project = QgsProject.instance()
            if project:
                layers = project.mapLayers().values()
                for layer in layers:
                    if hasattr(layer, 'renderer') and layer.renderer():
                        # Quick renderer stability check
                        try:
                            renderer = layer.renderer()
                            if not renderer:
                                self.debug_print("BETA 19: ABORT: Layer has null renderer - style change in progress")
                                return
                            # Check if renderer is accessible
                            _ = renderer.type()
                        except:
                            self.debug_print("BETA 19: ABORT: Renderer access failed - style change in progress")
                            return
        except:
            self.debug_print("BETA 19: ABORT: Project layer check failed - unsafe state")
            return
            
        # Check if parent canvas still exists and is valid
        if not self.canvas or not hasattr(self.canvas, 'isVisible'):
            self.debug_print("ABORT: Canvas invalid or missing")
            return
            
        # Check if widget is still valid
        try:
            if not self.isVisible() or not self.parent():
                self.debug_print("ABORT: Widget not visible or no parent")
                return
        except:
            self.debug_print("ABORT: Widget state check failed")
            return
            
        # Prevent recursive painting
        if self._painting or self._resizing:
            self.debug_print("Skipping paintEvent: already painting or resizing")
            return
            
        if not self.legend_items:
            return
            
        # CRITICAL: Set painting flag BEFORE any operations
        self._painting = True
        painter = QPainter()
        
        try:
            # Additional check after QPainter creation
            if getattr(self, '_destroyed', False):
                self.debug_print("Overlay destroyed during painter setup - aborting")
                return
                
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
    
    # BETA 20: Cache-based drawing methods
    
    def _draw_background_and_frame_beta20(self, painter):
        """BETA 20: Draw background and frame without API access"""
        try:
            # Draw background if enabled
            if self.settings.get('show_background', True):
                bg_color = QColor(self.settings.get('background_color', 'white'))
                bg_color.setAlpha(self.settings.get('background_alpha', 200))
                painter.fillRect(self.rect(), bg_color)
                
            # Draw frame if enabled
            if self.settings.get('show_frame', True):
                frame_color = QColor(self.settings.get('frame_color', 'black'))
                painter.setPen(frame_color)
                painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        except Exception as e:
            self.debug_print(f"BETA 20: Error drawing background/frame: {e}")
    
    def _draw_title_beta20(self, painter):
        """BETA 20: Draw title and return y_offset"""
        y_offset = 10
        try:
            if self.settings.get('show_title', True):
                title_text = self.settings.get('title_text', 'Map Legend')
                painter.setPen(QColor('black'))
                painter.setFont(QFont('Arial', 12, QFont.Bold))
                painter.drawText(10, y_offset + 15, title_text)
                y_offset += 25
        except Exception as e:
            self.debug_print(f"BETA 20: Error drawing title: {e}")
        
        return y_offset
    
    def _draw_legend_item_beta20(self, painter, item, y_offset):
        """BETA 20: Draw legend item using cache system"""
        try:
            line_height = 25
            padding = 10
            symbol_width = self.symbol_size
            symbol_height = self.symbol_size
            
            layer_name = item.get('layer_name', 'Unknown Layer')
            layer_id = item.get('layer_id', '')
            symbols = item.get('symbols', [])
            
            if not symbols:
                # No symbols, draw simple entry
                painter.setPen(QColor('black'))
                painter.setFont(QFont('Arial', 9))
                painter.drawText(padding, y_offset + 15, layer_name)
                return y_offset + line_height
            
            # Draw each symbol for this layer
            current_y = y_offset
            for symbol_info in symbols:
                symbol_rect = QRect(padding, current_y + 5, symbol_width, symbol_height)
                
                # Try to get symbol from cache
                symbol_pixmap = None
                if self._symbol_cache:
                    symbol_data = {
                        'type': symbol_info.get('type', 'unknown'),
                        'color': symbol_info.get('color', QColor('gray')),
                        'symbol': symbol_info.get('symbol')
                    }
                    
                    cache_key = f"{layer_id}_{symbol_info.get('label', 'default')}_{symbol_width}x{symbol_height}"
                    self._current_cache_keys.add(cache_key)
                    
                    symbol_pixmap = self._symbol_cache.get_symbol_pixmap(
                        layer_id, symbol_data, (symbol_width, symbol_height)
                    )
                
                # Draw symbol
                if symbol_pixmap and not symbol_pixmap.isNull():
                    # Draw cached symbol
                    painter.drawPixmap(symbol_rect, symbol_pixmap)
                else:
                    # Draw placeholder while loading
                    if self._symbol_cache:
                        placeholder = self._symbol_cache.get_placeholder_pixmap((symbol_width, symbol_height))
                        painter.drawPixmap(symbol_rect, placeholder)
                    else:
                        # Simple fallback
                        painter.fillRect(symbol_rect, QColor('lightgray'))
                
                # Draw label
                label = symbol_info.get('label', layer_name)
                text_x = padding + symbol_width + 15
                painter.setPen(QColor('black'))
                painter.setFont(QFont('Arial', 9))
                painter.drawText(text_x, current_y + 15, label)
                
                current_y += line_height
            
            return current_y
            
        except Exception as e:
            self.debug_print(f"BETA 20: Error drawing legend item: {e}")
            return y_offset + 25  # Fallback spacing
    
    def set_beta20_components(self, symbol_cache, enabled=True):
        """Set Beta 20 components from parent dialog"""
        self._symbol_cache = symbol_cache
        self._beta20_enabled = enabled
            
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
                    error_type = symbol_info.get('error_type', None)  # For placeholder detection
                    
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
                        # Check if we need to draw a placeholder
                        if error_type:
                            self.draw_symbol_placeholder(painter, symbol_rect, error_type)
                        else:
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
        """Draw symbol with multiple fallback methods and crash protection - BETA 19"""
        # CRITICAL: Check if overlay is destroyed
        if getattr(self, '_destroyed', False):
            self.debug_print("    -> Skipping symbol draw: overlay is destroyed")
            return
            
        # BETA 19: Check for style loading state before any symbol operations
        if getattr(self, '_style_loading_detected', False):
            self.debug_print("    -> Skipping symbol draw: style loading detected")
            painter.fillRect(symbol_rect, QColor('lightgray'))
            return
            
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
                    
                    # Level 4: DEFENSIVE - Test parent layer validity
                    if hasattr(symbol, 'layer'):
                        parent_layer = getattr(symbol, 'layer', None)
                        if parent_layer and hasattr(parent_layer, 'isValid'):
                            if not parent_layer.isValid():
                                self.debug_print(f"    -> Symbol's parent layer is invalid")
                                raise Exception("Parent layer invalid")
                    
                    # Level 5: Test size access
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
            # Emergency fallback - use placeholder system
            self.draw_symbol_placeholder(painter, symbol_rect, "corrupted")
            method_used = "emergency_placeholder"
            
        print(f"    -> Final method used: {method_used}")


class CanvasLegendDockWidget(QDockWidget):
    """Main dock widget for canvas legend configuration - BETA 20 REFACTORED"""
    
    def __init__(self, iface, parent=None):
        super().__init__("Arcadia Canvas Legend", parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.legend_overlay = None
        self.auto_update_enabled = True
        self.debug_mode = False  # Debug mode disabled by default
        
        # Version logging using centralized variable
        self.debug_print(f"PLUGIN: Starting {PLUGIN_VERSION_NAME} (v{PLUGIN_VERSION})")
        
        # CRITICAL: Initialize protection flags
        self._applying_legend = False  # Prevent recreation loops
        self._last_apply_time = 0  # Throttle rapid applies
        
        # BETA 18-19: Protección específica para carga de estilos
        self._style_loading_detected = False
        self._last_style_change_time = 0
        self._style_safety_delay = 5000  # 5 segundos de espera tras cambios de estilo
        self._properties_dialog_open = False
        
        # BETA 20: Initialize new architecture components
        self._initialize_beta20_components()
        
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
        
    def _initialize_beta20_components(self):
        """Initialize Beta 20 architecture components"""
        try:
            if BETA20_MODULES_AVAILABLE:
                # Initialize symbol cache manager
                self._symbol_cache = SymbolCacheManager(max_cache_size=1000)
                self._symbol_cache.cache_updated.connect(self._on_symbol_cache_updated)
                
                # Initialize symbol data extractor
                self._symbol_data_extractor = SymbolDataExtractor(debug_mode=self.debug_mode)
                
                # Beta 20 flags
                self._beta20_enabled = True
                self._legend_data_cache = []
                self._last_extraction_time = 0
                
                self.debug_print("BETA 20: New architecture components initialized successfully")
                self.debug_print(f"BETA 20: Cache manager: {self._symbol_cache}")
                self.debug_print(f"BETA 20: Data extractor: {self._symbol_data_extractor}")
            else:
                # Fallback to legacy system
                self._beta20_enabled = False
                self._symbol_cache = None
                self._symbol_data_extractor = None
                self.debug_print("BETA 20: Fallback to legacy system - new modules not available")
                
        except Exception as e:
            self._beta20_enabled = False
            self._symbol_cache = None
            self._symbol_data_extractor = None
            self.debug_print(f"BETA 20: Failed to initialize new components: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_symbol_cache_updated(self, cache_key: str):
        """Callback when symbol cache is updated"""
        try:
            if self.legend_overlay and self.legend_overlay.isVisible():
                # Only update if we're using Beta 20 system
                if self._beta20_enabled and hasattr(self, '_current_cache_keys'):
                    if cache_key in self._current_cache_keys:
                        # This symbol was updated, refresh the overlay
                        QTimer.singleShot(50, self._refresh_overlay_beta20)
        except Exception as e:
            self.debug_print(f"BETA 20: Error in cache update callback: {e}")
        
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
            
            # CRITICAL: Connect to layer style changes to detect symbology changes
            QgsProject.instance().layerStyleChanged.connect(self.on_layer_style_changed)
            
            # Additional signals for comprehensive detection
            QgsProject.instance().legendLayersAdded.connect(self.on_layers_changed)
            
            # Connect to each existing layer's signals for style changes
            self.connect_existing_layer_signals()
            
        except Exception as e:
            self.debug_print(f"Error connecting layer signals: {e}")
            
    def connect_existing_layer_signals(self):
        """Connect to existing layers' individual signals"""
        try:
            for layer in QgsProject.instance().mapLayers().values():
                if hasattr(layer, 'rendererChanged'):
                    layer.rendererChanged.connect(self.on_renderer_changed)
                if hasattr(layer, 'styleChanged'):
                    layer.styleChanged.connect(self.on_renderer_changed)
        except Exception as e:
            self.debug_print(f"Error connecting existing layer signals: {e}")
            
    def on_renderer_changed(self):
        """Handle renderer/symbology changes - BETA 19: ULTRA-PROTECCIÓN PARA CARGA QML"""
        try:
            # BETA 19: Detectar carga de estilos con protección ultra-agresiva
            from qgis.PyQt.QtCore import QTimer
            current_time = QTimer()
            current_ms = current_time.remainingTime() if hasattr(current_time, 'remainingTime') else 0
            
            self.debug_print("BETA 19: Renderer changed detected - activating ultra-protection")
            
            # Marcar que se detectó cambio de estilo
            self._style_loading_detected = True
            self._last_style_change_time = current_ms
            
            # CRITICAL: Check if this is a raster layer change
            sender_layer = self.sender()
            is_raster_change = False
            is_vector_style_change = False
            is_qml_loading = False
            
            if sender_layer and hasattr(sender_layer, '__class__'):
                layer_class_name = sender_layer.__class__.__name__
                if 'Raster' in layer_class_name:
                    is_raster_change = True
                    self.debug_print("BETA 19: RASTER renderer change detected")
                elif 'Vector' in layer_class_name:
                    is_vector_style_change = True
                    self.debug_print("BETA 19: VECTOR style change detected")
                    
                    # BETA 19: Check if this might be QML loading by inspecting renderer type changes
                    try:
                        if hasattr(sender_layer, 'renderer') and sender_layer.renderer():
                            renderer = sender_layer.renderer()
                            renderer_type = renderer.type() if hasattr(renderer, 'type') else "unknown"
                            if renderer_type in ['categorizedSymbol', 'graduatedSymbol', 'RuleRenderer']:
                                is_qml_loading = True
                                self.debug_print("BETA 19: QML LOADING DETECTED - Complex renderer change")
                    except:
                        # If we can't check the renderer, assume it's dangerous
                        is_qml_loading = True
                        self.debug_print("BETA 19: Renderer check failed - assuming QML loading")
            
            # BETA 19: Para cambios QML, usar protección ultra-extendida (10 segundos)
            if is_qml_loading:
                safety_delay = 10000  # 10 segundos para QML
                self.debug_print("BETA 19: QML loading detected - using 10 second protection")
            elif is_vector_style_change:
                safety_delay = 7000   # 7 segundos para cambios de vector
                self.debug_print("BETA 19: Vector style change - using 7 second protection")
            elif is_raster_change:
                safety_delay = 5000   # 5 segundos para raster
                self.debug_print("BETA 19: Raster change - using 5 second protection")
            else:
                safety_delay = 3000   # 3 segundos por defecto
                self.debug_print("BETA 19: General change - using 3 second protection")
            
            # BETA 19: Ocultar overlay inmediatamente durante cambios peligrosos
            if is_qml_loading or is_vector_style_change:
                if self.legend_overlay:
                    self.legend_overlay.setVisible(False)
                    self.debug_print("BETA 19: Overlay hidden during dangerous style change")
            
            # Store safety delay and schedule restoration
            self._style_safety_delay = safety_delay
            QTimer.singleShot(self._style_safety_delay, self._safe_post_style_update)
            
        except Exception as e:
            self.debug_print(f"BETA 19: Error in renderer change handler: {e}")
            # En caso de error, usar protección máxima
            self._style_loading_detected = True
            if hasattr(self, 'legend_overlay') and self.legend_overlay:
                self.legend_overlay.setVisible(False)
            QTimer.singleShot(10000, self._safe_post_style_update)  # 10 segundos de seguridad
            
    def force_overlay_recreation_raster_safe(self):
        """Force recreation with extended safety for raster layer changes"""
        try:
            self.debug_print("Force recreating overlay due to RASTER symbology changes")
            
            # Hide and destroy existing overlay with raster-safe approach
            if self.legend_overlay:
                # Mark as destroyed immediately
                self.legend_overlay._destroyed = True
                
                # Hide first
                try:
                    self.legend_overlay.hide()
                except:
                    pass
                
                # Delete with extended delay for raster safety
                try:
                    self.legend_overlay.deleteLater()
                except:
                    pass
                    
                self.legend_overlay = None
            
            # Extended delay for raster layer processing
            QTimer.singleShot(300, self.recreate_overlay_delayed_raster_safe)
            
        except Exception as e:
            self.debug_print(f"Error in force overlay recreation (raster): {e}")
            
    def recreate_overlay_delayed_raster_safe(self):
        """Recreate overlay after extended cleanup delay for raster safety"""
        try:
            self.debug_print("Recreating overlay after raster-safe delay")
            if self.auto_update_enabled:
                # Use apply_legend which has throttling and safety checks
                self.apply_legend()
        except Exception as e:
            self.debug_print(f"Error in delayed overlay recreation (raster): {e}")
            
    def force_overlay_recreation(self):
        """Force complete recreation of overlay to prevent symbol corruption crashes"""
        try:
            self.debug_print("Force recreating overlay due to symbology changes")
            
            # Hide and destroy existing overlay
            if self.legend_overlay:
                self.legend_overlay.hide()
                self.legend_overlay.deleteLater()
                self.legend_overlay = None
            
            # Small delay to ensure cleanup before recreation
            QTimer.singleShot(200, self.recreate_overlay_delayed)
            
        except Exception as e:
            self.debug_print(f"Error in force overlay recreation: {e}")
            
    def recreate_overlay_delayed(self):
        """Recreate overlay after cleanup delay"""
        try:
            if self.auto_update_enabled:
                self.apply_legend()  # This will create new overlay
        except Exception as e:
            self.debug_print(f"Error in delayed overlay recreation: {e}")
            
    def on_layer_visibility_changed(self, node):
        """Handle layer visibility changes"""
        if self.auto_update_enabled and self.legend_overlay and self.legend_overlay.isVisible():
            # Small delay to allow QGIS to process the change
            QTimer.singleShot(100, self.update_legend_auto)
            
    def on_layers_changed(self):
        """Handle layer addition/removal"""
        # BETA 20: Clear entire cache when layers are added/removed
        if (hasattr(self, '_symbol_cache') and 
            hasattr(self, '_beta20_enabled') and 
            self._beta20_enabled):
            try:
                self._symbol_cache.clear_cache()
                self.debug_print("BETA 20: Cache cleared due to layer changes")
            except Exception as e:
                self.debug_print(f"BETA 20: Error clearing cache on layer changes: {e}")
        
        if self.auto_update_enabled and self.legend_overlay and self.legend_overlay.isVisible():
            QTimer.singleShot(100, self.update_legend_auto)
            
    def on_layer_style_changed(self, layer_id):
        """Handle layer style changes"""
        # BETA 20: Invalidate cache for this layer
        if (hasattr(self, '_symbol_cache') and 
            hasattr(self, '_beta20_enabled') and 
            self._beta20_enabled):
            try:
                self._symbol_cache.invalidate_layer_cache(layer_id)
                self.debug_print(f"BETA 20: Cache invalidated for layer {layer_id}")
            except Exception as e:
                self.debug_print(f"BETA 20: Error invalidating cache for layer {layer_id}: {e}")
        
        if self.auto_update_enabled and self.legend_overlay and self.legend_overlay.isVisible():
            QTimer.singleShot(100, self.update_legend_auto)
    
    def _safe_post_style_update(self):
        """BETA 19: Actualización ultra-segura después de cambios de estilo QML"""
        try:
            self.debug_print("BETA 19: Executing ultra-safe post-style update after extended delay")
            
            # Reset style loading flag
            self._style_loading_detected = False
            
            # BETA 19: Verificación exhaustiva de estabilidad de capas
            layers_stable = True
            qml_layers_stable = True
            
            try:
                for layer in QgsProject.instance().mapLayers().values():
                    if not layer.isValid():
                        layers_stable = False
                        self.debug_print(f"BETA 19: Layer {layer.name() if hasattr(layer, 'name') else 'unknown'} is not stable yet")
                        break
                        
                    # Check if layer has renderer and it's accessible
                    if hasattr(layer, 'renderer'):
                        try:
                            renderer = layer.renderer()
                            if renderer and hasattr(renderer, 'type'):
                                renderer_type = renderer.type()
                                
                                # BETA 19: Special check for complex renderers (QML types)
                                if renderer_type in ['categorizedSymbol', 'graduatedSymbol', 'RuleRenderer']:
                                    self.debug_print(f"BETA 19: Checking QML-type renderer stability: {renderer_type}")
                                    
                                    # Test symbol access for complex renderers
                                    if hasattr(renderer, 'symbol'):
                                        try:
                                            test_symbol = renderer.symbol()
                                            if test_symbol and hasattr(test_symbol, 'symbolLayerCount'):
                                                layer_count = test_symbol.symbolLayerCount()
                                                if layer_count == 0:
                                                    qml_layers_stable = False
                                                    self.debug_print(f"BETA 19: QML symbol not stable - no layers")
                                                    break
                                        except:
                                            qml_layers_stable = False
                                            self.debug_print(f"BETA 19: QML symbol access failed - not stable")
                                            break
                                            
                                # Test general symbol access
                                if hasattr(renderer, 'symbol'):
                                    test_symbol = renderer.symbol()
                        except Exception as renderer_error:
                            layers_stable = False
                            self.debug_print(f"BETA 19: Renderer access failed for layer: {renderer_error}")
                            break
            except Exception as stability_check_error:
                self.debug_print(f"BETA 19: Error checking layer stability: {stability_check_error}")
                layers_stable = False
                qml_layers_stable = False
            
            # BETA 19: If QML layers are not stable, wait longer
            if not qml_layers_stable:
                self.debug_print("BETA 19: QML layers not stable yet, extending delay by 3 seconds")
                QTimer.singleShot(3000, self._safe_post_style_update)
                return
                
            if not layers_stable:
                self.debug_print("BETA 19: General layers not stable yet, retrying in 2 seconds")
                QTimer.singleShot(2000, self._safe_post_style_update)
                return
            
            # Layers are stable, proceed with safe recreation
            self.debug_print("BETA 19: All layers stable, proceeding with overlay recreation")
            
            # Show overlay again and recreate safely
            if self.legend_overlay:
                self.legend_overlay.setVisible(True)
            
            if self.auto_update_enabled:
                self.apply_legend()
                
        except Exception as e:
            self.debug_print(f"BETA 18: Error in safe post-style update: {e}")
            # Fallback: try basic recreation
            try:
                if self.auto_update_enabled:
                    self.apply_legend()
            except:
                pass
            
    def update_legend_auto(self):
        """Update legend automatically without user interaction - USE RECREATION STRATEGY WITH RASTER PROTECTION"""
        try:
            if self.legend_overlay and self.legend_overlay.isVisible():
                # CRITICAL: For raster layer changes, always use recreation for safety
                has_raster_layers = False
                try:
                    for layer in QgsProject.instance().mapLayers().values():
                        if hasattr(layer, '__class__') and ('Raster' in layer.__class__.__name__):
                            has_raster_layers = True
                            break
                except:
                    pass
                
                if has_raster_layers:
                    self.debug_print("Auto-update with raster layers detected - using recreation strategy for safety")
                else:
                    self.debug_print("Auto-update triggered - using recreation strategy for safety")
                    
                self.apply_legend()  # This will safely recreate the overlay
                
        except Exception as e:
            self.debug_print(f"Error auto-updating legend: {e}")
            # If auto-update fails, try to at least keep overlay visible
            try:
                if self.legend_overlay:
                    if not self.legend_overlay.isVisible():
                        self.legend_overlay.show()
            except:
                pass
        
    def setupUi(self):
        """Set up the user interface"""
        self.setWindowTitle('Arcadia Canvas Legend - Beta 17 (Raster Protection + Multi-Level Safety)')
        
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
            
            # Load debug mode setting
            debug_enabled = get_arcadia_setting('CANVAS_LEGEND', 'debug_mode', False)
            if hasattr(self, 'debug_mode_check'):
                self.debug_mode_check.setChecked(bool(debug_enabled))
                self.debug_mode = bool(debug_enabled)
                self.debug_print(f"Loaded debug mode from settings: {debug_enabled}")
            
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
            
            # Save debug mode setting
            if hasattr(self, 'debug_mode'):
                set_arcadia_setting('CANVAS_LEGEND', 'debug_mode', self.debug_mode)
                self.debug_print(f"Saved debug mode to settings: {self.debug_mode}")
                              
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
        """Apply the legend overlay to canvas with anti-recreation protection"""
        try:
            # CRITICAL: Throttle rapid applies to prevent recreation loops
            import time
            current_time = time.time()
            if current_time - getattr(self, '_last_apply_time', 0) < 0.5:  # 500ms throttle
                self.debug_print("THROTTLED: Apply called too soon, ignoring")
                return
            self._last_apply_time = current_time
            
            # CRITICAL: Prevent rapid recreation cycles
            if hasattr(self, '_applying_legend') and self._applying_legend:
                self.debug_print("ABORT: Already applying legend - preventing recursion")
                return
                
            self._applying_legend = True
            
            # If overlay exists and is working, just update instead of recreating
            if self.legend_overlay and not getattr(self.legend_overlay, '_destroyed', False):
                try:
                    # Try to update existing overlay instead of recreating
                    self.debug_print("Updating existing overlay instead of recreating")
                    settings = self.get_current_settings()
                    legend_items = self.get_legend_items()
                    
                    # Update content safely
                    self.legend_overlay.update_legend_content(legend_items, settings)
                    self.position_overlay()
                    
                    if not self.legend_overlay.isVisible():
                        self.legend_overlay.show()
                        
                    self.save_settings()
                    return
                    
                except Exception as update_error:
                    self.debug_print(f"Update failed, will recreate: {update_error}")
                    # Fall through to recreation
            
            # CRITICAL: Safely destroy existing overlay before creating new one
            if self.legend_overlay:
                self.debug_print("Destroying existing overlay before creating new one")
                
                # Mark as destroyed to prevent any ongoing operations
                if hasattr(self.legend_overlay, '_destroyed'):
                    self.legend_overlay._destroyed = True
                
                # Hide and cleanup
                self.legend_overlay.hide()
                self.legend_overlay.deleteLater()
                self.legend_overlay = None
                
                # Longer delay to ensure Qt processes the deletion completely
                QTimer.singleShot(150, self._create_new_overlay_safe)
                return
            else:
                self._create_new_overlay_safe()
                
        except Exception as e:
            self.debug_print(f"Error in apply_legend: {e}")
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error applying legend: {}').format(str(e)))
        finally:
            # Always reset the applying flag after a delay
            QTimer.singleShot(200, lambda: setattr(self, '_applying_legend', False))
                               
    def _create_new_overlay_safe(self):
        """Create new overlay after ensuring old one is destroyed - with safety checks"""
        try:
            # Additional safety check
            if hasattr(self, '_applying_legend') and not self._applying_legend:
                self.debug_print("ABORT: Apply operation was cancelled")
                return
                
            self.debug_print("Creating new legend overlay with enhanced safety")
            
            # Create new overlay
            self.legend_overlay = CanvasLegendOverlay(self.canvas)
            
            # BETA 20: Configure cache-based system if available
            if hasattr(self, '_symbol_cache') and hasattr(self, '_beta20_enabled'):
                self.legend_overlay.set_beta20_components(self._symbol_cache, self._beta20_enabled)
                self.debug_print(f"BETA 20: Overlay configured with cache system (enabled: {self._beta20_enabled})")
            else:
                self.debug_print("BETA 20: Cache system not available, using legacy mode")
                
            # Get current settings
            settings = self.get_current_settings()
            
            # Get legend items from current layers
            legend_items = self.get_legend_items()
            
            # Update overlay
            self.legend_overlay.update_legend_content(legend_items, settings)
            
            # Position overlay with bounds checking
            self.position_overlay_safe()
            
            # Show overlay
            self.legend_overlay.show()
            
            self.save_settings()
            
        except Exception as e:
            self.debug_print(f"Error creating new overlay: {e}")
            QMessageBox.critical(self, self.tr('Error'), 
                               self.tr('Error creating legend overlay: {}').format(str(e)))
        finally:
            # Always reset the applying flag
            self._applying_legend = False
            
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
        # BETA 20: Use new symbol data extractor if available
        if (hasattr(self, '_symbol_data_extractor') and 
            hasattr(self, '_beta20_enabled') and 
            self._beta20_enabled):
            try:
                self.debug_print("BETA 20: Using SymbolDataExtractor for legend items")
                legend_data = self._symbol_data_extractor.extract_legend_data()
                
                # Convert LayerSymbolInfo objects to dict format for compatibility
                converted_items = []
                for layer_info in legend_data:
                    if isinstance(layer_info, LayerSymbolInfo):
                        # Convert LayerSymbolInfo to dict format
                        item_dict = {
                            'layer_name': layer_info.layer_name,
                            'layer_id': layer_info.layer_id,
                            'name': layer_info.layer_name,  # Legacy compatibility
                            'type': 'layer',
                            'layer': layer_info.layer,  # Now this attribute exists
                            'visible': getattr(layer_info, 'is_visible', True),
                            'is_group_child': False,
                            'symbols': []
                        }
                        
                        # Convert symbols ensuring all required attributes
                        for symbol_info in layer_info.symbols:
                            symbol_dict = {
                                'label': symbol_info.get('label', layer_info.layer_name),
                                'layer_type': symbol_info.get('layer_type', layer_info.layer_type),
                                'geometry_type': symbol_info.get('geometry_type', layer_info.geometry_type),
                                'color': symbol_info.get('color', QColor('gray')),
                                'type': symbol_info.get('type', 'symbol'),
                                'symbol': symbol_info.get('symbol')
                            }
                            item_dict['symbols'].append(symbol_dict)
                        
                        # If no symbols, add a default one
                        if not item_dict['symbols']:
                            default_symbol = {
                                'label': layer_info.layer_name,
                                'layer_type': layer_info.layer_type,
                                'geometry_type': layer_info.geometry_type,
                                'color': QColor('gray'),
                                'type': 'default',
                                'symbol': None
                            }
                            item_dict['symbols'].append(default_symbol)
                        
                        converted_items.append(item_dict)
                    else:
                        # Already in dict format, use as-is
                        converted_items.append(layer_info)
                
                self.debug_print(f"BETA 20: Converted {len(converted_items)} layer items")
                return converted_items
                
            except Exception as e:
                self.debug_print(f"BETA 20: Error in SymbolDataExtractor, falling back to legacy: {e}")
                import traceback
                traceback.print_exc()
                # Continue with legacy system
        
        # Legacy system
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
            
            # Handle raster layers with CRITICAL safety checks
            if is_raster and not is_vector:
                self.debug_print(f"-> Raster layer detected (class-based)")
                
                try:
                    # CRITICAL: Safe renderer access with multiple fallbacks
                    renderer = None
                    renderer_type = 'unknown'
                    band_count = 1
                    
                    # Level 1: Basic renderer check
                    if hasattr(layer, 'renderer'):
                        try:
                            renderer = layer.renderer()
                            if renderer:
                                renderer_type = renderer.type() if hasattr(renderer, 'type') else 'unknown'
                        except Exception as e:
                            self.debug_print(f"-> ERROR accessing renderer: {e}")
                            renderer = None
                    
                    # Level 2: Safe band count check  
                    if hasattr(layer, 'bandCount'):
                        try:
                            band_count = layer.bandCount()
                        except Exception as e:
                            self.debug_print(f"-> ERROR accessing band count: {e}")
                            band_count = 1
                    
                    self.debug_print(f"-> Raster renderer type: {renderer_type}")
                    self.debug_print(f"-> Band count: {band_count}")
                    
                    # CRITICAL: Handle pseudocolor with extensive error protection
                    if renderer_type == 'singlebandpseudocolor' and renderer:
                        self.debug_print(f"-> Pseudocolor raster - generating color ramp with protection")
                        
                        try:
                            # Level 3: Safe shader access
                            shader = None
                            if hasattr(renderer, 'shader'):
                                try:
                                    shader = renderer.shader()
                                except Exception as e:
                                    self.debug_print(f"-> ERROR accessing shader: {e}")
                                    
                            if shader and hasattr(shader, 'rasterShaderFunction'):
                                try:
                                    ramp_function = shader.rasterShaderFunction()
                                    if ramp_function and hasattr(ramp_function, 'colorRampItemList'):
                                        try:
                                            color_items = ramp_function.colorRampItemList()
                                            if color_items and len(color_items) > 0:
                                                self.debug_print(f"-> Found {len(color_items)} color ramp items")
                                                
                                                # Get decimal places safely
                                                decimals = 2
                                                try:
                                                    if hasattr(self, 'pseudocolor_decimals_spin'):
                                                        decimals = self.pseudocolor_decimals_spin.value()
                                                except:
                                                    pass
                                                
                                                # CRITICAL: Safe color item processing
                                                for i, item in enumerate(color_items[:5]):  # Max 5 colors
                                                    try:
                                                        # Safe value access
                                                        value_text = "Unknown"
                                                        if hasattr(item, 'value'):
                                                            try:
                                                                value_text = f"{item.value:.{decimals}f}"
                                                            except:
                                                                value_text = f"Value {i+1}"
                                                        
                                                        # Safe label access
                                                        label = f"Color {i+1}"
                                                        if hasattr(item, 'label') and item.label:
                                                            try:
                                                                label = str(item.label)
                                                            except:
                                                                pass
                                                        else:
                                                            label = f"Value {value_text}"
                                                        
                                                        # Safe color access
                                                        color = QColor('gray')
                                                        if hasattr(item, 'color'):
                                                            try:
                                                                color = item.color
                                                                if not color.isValid():
                                                                    color = QColor('gray')
                                                            except:
                                                                pass
                                                        
                                                        symbols.append({
                                                            'label': label,
                                                            'symbol': None,
                                                            'color': color,
                                                            'layer_type': 'raster_pseudocolor',
                                                            'geometry_type': 'raster'
                                                        })
                                                        
                                                    except Exception as item_error:
                                                        self.debug_print(f"-> ERROR processing color item {i}: {item_error}")
                                                        # Continue with next item
                                                        continue
                                                
                                                if symbols:  # Return if we got any symbols
                                                    return symbols
                                                    
                                        except Exception as items_error:
                                            self.debug_print(f"-> ERROR accessing color ramp items: {items_error}")
                                            
                                except Exception as ramp_error:
                                    self.debug_print(f"-> ERROR accessing raster shader function: {ramp_error}")
                                    
                        except Exception as shader_error:
                            self.debug_print(f"-> ERROR in pseudocolor processing: {shader_error}")
                        
                        # Fallback for pseudocolor without detailed ramp info
                        self.debug_print(f"-> Using pseudocolor fallback")
                        symbols.append({
                            'label': f"{layer.name()} (Pseudocolor)",
                            'symbol': None,
                            'color': QColor('blue'),
                            'layer_type': 'raster_pseudocolor',
                            'geometry_type': 'raster',
                            'error_type': 'missing'  # Indicate fallback used
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
                    
                except Exception as raster_error:
                    self.debug_print(f"-> CRITICAL ERROR processing raster layer: {raster_error}")
                    # Ultimate fallback for any raster processing error
                    symbols.append({
                        'label': f"{layer.name()} (Raster Error)",
                        'symbol': None,
                        'color': QColor('red'),
                        'layer_type': 'raster_error',
                        'geometry_type': 'raster',
                        'error_type': 'corrupted'  # Indicate error occurred
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
                        # Ultimate fallback: Use placeholder
                        symbols.append({
                            'label': f"{layer.name()} (Error: {type(renderer_error).__name__})",
                            'symbol': None,
                            'color': QColor('lightgray'),
                            'layer_type': 'vector_fallback',
                            'geometry_type': geometry_type,
                            'error_type': 'corrupted'  # Flag for placeholder type
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
        
    def position_overlay_safe(self):
        """Position the legend overlay on canvas with enhanced crash protection and bounds checking"""
        if not self.legend_overlay or getattr(self.legend_overlay, '_destroyed', False):
            self.debug_print("ABORT: No overlay or overlay destroyed")
            return
            
        try:
            # Get canvas size (local coordinates since overlay is child of canvas)
            canvas_size = self.canvas.size()
            self.debug_print(f"Canvas size: {canvas_size.width()}x{canvas_size.height()}")
            
            # Validate canvas size
            if canvas_size.width() <= 0 or canvas_size.height() <= 0:
                self.debug_print("ABORT: Invalid canvas size")
                return
            
            # Use safe resize method
            target_width = max(100, min(self.width_spin.value(), canvas_size.width() - 20))
            target_height = max(100, min(self.height_spin.value(), canvas_size.height() - 20))
            
            self.debug_print(f"Resizing overlay to: {target_width}x{target_height}")
            self.legend_overlay._safe_resize(target_width, target_height)
            
            # Wait a moment for resize to complete before positioning
            QTimer.singleShot(30, lambda: self._complete_positioning_canvas_safe(canvas_size, target_width, target_height))
            
        except Exception as e:
            self.debug_print(f"Error in position_overlay_safe: {e}")
        
    def _complete_positioning_canvas_safe(self, canvas_size, target_width, target_height):
        """Complete the positioning in canvas local coordinates with bounds checking"""
        if not self.legend_overlay or getattr(self.legend_overlay, '_destroyed', False):
            self.debug_print("ABORT: Overlay destroyed during positioning")
            return
            
        try:
            position = self.position_combo.currentText().lower()
            x_offset = max(0, self.x_offset_spin.value())
            y_offset = max(0, self.y_offset_spin.value())
            
            self.debug_print(f"Position: {position}, offsets: ({x_offset}, {y_offset})")
            
            # Calculate position relative to canvas (local coordinates)
            if 'top' in position and 'left' in position:
                x = x_offset
                y = y_offset
            elif 'top' in position and 'right' in position:
                x = canvas_size.width() - target_width - x_offset
                y = y_offset
            elif 'bottom' in position and 'left' in position:
                x = x_offset
                y = canvas_size.height() - target_height - y_offset
            elif 'bottom' in position and 'right' in position:
                x = canvas_size.width() - target_width - x_offset
                y = canvas_size.height() - target_height - y_offset
            else:  # Custom position
                x = x_offset
                y = y_offset
                
            # CRITICAL: Ensure overlay stays within canvas bounds with margins
            margin = 10
            x = max(margin, min(x, canvas_size.width() - target_width - margin))
            y = max(margin, min(y, canvas_size.height() - target_height - margin))
            
            self.debug_print(f"Final position after bounds checking: ({x}, {y})")
            
            # Validate final position
            if x < 0 or y < 0 or x + target_width > canvas_size.width() or y + target_height > canvas_size.height():
                self.debug_print(f"WARNING: Position out of bounds, using safe default")
                x = margin
                y = margin
            
            self.legend_overlay.move(x, y)
            self.debug_print(f"Overlay positioned at canvas coordinates: ({x}, {y})")
            
        except Exception as e:
            self.debug_print(f"Error in positioning: {e}")
            # Fallback to safe position
            try:
                self.legend_overlay.move(10, 10)
                self.debug_print("Used fallback position (10, 10)")
            except:
                pass
        
    def position_overlay(self):
        """Legacy method - redirects to safe version"""
        self.position_overlay_safe()
        
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
    
    def draw_symbol_placeholder(self, painter, symbol_rect, error_type="unknown"):
        """Draw a placeholder for corrupted/invalid symbols"""
        try:
            # Different placeholder styles based on error type
            if error_type == "corrupted":
                # Red X for corrupted symbols
                painter.fillRect(symbol_rect, QColor(255, 200, 200, 150))  # Light red background
                painter.setPen(QPen(QColor('red'), 2))
                painter.drawLine(symbol_rect.topLeft(), symbol_rect.bottomRight())
                painter.drawLine(symbol_rect.topRight(), symbol_rect.bottomLeft())
            elif error_type == "missing":
                # Gray question mark for missing symbols
                painter.fillRect(symbol_rect, QColor(200, 200, 200, 150))  # Light gray background
                painter.setPen(QColor('black'))
                painter.setFont(QFont('Arial', 10, QFont.Bold))
                painter.drawText(symbol_rect, Qt.AlignCenter, "?")
            else:
                # Default placeholder - simple gray rectangle
                painter.fillRect(symbol_rect, QColor(180, 180, 180, 150))
                painter.setPen(QColor('darkgray'))
                painter.drawRect(symbol_rect)
                
            self.debug_print(f"    -> Drew {error_type} placeholder")
            
        except Exception as e:
            # Ultimate fallback - just fill with gray
            self.debug_print(f"    -> Placeholder drawing failed: {e}")
            painter.fillRect(symbol_rect, QColor('lightgray'))
    
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
        
        # Update symbol data extractor if available
        if hasattr(self, '_symbol_data_extractor') and self._symbol_data_extractor:
            self._symbol_data_extractor.debug_mode = enabled
            self.debug_print(f"Updated symbol data extractor debug mode: {enabled}")
        
        # Save to persistent settings
        self.save_settings()
        
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

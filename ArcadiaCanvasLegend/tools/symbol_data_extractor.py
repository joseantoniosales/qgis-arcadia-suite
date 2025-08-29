"""
Symbol Data Extractor - Abstracción para obtener símbolos de QGIS
Parte de la estrategia de refuerzo Beta 20
"""

from typing import List, Dict, Any, Optional, Tuple
from qgis.core import (
    QgsProject, QgsMapLayer, QgsVectorLayer, QgsRasterLayer,
    QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTree,
    QgsCategorizedSymbolRenderer, QgsGraduatedSymbolRenderer,
    QgsRuleBasedRenderer, QgsSingleSymbolRenderer
)
from qgis.PyQt.QtGui import QColor


class LayerSymbolInfo:
    """Información de símbolo de una capa"""
    
    def __init__(self, layer_id: str, layer_name: str, layer_type: str, 
                 geometry_type: str = 'unknown', symbols: List[Dict] = None, 
                 layer=None):
        self.layer_id = layer_id
        self.layer_name = layer_name
        self.layer_type = layer_type
        self.geometry_type = geometry_type
        self.symbols = symbols or []
        self.is_visible = True
        self.is_valid = True
        self.layer = layer  # Referencia al QgsVectorLayer original


class SymbolDataExtractor:
    """Extractor de datos de símbolos de QGIS - Centraliza acceso a API"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self._last_extraction_time = 0
        
    def debug_print(self, message: str):
        """Print debug message if debug mode is enabled"""
        if self.debug_mode:
            print(f"[SymbolExtractor] {message}")
    
    def extract_legend_data(self, visible_only: bool = True) -> List[LayerSymbolInfo]:
        """Extraer datos de leyenda de manera segura"""
        legend_data = []
        
        try:
            # Obtener el proyecto actual
            project = QgsProject.instance()
            if not project:
                self.debug_print("No project available")
                return legend_data
            
            # Obtener el árbol de capas
            layer_tree_root = project.layerTreeRoot()
            if not layer_tree_root:
                self.debug_print("No layer tree root available")
                return legend_data
            
            # Procesar el árbol de capas
            self._process_layer_tree_node(layer_tree_root, legend_data, visible_only)
            
        except Exception as e:
            self.debug_print(f"Error extracting legend data: {e}")
        
        return legend_data
    
    def _process_layer_tree_node(self, node, legend_data: List[LayerSymbolInfo], visible_only: bool):
        """Procesar nodo del árbol de capas recursivamente"""
        try:
            if isinstance(node, QgsLayerTreeGroup):
                # Procesar grupo
                if not visible_only or node.isVisible():
                    for child in node.children():
                        self._process_layer_tree_node(child, legend_data, visible_only)
                        
            elif isinstance(node, QgsLayerTreeLayer):
                # Procesar capa
                if not visible_only or node.isVisible():
                    layer_info = self._extract_layer_info(node)
                    if layer_info and layer_info.symbols:
                        legend_data.append(layer_info)
                        
        except Exception as e:
            self.debug_print(f"Error processing layer tree node: {e}")
    
    def _extract_layer_info(self, layer_node: QgsLayerTreeLayer) -> Optional[LayerSymbolInfo]:
        """Extraer información de una capa específica"""
        try:
            layer = layer_node.layer()
            if not layer or not layer.isValid():
                return None
            
            layer_info = LayerSymbolInfo(
                layer_id=layer.id(),
                layer_name=layer.name(),
                layer_type=self._get_layer_type(layer),
                geometry_type=self._get_geometry_type(layer),
                layer=layer  # Referencia al layer original
            )
            
            layer_info.is_visible = layer_node.isVisible()
            layer_info.is_valid = layer.isValid()
            
            # Extraer símbolos según el tipo de capa
            if isinstance(layer, QgsVectorLayer):
                layer_info.symbols = self._extract_vector_symbols(layer)
            elif isinstance(layer, QgsRasterLayer):
                layer_info.symbols = self._extract_raster_symbols(layer)
            
            return layer_info
            
        except Exception as e:
            self.debug_print(f"Error extracting layer info: {e}")
            return None
    
    def _get_layer_type(self, layer) -> str:
        """Obtener tipo de capa de manera segura"""
        try:
            if isinstance(layer, QgsVectorLayer):
                return 'vector'
            elif isinstance(layer, QgsRasterLayer):
                return 'raster'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    def _get_geometry_type(self, layer) -> str:
        """Obtener tipo de geometría de manera segura"""
        try:
            if isinstance(layer, QgsVectorLayer):
                geom_type = layer.geometryType()
                type_names = {0: 'point', 1: 'line', 2: 'polygon'}
                return type_names.get(geom_type, 'unknown')
            return 'raster'
        except:
            return 'unknown'
    
    def _extract_vector_symbols(self, layer: QgsVectorLayer) -> List[Dict]:
        """Extraer símbolos de capa vectorial de manera segura"""
        symbols = []
        
        try:
            renderer = layer.renderer()
            if not renderer:
                self.debug_print(f"No renderer for vector layer: {layer.name()}")
                return symbols
            
            renderer_type = renderer.type()
            self.debug_print(f"Processing vector layer '{layer.name()}' with renderer: {renderer_type}")
            
            if renderer_type == 'singleSymbol':
                symbols.extend(self._extract_single_symbol(renderer, layer.name()))
            elif renderer_type == 'categorizedSymbol':
                symbols.extend(self._extract_categorized_symbols(renderer, layer.name()))
            elif renderer_type == 'graduatedSymbol':
                symbols.extend(self._extract_graduated_symbols(renderer, layer.name()))
            elif renderer_type == 'RuleRenderer':
                symbols.extend(self._extract_rule_based_symbols(renderer, layer.name()))
            else:
                self.debug_print(f"Unknown renderer type: {renderer_type}")
                symbols.extend(self._extract_fallback_symbol(renderer, layer.name()))
                
        except Exception as e:
            self.debug_print(f"Error extracting vector symbols: {e}")
            # Crear símbolo de fallback
            symbols.append({
                'label': layer.name(),
                'type': 'fallback',
                'color': QColor('gray'),
                'symbol': None
            })
        
        return symbols
    
    def _extract_single_symbol(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolo único"""
        symbols = []
        try:
            if hasattr(renderer, 'symbol') and renderer.symbol():
                symbol = renderer.symbol()
                color = self._get_symbol_color(symbol)
                symbols.append({
                    'label': layer_name,
                    'type': 'single',
                    'color': color,
                    'symbol': symbol
                })
        except Exception as e:
            self.debug_print(f"Error extracting single symbol: {e}")
        
        return symbols
    
    def _extract_categorized_symbols(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolos categorizados"""
        symbols = []
        try:
            if hasattr(renderer, 'categories'):
                for category in renderer.categories():
                    try:
                        symbol = category.symbol()
                        label = category.label() or category.value()
                        color = self._get_symbol_color(symbol)
                        
                        symbols.append({
                            'label': f"{layer_name}: {label}",
                            'type': 'categorized',
                            'color': color,
                            'symbol': symbol,
                            'category_value': category.value()
                        })
                    except Exception as e:
                        self.debug_print(f"Error processing category: {e}")
                        continue
        except Exception as e:
            self.debug_print(f"Error extracting categorized symbols: {e}")
        
        return symbols
    
    def _extract_graduated_symbols(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolos graduados"""
        symbols = []
        try:
            if hasattr(renderer, 'ranges'):
                for range_item in renderer.ranges():
                    try:
                        symbol = range_item.symbol()
                        label = range_item.label()
                        color = self._get_symbol_color(symbol)
                        
                        symbols.append({
                            'label': f"{layer_name}: {label}",
                            'type': 'graduated',
                            'color': color,
                            'symbol': symbol,
                            'range_min': range_item.lowerValue(),
                            'range_max': range_item.upperValue()
                        })
                    except Exception as e:
                        self.debug_print(f"Error processing range: {e}")
                        continue
        except Exception as e:
            self.debug_print(f"Error extracting graduated symbols: {e}")
        
        return symbols
    
    def _extract_rule_based_symbols(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolos basados en reglas"""
        symbols = []
        try:
            if hasattr(renderer, 'rootRule'):
                root_rule = renderer.rootRule()
                if root_rule:
                    self._extract_rule_symbols_recursive(root_rule, layer_name, symbols)
        except Exception as e:
            self.debug_print(f"Error extracting rule-based symbols: {e}")
        
        return symbols
    
    def _extract_rule_symbols_recursive(self, rule, layer_name: str, symbols: List[Dict]):
        """Extraer símbolos de reglas recursivamente"""
        try:
            # Procesar regla actual
            if rule.symbol():
                symbol = rule.symbol()
                label = rule.label() or rule.filterExpression()
                color = self._get_symbol_color(symbol)
                
                symbols.append({
                    'label': f"{layer_name}: {label}",
                    'type': 'rule',
                    'color': color,
                    'symbol': symbol,
                    'rule_filter': rule.filterExpression()
                })
            
            # Procesar reglas hijas
            for child_rule in rule.children():
                self._extract_rule_symbols_recursive(child_rule, layer_name, symbols)
                
        except Exception as e:
            self.debug_print(f"Error processing rule: {e}")
    
    def _extract_fallback_symbol(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolo de fallback"""
        symbols = []
        try:
            if hasattr(renderer, 'symbol') and renderer.symbol():
                symbol = renderer.symbol()
                color = self._get_symbol_color(symbol)
            else:
                symbol = None
                color = QColor('gray')
            
            symbols.append({
                'label': layer_name,
                'type': 'fallback',
                'color': color,
                'symbol': symbol
            })
        except Exception as e:
            self.debug_print(f"Error extracting fallback symbol: {e}")
        
        return symbols
    
    def _extract_raster_symbols(self, layer: QgsRasterLayer) -> List[Dict]:
        """Extraer símbolos de capa raster de manera segura"""
        symbols = []
        
        try:
            # Para raster, crear una representación simplificada
            color = QColor('lightgray')
            
            # Intentar obtener información del renderer
            try:
                renderer = layer.renderer()
                if renderer and hasattr(renderer, 'type'):
                    renderer_type = renderer.type()
                    
                    # Ajustar color según el tipo de renderer
                    if 'singleband' in renderer_type.lower():
                        color = QColor('darkgray')
                    elif 'multiband' in renderer_type.lower():
                        color = QColor('blue')
                    elif 'palette' in renderer_type.lower():
                        color = QColor('green')
            except:
                pass
            
            symbols.append({
                'label': layer.name(),
                'type': 'raster',
                'color': color,
                'symbol': None
            })
            
        except Exception as e:
            self.debug_print(f"Error extracting raster symbols: {e}")
            symbols.append({
                'label': layer.name(),
                'type': 'raster_fallback',
                'color': QColor('lightgray'),
                'symbol': None
            })
        
        return symbols
    
    def _get_symbol_color(self, symbol) -> QColor:
        """Obtener color del símbolo de manera segura"""
        try:
            if symbol and hasattr(symbol, 'color'):
                return symbol.color()
        except:
            pass
        
        return QColor('gray')
    
    def is_layer_stable(self, layer_id: str) -> bool:
        """Verificar si una capa está en estado estable"""
        try:
            project = QgsProject.instance()
            if not project:
                return False
                
            layer = project.mapLayer(layer_id)
            if not layer or not layer.isValid():
                return False
            
            # Verificar que el renderer sea accesible
            if hasattr(layer, 'renderer'):
                renderer = layer.renderer()
                if not renderer:
                    return False
                    
                # Test básico de acceso al renderer
                _ = renderer.type()
            
            return True
            
        except Exception as e:
            self.debug_print(f"Layer stability check failed: {e}")
            return False
    
    def invalidate_layer_data(self, layer_id: str):
        """Invalidar datos de una capa específica"""
        # Método para futuras optimizaciones
        self.debug_print(f"Invalidating data for layer: {layer_id}")

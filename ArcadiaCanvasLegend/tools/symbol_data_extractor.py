"""
Symbol Data Extractor - Abstracción para obtener símbolos de QGIS
Beta 25 - SEPARACIÓN TOTAL DE RENDERIZADO
Extracción de datos primitivos SIN renderizado en worker threads
Solo el main thread puede hacer .asImage() con QgsRenderContext seguro
"""

from typing import List, Dict, Any, Optional, Tuple
from qgis.core import (
    QgsProject, QgsMapLayer, QgsVectorLayer, QgsRasterLayer,
    QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTree,
    QgsCategorizedSymbolRenderer, QgsGraduatedSymbolRenderer,
    QgsRuleBasedRenderer, QgsSingleSymbolRenderer, QgsRenderContext
)
from qgis.PyQt.QtGui import QColor, QImage
from qgis.PyQt.QtCore import QMutex, QMutexLocker, QSize


class LayerSymbolInfo:
    """Información de símbolo de una capa - Beta 25 SIN renderizado en worker thread"""
    
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
        
        # Beta 25: SOLO datos primitivos y símbolos clonados - NO IMÁGENES
        self._symbol_clones = {}  # Cache de símbolos clonados
        self._primitive_data = {}  # Datos primitivos extraídos (colores como RGBA, etc.)
        self._last_clone_time = 0
        self._clone_valid = True
        self._needs_main_thread_rendering = True  # Bandera para renderizado posterior


class SymbolDataExtractor:
    """
    Extractor de datos de símbolos de QGIS - Beta 25 SEPARACIÓN TOTAL
    
    NUEVA ESTRATEGIA: Worker thread SOLO extrae datos primitivos y clona símbolos.
    NUNCA hace renderizado (.asImage, .drawPreviewIcon). 
    El main thread es el ÚNICO que puede renderizar con QgsRenderContext seguro.
    """
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self._last_extraction_time = 0
        
        # Beta 25: Mutex solo para clonación, NO para renderizado
        self._symbol_mutex = QMutex()
        self._clone_cache = {}  # Cache de símbolos clonados
        self._primitive_cache = {}  # Cache de datos primitivos extraídos
        
        # Beta 25: ELIMINAMOS todo lo relacionado con imágenes y renderizado
        # NO MÁS: render_context, image_cache, pre_render_symbol_image
        
    def debug_print(self, message: str):
        """Print debug message if debug mode is enabled"""
        if self.debug_mode:
            print(f"[SymbolExtractor-Beta25] {message}")
    
    
    def _clone_symbol_safely(self, symbol, symbol_id: str = None) -> Optional[Any]:
        """
        Clona un símbolo de manera segura para almacenamiento
        
        Beta 25: SOLO clonación, SIN renderizado.
        El símbolo clonado se almacena para uso posterior en main thread.
        """
        if not symbol:
            return None
            
        try:
            with QMutexLocker(self._symbol_mutex):
                # Verificar cache primero
                cache_key = symbol_id or f"symbol_{id(symbol)}"
                if cache_key in self._clone_cache:
                    cached_clone = self._clone_cache[cache_key]
                    if cached_clone:
                        self.debug_print(f"Using cached clone for {cache_key}")
                        return cached_clone
                
                # Realizar clonación segura
                self.debug_print(f"Cloning symbol for safe storage: {cache_key}")
                
                if hasattr(symbol, 'clone'):
                    # Método preferido: clone() nativo de QGIS
                    cloned_symbol = symbol.clone()
                    self.debug_print(f"Successfully cloned symbol using .clone() method")
                    
                elif hasattr(symbol, 'copy'):
                    # Método alternativo: copy()
                    cloned_symbol = symbol.copy()
                    self.debug_print(f"Successfully cloned symbol using .copy() method")
                    
                else:
                    # Sin clonación disponible
                    self.debug_print(f"No clone method available, storing None")
                    cloned_symbol = None
                
                # Almacenar en cache
                if cloned_symbol:
                    self._clone_cache[cache_key] = cloned_symbol
                    self.debug_print(f"Cached cloned symbol: {cache_key}")
                
                return cloned_symbol
                
        except Exception as e:
            self.debug_print(f"Error cloning symbol safely: {e}")
            return None
    
    def _extract_primitive_symbol_data(self, symbol, symbol_id: str = None) -> Dict[str, Any]:
        """
        Extrae datos primitivos del símbolo SIN renderizar
        
        Beta 25: SOLO propiedades simples como enteros, strings, tuplas.
        NO .asImage(), NO .drawPreviewIcon(), NO QgsRenderContext.
        """
        primitive_data = {}
        
        if not symbol:
            return primitive_data
            
        try:
            with QMutexLocker(self._symbol_mutex):
                cache_key = symbol_id or f"primitive_{id(symbol)}"
                
                # Verificar cache
                if cache_key in self._primitive_cache:
                    return self._primitive_cache[cache_key]
                
                self.debug_print(f"Extracting primitive data for symbol: {cache_key}")
                
                # Extraer propiedades básicas como datos primitivos
                if hasattr(symbol, 'color'):
                    try:
                        color = symbol.color()
                        primitive_data['color_rgba'] = color.rgba()  # Entero RGBA
                        primitive_data['color_name'] = color.name()  # String hex
                    except:
                        primitive_data['color_rgba'] = QColor('gray').rgba()
                        primitive_data['color_name'] = '#808080'
                
                if hasattr(symbol, 'type'):
                    try:
                        primitive_data['symbol_type'] = symbol.type()  # Entero
                    except:
                        primitive_data['symbol_type'] = 0
                
                if hasattr(symbol, 'size'):
                    try:
                        primitive_data['symbol_size'] = float(symbol.size())  # Float
                    except:
                        primitive_data['symbol_size'] = 2.0
                
                if hasattr(symbol, 'angle'):
                    try:
                        primitive_data['symbol_angle'] = float(symbol.angle())  # Float
                    except:
                        primitive_data['symbol_angle'] = 0.0
                        
                if hasattr(symbol, 'opacity'):
                    try:
                        primitive_data['symbol_opacity'] = float(symbol.opacity())  # Float
                    except:
                        primitive_data['symbol_opacity'] = 1.0
                
                # Agregar información de disponibilidad de métodos
                primitive_data['has_clone_method'] = hasattr(symbol, 'clone')
                primitive_data['has_copy_method'] = hasattr(symbol, 'copy')
                primitive_data['extraction_time'] = self._last_extraction_time
                
                # Guardar en cache
                self._primitive_cache[cache_key] = primitive_data
                
                self.debug_print(f"Extracted primitive data: {primitive_data}")
                return primitive_data
                
        except Exception as e:
            self.debug_print(f"Error extracting primitive symbol data: {e}")
            return {
                'color_rgba': QColor('gray').rgba(),
                'color_name': '#808080',
                'symbol_type': 0,
                'symbol_size': 2.0,
                'symbol_angle': 0.0,
                'symbol_opacity': 1.0,
                'has_clone_method': False,
                'has_copy_method': False,
                'extraction_failed': True
            }
    
    def clear_symbol_cache(self):
        """Limpiar cache de símbolos clonados y datos primitivos"""
        try:
            with QMutexLocker(self._symbol_mutex):
                self._clone_cache.clear()
                self._primitive_cache.clear()
                self.debug_print("Symbol cache cleared")
        except Exception as e:
            self.debug_print(f"Error clearing symbol cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Obtener estadísticas del cache para debugging"""
        try:
            with QMutexLocker(self._symbol_mutex):
                return {
                    'clone_cache_size': len(self._clone_cache),
                    'primitive_cache_size': len(self._primitive_cache)
                }
        except:
            return {'clone_cache_size': 0, 'primitive_cache_size': 0}
    
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
        """Extraer símbolo único SIN renderizado - Solo datos primitivos"""
        symbols = []
        try:
            if hasattr(renderer, 'symbol') and renderer.symbol():
                original_symbol = renderer.symbol()
                
                # Beta 25: Clonación Y extracción de datos primitivos - NO RENDERIZADO
                symbol_id = f"single_{layer_name}_{id(original_symbol)}"
                cloned_symbol = self._clone_symbol_safely(original_symbol, symbol_id)
                primitive_data = self._extract_primitive_symbol_data(original_symbol, symbol_id)
                
                symbols.append({
                    'label': layer_name,
                    'type': 'single',
                    'color': QColor.fromRgba(primitive_data.get('color_rgba', QColor('gray').rgba())),
                    'symbol': cloned_symbol,  # Símbolo clonado para uso posterior en main thread
                    'primitive_data': primitive_data,  # Datos primitivos seguros
                    'original_symbol_id': symbol_id,
                    'needs_main_thread_rendering': True,  # Bandera para main thread
                    'is_worker_safe': True  # Solo datos seguros
                })
                
                self.debug_print(f"Safely extracted single symbol data for {layer_name}")
                
        except Exception as e:
            self.debug_print(f"Error extracting single symbol: {e}")
        
        return symbols
    
    def _extract_categorized_symbols(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolos categorizados SIN renderizado - Solo datos primitivos"""
        symbols = []
        try:
            if hasattr(renderer, 'categories'):
                for i, category in enumerate(renderer.categories()):
                    try:
                        original_symbol = category.symbol()
                        label = category.label() or category.value()
                        
                        # Beta 25: Clonación Y extracción de datos primitivos - NO RENDERIZADO
                        symbol_id = f"cat_{layer_name}_{i}_{id(original_symbol)}"
                        cloned_symbol = self._clone_symbol_safely(original_symbol, symbol_id)
                        primitive_data = self._extract_primitive_symbol_data(original_symbol, symbol_id)
                        
                        symbols.append({
                            'label': f"{layer_name}: {label}",
                            'type': 'categorized',
                            'color': QColor.fromRgba(primitive_data.get('color_rgba', QColor('gray').rgba())),
                            'symbol': cloned_symbol,  # Símbolo clonado para uso posterior en main thread
                            'primitive_data': primitive_data,  # Datos primitivos seguros
                            'category_value': category.value(),
                            'original_symbol_id': symbol_id,
                            'needs_main_thread_rendering': True,  # Bandera para main thread
                            'is_worker_safe': True  # Solo datos seguros
                        })
                        
                    except Exception as e:
                        self.debug_print(f"Error processing category {i}: {e}")
                        continue
                        
                self.debug_print(f"Safely extracted {len(symbols)} categorized symbols data for {layer_name}")
                
        except Exception as e:
            self.debug_print(f"Error extracting categorized symbols: {e}")
        
        return symbols
    
    def _extract_graduated_symbols(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolos graduados SIN renderizado - Solo datos primitivos"""
        symbols = []
        try:
            if hasattr(renderer, 'ranges'):
                for i, range_item in enumerate(renderer.ranges()):
                    try:
                        original_symbol = range_item.symbol()
                        label = range_item.label()
                        
                        # Beta 25: Clonación Y extracción de datos primitivos - NO RENDERIZADO
                        symbol_id = f"grad_{layer_name}_{i}_{id(original_symbol)}"
                        cloned_symbol = self._clone_symbol_safely(original_symbol, symbol_id)
                        primitive_data = self._extract_primitive_symbol_data(original_symbol, symbol_id)
                        
                        symbols.append({
                            'label': f"{layer_name}: {label}",
                            'type': 'graduated',
                            'color': QColor.fromRgba(primitive_data.get('color_rgba', QColor('gray').rgba())),
                            'symbol': cloned_symbol,  # Símbolo clonado para uso posterior en main thread
                            'primitive_data': primitive_data,  # Datos primitivos seguros
                            'range_min': range_item.lowerValue(),
                            'range_max': range_item.upperValue(),
                            'original_symbol_id': symbol_id,
                            'needs_main_thread_rendering': True,  # Bandera para main thread
                            'is_worker_safe': True  # Solo datos seguros
                        })
                        
                    except Exception as e:
                        self.debug_print(f"Error processing range {i}: {e}")
                        continue
                        
                self.debug_print(f"Safely extracted {len(symbols)} graduated symbols data for {layer_name}")
                
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
    
    def _extract_rule_symbols_recursive(self, rule, layer_name: str, symbols: List[Dict], rule_index: int = 0):
        """Extraer símbolos de reglas recursivamente SIN renderizado - Solo datos primitivos"""
        try:
            # Procesar regla actual
            if rule.symbol():
                original_symbol = rule.symbol()
                label = rule.label() or rule.filterExpression()
                
                # Beta 25: Clonación Y extracción de datos primitivos - NO RENDERIZADO
                symbol_id = f"rule_{layer_name}_{rule_index}_{id(original_symbol)}"
                cloned_symbol = self._clone_symbol_safely(original_symbol, symbol_id)
                primitive_data = self._extract_primitive_symbol_data(original_symbol, symbol_id)
                
                symbols.append({
                    'label': f"{layer_name}: {label}",
                    'type': 'rule',
                    'color': QColor.fromRgba(primitive_data.get('color_rgba', QColor('gray').rgba())),
                    'symbol': cloned_symbol,  # Símbolo clonado para uso posterior en main thread
                    'primitive_data': primitive_data,  # Datos primitivos seguros
                    'rule_filter': rule.filterExpression(),
                    'original_symbol_id': symbol_id,
                    'needs_main_thread_rendering': True,  # Bandera para main thread
                    'is_worker_safe': True  # Solo datos seguros
                })
            
            # Procesar reglas hijas
            child_index = 0
            for child_rule in rule.children():
                self._extract_rule_symbols_recursive(
                    child_rule, layer_name, symbols, 
                    rule_index * 100 + child_index  # Índice único para reglas anidadas
                )
                child_index += 1
                
        except Exception as e:
            self.debug_print(f"Error processing rule {rule_index}: {e}")
    
    def _extract_fallback_symbol(self, renderer, layer_name: str) -> List[Dict]:
        """Extraer símbolo de fallback SIN renderizado - Solo datos primitivos"""
        symbols = []
        try:
            original_symbol = None
            if hasattr(renderer, 'symbol') and renderer.symbol():
                original_symbol = renderer.symbol()
            
            # Beta 25: Clonación Y extracción de datos primitivos - NO RENDERIZADO
            symbol_id = f"fallback_{layer_name}_{id(original_symbol) if original_symbol else 'none'}"
            cloned_symbol = self._clone_symbol_safely(original_symbol, symbol_id) if original_symbol else None
            primitive_data = self._extract_primitive_symbol_data(original_symbol, symbol_id) if original_symbol else {}
            
            symbols.append({
                'label': layer_name,
                'type': 'fallback',
                'color': QColor.fromRgba(primitive_data.get('color_rgba', QColor('gray').rgba())),
                'symbol': cloned_symbol,  # Símbolo clonado para uso posterior en main thread o None
                'primitive_data': primitive_data,  # Datos primitivos seguros
                'original_symbol_id': symbol_id,
                'needs_main_thread_rendering': True,  # Bandera para main thread
                'is_worker_safe': True  # Solo datos seguros
            })
            
        except Exception as e:
            self.debug_print(f"Error extracting fallback symbol: {e}")
        
        return symbols
    
    def verify_symbol_thread_safety(self, symbol_data: Dict) -> bool:
        """
        Verificar que los datos de símbolo son seguros para uso en worker threads - Beta 25
        
        Verifica que tenemos datos primitivos seguros y símbolos clonados
        sin dependencias de renderizado en worker threads.
        """
        try:
            # Verificar marca de worker safety
            if not symbol_data.get('is_worker_safe', False):
                self.debug_print("Symbol data not marked as worker-safe")
                return False
            
            # Verificar que tenemos datos primitivos
            has_primitive_data = symbol_data.get('primitive_data') is not None
            has_clone = symbol_data.get('symbol') is not None
            
            if not has_primitive_data:
                self.debug_print("Symbol data has no primitive data for worker thread")
                return False
            
            # Verificar integridad del símbolo clonado si existe
            if has_clone:
                cloned_symbol = symbol_data.get('symbol')
                if hasattr(cloned_symbol, 'type'):
                    # Intentar acceso básico para verificar validez (sin renderizado)
                    try:
                        _ = cloned_symbol.type()
                    except:
                        self.debug_print("Cloned symbol appears to be invalid")
                        return False
            
            # Verificar que NO hay rendering requirements en worker thread
            needs_main_thread = symbol_data.get('needs_main_thread_rendering', False)
            if not needs_main_thread:
                self.debug_print("Warning: Symbol should require main thread rendering in Beta 25")
            
            # Verificar integridad de datos primitivos
            primitive_data = symbol_data.get('primitive_data', {})
            if not isinstance(primitive_data, dict):
                self.debug_print("Primitive data is not a valid dictionary")
                return False
                
            return True
            
        except Exception as e:
            self.debug_print(f"Error verifying symbol thread safety: {e}")
            return False
    
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
        """Invalidar datos de una capa específica y limpiar cache relacionado"""
        try:
            with QMutexLocker(self._symbol_mutex):
                # Limpiar entradas de cache relacionadas con esta capa
                keys_to_remove = []
                for key in self._clone_cache.keys():
                    if layer_id in key:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._clone_cache[key]
                    self.debug_print(f"Removed clone cache entry: {key}")
                
                # Limpiar cache de imágenes
                image_keys_to_remove = []
                for key in self._image_cache.keys():
                    if layer_id in key:
                        image_keys_to_remove.append(key)
                
                for key in image_keys_to_remove:
                    del self._image_cache[key]
                    self.debug_print(f"Removed image cache entry: {key}")
                
                self.debug_print(f"Invalidated data and cache for layer: {layer_id}")
                
        except Exception as e:
            self.debug_print(f"Error invalidating layer data: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Obtener estadísticas del cache para debugging"""
        try:
            with QMutexLocker(self._symbol_mutex):
                return {
                    'clone_cache_size': len(self._clone_cache),
                    'image_cache_size': len(self._image_cache)
                }
        except:
            return {'clone_cache_size': 0, 'image_cache_size': 0}

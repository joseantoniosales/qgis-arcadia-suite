"""
Symbol Cache Manager - Sistema de caché para símbolos de QGIS
Parte de la estrategia de refuerzo Beta 20
"""

import threading
import hashlib
import time
from typing import Dict, Optional, Tuple, Any
from qgis.PyQt.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker
from qgis.PyQt.QtGui import QPixmap, QColor, QPainter, QFont
from qgis.core import QgsProject, QgsMapLayer, QgsVectorLayer, QgsRasterLayer


class SymbolCacheKey:
    """Clave de caché para símbolos"""
    
    def __init__(self, layer_id: str, symbol_hash: str, size: Tuple[int, int]):
        self.layer_id = layer_id
        self.symbol_hash = symbol_hash
        self.size = size
        
    def __str__(self):
        return f"{self.layer_id}_{self.symbol_hash}_{self.size[0]}x{self.size[1]}"
        
    def __hash__(self):
        return hash(str(self))
        
    def __eq__(self, other):
        return str(self) == str(other)


class SymbolGeneratorWorker(QObject):
    """Worker para generar símbolos en segundo plano"""
    
    symbol_generated = pyqtSignal(str, QPixmap)  # cache_key, pixmap
    symbol_failed = pyqtSignal(str, str)  # cache_key, error_message
    
    def __init__(self):
        super().__init__()
        self.pending_requests = {}
        self.mutex = QMutex()
        
    def generate_symbol(self, cache_key: str, layer_id: str, symbol_data: dict, size: Tuple[int, int]):
        """Generar símbolo de manera segura en segundo plano"""
        try:
            with QMutexLocker(self.mutex):
                if cache_key in self.pending_requests:
                    return  # Ya se está procesando
                    
                self.pending_requests[cache_key] = time.time()
            
            # Generar el pixmap del símbolo
            pixmap = self._create_symbol_pixmap(layer_id, symbol_data, size)
            
            with QMutexLocker(self.mutex):
                if cache_key in self.pending_requests:
                    del self.pending_requests[cache_key]
            
            self.symbol_generated.emit(cache_key, pixmap)
            
        except Exception as e:
            with QMutexLocker(self.mutex):
                if cache_key in self.pending_requests:
                    del self.pending_requests[cache_key]
            
            self.symbol_failed.emit(cache_key, str(e))
    
    def _create_symbol_pixmap(self, layer_id: str, symbol_data: dict, size: Tuple[int, int]) -> QPixmap:
        """Crear pixmap del símbolo de manera segura"""
        width, height = size
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor('transparent'))
        
        painter = QPainter()
        if not painter.begin(pixmap):
            raise Exception("Failed to begin painting on pixmap")
            
        try:
            # Obtener la capa de manera segura
            layer = QgsProject.instance().mapLayer(layer_id)
            if not layer or not layer.isValid():
                raise Exception("Layer not found or invalid")
            
            # Generar el símbolo según el tipo de capa
            if isinstance(layer, QgsVectorLayer):
                self._draw_vector_symbol(painter, layer, symbol_data, width, height)
            elif isinstance(layer, QgsRasterLayer):
                self._draw_raster_symbol(painter, layer, symbol_data, width, height)
            else:
                self._draw_fallback_symbol(painter, symbol_data, width, height)
                
        finally:
            painter.end()
            
        return pixmap
    
    def _draw_vector_symbol(self, painter: QPainter, layer: QgsVectorLayer, symbol_data: dict, width: int, height: int):
        """Dibujar símbolo vectorial de manera segura"""
        try:
            renderer = layer.renderer()
            if not renderer:
                raise Exception("No renderer available")
            
            # Extraer símbolo del renderer de manera segura
            symbol = None
            if hasattr(renderer, 'symbol') and renderer.symbol():
                symbol = renderer.symbol()
            elif 'symbol' in symbol_data:
                symbol = symbol_data['symbol']
            
            if symbol and hasattr(symbol, 'asImage'):
                # Método preferido: usar asImage
                size_obj = QPixmap(width, height).size()
                symbol_image = symbol.asImage(size_obj)
                if symbol_image and not symbol_image.isNull():
                    painter.drawImage(0, 0, symbol_image)
                    return
            
            # Fallback: usar color del símbolo
            color = QColor('gray')
            if symbol and hasattr(symbol, 'color'):
                try:
                    color = symbol.color()
                except:
                    pass
            elif 'color' in symbol_data:
                color = symbol_data['color']
            
            painter.fillRect(0, 0, width, height, color)
            
        except Exception as e:
            # Último fallback
            self._draw_fallback_symbol(painter, symbol_data, width, height)
    
    def _draw_raster_symbol(self, painter: QPainter, layer: QgsRasterLayer, symbol_data: dict, width: int, height: int):
        """Dibujar símbolo raster de manera segura"""
        try:
            # Para raster, usar una representación simplificada
            color = symbol_data.get('color', QColor('lightgray'))
            painter.fillRect(0, 0, width, height, color)
            
            # Agregar texto indicativo
            painter.setPen(QColor('black'))
            painter.setFont(QFont('Arial', 8))
            painter.drawText(2, height - 4, "R")  # Indicador de raster
            
        except Exception as e:
            self._draw_fallback_symbol(painter, symbol_data, width, height)
    
    def _draw_fallback_symbol(self, painter: QPainter, symbol_data: dict, width: int, height: int):
        """Dibujar símbolo de fallback"""
        color = symbol_data.get('color', QColor('lightgray'))
        painter.fillRect(0, 0, width, height, color)


class SymbolCacheManager(QObject):
    """Gestor de caché de símbolos con generación en segundo plano"""
    
    cache_updated = pyqtSignal(str)  # cache_key updated
    
    def __init__(self, max_cache_size: int = 1000):
        super().__init__()
        self.cache: Dict[str, QPixmap] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.max_cache_size = max_cache_size
        
        # Worker para generación en segundo plano
        self.worker_thread = QThread()
        self.worker = SymbolGeneratorWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Conectar señales
        self.worker.symbol_generated.connect(self._on_symbol_generated)
        self.worker.symbol_failed.connect(self._on_symbol_failed)
        
        # Iniciar worker thread
        self.worker_thread.start()
        
        # Timer para limpieza periódica de caché
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_cache)
        self.cleanup_timer.start(300000)  # Limpiar cada 5 minutos
        
    def get_symbol_pixmap(self, layer_id: str, symbol_data: dict, size: Tuple[int, int] = (16, 16)) -> Optional[QPixmap]:
        """Obtener pixmap del símbolo desde caché o solicitarlo"""
        cache_key = self._generate_cache_key(layer_id, symbol_data, size)
        
        # Verificar si está en caché
        if cache_key in self.cache:
            self.cache_timestamps[cache_key] = time.time()  # Actualizar timestamp
            return self.cache[cache_key]
        
        # No está en caché, solicitar generación
        self._request_symbol_generation(cache_key, layer_id, symbol_data, size)
        return None  # Retornar None para mostrar placeholder
    
    def get_placeholder_pixmap(self, size: Tuple[int, int] = (16, 16)) -> QPixmap:
        """Obtener pixmap de placeholder para símbolos en carga"""
        width, height = size
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor('lightgray'))
        
        painter = QPainter()
        if painter.begin(pixmap):
            painter.setPen(QColor('darkgray'))
            painter.setFont(QFont('Arial', 6))
            painter.drawText(2, height - 2, "...")
            painter.end()
            
        return pixmap
    
    def invalidate_layer_cache(self, layer_id: str):
        """Invalidar caché para una capa específica"""
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{layer_id}_")]
        for key in keys_to_remove:
            del self.cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]
    
    def clear_cache(self):
        """Limpiar toda la caché"""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    def _generate_cache_key(self, layer_id: str, symbol_data: dict, size: Tuple[int, int]) -> str:
        """Generar clave de caché única"""
        # Crear hash del símbolo basado en sus propiedades
        symbol_str = f"{symbol_data.get('type', 'unknown')}_{symbol_data.get('color', 'none')}"
        if 'symbol' in symbol_data:
            # Si tenemos el objeto símbolo, intentar obtener más información
            try:
                symbol = symbol_data['symbol']
                if hasattr(symbol, 'type'):
                    symbol_str += f"_{symbol.type()}"
                if hasattr(symbol, 'symbolLayerCount'):
                    symbol_str += f"_{symbol.symbolLayerCount()}"
            except:
                pass
        
        symbol_hash = hashlib.md5(symbol_str.encode()).hexdigest()[:8]
        return f"{layer_id}_{symbol_hash}_{size[0]}x{size[1]}"
    
    def _request_symbol_generation(self, cache_key: str, layer_id: str, symbol_data: dict, size: Tuple[int, int]):
        """Solicitar generación de símbolo en segundo plano"""
        # Usar QTimer.singleShot para ejecutar en el hilo del worker
        QTimer.singleShot(0, lambda: self.worker.generate_symbol(cache_key, layer_id, symbol_data, size))
    
    def _on_symbol_generated(self, cache_key: str, pixmap: QPixmap):
        """Callback cuando se genera un símbolo"""
        self.cache[cache_key] = pixmap
        self.cache_timestamps[cache_key] = time.time()
        
        # Limpiar caché si está muy llena
        if len(self.cache) > self.max_cache_size:
            self._cleanup_cache()
        
        self.cache_updated.emit(cache_key)
    
    def _on_symbol_failed(self, cache_key: str, error_message: str):
        """Callback cuando falla la generación de símbolo"""
        # Crear pixmap de error
        error_pixmap = QPixmap(16, 16)
        error_pixmap.fill(QColor('red'))
        
        painter = QPainter()
        if painter.begin(error_pixmap):
            painter.setPen(QColor('white'))
            painter.setFont(QFont('Arial', 8))
            painter.drawText(2, 12, "!")
            painter.end()
        
        self.cache[cache_key] = error_pixmap
        self.cache_timestamps[cache_key] = time.time()
        self.cache_updated.emit(cache_key)
    
    def _cleanup_cache(self):
        """Limpiar entradas antiguas de la caché"""
        current_time = time.time()
        max_age = 3600  # 1 hora
        
        keys_to_remove = []
        for key, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > max_age:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]
    
    def __del__(self):
        """Cleanup al destruir el objeto"""
        if hasattr(self, 'worker_thread'):
            self.worker_thread.quit()
            self.worker_thread.wait()

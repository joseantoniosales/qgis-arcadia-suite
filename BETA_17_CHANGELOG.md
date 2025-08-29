# BETA 17 - PROTECCIÓN ESPECÍFICA PARA RASTER PSEUDOCOLOR

## Respuesta al Crash con Raster Pseudocolor de Beta 16

### 🔴 **PROBLEMA IDENTIFICADO**:
**Crash al activar capa raster con representación pseudocolor monobanda**

- Los renderers de raster pseudocolor tienen estructura compleja: **renderer → shader → rasterShaderFunction → colorRampItemList**
- Cualquier fallo en esta cadena causaba **access violation**
- Las propiedades de raster pueden ser **inválidas o nulas** en ciertos estados

### ✅ **SOLUCIONES IMPLEMENTADAS**:

#### 1. **PROTECCIÓN MULTI-NIVEL PARA RASTER PSEUDOCOLOR**
```python
def get_layer_symbols(self, layer):
    # Level 1: Safe renderer access
    if hasattr(layer, 'renderer'):
        try:
            renderer = layer.renderer()
            if renderer:
                renderer_type = renderer.type() if hasattr(renderer, 'type') else 'unknown'
        except Exception as e:
            renderer = None  # ABORT and use fallback
    
    # Level 2: Safe band count check
    if hasattr(layer, 'bandCount'):
        try:
            band_count = layer.bandCount()
        except Exception as e:
            band_count = 1  # SAFE default
    
    # Level 3: Pseudocolor processing with extensive protection
    if renderer_type == 'singlebandpseudocolor':
        try:
            shader = renderer.shader() if hasattr(renderer, 'shader') else None
            if shader and hasattr(shader, 'rasterShaderFunction'):
                ramp_function = shader.rasterShaderFunction()
                # ... more safe processing
        except Exception as shader_error:
            # Fallback to simple representation
            return safe_fallback_symbol()
```

#### 2. **PROCESAMIENTO SEGURO DE COLOR RAMP ITEMS**
```python
# CRITICAL: Safe color item processing
for i, item in enumerate(color_items[:5]):  # Max 5 colors
    try:
        # Safe value access
        value_text = "Unknown"
        if hasattr(item, 'value'):
            try:
                value_text = f"{item.value:.{decimals}f}"
            except:
                value_text = f"Value {i+1}"  # FALLBACK
        
        # Safe color access
        color = QColor('gray')  # DEFAULT
        if hasattr(item, 'color'):
            try:
                color = item.color
                if not color.isValid():
                    color = QColor('gray')  # VALIDATE
            except:
                pass  # Keep default
        
        symbols.append({...})  # Safe symbol creation
        
    except Exception as item_error:
        continue  # SKIP corrupted item, process next
```

#### 3. **FALLBACKS ESPECÍFICOS PARA ERRORES DE RASTER**
```python
except Exception as raster_error:
    # Ultimate fallback for any raster processing error
    symbols.append({
        'label': f"{layer.name()} (Raster Error)",
        'symbol': None,
        'color': QColor('red'),
        'layer_type': 'raster_error',
        'geometry_type': 'raster',
        'error_type': 'corrupted'  # Visual indicator of error
    })
```

#### 4. **DETECCIÓN ESPECÍFICA DE CAMBIOS DE RASTER**
```python
def on_renderer_changed(self):
    # Check if this is a raster layer change
    sender_layer = self.sender()
    is_raster_change = False
    if sender_layer and hasattr(sender_layer, '__class__'):
        if 'Raster' in sender_layer.__class__.__name__:
            is_raster_change = True
    
    if is_raster_change:
        # Extended recreation delay for raster safety
        self.force_overlay_recreation_raster_safe()  # 300ms delay
    else:
        self.force_overlay_recreation()  # Standard delay
```

#### 5. **RECREACIÓN EXTENDIDA PARA RASTER**
```python
def force_overlay_recreation_raster_safe(self):
    # Mark as destroyed immediately
    self.legend_overlay._destroyed = True
    
    # Hide and delete with raster-safe approach
    try:
        self.legend_overlay.hide()
        self.legend_overlay.deleteLater()
    except:
        pass  # Continue even if hide/delete fails
    
    # Extended delay for raster layer processing (300ms vs 150ms)
    QTimer.singleShot(300, self.recreate_overlay_delayed_raster_safe)
```

#### 6. **AUTO-UPDATE CON PROTECCIÓN DE RASTER**
```python
def update_legend_auto(self):
    # Check for raster layers in project
    has_raster_layers = False
    try:
        for layer in QgsProject.instance().mapLayers().values():
            if 'Raster' in layer.__class__.__name__:
                has_raster_layers = True
                break
    except:
        pass
    
    if has_raster_layers:
        self.debug_print("Auto-update with raster layers - using recreation")
```

### 🛡️ **ARQUITECTURA DE PROTECCIÓN RASTER**:

```
Raster Layer → Renderer Access → Shader Access → Color Ramp Access
     ↓              ↓              ↓               ↓
[Class Check]  [Safe Access]  [Null Check]   [Item Validation]
     ↓              ↓              ↓               ↓
[Type Detection] [Error Handle] [Fallback]    [Safe Processing]
     ↓              ↓              ↓               ↓
[Extended Delay] [Raster Flag] [Simple Symbol] [Color Validation]
```

### 📋 **TIPOS DE PROTECCIÓN POR NIVEL**:

| Nivel | Componente | Protección | Fallback |
|-------|------------|------------|----------|
| 1 | Renderer | try/except + null check | renderer = None |
| 2 | Band Count | safe access + validation | band_count = 1 |
| 3 | Shader | hasattr + try/except | shader = None |
| 4 | Ramp Function | existence + validation | simple symbol |
| 5 | Color Items | individual item processing | skip corrupted |
| 6 | Values/Colors | type checking + validation | safe defaults |

### 🎯 **OBJETIVO BETA 17**:

**ELIMINAR CRASHES ESPECÍFICOS DE RASTER** especialmente:
- ✅ **Pseudocolor monobanda** → Multi-level protection
- ✅ **Shader access failures** → Safe fallbacks
- ✅ **Color ramp corruption** → Item-by-item processing
- ✅ **Renderer state changes** → Extended cleanup delays
- ✅ **Mixed vector/raster projects** → Type-specific handling

### 🔬 **TESTING CRÍTICO BETA 17**:

1. **Pseudocolor Raster** → Activar/desactivar sin crash
2. **Color Ramp Changes** → Modificar rampa sin crash
3. **Mixed Projects** → Vector + Raster simultáneo
4. **Renderer Switching** → Cambiar de single band a pseudocolor
5. **Debug Mode + Raster** → Debe ser estable

**Beta 17 = Protección Total Raster + Fallbacks Robustos + Delays Extendidos**

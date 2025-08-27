# Arcadia WFS Downloader Suite para QGIS

## Descripción
Arcadia WFS Downloader es una suite de herramientas para QGIS que optimiza el flujo de trabajo con servicios de entidades vectoriales (WFS). El plugin automatiza la cadena de procesos de descarga, recorte a área de interés (AOI), filtrado y estilización de datos WFS, especialmente en un entorno de trabajo colaborativo.

## Instalación y Configuración Local

### 1. Instalación del Plugin
1. Abre QGIS
2. Ve a "Complementos > Administrar e instalar complementos"
3. Selecciona "Instalar desde ZIP"
4. Navega hasta el archivo `ArcadiaWFSDownloader.zip` y selecciónalo
5. Click en "Instalar Plugin"

### 2. Configuración Local
Por defecto, el plugin funciona en modo local sin necesidad de configuración adicional:

- Los archivos de configuración se almacenan en la carpeta del plugin
- La caché se guarda en la carpeta del plugin como `wfs_cache.gpkg`
- Los estilos se guardan junto a las capas descargadas

#### Ubicación de los archivos en modo local:
```
QGIS/profiles/default/python/plugins/ArcadiaWFSDownloader/
  ├── wfs_servers.dat    # Lista de servidores WFS
  ├── wfs_cache.gpkg     # Caché local de capas
  └── styles/            # Carpeta de estilos QML
```

### 3. Primeros Pasos
1. Abre QGIS
2. Ve a "Complementos > Arcadia Suite > Advanced WFS Downloader > Lanzador de Descargas WFS"
3. Selecciona un servidor de la lista (por defecto incluye el servidor de Delimitaciones Municipales)
4. Selecciona las capas a descargar
5. Configura el área de interés y otras opciones
6. Click en "Ejecutar"

### 4. Gestión de Servidores WFS
Para añadir o editar servidores WFS:
1. Ve a "Complementos > Arcadia Suite > Advanced WFS Downloader > Administrador de Fuentes WFS"
2. Usa los botones "Añadir", "Editar" o "Eliminar" para gestionar los servidores
3. Para cada servidor puedes:
   - Asignar un nombre descriptivo
   - Especificar la URL base
   - Detectar automáticamente las capas disponibles
   - Seleccionar el formato preferido de descarga

### 5. Migración de Local a Red
Si después de usar el plugin en modo local decides migrar a un entorno de trabajo en equipo:
1. Haz una copia de seguridad de tu archivo `wfs_servers.dat` local
2. Configura las carpetas compartidas como se describe en la siguiente sección
3. Copia tu archivo `wfs_servers.dat` a la carpeta de configuración compartida
4. Los estilos y la caché se generarán automáticamente en las nuevas ubicaciones

## Configuración para Trabajo en Equipo

### 1. Estructura de Carpetas Compartidas
El plugin utiliza tres carpetas principales que pueden configurarse para trabajo en equipo:

```
CARPETA_COMPARTIDA/
  ├── config/              # Configuraciones (wfs_servers.dat)
  ├── cache/              # Caché de capas descargadas (wfs_cache.gpkg)
  └── styles/             # Estilos QML compartidos
```

### 2. Configuración Inicial
1. Crea una estructura de carpetas compartida en red accesible para todo el equipo
2. Abre QGIS y ve a "Complementos > Arcadia Suite > Advanced WFS Downloader > Configurador"
3. Configura las rutas de las carpetas compartidas:
   - Carpeta de Configuración: `\\SERVIDOR\CARPETA_COMPARTIDA\config`
   - Carpeta de Estilos: `\\SERVIDOR\CARPETA_COMPARTIDA\styles`
   - Carpeta de Caché: `\\SERVIDOR\CARPETA_COMPARTIDA\cache`

### 3. Archivo wfs_servers.dat
El archivo `wfs_servers.dat` contiene la lista de servidores WFS disponibles. Se debe colocar en la carpeta de configuración.

Formato del archivo:
```
# Formato: Nombre (TAB) URL Base (TAB) TypeNames (TAB) Formato Preferido
Nombre_Servidor    URL_Base    TypeName1,TypeName2    Formato
```

Ejemplo incluido:
```
Delimitaciones municipales    https://terramapas.icv.gva.es/0105_Delimitaciones    ms:ICV.Comarcas,ms:ICV.ComunidadAutonoma,ms:ICV.Municipios,ms:ICV.Provincias    GeoPackage
```

Notas importantes:
- Usa TAB como separador (no espacios)
- Los TypeNames van separados por comas (sin espacios)
- Formatos soportados: GeoPackage, SHP (shape-zip), GML, GeoJSON

### 4. Sistema de Caché
- El archivo `wfs_cache.gpkg` se crea automáticamente en la carpeta de caché
- Las capas se almacenan como tablas dentro del GeoPackage
- El sistema verifica automáticamente si hay versiones más nuevas disponibles
- Cada usuario puede tener su propia caché local o usar la caché compartida

### 5. Sistema de Estilos
- Los estilos se guardan como archivos .qml en la carpeta de estilos
- Nombrado automático: `[typename].qml` (ejemplo: `ms_ICV_Municipios.qml`)
- Se aplican automáticamente al cargar las capas
- Se pueden compartir entre todos los usuarios

## Características Principales

### 1. Gestión Centralizada de Fuentes WFS
- Administrador de fuentes WFS con interfaz gráfica
- Configuración y prueba de conexiones
- Importación/exportación de configuraciones
- Detección automática de capas y formatos

### 2. Descarga Optimizada
- Soporte para múltiples formatos (SHP, GML, GeoJSON, GeoPackage)
- Sistema de caché local inteligente
- Validación de versiones remotas
- Manejo robusto de errores

### 3. Procesamiento Avanzado
- Recorte por AOI con buffer configurable
- Filtrado por expresiones
- Reparación automática de geometrías
- Asignación de CRS

### 4. Trabajo en Equipo
- Configuraciones compartidas
- Sistema de estilos centralizados
- Caché compartida
- Exportación/importación de configuraciones

## Requisitos
- QGIS 3.16 o superior
- Python 3.x
- Módulos requeridos: requests, configparser

## Instalación
1. Abrir QGIS
2. Ir a Complementos > Administrar e instalar complementos
3. Buscar "Arcadia WFS Downloader"
4. Click en Instalar

## Uso Básico
1. Configurar carpetas compartidas (opcional)
2. Añadir fuentes WFS en el Administrador
3. Usar el Lanzador para seleccionar y descargar capas
4. Las capas se descargarán, procesarán y cargarán automáticamente

## Desarrollo
Este plugin está desarrollado en Python utilizando PyQGIS y PyQt5. La arquitectura está diseñada siguiendo principios de separación de responsabilidades y modularidad.

### Estructura del Proyecto
- `configurator_dialog.py`: Configuración de carpetas compartidas
- `manager_dialog.py`: Administrador de fuentes WFS
- `launcher_dialog.py`: Interfaz principal de selección
- `downloader_tool.py`: Motor de procesamiento
- `settings_utils.py`: Utilidades de configuración
- `plugin_main.py`: Punto de entrada del plugin

## Contribuir
Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu funcionalidad
3. Envía un pull request

## Licencia
Este proyecto está licenciado bajo MIT License.

## Créditos
Desarrollado por José A. Sales con asistencia de IA.

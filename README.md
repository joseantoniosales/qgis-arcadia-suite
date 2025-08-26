# Arcadia WFS Downloader Suite para QGIS

## Descripción
Arcadia WFS Downloader es una suite de herramientas para QGIS que optimiza el flujo de trabajo con servicios de entidades vectoriales (WFS). El plugin automatiza la cadena de procesos de descarga, recorte a área de interés (AOI), filtrado y estilización de datos WFS, especialmente en un entorno de trabajo colaborativo.

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

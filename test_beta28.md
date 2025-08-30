1. Instalar complemento. Resultado OK
2. Cargar complemento. Resultado OK
3. Habilitar dos capas vectoriales. Resultado Error de python:

Ha ocurrido un error mientras se ejecutaba el código de Python: 

AttributeError: 'QGISChangeDebouncer' object has no attribute 'legend_executor' 
Traceback (most recent call last):
  File "/Users/jose/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/ArcadiaCanvasLegend/dialogs/canvas_legend_dialog.py", line 135, in _start_stability_verification
    self.legend_executor.start_legend_update()
AttributeError: 'QGISChangeDebouncer' object has no attribute 'legend_executor'

4. Click en botón "Apply". Resultado OK. Se carga la leyenda.
5. Activar capa raster con simbología psudocolor monobanda. Resultado Error de python y no aparece en la leyenda:

Ha ocurrido un error mientras se ejecutaba el código de Python: 

AttributeError: 'QGISChangeDebouncer' object has no attribute 'legend_executor' 
Traceback (most recent call last):
  File "/Users/jose/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/ArcadiaCanvasLegend/dialogs/canvas_legend_dialog.py", line 135, in _start_stability_verification
    self.legend_executor.start_legend_update()
AttributeError: 'QGISChangeDebouncer' object has no attribute 'legend_executor'


Python version: 3.9.5 (default, Sep 10 2021, 16:18:19) [Clang 12.0.5 (clang-1205.0.22.11)] 
QGIS version: 3.42.1-Münster Münster, 1fc52835a89 

6. Cargar archivo de estilos en capa vectorial. Resultado CRASH de QGIS (Ver log)
"""
Arcadia Canvas Legend Plugin for QGIS
Part of the Arcadia Suite

This plugin allows users to display and configure map legends
overlay on the QGIS canvas with full customization options.
"""

def classFactory(iface):
    """Load ArcadiaCanvasLegend class from file plugin_main.py"""
    from .plugin_main import ArcadiaCanvasLegendPlugin
    return ArcadiaCanvasLegendPlugin(iface)

def classFactory(iface):
    from .plugin_main import ArcadiaWFSDownloaderPlugin
    return ArcadiaWFSDownloaderPlugin(iface)
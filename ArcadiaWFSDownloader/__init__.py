def classFactory(iface):
    from .plugin_main import WFSDownloaderSuitePlugin
    return WFSDownloaderSuitePlugin(iface)

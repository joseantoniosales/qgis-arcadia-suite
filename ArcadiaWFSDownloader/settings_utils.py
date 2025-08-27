# settings_utils.py
import os

def get_settings_file_path():
    """Devuelve la ruta al archivo de configuración."""
    return os.path.join(get_config_dir(), 'config.ini')

def get_config_dir():
    """Devuelve la ruta al directorio de configuración."""
    config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return config_dir

def get_styles_dir():
    """Devuelve la ruta al directorio de estilos."""
    styles_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'styles')
    if not os.path.exists(styles_dir):
        os.makedirs(styles_dir)
    return styles_dir

def get_cache_dir():
    """Devuelve la ruta al directorio de caché."""
    cache_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir

def get_wfs_servers_path():
    """Devuelve la ruta al archivo de servidores WFS."""
    return os.path.join(get_config_dir(), 'wfs_servers.dat')

def ensure_plugin_directories():
    """Asegura que existan todos los directorios necesarios para el plugin."""
    get_config_dir()  # Directorio de configuración
    get_styles_dir()  # Directorio de estilos
    get_cache_dir()   # Directorio de caché


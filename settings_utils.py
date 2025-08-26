# settings_utils.py
import os

def get_settings_file_path():
    """Devuelve la ruta al archivo de configuración."""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.ini')


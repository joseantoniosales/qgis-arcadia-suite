"""
Utility functions for Arcadia Canvas Legend Plugin
Shared functions to avoid circular imports and provide common functionality
"""

import os
import configparser
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QStandardPaths


def get_settings_file_path():
    """
    Get the path to the Arcadia Suite settings file
    Returns the path to arcadia_suite_settings.ini
    """
    try:
        # Try to get the QGIS user profile directory
        profile_dir = QgsApplication.qgisSettingsDirPath()
        settings_path = os.path.join(profile_dir, 'arcadia_suite_settings.ini')
        
        # If file doesn't exist, create a default one
        if not os.path.exists(settings_path):
            create_default_settings_file(settings_path)
            
        return settings_path
    except Exception as e:
        print(f"Error getting settings file path: {e}")
        # Fallback to user documents directory
        docs_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        fallback_path = os.path.join(docs_dir, 'ArcadiaSuite', 'arcadia_suite_settings.ini')
        os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
        if not os.path.exists(fallback_path):
            create_default_settings_file(fallback_path)
        return fallback_path


def create_default_settings_file(file_path):
    """
    Create a default settings file for Arcadia Suite
    """
    try:
        config = configparser.ConfigParser()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Default settings sections
        config['PATHS'] = {
            'styles_directory': '',
            'cache_directory': '',
            'export_directory': ''
        }
        
        config['CANVAS_LEGEND'] = {
            'default_position': 'bottom_right',
            'default_font_family': 'Arial',
            'default_font_size': '10',
            'default_background_color': 'white',
            'default_frame_color': 'black',
            'default_frame_width': '1'
        }
        
        # Write the configuration file
        with open(file_path, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
            
    except Exception as e:
        print(f"Error creating default settings file: {e}")


def get_arcadia_setting(section, key, default_value=''):
    """
    Get a setting value from the Arcadia Suite configuration
    
    Args:
        section (str): Configuration section name
        key (str): Configuration key name
        default_value (str): Default value if key not found
        
    Returns:
        str: The configuration value or default_value
    """
    try:
        settings_path = get_settings_file_path()
        config = configparser.ConfigParser()
        config.read(settings_path, encoding='utf-8')
        
        if config.has_section(section) and config.has_option(section, key):
            return config.get(section, key)
        else:
            return default_value
            
    except Exception as e:
        print(f"Error reading Arcadia setting {section}.{key}: {e}")
        return default_value


def set_arcadia_setting(section, key, value):
    """
    Set a setting value in the Arcadia Suite configuration
    
    Args:
        section (str): Configuration section name
        key (str): Configuration key name
        value (str): Value to set
    """
    try:
        settings_path = get_settings_file_path()
        config = configparser.ConfigParser()
        config.read(settings_path, encoding='utf-8')
        
        if not config.has_section(section):
            config.add_section(section)
            
        config.set(section, key, str(value))
        
        with open(settings_path, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
            
    except Exception as e:
        print(f"Error setting Arcadia setting {section}.{key}: {e}")


def validate_color_value(color_str):
    """
    Validate if a string represents a valid color value
    
    Args:
        color_str (str): Color string to validate
        
    Returns:
        bool: True if valid color, False otherwise
    """
    try:
        from qgis.PyQt.QtGui import QColor
        color = QColor(color_str)
        return color.isValid()
    except:
        return False


def safe_float_conversion(value, default=0.0):
    """
    Safely convert a value to float with a default fallback
    
    Args:
        value: Value to convert
        default (float): Default value if conversion fails
        
    Returns:
        float: Converted value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_conversion(value, default=0):
    """
    Safely convert a value to int with a default fallback
    
    Args:
        value: Value to convert
        default (int): Default value if conversion fails
        
    Returns:
        int: Converted value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

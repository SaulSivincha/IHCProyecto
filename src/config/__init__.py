#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de configuración centralizada
Importa todas las configuraciones del proyecto

@author: mherrera
"""

from .stereo_config import StereoConfig
from .game_config import GameConfig
from .app_config import AppConfig

__all__ = [
    'StereoConfig',
    'GameConfig',
    'AppConfig',
]


def print_all_configs():
    """Imprime todas las configuraciones del sistema"""
    AppConfig.print_config()
    StereoConfig.print_config()
    GameConfig.print_config()
    AppConfig.print_controls()


def load_all_configurations():
    """Carga todas las configuraciones necesarias"""
    print("Cargando configuraciones...")
    
    # Cargar calibración estéreo
    StereoConfig.load_calibration()
    
    # Asegurar directorios
    AppConfig.ensure_directories()
    
    # Verificar soundfont
    soundfont = AppConfig.get_soundfont_path()
    if not soundfont:
        print("⚠ ADVERTENCIA: No se encontró el archivo soundfont")
        print("  El audio puede no funcionar correctamente")
    
    print("✓ Configuraciones cargadas\n")
    
    return True

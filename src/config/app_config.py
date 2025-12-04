#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración general de la aplicación
Parámetros de app, modos, audio y UI general

@author: mherrera
"""

import os
from pathlib import Path


class AppConfig:
    """Configuración general de la aplicación"""
    
    # ==================== APP ====================
    APP_NAME = "Virtual Piano & Rhythm Game"
    APP_VERSION = "2.0.0"
    APP_AUTHOR = "mherrera"
    
    # ==================== MODOS DE JUEGO ====================
    class GameMode:
        FREE_PLAY = "free_play"           # Modo libre (piano virtual)
        RHYTHM_GAME = "rhythm_game"       # Juego de ritmo
        LEARN_MODE = "learn"              # Modo aprendizaje (ritmo lento)
        SONG_SELECTOR = "song_selector"   # Selector de canciones
        PAUSED = "paused"                 # Pausado
    
    DEFAULT_MODE = GameMode.FREE_PLAY
    
    # ==================== AUDIO ====================
    AUDIO_ENABLED_DEFAULT = True
    OCTAVE_BASE = 0                       # Octava base para MIDI
    
    # Ruta del soundfont - buscar en múltiples ubicaciones
    SOUNDFONT_PATHS = [
        r"C:\CodingWindows\IHC_Proyecto_Fork\IHCProyecto\utils\fluid\FluidR3_GM.sf2",
        r"utils/fluid/FluidR3_GM.sf2",
        r"../utils/fluid/FluidR3_GM.sf2",
    ]
    
    @staticmethod
    def get_soundfont_path():
        """Encuentra el soundfont en las rutas configuradas"""
        for path in AppConfig.SOUNDFONT_PATHS:
            if os.path.exists(path):
                return path
        print("⚠ No se encontró el archivo soundfont")
        return None
    
    # ==================== UI GENERAL ====================
    SHOW_DASHBOARD_DEFAULT = False        # Mostrar dashboard de debugging
    SHOW_INSTRUCTIONS = True              # Mostrar instrucciones al inicio
    INSTRUCTIONS_TIMEOUT = 300            # Frames antes de ocultar instrucciones
    
    # Window
    MAIN_WINDOW_NAME = "Virtual Piano - Rhythm Game"
    
    # Colors para UI general (no específicos del juego)
    COLOR_INSTRUCTIONS_BG = (20, 40, 60)
    COLOR_INSTRUCTIONS_TEXT = (200, 220, 255)
    COLOR_DASHBOARD_TEXT = (0, 255, 0)
    
    # ==================== CÁMARAS ====================
    CAMERA_INIT_WAIT = 0.5                # Tiempo de espera para inicialización de cámaras (segundos)
    
    # ==================== PERFORMANCE ====================
    TARGET_FPS = 30                       # FPS objetivo de la aplicación
    ENABLE_PERFORMANCE_STATS = False      # Mostrar estadísticas de rendimiento
    
    # ==================== CONTROLS ====================
    # Teclas de control de la aplicación
    KEY_QUIT = ord('q')                   # Salir
    KEY_DASHBOARD = ord('d')              # Toggle dashboard
    KEY_RHYTHM_GAME = ord('g')            # Modo juego de ritmo
    KEY_FREE_PLAY = ord('f')              # Modo libre
    KEY_LEARN_MODE = ord('a')             # Modo aprendizaje
    KEY_DEPTH_SHOW = ord('p')             # Mostrar profundidades
    
    # ==================== PATHS ====================
    # Directorio base del proyecto
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # Directorios de datos
    DATA_DIR = BASE_DIR / "data"
    SONGS_DIR = DATA_DIR / "songs"
    CALIBRATION_DIR = BASE_DIR / "camcalibration"
    
    @staticmethod
    def ensure_directories():
        """Crea directorios necesarios si no existen"""
        AppConfig.DATA_DIR.mkdir(exist_ok=True)
        AppConfig.SONGS_DIR.mkdir(exist_ok=True)
        AppConfig.CALIBRATION_DIR.mkdir(exist_ok=True)
    
    # ==================== DEBUG ====================
    DEBUG_MODE = False                    # Modo debug (más logging)
    VERBOSE_HAND_DETECTION = False        # Logging detallado de detección
    
    # ==================== DETECCIÓN DE TECLAS ====================
    # Sistema de detección por profundidad y velocidad
    DEPTH_THRESHOLD = 3.5                 # Umbral de profundidad para presión (cm)
                                          # Rango recomendado: 2.0-5.0 cm
                                          # Menor valor = más estricto
    
    # Sistema de detección de movimiento (velocity-based triggering)
    VELOCITY_THRESHOLD = 1.5              # Velocidad mínima hacia abajo (cm/frame)
                                          # para activar tecla
                                          # Valores típicos: 1.0-3.0 cm/frame
                                          # Mayor valor = requiere golpe más fuerte
    
    VELOCITY_ENABLED = False              # Activar detección por velocidad
                                          # True = requiere movimiento descendente
                                          # False = modo clásico (solo profundidad)
    
    VELOCITY_HISTORY_SIZE = 3             # Número de frames para calcular velocidad
                                          # Valores típicos: 2-5 frames
                                          # Más frames = más suave pero menos responsivo
    
    @staticmethod
    def set_key_sensitivity(sensitivity='normal'):
        """
        Ajusta la sensibilidad de detección de teclas
        
        Args:
            sensitivity: 'soft', 'normal', 'hard', 'classic'
        """
        if sensitivity == 'soft':
            # Piano sensible (toques suaves)
            AppConfig.DEPTH_THRESHOLD = 4.0
            AppConfig.VELOCITY_THRESHOLD = 1.0
            AppConfig.VELOCITY_ENABLED = True
            print("✓ Sensibilidad: SUAVE (toques ligeros)")
        
        elif sensitivity == 'normal':
            # Configuración balanceada (recomendado)
            AppConfig.DEPTH_THRESHOLD = 3.5
            AppConfig.VELOCITY_THRESHOLD = 1.5
            AppConfig.VELOCITY_ENABLED = False
            print("✓ Sensibilidad: NORMAL (balanceado - modo clásico)")
        
        elif sensitivity == 'hard':
            # Requiere golpe fuerte
            AppConfig.DEPTH_THRESHOLD = 2.5
            AppConfig.VELOCITY_THRESHOLD = 2.5
            AppConfig.VELOCITY_ENABLED = True
            print("✓ Sensibilidad: FUERTE (golpes pronunciados)")
        
        elif sensitivity == 'classic':
            # Modo clásico sin detección de velocidad
            AppConfig.DEPTH_THRESHOLD = 4.5
            AppConfig.VELOCITY_ENABLED = False
            print("✓ Sensibilidad: CLÁSICA (sin detección de velocidad)")
        
        else:
            print(f"⚠ Sensibilidad '{sensitivity}' no reconocida")
            print("   Opciones: 'soft', 'normal', 'hard', 'classic'")
    
    # ==================== MÉTODOS ====================
    
    @staticmethod
    def print_config():
        """Imprime la configuración actual de la app"""
        print("\n" + "="*60)
        print(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        print("="*60)
        print(f"Modo por defecto: {AppConfig.DEFAULT_MODE}")
        print(f"Audio: {'Enabled' if AppConfig.AUDIO_ENABLED_DEFAULT else 'Disabled'}")
        print(f"Soundfont: {AppConfig.get_soundfont_path() or 'No encontrado'}")
        print(f"Target FPS: {AppConfig.TARGET_FPS}")
        print(f"Debug mode: {'On' if AppConfig.DEBUG_MODE else 'Off'}")
        print(f"\nDetección de teclas:")
        print(f"  Umbral profundidad: {AppConfig.DEPTH_THRESHOLD} cm")
        print(f"  Detección por velocidad: {'On' if AppConfig.VELOCITY_ENABLED else 'Off'}")
        if AppConfig.VELOCITY_ENABLED:
            print(f"  Velocidad mínima: {AppConfig.VELOCITY_THRESHOLD} cm/frame")
        print("="*60 + "\n")
    
    @staticmethod
    def enable_debug(enabled=True):
        """Activa/desactiva modo debug"""
        AppConfig.DEBUG_MODE = enabled
        AppConfig.ENABLE_PERFORMANCE_STATS = enabled
        AppConfig.VERBOSE_HAND_DETECTION = enabled
        status = "activado" if enabled else "desactivado"
        print(f"✓ Modo debug {status}")
    
    @staticmethod
    def get_key_bindings():
        """Retorna diccionario con las teclas de control"""
        return {
            'quit': chr(AppConfig.KEY_QUIT),
            'dashboard': chr(AppConfig.KEY_DASHBOARD),
            'rhythm_game': chr(AppConfig.KEY_RHYTHM_GAME),
            'free_play': chr(AppConfig.KEY_FREE_PLAY),
            'learn_mode': chr(AppConfig.KEY_LEARN_MODE),
            'show_depth': chr(AppConfig.KEY_DEPTH_SHOW),
        }
    
    @staticmethod
    def print_controls():
        """Imprime los controles de la aplicación"""
        bindings = AppConfig.get_key_bindings()
        print("\n" + "="*60)
        print("CONTROLES")
        print("="*60)
        print(f"[{bindings['quit']}] Salir")
        print(f"[{bindings['dashboard']}] Toggle Dashboard")
        print(f"[{bindings['rhythm_game']}] Juego de Ritmo")
        print(f"[{bindings['free_play']}] Modo Libre")
        print(f"[{bindings['learn_mode']}] Modo Aprendizaje")
        print(f"[{bindings['show_depth']}] Mostrar Profundidades")
        print("="*60 + "\n")


# Crear directorios al importar el módulo
AppConfig.ensure_directories()

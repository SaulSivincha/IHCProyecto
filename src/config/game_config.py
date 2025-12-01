#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada para el juego de ritmo
Todos los parámetros de gameplay, UI, timing y colores

@author: mherrera
"""


class GameConfig:
    """Configuración centralizada para el juego de ritmo"""
    
    # ==================== GAMEPLAY ====================
    NOTE_SPEED = 50                    # Velocidad de caída de notas (px/s)
    HIT_ZONE_Y = 300                   # Posición Y de la zona de acierto
    HIT_ZONE_HEIGHT = 40               # Altura de la zona de acierto
    
    # ==================== TIMING ====================
    PERFECT_WINDOW = 0.10              # Ventana para PERFECT (segundos) ±100ms
    GOOD_WINDOW = 0.25                 # Ventana para GOOD (segundos) ±250ms
    MISS_MULTIPLIER = 1.5              # Multiplicador para considerar nota perdida
    
    # ==================== SCORING ====================
    PERFECT_SCORE_BASE = 100           # Puntos base por PERFECT
    GOOD_SCORE_BASE = 50               # Puntos base por GOOD
    COMBO_MULTIPLIER_ENABLED = True    # Multiplicar score por combo
    
    # ==================== UI COLORS - Professional Dark Theme ====================
    COLOR_BG_OVERLAY = (20, 20, 40)              # Fondo oscuro semi-transparente
    COLOR_HIT_ZONE_PRIMARY = (0, 200, 100)       # Color primario zona de acierto
    COLOR_HIT_ZONE_SECONDARY = (0, 255, 150)     # Color secundario zona de acierto
    COLOR_NOTE = (0, 200, 255)                   # Color de las notas (cyan)
    COLOR_NOTE_GLOW = (100, 230, 255)            # Color del efecto glow
    COLOR_LANE_DIVIDER = (60, 60, 80)            # Color de líneas divisoras
    COLOR_PERFECT_LINE = (255, 255, 0)           # Color línea de timing perfecto
    
    # Stats Panel Colors
    COLOR_SCORE_GOLD = (255, 215, 0)             # Color dorado para score
    COLOR_PERFECT = (0, 255, 100)                # Color verde para PERFECT
    COLOR_GOOD = (255, 255, 0)                   # Color amarillo para GOOD
    COLOR_MISS = (255, 50, 50)                   # Color rojo para MISS
    COLOR_PANEL_BG = (30, 30, 50)                # Fondo de paneles UI
    COLOR_PANEL_BORDER_SCORE = (255, 215, 0)     # Borde dorado panel score
    COLOR_PANEL_BORDER_STATS = (100, 200, 255)   # Borde azul panel stats
    COLOR_TEXT_WHITE = (255, 255, 255)           # Texto blanco
    COLOR_TEXT_BLACK = (0, 0, 0)                 # Texto negro (sombra)
    
    # Combo Colors (dinámico según combo)
    COLOR_COMBO_LOW = (0, 255, 255)              # Combo < 10 (cyan)
    COLOR_COMBO_HIGH = (255, 100, 255)           # Combo >= 10 (magenta)
    
    # ==================== VISUAL EFFECTS ====================
    GLOW_DISTANCE_THRESHOLD = 80       # Distancia (px) para activar efecto glow
    GLOW_INTENSITY_MAX = 0.4           # Intensidad máxima del glow
    
    COMBO_SCALE_MIN = 0.8              # Escala mínima del texto combo
    COMBO_SCALE_MAX = 1.2              # Escala máxima del texto combo
    COMBO_SCALE_RATE = 0.02            # Tasa de crecimiento (por unidad de combo)
    
    BACKGROUND_OVERLAY_ALPHA = 0.85    # Transparencia del overlay oscuro
    HIT_ZONE_GRADIENT_ALPHA = 0.3      # Transparencia del gradiente
    NOTE_ALPHA = 0.3                   # Transparencia de las notas
    PANEL_ALPHA = 0.3                  # Transparencia de paneles UI
    
    # ==================== UI LAYOUT ====================
    # Score Panel (izquierda)
    SCORE_PANEL_WIDTH = 280
    SCORE_PANEL_HEIGHT = 160
    SCORE_PANEL_X = 10
    SCORE_PANEL_Y = 10
    
    # Stats Panel (derecha)
    STATS_PANEL_WIDTH = 240
    STATS_PANEL_HEIGHT = 200
    STATS_PANEL_OFFSET_RIGHT = 10      # Distancia desde borde derecho
    STATS_PANEL_Y = 10
    
    # Font Sizes
    FONT_SIZE_SCORE = 0.9
    FONT_SIZE_COMBO = 1.0              # Base (se escala dinámicamente)
    FONT_SIZE_STATS_TITLE = 0.8
    FONT_SIZE_STATS_ITEM = 0.7
    
    # ==================== HAND DETECTION ====================
    REQUIRE_BOTH_HANDS = True          # Requiere ambas manos para iniciar
    HAND_LOSS_GRACE_PERIOD = 2.0      # Segundos antes de pausar por pérdida de manos
    HAND_DETECTION_MESSAGE = "Esperando ambas manos..."
    
    # ==================== SONG SELECTOR ====================
    SELECTOR_PANEL_WIDTH = 400
    SELECTOR_PANEL_HEIGHT_PER_SONG = 70
    SELECTOR_TITLE_SIZE = 1.8
    SELECTOR_SONG_SIZE = 0.8
    SELECTOR_BPM_SIZE = 0.6
    
    # ==================== MÉTODOS ====================
    
    @staticmethod
    def print_config():
        """Imprime la configuración actual del juego"""
        print("\n" + "="*60)
        print("CONFIGURACIÓN DEL JUEGO DE RITMO")
        print("="*60)
        print(f"Velocidad de notas: {GameConfig.NOTE_SPEED} px/s")
        print(f"Zona de acierto: Y={GameConfig.HIT_ZONE_Y}, Height={GameConfig.HIT_ZONE_HEIGHT}")
        print(f"Timing: PERFECT=±{GameConfig.PERFECT_WINDOW*1000:.0f}ms, GOOD=±{GameConfig.GOOD_WINDOW*1000:.0f}ms")
        print(f"Scoring: PERFECT={GameConfig.PERFECT_SCORE_BASE}, GOOD={GameConfig.GOOD_SCORE_BASE}")
        print(f"Combo multiplier: {'Enabled' if GameConfig.COMBO_MULTIPLIER_ENABLED else 'Disabled'}")
        print(f"Require both hands: {'Yes' if GameConfig.REQUIRE_BOTH_HANDS else 'No'}")
        print("="*60 + "\n")
    
    @staticmethod
    def update_note_speed(new_speed):
        """Actualiza la velocidad de las notas"""
        if new_speed < 10:
            print("⚠ Velocidad muy baja (mínimo 10 px/s)")
            return False
        if new_speed > 200:
            print("⚠ Velocidad muy alta (máximo 200 px/s)")
            return False
        GameConfig.NOTE_SPEED = new_speed
        print(f"✓ Velocidad actualizada a: {new_speed} px/s")
        return True
    
    @staticmethod
    def update_timing_windows(perfect_ms=None, good_ms=None):
        """Actualiza las ventanas de timing"""
        if perfect_ms is not None:
            GameConfig.PERFECT_WINDOW = perfect_ms / 1000.0
            print(f"✓ Ventana PERFECT actualizada a: ±{perfect_ms}ms")
        
        if good_ms is not None:
            GameConfig.GOOD_WINDOW = good_ms / 1000.0
            print(f"✓ Ventana GOOD actualizada a: ±{good_ms}ms")
        
        return True
    
    @staticmethod
    def enable_combo_multiplier(enabled=True):
        """Activa/desactiva el multiplicador de combo"""
        GameConfig.COMBO_MULTIPLIER_ENABLED = enabled
        status = "activado" if enabled else "desactivado"
        print(f"✓ Multiplicador de combo {status}")
        return True
    
    @staticmethod
    def set_difficulty_preset(difficulty):
        """
        Configura presets de dificultad
        difficulty: 'easy', 'normal', 'hard', 'expert'
        """
        presets = {
            'easy': {
                'note_speed': 30,
                'perfect_window': 0.15,
                'good_window': 0.35
            },
            'normal': {
                'note_speed': 50,
                'perfect_window': 0.10,
                'good_window': 0.25
            },
            'hard': {
                'note_speed': 75,
                'perfect_window': 0.08,
                'good_window': 0.20
            },
            'expert': {
                'note_speed': 100,
                'perfect_window': 0.05,
                'good_window': 0.15
            }
        }
        
        if difficulty not in presets:
            print(f"✗ Dificultad '{difficulty}' no válida")
            print(f"  Opciones: {', '.join(presets.keys())}")
            return False
        
        preset = presets[difficulty]
        GameConfig.NOTE_SPEED = preset['note_speed']
        GameConfig.PERFECT_WINDOW = preset['perfect_window']
        GameConfig.GOOD_WINDOW = preset['good_window']
        
        print(f"✓ Dificultad configurada: {difficulty.upper()}")
        print(f"  Velocidad: {preset['note_speed']} px/s")
        print(f"  PERFECT: ±{preset['perfect_window']*1000:.0f}ms")
        print(f"  GOOD: ±{preset['good_window']*1000:.0f}ms")
        
        return True

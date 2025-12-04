#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de importaciones - Verifica que todos los módulos se importan correctamente
"""

print("\n" + "="*70)
print("VERIFICANDO IMPORTACIONES DEL PROYECTO")
print("="*70 + "\n")

try:
    print("✓ Importando stereo_config...")
    from src.vision.stereo_config import StereoConfig
    config = StereoConfig()
    print(f"  ✓ StereoConfig cargado correctamente")
    print(f"    - Cámaras: LEFT={config.LEFT_CAMERA_SOURCE}, RIGHT={config.RIGHT_CAMERA_SOURCE}")
    print(f"    - Resolución: {config.PIXEL_WIDTH}x{config.PIXEL_HEIGHT}")
    print(f"    - Umbral profundidad: {config.DEPTH_THRESHOLD} cm\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando hand_detector...")
    from src.vision.hand_detector import HandDetector
    print(f"  ✓ HandDetector cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando keyboard_mapper...")
    from src.vision.keyboard_mapper import KeyboardMap
    km = KeyboardMap(depth_threshold=config.DEPTH_THRESHOLD)
    print(f"  ✓ KeyboardMap cargado correctamente")
    print(f"    - Umbral: {km.depth_threshold} cm\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando angles...")
    from src.vision.angles import Frame_Angles
    print(f"  ✓ Frame_Angles cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando video_thread...")
    from src.vision.video_thread import VideoThread
    print(f"  ✓ VideoThread cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando side_contact_detector...")
    from src.vision.side_contact_detector import SideContactDetector
    print(f"  ✓ SideContactDetector cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando virtual_keyboard...")
    from src.piano.virtual_keyboard import VirtualKeyboard
    print(f"  ✓ VirtualKeyboard cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando ui_helper...")
    from src.ui.ui_helper import UIHelper
    print(f"  ✓ UIHelper cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

try:
    print("✓ Importando rythm_game...")
    from src.gameplay.rythm_game import RhythmGame
    print(f"  ✓ RhythmGame cargado correctamente\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
    exit(1)

print("="*70)
print("✓ TODOS LOS MÓDULOS SE IMPORTAN CORRECTAMENTE")
print("="*70)
print("\nResumen de configuración:")
config.print_config()
print("\n¡Listo para ejecutar main.py!\n")

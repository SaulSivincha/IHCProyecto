#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada para visión estereoscópica
Contiene todos los parámetros de hardware y calibración

@author: mherrera
"""

import json
import os
from pathlib import Path


class StereoConfig:
    """Clase de configuración para el sistema estéreo"""
    
    # ==================== CÁMARAS ====================
    LEFT_CAMERA_SOURCE = 1          # ID de cámara izquierda
    RIGHT_CAMERA_SOURCE = 2         # ID de cámara derecha
    PIXEL_WIDTH = 640               # Ancho en píxeles
    PIXEL_HEIGHT = 480              # Alto en píxeles
    FRAME_RATE = 30                 # FPS objetivo
    
    # ==================== CALIBRACIÓN ÓPTICA ====================
    # Logi C920s HD Pro Webcam
    CAMERA_H_FOV = 70.42            # Campo de visión horizontal (grados)
    CAMERA_V_FOV = 43.3             # Campo de visión vertical (grados)
    H_FOV_RECTIFICATION = 21.42     # Corrección de FoV horizontal
    V_FOV_RECTIFICATION = (CAMERA_V_FOV * H_FOV_RECTIFICATION / CAMERA_H_FOV)
    
    # Ángulos efectivos después de corrección
    ANGLE_WIDTH = CAMERA_H_FOV - H_FOV_RECTIFICATION
    ANGLE_HEIGHT = CAMERA_V_FOV - V_FOV_RECTIFICATION
    
    # ==================== GEOMETRÍA ESTÉREO ====================
    CAMERA_SEPARATION = 14.21       # Distancia entre cámaras (cm)
    VKB_CENTER_DISTANCE = 71        # Distancia del teclado virtual (cm)
    
    # ==================== DETECCIÓN DE PROFUNDIDAD ====================
    DEPTH_THRESHOLD = 3.5           # Umbral de profundidad para presión (cm)
                                     # Aumentado para mejor detección de dedos
                                     # Rango recomendado: 2.0-5.0 cm
    
    # ==================== PARÁMETROS DE DETECCIÓN ====================
    HAND_DETECTION_CONFIDENCE = 0.75  # Confianza para detectar mano
    HAND_TRACKING_CONFIDENCE = 0.5    # Confianza para rastrear mano
    MAX_HANDS = 2                     # Máximo de manos a detectar
    
    # ==================== UI ====================
    CAMERA_IN_FRONT_OF_YOU = True   # Vista frontal (True) o lateral (False)
    DISPLAY_DASHBOARD_DEFAULT = False  # Mostrar dashboard por defecto
    
    # ==================== RUTA DE AUDIO ====================
    SOUNDFONT_PATH = r"C:\CodingWindows\IHC_Proyecto_Fork\IHCProyecto\utils\fluid\FluidR3_GM.sf2"
    
    # ==================== TECLADO VIRTUAL ====================
    KEYBOARD_TOTAL_KEYS = 24        # 2 octavas completas: C-B x2
    KEYBOARD_WHITE_KEYS = 14        # 7 teclas blancas por octava
    OCTAVE_BASE = 0                 # Octava base
    
    # Posición del teclado virtual (porcentajes del canvas)
    KEYBOARD_X0_RATIO = 0.20        # Posición X inicial (20% del ancho)
    KEYBOARD_Y0_RATIO = 0.35        # Posición Y inicial (35% del alto)
    KEYBOARD_X1_RATIO = 0.80        # Posición X final (80% del ancho)
    KEYBOARD_Y1_RATIO = 0.55        # Posición Y final (55% del alto)
    
    # Relaciones de tamaño de teclas (basado en piano real)
    BLACK_KEY_WIDTH_RATIO = 0.54    # Ancho tecla negra / ancho tecla blanca (13.7mm / 23.5mm)
    WHITE_KEY_WIDTH_RATIO = 0.93    # Ancho tecla blanca base
    BLACK_KEY_HEIGHT_RATIO = 2/3    # Altura tecla negra / altura tecla blanca
    KEYBOARD_ALPHA = 0.5            # Transparencia del teclado virtual
    
    # ==================== CORRECCIÓN DE PROFUNDIDAD ====================
    # Coeficientes para corrección de profundidad (delta_y)
    DEPTH_CORRECTION_A = 0.006509695290859  # Coeficiente cuadrático
    DEPTH_CORRECTION_B = 0.039473684210526  # Coeficiente lineal
    
    # ==================== JUEGO DE RITMO ====================
    NOTE_SPEED = 50                 # Velocidad de caída de notas (píxeles/segundo)
    NOTE_SPEED_LEARN = 30           # Velocidad en modo aprender
    HIT_ZONE_Y = 300                # Posición Y de la zona de acierto
    HIT_ZONE_HEIGHT = 40            # Altura de la zona de acierto
    PERFECT_WINDOW = 0.10           # Ventana de tiempo para PERFECT (±100ms)
    GOOD_WINDOW = 0.25              # Ventana de tiempo para GOOD (±250ms)
    
    # ==================== AUDIO ====================
    NOTE_VELOCITY = 127 * 2 // 3    # Velocidad de notas MIDI (84)
    AUDIO_DRIVER = 'dsound'         # Driver de audio (Windows)
    
    # ==================== DETECCIÓN DE CONTACTO ====================
    TABLE_Y_THRESHOLD_RATIO = 0.75  # Ratio de posición Y para detectar mesa (75% del alto)
    CONTACT_TOLERANCE = 10          # Tolerancia en píxeles para detectar contacto
    
    # ==================== PROCESAMIENTO ====================
    QUEUE_LENGTH = 3                # Longitud de cola para estabilización
    FRAME_WAIT_TIME = 0.1           # Tiempo de espera entre frames (segundos)
    FRAME_WAIT_TIME_GAME = 0.0      # Tiempo de espera en modo juego (sin delay)
    FRAME_WAIT_TIME_SETUP = 0.01    # Tiempo de espera en setup
    CAMERA_INIT_WAIT = 0.5          # Tiempo de espera para inicializar cámaras
    STABILIZATION_WAIT = 0.5        # Tiempo de espera para estabilización
    
    # ==================== UI ====================
    INSTRUCTIONS_TIMEOUT = 300      # Frames antes de ocultar instrucciones (10s a 30fps)
    CROSSHAIR_RADIUS = 24           # Radio de las cruces de referencia
    CROSSHAIR_LINE_WIDTH = 2        # Grosor de líneas de cruces
    CROSSHAIR_CIRCLE_WIDTH = 1      # Grosor de círculo de cruces
    
    # ==================== MÉTODOS ====================
    
    @staticmethod
    def print_config():
        """Imprime la configuración actual en pantalla"""
        print("\n" + "="*70)
        print("CONFIGURACIÓN ESTÉREO ACTUAL")
        print("="*70)
        print(f"Cámaras: LEFT={StereoConfig.LEFT_CAMERA_SOURCE}, RIGHT={StereoConfig.RIGHT_CAMERA_SOURCE}")
        print(f"Resolución: {StereoConfig.PIXEL_WIDTH}x{StereoConfig.PIXEL_HEIGHT} @ {StereoConfig.FRAME_RATE}fps")
        print(f"FoV: H={StereoConfig.CAMERA_H_FOV}°, V={StereoConfig.CAMERA_V_FOV}°")
        print(f"Ángulos efectivos: W={StereoConfig.ANGLE_WIDTH:.2f}°, H={StereoConfig.ANGLE_HEIGHT:.2f}°")
        print(f"Separación cámaras: {StereoConfig.CAMERA_SEPARATION} cm")
        print(f"Distancia teclado: {StereoConfig.VKB_CENTER_DISTANCE} cm")
        print(f"Umbral profundidad: {StereoConfig.DEPTH_THRESHOLD} cm")
        print(f"Confianza detección: {StereoConfig.HAND_DETECTION_CONFIDENCE}")
        print(f"Confianza rastreo: {StereoConfig.HAND_TRACKING_CONFIDENCE}")
        print(f"Teclado: {StereoConfig.KEYBOARD_WHITE_KEYS} blancas + "
              f"{StereoConfig.KEYBOARD_TOTAL_KEYS - StereoConfig.KEYBOARD_WHITE_KEYS} negras")
        print(f"Juego: Velocidad={StereoConfig.NOTE_SPEED}px/s, "
              f"Perfect={StereoConfig.PERFECT_WINDOW*1000:.0f}ms, "
              f"Good={StereoConfig.GOOD_WINDOW*1000:.0f}ms")
        print("="*70 + "\n")
    
    @staticmethod
    def update_depth_threshold(new_threshold):
        """Actualiza dinámicamente el umbral de profundidad"""
        if new_threshold < 0.5:
            print("⚠ Umbral muy bajo (mínimo 0.5 cm)")
            return False
        if new_threshold > 10:
            print("⚠ Umbral muy alto (máximo 10 cm)")
            return False
        StereoConfig.DEPTH_THRESHOLD = new_threshold
        print(f"✓ Umbral actualizado a: {new_threshold:.2f} cm")
        return True
    
    @staticmethod
    def update_camera_sources(left_id, right_id):
        """Actualiza las fuentes de cámara"""
        StereoConfig.LEFT_CAMERA_SOURCE = left_id
        StereoConfig.RIGHT_CAMERA_SOURCE = right_id
        print(f"✓ Cámaras actualizadas: LEFT={left_id}, RIGHT={right_id}")
    
    @staticmethod
    def load_calibration(calibration_path='camcalibration/calibration.json'):
        """
        Carga calibración guardada desde archivo JSON
        
        Args:
            calibration_path: Ruta del archivo de calibración
            
        Returns:
            True si se cargó exitosamente, False en caso contrario
        """
        if not os.path.exists(calibration_path):
            print(f"⚠ No se encontró archivo de calibración en: {calibration_path}")
            print("  Usando valores por defecto")
            return False
        
        try:
            with open(calibration_path, 'r') as f:
                calib_data = json.load(f)
            
            # Actualizar parámetros desde la calibración
            if 'camera_separation_cm' in calib_data:
                StereoConfig.CAMERA_SEPARATION = calib_data['camera_separation_cm']
            
            if 'keyboard_distance_cm' in calib_data:
                StereoConfig.VKB_CENTER_DISTANCE = calib_data['keyboard_distance_cm']
            
            print(f"✓ Calibración cargada desde: {calibration_path}")
            print(f"  Separación cámaras: {StereoConfig.CAMERA_SEPARATION:.2f} cm")
            print(f"  Distancia teclado: {StereoConfig.VKB_CENTER_DISTANCE:.2f} cm")
            
            return True
        
        except Exception as e:
            print(f"✗ Error al cargar calibración: {e}")
            print("  Usando valores por defecto")
            return False


# Cargar calibración automáticamente al importar
StereoConfig.load_calibration()

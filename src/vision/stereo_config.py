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
    RIGHT_CAMERA_SOURCE =  2         # ID de cámara derecha
    PIXEL_WIDTH = 640               # Ancho en píxeles
    PIXEL_HEIGHT = 480              # Alto en píxeles
    FRAME_RATE = 30                 # FPS objetivo
    
    # Flag que indica si los IDs de cámara actuales están invertidos
    # respecto a los IDs usados durante la calibración estéreo.
    # Si True, se deben intercambiar los frames/datos L<->R en el procesamiento.
    CAMERAS_SWAPPED = False
    
    @staticmethod
    def load_camera_ids_from_calibration():
        """
        Lee los IDs de cámaras desde calibration.json si existe.
        
        Este método debe llamarse ANTES de crear instancias de StereoConfig
        para que aplique los IDs configurados por el usuario.
        
        También detecta si los IDs actuales están invertidos respecto a
        los IDs originales de calibración y configura CAMERAS_SWAPPED.
        """
        from pathlib import Path
        
        calib_path = Path("camcalibration/calibration.json")
        
        try:
            if calib_path.exists():
                with open(calib_path, 'r') as f:
                    data = json.load(f)
                
                if 'camera_ids' in data:
                    StereoConfig.LEFT_CAMERA_SOURCE = data['camera_ids']['left']
                    StereoConfig.RIGHT_CAMERA_SOURCE = data['camera_ids']['right']
                    print(f"  [DEBUG] Cargado camera_ids: LEFT={StereoConfig.LEFT_CAMERA_SOURCE}, RIGHT={StereoConfig.RIGHT_CAMERA_SOURCE}")
                    
                    # Detectar si los IDs están invertidos respecto a la calibración
                    StereoConfig.CAMERAS_SWAPPED = False
                    
                    # Primero: Verificar flag explícito en JSON
                    if 'cameras_swapped' in data:
                        StereoConfig.CAMERAS_SWAPPED = data['cameras_swapped']
                        print(f"  [DEBUG] cameras_swapped (from JSON): {StereoConfig.CAMERAS_SWAPPED}")
                    # Segundo: Auto-detectar si los IDs son diferentes
                    elif 'calibration_camera_ids' in data:
                        calib_left = data['calibration_camera_ids']['left']
                        calib_right = data['calibration_camera_ids']['right']
                        print(f"  [DEBUG] calibration_camera_ids: LEFT={calib_left}, RIGHT={calib_right}")
                        
                        # Si los IDs actuales son los opuestos a los de calibración
                        if (StereoConfig.LEFT_CAMERA_SOURCE == calib_right and 
                            StereoConfig.RIGHT_CAMERA_SOURCE == calib_left):
                            StereoConfig.CAMERAS_SWAPPED = True
                    
                    if StereoConfig.CAMERAS_SWAPPED:
                        print(f"  [INFO] CAMERAS_SWAPPED=True - intercambiando datos L/R en runtime")
                    
                    return True
        except Exception as e:
            pass
        
        return False
    
    @staticmethod
    def apply_camera_transforms(frame):
        """
        Aplica transformaciones para CALIBRACIÓN y DETECCIÓN.
        
        Estas transformaciones afectan la geometría estéreo y DEBEN aplicarse
        consistentemente durante calibración Y runtime para que las matrices
        R, T, P funcionen correctamente.
        
        IMPORTANTE: NO aplicar espejado aquí porque afecta la geometría.
        El espejado solo se aplica para visualización con apply_display_transform().
        
        Args:
            frame: Frame original de OpenCV (numpy array)
            
        Returns:
            Frame transformado para procesamiento interno
        """
        import cv2
        
        if frame is None:
            return None
        
        result = frame.copy()
        
        # NO aplicar ninguna transformación para mantener geometría correcta
        # La calibración y detección trabajan con imágenes RAW
        # El espejado se aplica SOLO para visualización
        
        return result
    
    @staticmethod
    def apply_display_transform(frame):
        """
        Aplica transformación SOLO para VISUALIZACIÓN (Rotación 180°).
        
        Esta transformación hace DOS cosas:
        1. Rota la imagen 180° (Flip Vertical + Flip Horizontal)
           -> Pone al usuario "abajo" (posición natural de piano)
        2. Al incluir Flip Horizontal, mantiene el efecto espejo/selfie
           -> Mover derecha física = Mover derecha pantalla
        
        IMPORTANTE: Usar DESPUÉS de la detección de manos, solo para mostrar.
        
        Args:
            frame: Frame procesado (después de detección)
            
        Returns:
            Frame rotado 180° para visualización perfecta
        """
        import cv2
        
        if frame is None:
            return None
        
        # Rotación 180° = Flip Vertical + Flip Horizontal
        result = cv2.rotate(frame, cv2.ROTATE_180)
        
        return result

    @staticmethod
    def transform_point_for_display(point, width, height):
        """
        Transforma un punto (x, y) del espacio RAW al espacio DISPLAY.
        Debe coincidir con la transformación de apply_display_transform.
        """
        x, y = point
        # Rotación 180: (x, y) -> (w-x, h-y)
        new_x = width - x
        new_y = height - y
        return (new_x, new_y)

    # ==================== ORIENTACIÓN DE CÁMARAS ====================
    # NOTA: Estas configuraciones ya NO afectan la geometría.
    # La calibración y detección usan imágenes RAW.
    # Solo apply_display_transform() afecta la visualización.
    
    # ROTATE_CAMERAS_180: Ya no se usa (mantenido por compatibilidad)
    ROTATE_CAMERAS_180 = False       # Desactivado - no afecta nada
    
    # MIRROR_HORIZONTAL: Ya no se usa (mantenido por compatibilidad)
    MIRROR_HORIZONTAL = False        # Desactivado - apply_display_transform() lo hace
    
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
    CAMERA_SEPARATION = 9.62        # Distancia entre cámaras (cm) - Actualizado según calibration.json
    VKB_CENTER_DISTANCE = 71        # Distancia del teclado virtual (cm)
    
    # ==================== DETECCIÓN DE PROFUNDIDAD ====================
    DEPTH_THRESHOLD = 3.0           # Umbral de profundidad para presión (cm) - 3cm para testing
                                     # CONTACTO DIRECTO: Solo activa cuando dedo TOCA la mesa
                                     # depth <= 0.5cm = TECLA ACTIVA (prácticamente 0)
    DEPTH_CORRECTION_FACTOR = 1.0   # Factor de corrección de profundidad (calculado en Fase 3)
    KEYBOARD_OFFSET_CM = 0.0        # [NUEVO] Ajuste manual de altura de mesa (+ = subir mesa hacia cámara)
    
    TABLE_CORNERS = None            # [NUEVO] Esquinas de mesa para proyección AR [(x,y), (x,y), (x,y), (x,y)]
    CALIB_PIXEL_WIDTH = None        # Resolución usada durante la calibración (para escalar puntos)
    CALIB_PIXEL_HEIGHT = None       # Resolución usada durante la calibración (para escalar puntos)
    
    # Sistema de detección de movimiento (velocity-based triggering)
    VELOCITY_THRESHOLD = 1.5        # Velocidad mínima hacia abajo (cm/frame) para activar tecla
                                     # Valores típicos: 1.0-3.0 cm/frame
                                     # Mayor valor = requiere golpe más fuerte
    VELOCITY_ENABLED = True          # Activar detección por velocidad
    VELOCITY_HISTORY_SIZE = 3        # Número de frames para calcular velocidad
    
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
    # CORREGIDO: Expandido a 84% del ancho para cubrir todas las teclas
    KEYBOARD_X0_RATIO = 0.080       # Posición X inicial (8% del ancho) - expandido desde 14%
    KEYBOARD_Y0_RATIO = 0.520       # Posición Y inicial (52% del alto)
    KEYBOARD_X1_RATIO = 0.920       # Posición X final (92% del ancho) - expandido desde 86%
    KEYBOARD_Y1_RATIO = 0.820       # Posición Y final (82% del alto)
    
    # Relaciones de tamaño de teclas (basado en piano real)
    BLACK_KEY_WIDTH_RATIO = 0.40    # [TUNED] Reducido de 0.54 a 0.40 para evitar overlap visual/táctil
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
    
    # ==================== PROCESAMIENTO ====================
    QUEUE_LENGTH = 3                # Longitud de cola para estabilización
    FRAME_WAIT_TIME = 0.1           # Tiempo de espera entre frames (segundos)
    FRAME_WAIT_TIME_GAME = 0.0      # Tiempo de espera en modo juego (sin delay)
    FRAME_WAIT_TIME_SETUP = 0.01    # Tiempo de espera en setup
    CAMERA_INIT_WAIT = 0.5          # Tiempo de espera para inicializar cámaras
    STABILIZATION_WAIT = 0.5        # Tiempo de espera para estabilización
    
    # ==================== UI ====================
    INSTRUCTIONS_TIMEOUT = 300      # Frames antes de ocultar instrucciones (10s a 30fps)
    SHOW_CROSSHAIRS = False         # Mostrar líneas de referencia (desactivado por defecto)
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
        print(f"Camaras: IZQ={StereoConfig.LEFT_CAMERA_SOURCE}, DER={StereoConfig.RIGHT_CAMERA_SOURCE}")
        print(f"Resolucion: {StereoConfig.PIXEL_WIDTH}x{StereoConfig.PIXEL_HEIGHT} @ {StereoConfig.FRAME_RATE}fps")
        print(f"FoV: H={StereoConfig.CAMERA_H_FOV}°, V={StereoConfig.CAMERA_V_FOV}°")
        print(f"Angulos efectivos: W={StereoConfig.ANGLE_WIDTH:.2f}°, H={StereoConfig.ANGLE_HEIGHT:.2f}°")
        print(f"Separacion camaras: {StereoConfig.CAMERA_SEPARATION} cm")
        print(f"Distancia teclado: {StereoConfig.VKB_CENTER_DISTANCE} cm")
        print(f"Umbral profundidad: {StereoConfig.DEPTH_THRESHOLD} cm")
        print(f"Confianza deteccion: {StereoConfig.HAND_DETECTION_CONFIDENCE}")
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
            print("[ALERTA] Umbral muy bajo (minimo 0.5 cm)")
            return False
        if new_threshold > 10:
            print("[ALERTA] Umbral muy alto (maximo 10 cm)")
            return False
        StereoConfig.DEPTH_THRESHOLD = new_threshold
        print(f"[INFO] Umbral actualizado a: {new_threshold:.2f} cm")
        return True
    
    @staticmethod
    def update_camera_sources(left_id, right_id):
        """Actualiza las fuentes de cámara"""
        StereoConfig.LEFT_CAMERA_SOURCE = left_id
        StereoConfig.RIGHT_CAMERA_SOURCE = right_id
        print(f"[INFO] Camaras actualizadas: IZQ={left_id}, DER={right_id}")
    
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
            print(f"[ALERTA] No se encontro archivo de calibracion en: {calibration_path}")
            print("  Usando valores por defecto")
            return False
        
        try:
            with open(calibration_path, 'r') as f:
                calib_data = json.load(f)
            
            # Actualizar parámetros desde la calibración
            # 1. Separación de cámaras (baseline)
            if 'stereo' in calib_data and 'baseline_cm' in calib_data['stereo']:
                StereoConfig.CAMERA_SEPARATION = calib_data['stereo']['baseline_cm']
            elif 'camera_separation_cm' in calib_data:
                StereoConfig.CAMERA_SEPARATION = calib_data['camera_separation_cm']
            
            # 2. Distancia del teclado (de Fase 3 - depth_correction)
            if 'depth_correction' in calib_data and 'keyboard_distance_cm' in calib_data['depth_correction']:
                StereoConfig.VKB_CENTER_DISTANCE = calib_data['depth_correction']['keyboard_distance_cm']

            # 3. Definición de Mesa (AR Projection - NUEVO)
            if 'table_definition' in calib_data and 'corners' in calib_data['table_definition']:
                StereoConfig.TABLE_CORNERS = calib_data['table_definition']['corners']
                # Cargar resolución de calibración si existe
                if 'resolution' in calib_data['table_definition']:
                    StereoConfig.CALIB_PIXEL_WIDTH = calib_data['table_definition']['resolution'][0]
                    StereoConfig.CALIB_PIXEL_HEIGHT = calib_data['table_definition']['resolution'][1]
                else:
                     # Si no existe, asumir valores por defecto (ej. HD) o None
                     StereoConfig.CALIB_PIXEL_WIDTH = 1280
                     StereoConfig.CALIB_PIXEL_HEIGHT = 720
                
                print(f"[INFO] Esquinas de mesa cargadas: {StereoConfig.TABLE_CORNERS} (Ref: {StereoConfig.CALIB_PIXEL_WIDTH}x{StereoConfig.CALIB_PIXEL_HEIGHT})")
            
            # Prioridad: depth_correction.keyboard_distance_cm > depth_calibration > raíz
            if 'depth_correction' in calib_data and 'keyboard_distance_cm' in calib_data['depth_correction']:
                StereoConfig.VKB_CENTER_DISTANCE = calib_data['depth_correction']['keyboard_distance_cm']
            elif 'depth_calibration' in calib_data and 'keyboard_distance_cm' in calib_data['depth_calibration']:
                StereoConfig.VKB_CENTER_DISTANCE = calib_data['depth_calibration']['keyboard_distance_cm']
            elif 'keyboard_distance_cm' in calib_data:
                StereoConfig.VKB_CENTER_DISTANCE = calib_data['keyboard_distance_cm']
            
            # 3. Umbral de profundidad (de Fase 3 si existe)
            if 'depth_calibration' in calib_data and 'depth_threshold_cm' in calib_data['depth_calibration']:
                StereoConfig.DEPTH_THRESHOLD = calib_data['depth_calibration']['depth_threshold_cm']
            
            # 4. Factor de corrección de profundidad (puede estar en depth_correction o depth_calibration)
            if 'depth_correction' in calib_data and 'factor' in calib_data['depth_correction']:
                StereoConfig.DEPTH_CORRECTION_FACTOR = calib_data['depth_correction']['factor']
            elif 'depth_calibration' in calib_data and 'correction_factor' in calib_data['depth_calibration']:
                StereoConfig.DEPTH_CORRECTION_FACTOR = calib_data['depth_calibration']['correction_factor']
            
            # 5. IDs de cámaras
            if 'camera_ids' in calib_data:
                if 'left' in calib_data['camera_ids']:
                    StereoConfig.LEFT_CAMERA_SOURCE = calib_data['camera_ids']['left']
                if 'right' in calib_data['camera_ids']:
                    StereoConfig.RIGHT_CAMERA_SOURCE = calib_data['camera_ids']['right']
            
            print(f"[EXITO] Calibracion cargada desde: {calibration_path}")
            print(f"  Separacion camaras: {StereoConfig.CAMERA_SEPARATION:.2f} cm")
            print(f"  Distancia teclado: {StereoConfig.VKB_CENTER_DISTANCE:.2f} cm")
            print(f"  Umbral profundidad: {StereoConfig.DEPTH_THRESHOLD:.2f} cm")
            
            return True
        
        except Exception as e:
            print(f"[ERROR] Error al cargar calibracion: {e}")
            print("  Usando valores por defecto")
            return False


# Cargar calibración automáticamente al importar
StereoConfig.load_calibration()

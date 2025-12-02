#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración para el proceso de calibración
Define constantes y parámetros del proceso
"""

import os
from pathlib import Path


class CalibrationConfig:
    """Configuración centralizada para calibración"""
    
    # ==================== RUTAS ====================
    BASE_DIR = Path(__file__).parent.parent.parent
    CALIBRATION_DATA_DIR = BASE_DIR / "camcalibration"
    CALIBRATION_IMAGES_DIR = CALIBRATION_DATA_DIR / "images"
    CALIBRATION_FILE = CALIBRATION_DATA_DIR / "calibration.json"
    
    # ==================== TABLERO DE CALIBRACIÓN ====================
    # Valores por defecto (el usuario puede cambiarlos)
    DEFAULT_CHESSBOARD_ROWS = 6  # Filas internas (esquinas)
    DEFAULT_CHESSBOARD_COLS = 9  # Columnas internas (esquinas)
    DEFAULT_SQUARE_SIZE_MM = 25.0  # Tamaño del cuadrado en mm
    
    # ==================== CAPTURA DE IMÁGENES ====================
    MIN_IMAGES = 15  # Mínimo de imágenes por cámara
    RECOMMENDED_IMAGES = 25  # Recomendado para mejor precisión
    MAX_IMAGES = 30  # Máximo permitido
    
    # ==================== CATEGORÍAS DE FOTOS ====================
    PHOTO_CATEGORIES = {
        'distancia': {
            'nombre': 'A. VARIAR DISTANCIA',
            'cantidad': 5,
            'instrucciones': [
                '1. Tablero MUY CERCA (ocupa casi toda la imagen)',
                '2. Tablero CERCA (75% del frame)',
                '3. Tablero a DISTANCIA MEDIA (50% del frame)',
                '4. Tablero UN POCO LEJOS',
                '5. Tablero MUY LEJOS (pero visible claramente)'
            ],
            'objetivo': 'Información sobre focal y distorsión'
        },
        'posicion': {
            'nombre': 'B. VARIAR POSICIÓN EN EL FRAME',
            'cantidad': 8,
            'instrucciones': [
                '1. Tablero en SUPERIOR IZQUIERDA',
                '2. Tablero en SUPERIOR DERECHA',
                '3. Tablero en INFERIOR IZQUIERDA',
                '4. Tablero en INFERIOR DERECHA',
                '5. Tablero en el CENTRO EXACTO',
                '6. Tablero DESPLAZADO A LA DERECHA',
                '7. Tablero DESPLAZADO A LA IZQUIERDA',
                '8. Tablero LIGERAMENTE ABAJO DEL CENTRO'
            ],
            'objetivo': 'Estimación del centro óptico'
        },
        'inclinacion': {
            'nombre': 'C. VARIAR INCLINACIÓN DEL TABLERO',
            'cantidad': 7,
            'instrucciones': [
                '1. Inclinación HACIA DELANTE (cae hacia cámara)',
                '2. Inclinación HACIA ATRÁS (alejándose)',
                '3. Inclinación HACIA LA IZQUIERDA',
                '4. Inclinación HACIA LA DERECHA',
                '5. Tablero ROTADO COMO ROMBO (45°)',
                '6. Tablero ROTADO 20-30° IZQUIERDA',
                '7. Tablero ROTADO 20-30° DERECHA'
            ],
            'objetivo': 'Modelar distorsiones angulares'
        },
        'perspectiva': {
            'nombre': 'D. VARIAR ORIENTACIÓN Y PERSPECTIVA',
            'cantidad': 5,
            'instrucciones': [
                '1. Ángulo BAJO (cámara mira hacia arriba)',
                '2. Ángulo ALTO (cámara mira hacia abajo)',
                '3. Perspectiva FUERTE desde UN COSTADO',
                '4. Perspectiva FUERTE desde OTRO COSTADO',
                '5. ROTACIÓN LEVE + PERSPECTIVA combinada'
            ],
            'objetivo': 'Robustez en detección de esquinas'
        }
    }
    
    # ==================== CRITERIOS DE CALIDAD ====================
    # Criterios de terminación para cv2.cornerSubPix
    SUBPIX_CRITERIA = {
        'type': 'EPS_MAX_ITER',  # cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER
        'max_iter': 30,
        'epsilon': 0.001
    }
    
    # Criterios de calibración
    CALIBRATION_FLAGS = 0  # Flags adicionales para cv2.calibrateCamera
    
    # ==================== VALIDACIÓN ====================
    MIN_REPROJECTION_ERROR = 0.0  # Error mínimo aceptable (píxeles)
    MAX_REPROJECTION_ERROR = 1.0  # Error máximo aceptable (píxeles)
    
    # ==================== UI ====================
    INSTRUCTIONS_FONT_SCALE = 0.6
    TITLE_FONT_SCALE = 1.0
    COUNTER_FONT_SCALE = 1.5
    
    # Colores (BGR)
    COLOR_SUCCESS = (0, 255, 0)  # Verde
    COLOR_WARNING = (0, 165, 255)  # Naranja
    COLOR_ERROR = (0, 0, 255)  # Rojo
    COLOR_INFO = (255, 255, 100)  # Cyan claro
    COLOR_TITLE = (0, 200, 255)  # Amarillo-naranja
    
    @classmethod
    def ensure_directories(cls):
        """Crea los directorios necesarios si no existen"""
        cls.CALIBRATION_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.CALIBRATION_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Crear subdirectorios para cada cámara
        (cls.CALIBRATION_IMAGES_DIR / "left").mkdir(exist_ok=True)
        (cls.CALIBRATION_IMAGES_DIR / "right").mkdir(exist_ok=True)
    
    @classmethod
    def get_total_photos(cls):
        """Retorna el número total de fotos requeridas"""
        return sum(cat['cantidad'] for cat in cls.PHOTO_CATEGORIES.values())
    
    @classmethod
    def get_category_by_index(cls, photo_index):
        """
        Retorna la categoría correspondiente a un índice de foto
        
        Args:
            photo_index: Índice de la foto (0-24)
            
        Returns:
            tuple: (categoria_key, posicion_en_categoria, total_en_categoria)
        """
        current_idx = 0
        for cat_key, cat_data in cls.PHOTO_CATEGORIES.items():
            cat_count = cat_data['cantidad']
            if photo_index < current_idx + cat_count:
                position_in_cat = photo_index - current_idx
                return cat_key, position_in_cat, cat_count
            current_idx += cat_count
        
        return None, None, None
    
    @classmethod
    def get_instruction_for_photo(cls, photo_index):
        """
        Retorna la instrucción específica para una foto
        
        Args:
            photo_index: Índice de la foto (0-24)
            
        Returns:
            tuple: (titulo_categoria, instruccion_especifica, objetivo)
        """
        cat_key, pos, total = cls.get_category_by_index(photo_index)
        
        if cat_key is None:
            return "Foto adicional", "Captura adicional", ""
        
        cat_data = cls.PHOTO_CATEGORIES[cat_key]
        instruction = cat_data['instrucciones'][pos]
        
        return cat_data['nombre'], instruction, cat_data['objetivo']

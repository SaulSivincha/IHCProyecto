#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estimador de Profundidad usando Calibración Estéreo
Usa la calibración Fase 1 y Fase 2 para triangular puntos 3D
"""

import cv2
import numpy as np
import json
from pathlib import Path


class DepthEstimator:
    """
    Estima profundidad 3D usando calibración estéreo completa
    Rectifica imágenes y triangula puntos para obtener coordenadas (X, Y, Z)
    """
    
    def __init__(self, calibration_file):
        """
        Carga calibración y prepara mapas de rectificación
        
        Args:
            calibration_file: Path o str con ruta a calibration.json
        """
        self.calibration_file = Path(calibration_file)
        
        # Parámetros intrínsecos
        self.K_left = None
        self.D_left = None
        self.K_right = None
        self.D_right = None
        
        # Parámetros extrínsecos
        self.R = None
        self.T = None
        self.baseline_cm = None
        
        # Parámetros de rectificación
        self.R1 = None
        self.R2 = None
        self.P1 = None
        self.P2 = None
        self.Q = None
        
        # Mapas de rectificación (calculados una sola vez)
        self.mapx_left = None
        self.mapy_left = None
        self.mapx_right = None
        self.mapy_right = None
        
        # Resolución de imágenes
        self.image_size = None
        
        # Cargar calibración
        self._load_calibration()
        
        # Generar mapas de rectificación
        self._generate_rectification_maps()
    
    def _load_calibration(self):
        """Carga todos los parámetros desde calibration.json"""
        if not self.calibration_file.exists():
            raise FileNotFoundError(
                f"❌ Archivo de calibración no encontrado: {self.calibration_file}\n"
                f"   Ejecuta calibración completa primero."
            )
        
        with open(self.calibration_file, 'r') as f:
            data = json.load(f)
        
        # Verificar que existan todas las secciones necesarias
        if 'left_camera' not in data or 'right_camera' not in data:
            raise ValueError("❌ Calibración incompleta: falta Fase 1 (cámaras individuales)")
        
        if 'stereo' not in data or data['stereo'] is None:
            raise ValueError("❌ Calibración incompleta: falta Fase 2 (calibración estéreo)")
        
        if 'rectification' not in data['stereo']:
            raise ValueError(
                "❌ Calibración incompleta: falta rectificación.\n"
                "   Re-calibra Fase 2 para generar parámetros de rectificación."
            )
        
        # Cargar parámetros intrínsecos (Fase 1)
        left_cam = data['left_camera']
        right_cam = data['right_camera']
        
        self.K_left = np.array(left_cam['camera_matrix'], dtype=np.float32)
        self.D_left = np.array(left_cam['distortion_coeffs'], dtype=np.float32)
        self.K_right = np.array(right_cam['camera_matrix'], dtype=np.float32)
        self.D_right = np.array(right_cam['distortion_coeffs'], dtype=np.float32)
        
        # Obtener resolución desde image_size (ancho, alto)
        if 'image_size' in left_cam:
            self.image_size = tuple(left_cam['image_size'])
        else:
            # Fallback: inferir desde matriz K
            self.image_size = (int(self.K_left[0, 2] * 2), int(self.K_left[1, 2] * 2))
        
        # Cargar parámetros extrínsecos (Fase 2)
        stereo = data['stereo']
        self.R = np.array(stereo['rotation_matrix'], dtype=np.float32)
        self.T = np.array(stereo['translation_vector'], dtype=np.float32)
        self.baseline_cm = stereo.get('baseline_cm', np.linalg.norm(self.T) * 100)
        
        # Cargar parámetros de rectificación
        rect = stereo['rectification']
        self.R1 = np.array(rect['R1'], dtype=np.float32)
        self.R2 = np.array(rect['R2'], dtype=np.float32)
        self.P1 = np.array(rect['P1'], dtype=np.float32)
        self.P2 = np.array(rect['P2'], dtype=np.float32)
        self.Q = np.array(rect['Q'], dtype=np.float32)
        
        print(f"✓ Calibración cargada desde: {self.calibration_file}")
        print(f"  Baseline: {self.baseline_cm:.2f} cm")
        print(f"  Resolución: {self.image_size[0]}x{self.image_size[1]}")
    
    def _generate_rectification_maps(self):
        """
        Genera mapas de rectificación usando cv2.initUndistortRectifyMap
        Estos mapas se usan con cv2.remap() para rectificar imágenes
        """
        # Mapas para cámara izquierda
        self.mapx_left, self.mapy_left = cv2.initUndistortRectifyMap(
            self.K_left,
            self.D_left,
            self.R1,
            self.P1,
            self.image_size,
            cv2.CV_32FC1
        )
        
        # Mapas para cámara derecha
        self.mapx_right, self.mapy_right = cv2.initUndistortRectifyMap(
            self.K_right,
            self.D_right,
            self.R2,
            self.P2,
            self.image_size,
            cv2.CV_32FC1
        )
        
        print(f"✓ Mapas de rectificación generados")
    
    def rectify_images(self, img_left, img_right):
        """
        Rectifica un par de imágenes estéreo
        
        Args:
            img_left: Imagen de cámara izquierda (BGR)
            img_right: Imagen de cámara derecha (BGR)
        
        Returns:
            tuple: (img_left_rect, img_right_rect) imágenes rectificadas
        """
        img_left_rect = cv2.remap(
            img_left,
            self.mapx_left,
            self.mapy_left,
            cv2.INTER_LINEAR
        )
        
        img_right_rect = cv2.remap(
            img_right,
            self.mapx_right,
            self.mapy_right,
            cv2.INTER_LINEAR
        )
        
        return img_left_rect, img_right_rect
    
    def triangulate_point(self, point_left, point_right):
        """
        Triangula un punto 3D desde coordenadas 2D en imágenes RECTIFICADAS
        
        Args:
            point_left: (x, y) en imagen izquierda rectificada
            point_right: (x, y) en imagen derecha rectificada
        
        Returns:
            tuple: (X, Y, Z) coordenadas 3D en cm, o None si falla
        """
        x_left, y_left = point_left
        x_right, y_right = point_right
        
        # Calcular disparidad
        disparity = x_left - x_right
        
        # Validar disparidad (debe ser positiva y razonable)
        if disparity <= 0:
            return None  # Punto está detrás de las cámaras o es inválido
        
        # Reproyectar usando matriz Q
        # Q transforma (x, y, disparity) → (X, Y, Z, W)
        point_3d_homogeneous = cv2.perspectiveTransform(
            np.array([[[x_left, y_left, disparity]]], dtype=np.float32),
            self.Q
        )[0, 0]
        
        # Convertir de homogéneas a cartesianas
        X = point_3d_homogeneous[0] / point_3d_homogeneous[3]
        Y = point_3d_homogeneous[1] / point_3d_homogeneous[3]
        Z = point_3d_homogeneous[2] / point_3d_homogeneous[3]
        
        # Convertir a centímetros
        X_cm = X * 100
        Y_cm = Y * 100
        Z_cm = Z * 100
        
        return (X_cm, Y_cm, Z_cm)
    
    def get_depth(self, point_left, point_right):
        """
        Obtiene solo la profundidad (distancia Z) de un punto
        
        Args:
            point_left: (x, y) en imagen izquierda rectificada
            point_right: (x, y) en imagen derecha rectificada
        
        Returns:
            float: Profundidad en cm, o None si falla
        """
        result = self.triangulate_point(point_left, point_right)
        if result is None:
            return None
        return result[2]  # Z
    
    def batch_triangulate(self, points_left, points_right):
        """
        Triangula múltiples puntos de manera eficiente
        
        Args:
            points_left: Lista de (x, y) en imagen izquierda
            points_right: Lista de (x, y) en imagen derecha
        
        Returns:
            list: Lista de (X, Y, Z) o None para puntos inválidos
        """
        if len(points_left) != len(points_right):
            raise ValueError("Las listas deben tener la misma longitud")
        
        results = []
        for pt_left, pt_right in zip(points_left, points_right):
            result = self.triangulate_point(pt_left, pt_right)
            results.append(result)
        
        return results
    
    def rectify_point(self, point, is_left=True):
        """
        Rectifica un punto 2D de imagen original a imagen rectificada
        
        Args:
            point: (x, y) en imagen original
            is_left: True si es cámara izquierda, False si derecha
        
        Returns:
            tuple: (x_rect, y_rect) en imagen rectificada
        """
        x, y = point
        
        if is_left:
            mapx, mapy = self.mapx_left, self.mapy_left
        else:
            mapx, mapy = self.mapx_right, self.mapy_right
        
        # Obtener coordenadas rectificadas usando mapas
        x_rect = mapx[int(y), int(x)]
        y_rect = mapy[int(y), int(x)]
        
        return (x_rect, y_rect)


# Función auxiliar para cargar rápidamente
def load_depth_estimator(calibration_file="camcalibration/calibration.json"):
    """
    Carga y retorna un DepthEstimator configurado
    
    Args:
        calibration_file: Ruta a calibration.json
    
    Returns:
        DepthEstimator: Instancia lista para usar
    
    Raises:
        FileNotFoundError: Si no existe el archivo
        ValueError: Si la calibración está incompleta
    """
    return DepthEstimator(calibration_file)

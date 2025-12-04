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
from scipy import linalg
from collections import deque


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
        
        # NUEVO: Transformaciones al mundo (para DLT correcto)
        self.R_world_left = None   # Rotación cámara izq respecto al mundo
        self.T_world_left = None   # Traslación cámara izq respecto al mundo
        self.R_world_right = None  # Rotación cámara der respecto al mundo
        self.T_world_right = None  # Traslación cámara der respecto al mundo
        
        # Factor de corrección de profundidad (calibrado empíricamente)
        # Basado en mediciones reales vs estimadas
        self.DEPTH_CORRECTION_FACTOR = 0.74
        
        # Sistema de suavizado temporal (para reducir jitter)
        self.smoothing_enabled = True
        self.smoothing_window = 5  # Últimos N frames
        self.position_history = {}  # {landmark_id: deque([(x,y,z), ...], maxlen=N)}
        
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
        
        # NUEVO: Cargar transformaciones al mundo si están disponibles
        # (Backward compatible: si no existen, usa convención por defecto)
        if 'world_rotation' in left_cam and 'world_rotation' in right_cam:
            self.R_world_left = np.array(left_cam['world_rotation'], dtype=np.float32)
            self.T_world_left = np.array(left_cam['world_translation'], dtype=np.float32).reshape(3, 1)
            self.R_world_right = np.array(right_cam['world_rotation'], dtype=np.float32)
            self.T_world_right = np.array(right_cam['world_translation'], dtype=np.float32).reshape(3, 1)
            print("  ✓ Transformaciones al mundo cargadas desde calibración")
        else:
            # Fallback: usar convención estándar (cam izq = origen)
            self.R_world_left = np.eye(3, dtype=np.float32)
            self.T_world_left = np.zeros((3, 1), dtype=np.float32)
            self.R_world_right = self.R  # Rotación estéreo
            self.T_world_right = self.T  # Traslación estéreo
            print("  ⚠ Transformaciones al mundo no encontradas, usando convención por defecto")
        
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
    
    def _make_homogeneous_transform(self, R, t):
        """
        Convierte matriz de rotación R y vector de traslación t en matriz homogénea 4x4
        
        Args:
            R: Matriz de rotación 3x3
            t: Vector de traslación 3x1
        
        Returns:
            P: Matriz homogénea 4x4
        """
        P = np.zeros((4, 4), dtype=np.float32)
        P[:3, :3] = R
        P[:3, 3] = t.reshape(3)
        P[3, 3] = 1.0
        return P
    
    def _get_projection_matrix(self, camera_matrix, R, T):
        """
        Construye matriz de proyección P = K @ [R | T]
        
        Args:
            camera_matrix: Matriz intrínseca K (3x3)
            R: Matriz de rotación (3x3)
            T: Vector de traslación (3x1)
        
        Returns:
            P: Matriz de proyección 3x4
        """
        RT = self._make_homogeneous_transform(R, T)[:3, :]
        P = camera_matrix @ RT
        return P
    
    def _get_projection_matrices_for_DLT(self):
        """
        Construye matrices de proyección CORRECTAS para DLT siguiendo el método
        del repositorio StereoVision funcional.
        
        P = K @ [R | T] donde R y T son transformaciones respecto al mundo
        
        ACTUALIZADO: Usa transformaciones al mundo si están disponibles en calibración,
        o usa convención por defecto (cam izquierda = origen).
        
        Convención:
        - Cámara izquierda = origen del mundo: R0 = I, T0 = [0,0,0]
        - Cámara derecha = transformación estéreo: R1 = R_stereo, T1 = T_stereo
        
        Returns:
            tuple: (P0, P1) matrices de proyección 3x4 para cámara izquierda y derecha
        """
        # Usar transformaciones al mundo si están disponibles
        # (cargadas desde calibration.json si existe el campo world_rotation)
        RT0 = np.hstack([self.R_world_left, self.T_world_left])  # [R | T] matriz 3x4
        P0 = self.K_left @ RT0      # K @ [R | T]
        
        RT1 = np.hstack([self.R_world_right, self.T_world_right])  # [R | T] matriz 3x4
        P1 = self.K_right @ RT1     # K @ [R | T]
        
        return P0, P1
    
    def triangulate_point_DLT(self, point_left, point_right):
        """
        Triangula un punto 3D usando Direct Linear Transform (DLT)
        Método más robusto que usa matrices de proyección directamente
        
        CORREGIDO: Ahora usa matrices K @ [R|T] con R y T respecto al mundo,
        igual que el repositorio StereoVision funcional.
        
        Args:
            point_left: (x, y) en imagen izquierda rectificada
            point_right: (x, y) en imagen derecha rectificada
        
        Returns:
            tuple: (X, Y, Z) coordenadas 3D en cm, o None si falla
        """
        # Obtener matrices de proyección CORRECTAS
        # P0 = K_left @ [I | 0] (cámara izquierda como origen)
        # P1 = K_right @ [R | T] (cámara derecha en el mundo)
        P0, P1 = self._get_projection_matrices_for_DLT()
        
        # Construir sistema de ecuaciones A
        x1, y1 = point_left
        x2, y2 = point_right
        
        A = np.array([
            y1 * P0[2, :] - P0[1, :],
            P0[0, :] - x1 * P0[2, :],
            y2 * P1[2, :] - P1[1, :],
            P1[0, :] - x2 * P1[2, :]
        ], dtype=np.float32)
        
        # Resolver usando SVD (Singular Value Decomposition)
        # La solución es el vector singular correspondiente al menor valor singular
        try:
            B = A.T @ A
            U, s, Vh = linalg.svd(B, full_matrices=False)
            
            # Punto 3D en coordenadas homogéneas
            X_homogeneous = Vh[3, :]
            
            # Convertir a coordenadas cartesianas (dividir por W)
            X = X_homogeneous[0] / X_homogeneous[3]
            Y = X_homogeneous[1] / X_homogeneous[3]
            Z = X_homogeneous[2] / X_homogeneous[3]
            
            # Validar que Z sea positivo (delante de la cámara)
            if Z <= 0:
                return None
            
            # Convertir de metros a centímetros
            X_cm = X * 100
            Y_cm = Y * 100
            Z_cm = Z * 100
            
            # Aplicar factor de corrección de profundidad
            Z_cm_corrected = Z_cm * self.DEPTH_CORRECTION_FACTOR
            
            return (X_cm, Y_cm, Z_cm_corrected)
            
        except Exception as e:
            print(f"Error en triangulación DLT: {e}")
            return None
    
    def triangulate_point(self, point_left, point_right, method='DLT'):
        """
        Triangula un punto 3D desde coordenadas 2D en imágenes RECTIFICADAS
        
        Args:
            point_left: (x, y) en imagen izquierda rectificada
            point_right: (x, y) en imagen derecha rectificada
            method: 'DLT' (recomendado) o 'Q' (matriz de reproyección)
        
        Returns:
            tuple: (X, Y, Z) coordenadas 3D en cm, o None si falla
        """
        if method == 'DLT':
            return self.triangulate_point_DLT(point_left, point_right)
        
        # Método original con matriz Q (menos robusto)
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
        
        # Verificar si el resultado tiene 4 componentes (homogéneas)
        if len(point_3d_homogeneous) == 4:
            # Convertir de homogéneas a cartesianas
            X = point_3d_homogeneous[0] / point_3d_homogeneous[3]
            Y = point_3d_homogeneous[1] / point_3d_homogeneous[3]
            Z = point_3d_homogeneous[2] / point_3d_homogeneous[3]
        elif len(point_3d_homogeneous) == 3:
            # Ya está en coordenadas cartesianas
            X = point_3d_homogeneous[0]
            Y = point_3d_homogeneous[1]
            Z = point_3d_homogeneous[2]
        else:
            return None
        
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
    
    def enable_smoothing(self, enabled=True, window_size=5):
        """
        Activa/desactiva el suavizado temporal de coordenadas 3D
        
        Args:
            enabled: True para activar, False para desactivar
            window_size: Número de frames a promediar (3-10 recomendado)
        """
        self.smoothing_enabled = enabled
        self.smoothing_window = window_size
        if not enabled:
            self.position_history.clear()
    
    def smooth_position(self, position_3d, landmark_id=0):
        """
        Aplica suavizado temporal a una posición 3D usando media móvil
        
        Args:
            position_3d: tuple (X, Y, Z) en cm
            landmark_id: ID del landmark (para mantener historiales separados)
        
        Returns:
            tuple: (X_smooth, Y_smooth, Z_smooth) coordenadas suavizadas
        """
        if not self.smoothing_enabled or position_3d is None:
            return position_3d
        
        # Inicializar buffer para este landmark si no existe
        if landmark_id not in self.position_history:
            self.position_history[landmark_id] = deque(maxlen=self.smoothing_window)
        
        # Agregar nueva posición al buffer
        self.position_history[landmark_id].append(position_3d)
        
        # Calcular promedio de las últimas N posiciones
        history = np.array(list(self.position_history[landmark_id]))
        smoothed = np.mean(history, axis=0)
        
        return tuple(smoothed)
    
    def reset_smoothing(self, landmark_id=None):
        """
        Limpia el historial de suavizado
        
        Args:
            landmark_id: Si se especifica, limpia solo ese landmark. 
                        Si es None, limpia todos.
        """
        if landmark_id is not None:
            if landmark_id in self.position_history:
                del self.position_history[landmark_id]
        else:
            self.position_history.clear()


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

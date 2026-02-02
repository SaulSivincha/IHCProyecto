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
        
        # Factor de corrección de profundidad (calculado en Fase 3)
        # 1.0 = sin corrección (valores RAW de triangulación)
        self.DEPTH_CORRECTION_FACTOR = 1.0
        
        # Distancia del plano del teclado (calculada en Fase 3)
        # Esta es la referencia para determinar si un dedo "toca" el teclado
        self.keyboard_distance_cm = None
        
        # Sistema de suavizado temporal (para reducir jitter)
        self.smoothing_enabled = True
        self.smoothing_window = 5  # Últimos N frames
        self.position_history = {}  # {landmark_id: deque([(x,y,z), ...], maxlen=N)}
        self.finger_position_history = {}  # Para KeyboardProcessor: {finger_id: deque}
        
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
        
        # Resolución de imágenes (de calibración)
        self.image_size = None
        self.calib_width = None   # Ancho usado durante calibración
        self.calib_height = None  # Alto usado durante calibración
        
        # Resolución actual de runtime (puede ser diferente de calibración)
        self.runtime_width = None
        self.runtime_height = None
        
        # Cargar calibración
        self._load_calibration()
        
        # Generar mapas de rectificación
        self._generate_rectification_maps()
    
    def _load_calibration(self):
        """Carga todos los parámetros desde calibration.json"""
        if not self.calibration_file.exists():
            raise FileNotFoundError(
                f"[ERROR] Archivo de calibracion no encontrado: {self.calibration_file}\n"
                f"   Ejecuta calibracion completa primero."
            )
        
        with open(self.calibration_file, 'r') as f:
            data = json.load(f)
        
        # Verificar que existan todas las secciones necesarias
        if 'left_camera' not in data or 'right_camera' not in data:
            raise ValueError("[ERROR] Calibracion incompleta: falta Fase 1 (camaras individuales)")
        
        if 'stereo' not in data or data['stereo'] is None:
            raise ValueError("[ERROR] Calibracion incompleta: falta Fase 2 (calibracion estereo)")
        
        if 'rectification' not in data['stereo']:
            raise ValueError(
                "[ERROR] Calibracion incompleta: falta rectificacion.\n"
                "   Re-calibra Fase 2 para generar parametros de rectificacion."
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
        
        # Guardar resolución de calibración
        self.calib_width = self.image_size[0]
        self.calib_height = self.image_size[1]
        
        # Por defecto, asumir que runtime usa la misma resolución
        # (se puede actualizar con set_runtime_resolution)
        self.runtime_width = self.calib_width
        self.runtime_height = self.calib_height
        
        # Cargar parámetros extrínsecos (Fase 2)
        stereo = data['stereo']
        self.R = np.array(stereo['rotation_matrix'], dtype=np.float32).reshape(3, 3)
        self.T = np.array(stereo['translation_vector'], dtype=np.float32).reshape(3, 1)
        self.baseline_cm = stereo.get('baseline_cm', np.linalg.norm(self.T) * 100)
        
        # NUEVO: Cargar transformaciones al mundo si están disponibles
        # (Backward compatible: si no existen, usa convención por defecto)
        if 'world_rotation' in left_cam and 'world_rotation' in right_cam:
            self.R_world_left = np.array(left_cam['world_rotation'], dtype=np.float32).reshape(3, 3)
            self.T_world_left = np.array(left_cam['world_translation'], dtype=np.float32).reshape(3, 1)
            self.R_world_right = np.array(right_cam['world_rotation'], dtype=np.float32).reshape(3, 3)
            self.T_world_right = np.array(right_cam['world_translation'], dtype=np.float32).reshape(3, 1)
            print("  [INFO] Transformaciones al mundo cargadas desde calibracion")
        else:
            # Fallback: usar convención estándar (cam izq = origen)
            self.R_world_left = np.eye(3, dtype=np.float32)
            self.T_world_left = np.zeros((3, 1), dtype=np.float32)
            self.R_world_right = self.R  # Rotación estéreo
            self.T_world_right = self.T  # Traslación estéreo
            print("  [ALERTA] Transformaciones al mundo no encontradas, usando convencion por defecto")
        
        # Cargar parámetros de rectificación
        rect = stereo['rectification']
        self.R1 = np.array(rect['R1'], dtype=np.float32)
        self.R2 = np.array(rect['R2'], dtype=np.float32)
        self.P1 = np.array(rect['P1'], dtype=np.float32)
        self.P2 = np.array(rect['P2'], dtype=np.float32)
        self.Q = np.array(rect['Q'], dtype=np.float32)
        
        # NUEVO: Parámetros de regresión lineal para corrección de profundidad
        # Real = depth_slope * Medido + depth_intercept
        self.depth_slope = 1.0
        self.depth_intercept = 0.0
        
        # NUEVO: Cargar datos de Fase 3 si existen
        if 'depth_correction' in data:
            depth_corr = data['depth_correction']
            
            # Soporte para nuevo método de regresión lineal
            if depth_corr.get('method') == 'linear_regression':
                self.depth_slope = depth_corr.get('slope', 1.0)
                self.depth_intercept = depth_corr.get('intercept', 0.0)
                print(f"  [INFO] Regresión lineal cargada:")
                print(f"         Real = {self.depth_slope:.4f} * Medido + {self.depth_intercept:.4f}")
                # Mantener DEPTH_CORRECTION_FACTOR para retrocompatibilidad
                self.DEPTH_CORRECTION_FACTOR = self.depth_slope
            else:
                # Soporte retroactivo para método anterior (factor simple)
                self.DEPTH_CORRECTION_FACTOR = depth_corr.get('correction_factor', depth_corr.get('factor', 1.0))
                self.depth_slope = self.DEPTH_CORRECTION_FACTOR
                self.depth_intercept = 0.0
                if self.DEPTH_CORRECTION_FACTOR != 1.0:
                    print(f"  Factor de correccion (legacy): {self.DEPTH_CORRECTION_FACTOR:.4f}")
            
            # Distancia del teclado (IMPORTANTE - calculada en Fase 3)
            if 'keyboard_distance_cm' in depth_corr:
                self.keyboard_distance_cm = depth_corr['keyboard_distance_cm']
                print(f"  [INFO] Distancia del teclado cargada: {self.keyboard_distance_cm:.2f} cm")
            else:
                print("  [ALERTA] Distancia del teclado no encontrada en calibracion")
                print("    Ejecuta Fase 3 para calibrar la distancia del teclado")
        else:
            # Sin Fase 3 - usar valores por defecto
            self.DEPTH_CORRECTION_FACTOR = 1.0
            self.depth_slope = 1.0
            self.depth_intercept = 0.0
            print("  [ALERTA] Fase 3 no completada - la deteccion de notas puede no funcionar")
            print("    Ejecuta Fase 3 (Calibracion de Distancia) para habilitar la deteccion")
        
        # NUEVO: Cargar plano 3D de la mesa (Fase 4 mejorada)
        self.table_plane = None
        
        # NUEVO: Interpolación bilineal (Fase 4B)
        self.bilinear_corners = None  # 4 esquinas [(x,y), ...]
        self.bilinear_depths = None   # 4 profundidades [z1, z2, z3, z4]
        self.bilinear_x_min = 0
        self.bilinear_x_max = 1280
        self.bilinear_y_min = 0
        self.bilinear_y_max = 720
        
        if 'table_definition' in data:
            table_def = data['table_definition']
            
            # Cargar esquinas 2D para interpolación
            if 'corners' in table_def and table_def['corners']:
                corners = table_def['corners']
                self.bilinear_corners = np.array(corners, dtype=np.float32)
                # Calcular bounding box
                try:
                    self.bilinear_x_min = min(c[0] for c in corners)
                    self.bilinear_x_max = max(c[0] for c in corners)
                    self.bilinear_y_min = min(c[1] for c in corners)
                    self.bilinear_y_max = max(c[1] for c in corners)
                    print(f"  [INFO] Esquinas del teclado cargadas para interpolación")
                except Exception as e:
                    print(f"  [ALERTA] Error procesando corners: {e}")
                    self.bilinear_corners = None
            else:
                self.bilinear_corners = None
                print(f"  [INFO] No hay esquinas definidas ('corners' vacío o ausente)")
            
            # Cargar profundidades de esquinas (Fase 4B)
            if 'corner_depths' in table_def:
                self.bilinear_depths = np.array(table_def['corner_depths'], dtype=np.float32)
                print(f"  [INFO] Profundidades de esquinas cargadas: {self.bilinear_depths}")
                print(f"         [BILINEAR] Interpolación activa para corrección de sesgo")
            else:
                print("  [INFO] corner_depths no encontrado - ejecuta Fase 4B para calibrar")
            
            # Cargar plano 3D si existe (método alternativo)
            if 'plane_3d' in table_def:
                plane_data = table_def['plane_3d']
                coeffs = plane_data.get('coefficients')
                if coeffs and len(coeffs) == 4:
                    self.table_plane = np.array(coeffs, dtype=np.float64)
                    print(f"  [INFO] Plano 3D de mesa cargado: {self.table_plane}")
                else:
                    print("  [ALERTA] Plano 3D encontrado pero coeficientes inválidos")
        else:
            print("  [INFO] table_definition no encontrado - usando distancia fija")
        
        print(f"[EXITO] Calibracion cargada desde: {self.calibration_file}")
        print(f"  Baseline: {self.baseline_cm:.2f} cm")
        print(f"  Resolucion: {self.image_size[0]}x{self.image_size[1]}")
    
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
        
        # print(f"[INFO] Mapas de rectificacion generados")
    
    def set_runtime_resolution(self, width, height):
        """
        Establece la resolución usada en runtime.
        
        IMPORTANTE: Si es diferente de la resolución de calibración,
        los parámetros intrínsecos (focal, centro óptico) deben escalarse.
        
        Args:
            width: Ancho en píxeles del frame en runtime
            height: Alto en píxeles del frame en runtime
        """
        self.runtime_width = width
        self.runtime_height = height
        
        if width != self.calib_width or height != self.calib_height:
            print(f"  [INFO] Resolucion runtime ({width}x{height}) != calibracion ({self.calib_width}x{self.calib_height})")
            print(f"  [INFO] Los parametros se escalaran automaticamente")
    
    def get_resolution_scale(self):
        """
        Calcula el factor de escala entre resolución de calibración y runtime.
        
        Returns:
            tuple: (scale_x, scale_y) factores de escala
        """
        if self.calib_width and self.runtime_width:
            scale_x = self.runtime_width / self.calib_width
            scale_y = self.runtime_height / self.calib_height
            return (scale_x, scale_y)
        return (1.0, 1.0)
    
    def pixel_to_point_3d(self, x_pixel, y_pixel, depth_cm):
        """
        Convierte un punto 2D (u, v) y una profundidad Z conocida 
        a coordenadas 3D (X, Y, Z) usando la matriz intrínseca.
        """
        if depth_cm is None or depth_cm <= 0:
            return None
            
        # Obtener intrínsecos escalados a la resolución actual
        fx, fy, cx, cy = self.get_scaled_intrinsics()
        
        # Fórmulas de proyección inversa (Pinhole Camera Model)
        # x = (u - cx) * Z / fx
        # y = (v - cy) * Z / fy
        X = (x_pixel - cx) * depth_cm / fx
        Y = (y_pixel - cy) * depth_cm / fy
        Z = depth_cm
        
        return (X, Y, Z)

    def get_scaled_intrinsics(self):
        """
        Retorna fx, fy, cx, cy ajustados a la resolucion actual de runtime.
        """
        # Matriz original (de calibracion) de camara IZQUIERDA (usada para deteccion)
        K = self.K_left
        
        # Resolucion original
        orig_w = 1280.0
        orig_h = 720.0
        if hasattr(self, 'calib_width') and self.calib_width:
             orig_w = float(self.calib_width)
        if hasattr(self, 'calib_height') and self.calib_height:
             orig_h = float(self.calib_height)
             
        # Factores de escala
        scale_x = self.runtime_width / orig_w
        scale_y = self.runtime_height / orig_h
        
        fx = K[0,0] * scale_x
        fy = K[1,1] * scale_y
        cx = K[0,2] * scale_x
        cy = K[1,2] * scale_y
        
        return fx, fy, cx, cy

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
        
        NOTA: Este método tiene un bug conocido que produce Z negativo.
        Se mantiene por compatibilidad pero se recomienda usar 'simple'.
        
        Args:
            point_left: (x, y) en imagen izquierda 
            point_right: (x, y) en imagen derecha 
        
        Returns:
            tuple: (X, Y, Z) coordenadas 3D en cm, o None si falla
        """
        P0, P1 = self._get_projection_matrices_for_DLT()
        
        x1, y1 = point_left
        x2, y2 = point_right
        
        A = np.array([
            y1 * P0[2, :] - P0[1, :],
            P0[0, :] - x1 * P0[2, :],
            y2 * P1[2, :] - P1[1, :],
            P1[0, :] - x2 * P1[2, :]
        ], dtype=np.float32)
        
        try:
            B = A.T @ A
            U, s, Vh = linalg.svd(B, full_matrices=False)
            
            X_homogeneous = Vh[3, :]
            
            X = X_homogeneous[0] / X_homogeneous[3]
            Y = X_homogeneous[1] / X_homogeneous[3]
            Z = X_homogeneous[2] / X_homogeneous[3]
            
            if Z <= 0:
                return None
            
            X_cm = X * 100
            Y_cm = Y * 100
            Z_cm = Z * 100
            
            # Aplicar corrección de regresión lineal: Real = slope * Z + intercept
            Z_cm_corrected = self.apply_depth_correction(Z_cm)
            
            return (X_cm, Y_cm, Z_cm_corrected)
            
        except Exception as e:
            return None
    
    def rectify_point(self, point, camera='left'):
        """
        Rectifica un punto 2D individual
        
        Args:
            point: (x, y) coordenadas en imagen original
            camera: 'left' o 'right'
            
        Returns:
            tuple: (x, y) coordenadas en imagen rectificada
        """
        if camera == 'left':
            K, D, R, P = self.K_left, self.D_left, self.R1, self.P1
        else:
            K, D, R, P = self.K_right, self.D_right, self.R2, self.P2
            
        # Convertir a formato numpy array (N, 1, 2)
        pt = np.array([[[point[0], point[1]]]], dtype=np.float32)
        
        # Undistort y rectificar
        rect_pt = cv2.undistortPoints(pt, K, D, R=R, P=P)
        
        return rect_pt[0, 0]

    def triangulate_point_simple(self, pt_left, pt_right):
        """
        Triangulación robusta usando fórmula Z = f*B/d
        Optimizado para coordenadas rectificadas.
        """
        # Extraer coordenadas X
        x_left = pt_left[0]
        x_right = pt_right[0]
        
        # Calcular disparidad
        disparity = abs(x_left - x_right)
        
        # Evitar división por cero o disparidad negativa (infinito/detrás)
        if disparity <= 0.1:
            return None

        # --- SECCIÓN CRÍTICA DE FOCAL ---
        # Debemos usar la focal de la matriz P (Rectificada), no K (Original)
        if hasattr(self, 'P1') and self.P1 is not None:
            scale_x, scale_y = self.get_resolution_scale()
            # P1[0,0] es la focal rectificada
            focal = self.P1[0, 0] * scale_x
            
            # Ajustar centros ópticos rectificados
            cx = self.P1[0, 2] * scale_x
            cy = self.P1[1, 2] * scale_y
            
            # DEBUG TEMPORAL
            # print(f"[DEBUG 4B] Focal Rectificada: {focal:.1f}")
        else:
            # Fallback (Causa del error de 37cm)
            print("[ALERTA] Usando focal NO rectificada (K)")
            fx, fy, cx, cy = self.get_scaled_intrinsics()
            focal = (fx + fy) / 2
        # --------------------------------
        
        # Baseline en cm
        B = self.baseline_cm
        
        # Calcular profundidad: Z = (f * B) / d
        Z_cm = (focal * B) / disparity
        
        # Calcular X, Y usando similar triángulos
        # Usamos las coordenadas rectificadas y el centro óptico rectificado
        X_cm = (x_left - cx) * Z_cm / focal
        Y_cm = (pt_left[1] - cy) * Z_cm / focal  # Usamos Y izquierda
        
        # Aplicar corrección de regresión lineal (si existe)
        # Real = slope * Z + intercept
        Z_cm_corrected = self.apply_depth_correction(Z_cm)
        
        # Validar rango razonable (10cm a 200cm)
        if Z_cm_corrected and (Z_cm_corrected < 10 or Z_cm_corrected > 200):
             return None
             
        return (X_cm, Y_cm, Z_cm_corrected)

    def triangulate_point(self, point_left, point_right, method='simple'):
        """
        Triangula un punto 3D desde coordenadas 2D en imágenes RECTIFICADAS
        
        Args:
            point_left: (x, y) en imagen izquierda rectificada
            point_right: (x, y) en imagen derecha rectificada
            method: 'simple' (recomendado), 'DLT' o 'Q' (matriz de reproyección)
        
        Returns:
            tuple: (X, Y, Z) coordenadas 3D en cm, o None si falla
        """
        # NUEVO: Método simple como default (más robusto)
        if method == 'simple':
            return self.triangulate_point_simple(point_left, point_right)
        
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
    
    def apply_depth_correction(self, raw_depth):
        """
        Aplica la corrección de profundidad usando regresión lineal.
        
        Fórmula: Real = slope * Raw + intercept
        
        Args:
            raw_depth: Profundidad cruda medida por el sistema (cm)
        
        Returns:
            float: Profundidad corregida en cm, o None si raw_depth es None
        """
        if raw_depth is None:
            return None
        
        # Aplicar fórmula de regresión lineal: Real = m * Medido + b
        corrected_depth = (raw_depth * self.depth_slope) + self.depth_intercept
        
        return corrected_depth
    
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
        usando cv2.undistortPoints (método correcto para puntos individuales)
        
        Args:
            point: (x, y) en imagen original
            is_left: True si es cámara izquierda, False si derecha
        
        Returns:
            tuple: (x_rect, y_rect) en imagen rectificada
        """
        x, y = point
        
        if is_left:
            K, D, R, P = self.K_left, self.D_left, self.R1, self.P1
        else:
            K, D, R, P = self.K_right, self.D_right, self.R2, self.P2
        
        # cv2.undistortPoints requires shape (N, 1, 2)
        pt = np.array([[[x, y]]], dtype=np.float32)
        
        # Esto desdistorsiona y rectifica el punto correctamente
        rect_pt = cv2.undistortPoints(pt, K, D, R=R, P=P)
        
        return (rect_pt[0, 0, 0], rect_pt[0, 0, 1])
    
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

    # ==================== PLANO 3D DEL TECLADO ====================
    
    def set_table_plane(self, plane_coeffs):
        """
        Establece los coeficientes del plano 3D de la mesa/teclado.
        
        El plano se define como: ax + by + cz + d = 0
        Donde (a, b, c) es el vector normal del plano.
        
        Args:
            plane_coeffs: tuple o lista (a, b, c, d)
        """
        self.table_plane = np.array(plane_coeffs, dtype=np.float64)
        print(f"  [INFO] Plano de mesa configurado: {self.table_plane}")
    
    def triangulate_corners(self, corners_left, corners_right):
        """
        Triangula las 4 esquinas del teclado para obtener sus coordenadas 3D.
        
        Args:
            corners_left: Lista de 4 puntos (x, y) en cámara izquierda
            corners_right: Lista de 4 puntos (x, y) en cámara derecha
            
        Returns:
            list: Lista de 4 tuplas (X, Y, Z) en cm, o None si falla
        """
        corners_3d = []
        for i, (pt_l, pt_r) in enumerate(zip(corners_left, corners_right)):
            point_3d = self.triangulate_point_simple(pt_l, pt_r)
            if point_3d is None:
                print(f"  [ERROR] No se pudo triangular esquina {i}: L={pt_l}, R={pt_r}")
                return None
            corners_3d.append(point_3d)
            print(f"  [DEBUG] Esquina {i}: 2D_L={pt_l}, 2D_R={pt_r} -> 3D={point_3d}")
        return corners_3d
    
    def compute_table_plane(self, corners_3d):
        """
        Calcula el plano 3D que mejor ajusta las 4 esquinas del teclado.
        
        Usa mínimos cuadrados para encontrar el plano ax + by + cz + d = 0
        que minimiza la distancia a los 4 puntos.
        
        Args:
            corners_3d: Lista de 4 tuplas (X, Y, Z) en cm
            
        Returns:
            tuple: (a, b, c, d) coeficientes del plano, o None si falla
        """
        if len(corners_3d) < 3:
            print("[ERROR] Se necesitan al menos 3 puntos para definir un plano")
            return None
        
        # Convertir a numpy array
        points = np.array(corners_3d, dtype=np.float64)
        
        # Método 1: Usar los primeros 3 puntos para calcular el plano
        # (más simple pero menos robusto a ruido)
        p1, p2, p3 = points[0], points[1], points[2]
        
        # Vectores en el plano
        v1 = p2 - p1
        v2 = p3 - p1
        
        # Vector normal (producto cruz)
        normal = np.cross(v1, v2)
        normal_magnitude = np.linalg.norm(normal)
        
        if normal_magnitude < 1e-10:
            print("[ERROR] Puntos colineales, no se puede definir plano")
            return None
        
        # Normalizar el vector normal
        normal = normal / normal_magnitude
        a, b, c = normal
        
        # Calcular d usando el primer punto
        d = -np.dot(normal, p1)
        
        # Verificar ajuste con el 4to punto
        if len(corners_3d) >= 4:
            p4 = points[3]
            distance_to_plane = abs(a * p4[0] + b * p4[1] + c * p4[2] + d)
            print(f"  [INFO] Distancia del 4to punto al plano: {distance_to_plane:.2f} cm")
            if distance_to_plane > 5:  # Más de 5cm = algo está mal
                print(f"  [ALERTA] El 4to punto está lejos del plano, posible error de calibración")
        
        # Guardar el plano
        self.table_plane = np.array([a, b, c, d], dtype=np.float64)
        
        print(f"  [INFO] Plano calculado: {a:.4f}x + {b:.4f}y + {c:.4f}z + {d:.2f} = 0")
        
        return (a, b, c, d)
    
    def get_expected_z_at_pixel(self, x_pixel, y_pixel):
        """
        Calcula la profundidad Z esperada del plano de la mesa en una posición (x, y) de píxel.
        
        Método: 
        1. Convertir (x_pixel, y_pixel) a un rayo 3D desde la cámara
        2. Intersectar el rayo con el plano de la mesa
        3. Devolver la Z del punto de intersección
        
        Args:
            x_pixel: Coordenada X en píxeles (en resolución runtime)
            y_pixel: Coordenada Y en píxeles (en resolución runtime)
            
        Returns:
            float: Z esperada en cm, o None si no hay plano definido
        """
        if not hasattr(self, 'table_plane') or self.table_plane is None:
            return None
        
        a, b, c, d = self.table_plane
        
        # Obtener parámetros intrínsecos escalados
        fx, fy, cx, cy = self.get_scaled_intrinsics()
        
        # Rayo desde la cámara: dirección = ((x - cx)/fx, (y - cy)/fy, 1)
        # El rayo parte del origen (cámara) en dirección (dx, dy, 1)
        dx = (x_pixel - cx) / fx
        dy = (y_pixel - cy) / fy
        dz = 1.0
        
        # Intersección rayo-plano:
        # Punto en el rayo: P = t * (dx, dy, dz)
        # Plano: a*x + b*y + c*z + d = 0
        # Sustituyendo: a*t*dx + b*t*dy + c*t*dz + d = 0
        # t = -d / (a*dx + b*dy + c*dz)
        
        denominator = a * dx + b * dy + c * dz
        
        if abs(denominator) < 1e-10:
            # Rayo paralelo al plano
            return None
        
        t = -d / denominator
        
        if t <= 0:
            # Intersección detrás de la cámara
            return None
        
        # Punto de intersección
        # X = t * dx, Y = t * dy, Z = t * dz = t
        Z_cm = t * dz  # = t, ya que dz = 1
        
        return Z_cm
    
    def get_depth_relative_to_plane(self, finger_x, finger_y, finger_z):
        """
        Calcula la profundidad relativa de un dedo respecto al plano de la mesa.
        
        Args:
            finger_x: Coordenada X del dedo en píxeles
            finger_y: Coordenada Y del dedo en píxeles  
            finger_z: Profundidad Z del dedo en cm (de triangulación)
            
        Returns:
            float: Profundidad relativa en cm
                   - Positivo = dedo en el aire (más cerca de cámara que la mesa)
                   - 0 = dedo tocando la mesa
                   - Negativo = dedo "debajo" de la mesa (tocando fuerte)
                   
                   O None si no hay plano definido
        """
        z_expected = self.get_expected_z_at_pixel(finger_x, finger_y)
        
        if z_expected is None:
            return None
        
        # depth_rel = z_mesa - z_dedo
        # Si dedo está en aire (z_dedo < z_mesa): depth_rel > 0
        # Si dedo toca (z_dedo ≈ z_mesa): depth_rel ≈ 0
        depth_rel = z_expected - finger_z
        
        return depth_rel
    
    def pixel_to_point_3d(self, x_pixel, y_pixel, depth_cm):
        """
        Convierte un punto 2D (u, v) y una profundidad Z conocida 
        a coordenadas 3D (X, Y, Z) usando la matriz intrínseca.
        
        Args:
            x_pixel: Coordenada X en píxeles
            y_pixel: Coordenada Y en píxeles
            depth_cm: Profundidad Z conocida en cm
            
        Returns:
            tuple: (X, Y, Z) coordenadas 3D en cm, o None si falla
        """
        if depth_cm is None or depth_cm <= 0:
            return None
            
        # Obtener intrínsecos escalados a la resolución actual
        fx, fy, cx, cy = self.get_scaled_intrinsics()
        
        # Fórmulas de proyección inversa (Pinhole Camera Model)
        # x = (u - cx) * Z / fx
        # y = (v - cy) * Z / fy
        X = (x_pixel - cx) * depth_cm / fx
        Y = (y_pixel - cy) * depth_cm / fy
        Z = depth_cm
        
        return (X, Y, Z)
    
    # ==================== INTERPOLACIÓN BILINEAR (Fase 4B) ====================
    
    def setup_bilinear_interpolation(self, corners_2d, corner_depths):
        """
        Configura interpolación bilineal desde esquinas con profundidades conocidas.
        
        Args:
            corners_2d: Lista de 4 esquinas [(x,y), ...] en orden:
                        [top-left, top-right, bottom-right, bottom-left]
            corner_depths: Lista de 4 profundidades [z_tl, z_tr, z_br, z_bl] en cm
        """
        self.bilinear_corners = np.array(corners_2d, dtype=np.float32)
        self.bilinear_depths = np.array(corner_depths, dtype=np.float32)
        
        # Calcular bounding box
        self.bilinear_x_min = min(c[0] for c in corners_2d)
        self.bilinear_x_max = max(c[0] for c in corners_2d)
        self.bilinear_y_min = min(c[1] for c in corners_2d)
        self.bilinear_y_max = max(c[1] for c in corners_2d)
        
        print(f"[INFO] Interpolación bilineal configurada")
        print(f"       Esquinas: {corners_2d}")
        print(f"       Profundidades: {corner_depths}")
    
    def get_expected_z_bilinear(self, x_pixel, y_pixel):
        """
        Calcula Z esperada usando corrección de perspectiva (Homografía).
        Transforma el trapecio visual a un cuadrado unitario para interpolar con precisión.
        
        Esto corrige el "efecto trapecio" donde la cámara inclinada hace que
        el centro físico del teclado no coincida con el centro visual.
        """
        if self.bilinear_depths is None or self.bilinear_corners is None:
            return self.keyboard_distance_cm if self.keyboard_distance_cm else 40.0

        # 1. Definir coordenadas origen (Esquinas detectadas en Fase 4) y destino (Cuadrado Unitario)
        # Orden asumido: TL, TR, BR, BL
        src_pts = self.bilinear_corners
        dst_pts = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)

        try:
            # 2. Calcular Matriz de Perspectiva (Homografía)
            # Esto 'endereza' el teclado matemáticamente
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)

            # 3. Transformar el punto del dedo (x, y)
            point_array = np.array([[[x_pixel, y_pixel]]], dtype=np.float32)
            transformed_point = cv2.perspectiveTransform(point_array, M)[0][0]
            
            u, v = transformed_point[0], transformed_point[1]
            
            # Clamp de seguridad (evitar valores extremos fuera de la mesa)
            u = np.clip(u, -0.1, 1.1)
            v = np.clip(v, -0.1, 1.1)

        except Exception as e:
            # Fallback lineal si falla la matriz (método antiguo)
            x_range = self.bilinear_x_max - self.bilinear_x_min
            y_range = self.bilinear_y_max - self.bilinear_y_min
            u = (x_pixel - self.bilinear_x_min) / x_range if x_range > 0 else 0.5
            v = (y_pixel - self.bilinear_y_min) / y_range if y_range > 0 else 0.5

        # 4. Interpolación Bilineal usando coordenadas corregidas (u, v)
        z_tl, z_tr, z_br, z_bl = self.bilinear_depths
        
        # Fórmula exacta: Z(u,v) = (1-u)(1-v)Ztl + u(1-v)Ztr + (1-u)v*Zbl + uv*Zbr
        z_top = z_tl * (1 - u) + z_tr * u
        z_bot = z_bl * (1 - u) + z_br * u
        
        z_expected = z_top * (1 - v) + z_bot * v
        
        return float(z_expected)
    
    def get_depth_relative_bilinear(self, finger_x, finger_y, finger_z):
        """
        Calcula depth_rel usando interpolación bilineal.
        
        Args:
            finger_x, finger_y: Posición del dedo en píxeles
            finger_z: Profundidad medida del dedo en cm
            
        Returns:
            float: z_expected - finger_z
                   Positivo = aire, 0 = tocando, negativo = presionando
        """
        z_expected = self.get_expected_z_bilinear(finger_x, finger_y)
        return z_expected - finger_z
    
    def has_bilinear_interpolation(self):
        """Retorna True si la interpolación bilineal está configurada."""
        return self.bilinear_depths is not None and len(self.bilinear_depths) == 4


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

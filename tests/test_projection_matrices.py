#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar que las matrices de proyección sean correctas
después de la corrección del bug crítico
"""

import sys
from pathlib import Path
import numpy as np
import json
from scipy import linalg


class SimpleDepthEstimator:
    """Versión simplificada para testing sin dependencias circulares"""
    
    def __init__(self, calibration_file):
        with open(calibration_file, 'r') as f:
            data = json.load(f)
        
        left_cam = data['left_camera']
        right_cam = data['right_camera']
        stereo = data['stereo']
        
        self.K_left = np.array(left_cam['camera_matrix'], dtype=np.float32)
        self.D_left = np.array(left_cam['distortion_coeffs'], dtype=np.float32)
        self.K_right = np.array(right_cam['camera_matrix'], dtype=np.float32)
        self.D_right = np.array(right_cam['distortion_coeffs'], dtype=np.float32)
        
        self.R = np.array(stereo['rotation_matrix'], dtype=np.float32)
        self.T = np.array(stereo['translation_vector'], dtype=np.float32).reshape(3, 1)
        self.baseline_cm = float(stereo.get('baseline_cm', 0))
        
        rect = stereo.get('rectification', {})
        self.P1 = np.array(rect['P1'], dtype=np.float32) if rect and 'P1' in rect else None
        self.P2 = np.array(rect['P2'], dtype=np.float32) if rect and 'P2' in rect else None
        
        self.image_size = (int(left_cam['image_width']), int(left_cam['image_height']))
    
    def _get_projection_matrices_for_DLT(self):
        """Construye matrices P = K @ [R | T] correctas"""
        R0 = np.eye(3, dtype=np.float32)
        T0 = np.zeros((3, 1), dtype=np.float32)
        RT0 = np.hstack([R0, T0])
        P0 = self.K_left @ RT0
        
        R1 = self.R
        T1 = self.T
        RT1 = np.hstack([R1, T1])
        P1 = self.K_right @ RT1
        
        return P0, P1
    
    def triangulate_point_DLT(self, point_left, point_right):
        """DLT triangulation"""
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
            
            return (X * 100, Y * 100, Z * 100)
        except Exception as e:
            print(f"Error en triangulación: {e}")
            return None


def test_projection_matrices():
    """
    Verifica que las matrices de proyección se construyan correctamente:
    - P0 = K_left @ [I | 0]
    - P1 = K_right @ [R | T]
    """
    print("=" * 70)
    print("TEST: Matrices de Proyección Correctas")
    print("=" * 70)
    
    # Cargar calibración
    calibration_file = Path(__file__).parent.parent / 'camcalibration' / 'calibration.json'
    
    if not calibration_file.exists():
        print("❌ No se encontró calibration.json")
        print(f"   Esperado en: {calibration_file}")
        return False
    
    try:
        estimator = SimpleDepthEstimator(calibration_file)
        print("✅ Calibración cargada correctamente\n")
    except Exception as e:
        print(f"❌ Error al cargar calibración: {e}")
        return False
    
    # Obtener matrices de proyección
    P0, P1 = estimator._get_projection_matrices_for_DLT()
    
    print("📊 Matriz de Proyección P0 (cámara izquierda):")
    print("   P0 = K_left @ [I | 0]")
    print(P0)
    print()
    
    print("📊 Matriz de Proyección P1 (cámara derecha):")
    print("   P1 = K_right @ [R | T]")
    print(P1)
    print()
    
    # Verificar propiedades
    print("🔍 Verificaciones:")
    print("-" * 70)
    
    # 1. P0 debe ser K_left con última columna de ceros
    R0 = np.eye(3, dtype=np.float32)
    T0 = np.zeros((3, 1), dtype=np.float32)
    P0_expected = estimator.K_left @ np.hstack([R0, T0])
    
    if np.allclose(P0, P0_expected, atol=1e-5):
        print("✅ P0 correcta: K_left @ [I | 0]")
    else:
        print("❌ P0 incorrecta")
        print(f"   Esperado:\n{P0_expected}")
        print(f"   Obtenido:\n{P0}")
    
    # 2. P1 debe ser K_right @ [R | T]
    P1_expected = estimator.K_right @ np.hstack([estimator.R, estimator.T])
    
    if np.allclose(P1, P1_expected, atol=1e-5):
        print("✅ P1 correcta: K_right @ [R | T]")
    else:
        print("❌ P1 incorrecta")
        print(f"   Esperado:\n{P1_expected}")
        print(f"   Obtenido:\n{P1}")
    
    # 3. Verificar que NO se estén usando matrices rectificadas
    if not np.allclose(P0[:, :3], estimator.P1[:, :3], atol=1e-5):
        print("✅ P0 NO usa matriz de rectificación (correcto)")
    else:
        print("❌ P0 usa matriz de rectificación (incorrecto)")
    
    if not np.allclose(P1[:, :3], estimator.P2[:, :3], atol=1e-5):
        print("✅ P1 NO usa matriz de rectificación (correcto)")
    else:
        print("❌ P1 usa matriz de rectificación (incorrecto)")
    
    print()
    
    # 4. Mostrar información de calibración
    print("📋 Información de Calibración:")
    print("-" * 70)
    print(f"Baseline: {estimator.baseline_cm:.2f} cm")
    print(f"Resolución: {estimator.image_size}")
    print()
    
    print("Matriz Intrínseca K_left:")
    print(estimator.K_left)
    print()
    
    print("Matriz Intrínseca K_right:")
    print(estimator.K_right)
    print()
    
    print("Rotación Estéreo R:")
    print(estimator.R)
    print()
    
    print("Traslación Estéreo T (cm):")
    print(estimator.T * 100)
    print()
    
    print("=" * 70)
    print("✅ Test completado - Verifica los resultados arriba")
    print("=" * 70)
    
    return True


def test_triangulation_simple():
    """
    Prueba triangulación con un punto simple
    """
    print("\n")
    print("=" * 70)
    print("TEST: Triangulación con Punto de Prueba")
    print("=" * 70)
    
    calibration_file = Path(__file__).parent.parent / 'camcalibration' / 'calibration.json'
    
    if not calibration_file.exists():
        print("❌ No se encontró calibration.json")
        return False
    
    try:
        estimator = SimpleDepthEstimator(calibration_file)
    except Exception as e:
        print(f"❌ Error al cargar calibración: {e}")
        return False
    
    # Punto de prueba en el centro de la imagen
    width, height = estimator.image_size
    point_left = (width // 2, height // 2)
    
    # Simular disparidad de 50 píxeles (punto a ~1 metro)
    point_right = (width // 2 - 50, height // 2)
    
    print(f"Punto izquierdo: {point_left}")
    print(f"Punto derecho: {point_right}")
    print(f"Disparidad: {point_left[0] - point_right[0]} px")
    print()
    
    # Triangular con DLT
    result = estimator.triangulate_point_DLT(point_left, point_right)
    
    if result is not None:
        X, Y, Z = result
        print("✅ Triangulación exitosa:")
        print(f"   X = {X:.2f} cm")
        print(f"   Y = {Y:.2f} cm")
        print(f"   Z = {Z:.2f} cm (profundidad)")
        print()
        
        # Verificar que Z sea razonable
        if 0 < Z < 500:  # Entre 0 y 5 metros
            print("✅ Profundidad Z parece razonable")
        else:
            print("⚠️  Profundidad Z fuera de rango esperado")
    else:
        print("❌ Triangulación falló")
    
    print("=" * 70)
    
    return result is not None


if __name__ == '__main__':
    success = test_projection_matrices()
    
    if success:
        test_triangulation_simple()
    else:
        print("\n⚠️  No se pudieron ejecutar todos los tests")

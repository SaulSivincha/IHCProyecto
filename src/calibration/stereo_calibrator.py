#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calibrador Estéreo - Fase 2
Calibración del par estéreo usando imágenes simultáneas
Determina la posición y orientación relativa entre las cámaras
"""

import cv2
import numpy as np
from pathlib import Path
from .calibration_config import CalibrationConfig


class StereoCalibrator:
    """
    Calibra un par estéreo de cámaras
    Calcula los parámetros extrínsecos (R, T, E, F)
    """
    
    def __init__(self, calibrator_left, calibrator_right):
        """
        Args:
            calibrator_left: CameraCalibrator de la cámara izquierda (ya calibrada)
            calibrator_right: CameraCalibrator de la cámara derecha (ya calibrada)
        """
        self.calibrator_left = calibrator_left
        self.calibrator_right = calibrator_right
        
        # Parámetros intrínsecos (ya conocidos de Fase 1)
        self.K_left = calibrator_left.camera_matrix
        self.D_left = calibrator_left.distortion_coeffs
        self.K_right = calibrator_right.camera_matrix
        self.D_right = calibrator_right.distortion_coeffs
        
        # Parámetros extrínsecos (a calcular)
        self.R = None  # Matriz de rotación (3x3)
        self.T = None  # Vector de traslación (3x1)
        self.E = None  # Matriz esencial (3x3)
        self.F = None  # Matriz fundamental (3x3)
        
        # Parámetros de rectificación
        self.R1 = None  # Rotación para rectificar cámara izquierda
        self.R2 = None  # Rotación para rectificar cámara derecha
        self.P1 = None  # Matriz de proyección izquierda
        self.P2 = None  # Matriz de proyección derecha
        self.Q = None   # Matriz de reproyección 4x4
        
        # Almacenamiento de pares de imágenes
        self.obj_points = []  # Puntos 3D en el mundo real
        self.img_points_left = []  # Puntos 2D en cámara izquierda
        self.img_points_right = []  # Puntos 2D en cámara derecha
        self.pairs_captured = []  # Lista de pares (frame_left, frame_right)
        
        self.image_size = None
        self.stereo_error = None
        
    def detect_chessboard_pair(self, frame_left, frame_right, refine_corners=False):
        """
        Detecta el tablero en ambas cámaras simultáneamente
        
        Args:
            frame_left: Frame de cámara izquierda
            frame_right: Frame de cámara derecha
            refine_corners: Si True, aplica cornerSubPix (lento pero preciso)
            
        Returns:
            tuple: (detected_both, corners_left, corners_right, frame_left_display, frame_right_display)
        """
        # Detectar en izquierda
        detected_left, corners_left, frame_left_display = \
            self.calibrator_left.detect_chessboard(frame_left, refine_corners=refine_corners)
        
        # Detectar en derecha
        detected_right, corners_right, frame_right_display = \
            self.calibrator_right.detect_chessboard(frame_right, refine_corners=refine_corners)
        
        # Ambas deben detectar
        detected_both = detected_left and detected_right
        
        if not detected_both:
            corners_left = None
            corners_right = None
        
        return detected_both, corners_left, corners_right, frame_left_display, frame_right_display
    
    def capture_stereo_pair(self, frame_left, frame_right, corners_left, corners_right):
        """
        Guarda un par de imágenes para calibración estéreo
        
        Args:
            frame_left: Frame izquierdo
            frame_right: Frame derecho
            corners_left: Esquinas detectadas en izquierda
            corners_right: Esquinas detectadas en derecha
            
        Returns:
            bool: True si se guardó exitosamente
        """
        if self.image_size is None:
            self.image_size = (frame_left.shape[1], frame_left.shape[0])
        
        # Usar el mismo objeto 3D que en calibración individual
        self.obj_points.append(self.calibrator_left.objp)
        self.img_points_left.append(corners_left)
        self.img_points_right.append(corners_right)
        self.pairs_captured.append((frame_left.copy(), frame_right.copy()))
        
        # Guardar imágenes en disco (opcional, para referencia)
        save_dir = CalibrationConfig.CALIBRATION_IMAGES_DIR / "stereo"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        pair_num = len(self.pairs_captured)
        cv2.imwrite(str(save_dir / f"stereo_left_{pair_num:03d}.jpg"), frame_left)
        cv2.imwrite(str(save_dir / f"stereo_right_{pair_num:03d}.jpg"), frame_right)
        
        return True
    
    def get_pair_count(self):
        """Retorna el número de pares capturados"""
        return len(self.pairs_captured)
    
    def calibrate_stereo_pair(self):
        """
        Calibra el par estéreo usando cv2.stereoCalibrate()
        Calcula R, T, E, F
        
        Returns:
            dict: Parámetros de calibración estéreo o None si falla
        """
        min_pairs = 8
        if len(self.obj_points) < min_pairs:
            print(f"X Insuficientes pares de imágenes: {len(self.obj_points)} < {min_pairs}")
            return None
        
        print(f"\n{'='*70}")
        print(f"CALIBRANDO PAR ESTÉREO")
        print(f"{'='*70}")
        print(f"Pares de imágenes: {len(self.obj_points)}")
        print(f"Resolviendo parámetros extrínsecos...")
        
        # Flags para calibración estéreo
        # Usamos CALIB_FIX_INTRINSIC porque ya tenemos los parámetros intrínsecos
        flags = cv2.CALIB_FIX_INTRINSIC
        
        # Criterios de optimización (epsilon más permisivo para mejor convergencia)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
        
        try:
            # Ejecutar calibración estéreo
            ret, K1, D1, K2, D2, R, T, E, F = cv2.stereoCalibrate(
                self.obj_points,
                self.img_points_left,
                self.img_points_right,
                self.K_left,
                self.D_left,
                self.K_right,
                self.D_right,
                self.image_size,
                criteria=criteria,
                flags=flags
            )
            
            print(f"[DEBUG] stereoCalibrate retornó: ret={ret}, type={type(ret)}")
            
            # ret es el error RMS, un float > 0 para calibración exitosa
            if ret is None or ret <= 0:
                print("X Error durante la calibración estéreo (ret inválido)")
                return None
            
            # Guardar resultados
            self.R = R
            self.T = T
            self.E = E
            self.F = F
            self.stereo_error = ret
            
            print(f"[DEBUG] Valores asignados: R shape={R.shape}, T shape={T.shape}")
            print(f"[DEBUG] self.R es None: {self.R is None}")
            
            # Calcular baseline (distancia entre cámaras)
            baseline = np.linalg.norm(T)
            
            # Mostrar resultados
            print(f"[OK] Calibración estéreo completada")
            print(f"Error RMS: {ret:.6f}")
            print(f"\nPARÁMETROS EXTRÍNSECOS:")
            print(f"Baseline (distancia entre cámaras): {baseline*100:.2f} cm")
            print(f"\nMatriz de Rotación R:")
            print(R)
            print(f"\nVector de Traslación T (metros):")
            print(T.ravel())
            print(f"  T en cm: [{T[0][0]*100:.2f}, {T[1][0]*100:.2f}, {T[2][0]*100:.2f}]")
            print(f"{'='*70}\n")
            
            return {
                'rotation_matrix': R,
                'translation_vector': T,
                'essential_matrix': E,
                'fundamental_matrix': F,
                'rms_error': ret,
                'baseline_cm': baseline * 100,
                'num_pairs': len(self.obj_points)
            }
            
        except Exception as e:
            print(f"X Excepción durante calibración estéreo: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def compute_rectification(self):
        """
        Calcula parámetros de rectificación estéreo
        Permite crear mapas para enderezar las imágenes
        
        Returns:
            dict: Parámetros de rectificación o None si falla
        """
        if self.R is None or self.T is None:
            print("X Debes ejecutar calibrate_stereo_pair() primero")
            return None
        
        print(f"\n{'='*70}")
        print(f"CALCULANDO RECTIFICACIÓN ESTÉREO")
        print(f"{'='*70}")
        
        # Calcular rectificación
        R1, R2, P1, P2, Q, validPixROI1, validPixROI2 = cv2.stereoRectify(
            self.K_left,
            self.D_left,
            self.K_right,
            self.D_right,
            self.image_size,
            self.R,
            self.T,
            flags=cv2.CALIB_ZERO_DISPARITY,
            alpha=0  # 0 = sin píxeles negros, 1 = retiene todos los píxeles
        )
        
        self.R1 = R1
        self.R2 = R2
        self.P1 = P1
        self.P2 = P2
        self.Q = Q
        
        print(f"[OK] Rectificación calculada")
        print(f"\nMatriz de reproyección Q:")
        print(Q)
        print(f"{'='*70}\n")
        
        return {
            'R1': R1,
            'R2': R2,
            'P1': P1,
            'P2': P2,
            'Q': Q,
            'validPixROI1': validPixROI1,
            'validPixROI2': validPixROI2
        }
    
    def get_calibration_data(self):
        """
        Retorna los datos de calibración estéreo en formato serializable
        
        ACTUALIZADO: Incluye transformaciones al mundo para DLT correcto
        - Cámara izquierda = origen del mundo (R=I, T=0)
        - Cámara derecha = transformación estéreo (R=R_stereo, T=T_stereo)
        
        Returns:
            dict: Datos para guardar en JSON
        """
        if self.R is None:
            return None
        
        data = {
            'rotation_matrix': self.R.tolist(),
            'translation_vector': self.T.tolist(),
            'essential_matrix': self.E.tolist(),
            'fundamental_matrix': self.F.tolist(),
            'rms_error': float(self.stereo_error),
            'baseline_cm': float(np.linalg.norm(self.T) * 100),
            'num_pairs': len(self.obj_points),
            # NUEVO: Transformaciones al mundo para DLT
            'world_transforms': {
                'left_camera': {
                    'rotation': np.eye(3).tolist(),  # Cámara izq = origen (R = I)
                    'translation': np.zeros((3, 1)).tolist()  # T = [0, 0, 0]
                },
                'right_camera': {
                    'rotation': self.R.tolist(),  # Rotación estéreo
                    'translation': self.T.tolist()  # Traslación estéreo
                }
            }
        }
        
        # Agregar parámetros de rectificación si existen
        if self.R1 is not None:
            data['rectification'] = {
                'R1': self.R1.tolist(),
                'R2': self.R2.tolist(),
                'P1': self.P1.tolist(),
                'P2': self.P2.tolist(),
                'Q': self.Q.tolist()
            }
        
        return data


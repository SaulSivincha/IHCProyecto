#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calibrador Individual de Cámara
Fase 1: Calibración monocular de cada cámara por separado
"""

import cv2
import numpy as np
import time
from pathlib import Path
from .calibration_config import CalibrationConfig


class CameraCalibrator:
    """Calibra una cámara individual usando imágenes del tablero de ajedrez"""
    
    def __init__(self, camera_id, camera_name, board_size, square_size_mm):
        """
        Args:
            camera_id: ID de la cámara (0, 1, 2, etc.)
            camera_name: Nombre descriptivo ('left' o 'right')
            board_size: Tupla (cols, rows) de esquinas internas del tablero
            square_size_mm: Tamaño del cuadrado en milímetros
        """
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.board_size = board_size
        self.square_size_m = square_size_mm / 1000.0  # Convertir a metros
        
        # Criterios para cornerSubPix
        self.criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            CalibrationConfig.SUBPIX_CRITERIA['max_iter'],
            CalibrationConfig.SUBPIX_CRITERIA['epsilon']
        )
        
        # Almacenar puntos 3D y 2D
        self.obj_points = []  # Puntos 3D en el mundo real
        self.img_points = []  # Puntos 2D en la imagen
        self.images_captured = []  # Lista de frames capturados
        self.image_size = None
        
        # Preparar puntos del tablero (grid 3D)
        self.objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
        self.objp *= self.square_size_m
        
        # Resultados de calibración
        self.camera_matrix = None
        self.distortion_coeffs = None
        self.reprojection_error = None
        self.is_calibrated = False
        
    def detect_chessboard(self, frame):
        """
        Detecta el tablero de ajedrez en un frame
        
        Args:
            frame: Imagen BGR
            
        Returns:
            tuple: (success, corners, frame_with_overlay)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Método 1: Detección con flags estándar
        flags = (cv2.CALIB_CB_ADAPTIVE_THRESH + 
                cv2.CALIB_CB_NORMALIZE_IMAGE + 
                cv2.CALIB_CB_FAST_CHECK)
        
        ret, corners = cv2.findChessboardCorners(gray, self.board_size, flags)
        
        # Método 2: Si falla, intentar sin FAST_CHECK (más lento pero más robusto)
        if not ret:
            flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
            ret, corners = cv2.findChessboardCorners(gray, self.board_size, flags)
        
        # Método 3: Si falla, intentar con ecualización de histograma
        if not ret:
            gray_eq = cv2.equalizeHist(gray)
            ret, corners = cv2.findChessboardCorners(gray_eq, self.board_size, flags)
        
        frame_display = frame.copy()
        
        # Mostrar configuración del tablero en pantalla (debug)
        debug_text = f"Buscando: {self.board_size[0]}x{self.board_size[1]} esquinas"
        cv2.putText(frame_display, debug_text, (10, frame.shape[0] - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        if ret:
            # Refinar esquinas con precisión subpíxel
            corners_refined = cv2.cornerSubPix(
                gray, 
                corners, 
                (11, 11), 
                (-1, -1), 
                self.criteria
            )
            
            # Dibujar esquinas detectadas
            cv2.drawChessboardCorners(
                frame_display, 
                self.board_size, 
                corners_refined, 
                ret
            )
            
            return True, corners_refined, frame_display
        
        return False, None, frame_display
    
    def capture_image(self, frame, corners):
        """
        Guarda una imagen capturada para calibración
        
        Args:
            frame: Frame original
            corners: Esquinas detectadas y refinadas
            
        Returns:
            bool: True si se guardó exitosamente
        """
        if self.image_size is None:
            self.image_size = (frame.shape[1], frame.shape[0])
        
        self.obj_points.append(self.objp)
        self.img_points.append(corners)
        self.images_captured.append(frame.copy())
        
        # Guardar imagen en disco (opcional, para referencia)
        save_dir = CalibrationConfig.CALIBRATION_IMAGES_DIR / self.camera_name
        save_dir.mkdir(parents=True, exist_ok=True)
        
        filename = save_dir / f"calib_{len(self.images_captured):03d}.jpg"
        cv2.imwrite(str(filename), frame)
        
        return True
    
    def get_capture_count(self):
        """Retorna el número de imágenes capturadas"""
        return len(self.images_captured)
    
    def calibrate(self):
        """
        Ejecuta la calibración con las imágenes capturadas
        
        Returns:
            dict: Resultados de calibración o None si falla
        """
        if len(self.obj_points) < CalibrationConfig.MIN_IMAGES:
            print(f"✗ Insuficientes imágenes: {len(self.obj_points)} < {CalibrationConfig.MIN_IMAGES}")
            return None
        
        print(f"\n{'='*70}")
        print(f"CALIBRANDO CÁMARA {self.camera_name.upper()}")
        print(f"{'='*70}")
        print(f"Imágenes utilizadas: {len(self.obj_points)}")
        print(f"Tamaño del tablero: {self.board_size[0]}x{self.board_size[1]}")
        print(f"Tamaño del cuadrado: {self.square_size_m*1000:.1f} mm")
        print(f"Resolviendo...")
        
        # Ejecutar calibración
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            self.obj_points,
            self.img_points,
            self.image_size,
            None,
            None,
            flags=CalibrationConfig.CALIBRATION_FLAGS
        )
        
        if not ret:
            print("✗ Error durante la calibración")
            return None
        
        # Calcular error de reproyección
        total_error = 0
        for i in range(len(self.obj_points)):
            img_points2, _ = cv2.projectPoints(
                self.obj_points[i],
                rvecs[i],
                tvecs[i],
                camera_matrix,
                dist_coeffs
            )
            error = cv2.norm(self.img_points[i], img_points2, cv2.NORM_L2) / len(img_points2)
            total_error += error
        
        mean_error = total_error / len(self.obj_points)
        
        # Almacenar resultados
        self.camera_matrix = camera_matrix
        self.distortion_coeffs = dist_coeffs
        self.reprojection_error = mean_error
        self.is_calibrated = True
        
        # Mostrar resultados
        print(f"✓ Calibración completada")
        print(f"Error de reproyección: {mean_error:.4f} píxeles")
        
        if mean_error > CalibrationConfig.MAX_REPROJECTION_ERROR:
            print(f"⚠ ADVERTENCIA: Error alto (>{CalibrationConfig.MAX_REPROJECTION_ERROR} px)")
            print(f"  Considera recapturar imágenes con mejor calidad")
        
        print(f"\nMatriz de cámara:")
        print(camera_matrix)
        print(f"\nCoeficientes de distorsión:")
        print(dist_coeffs.ravel())
        print(f"{'='*70}\n")
        
        return {
            'camera_matrix': camera_matrix,
            'distortion_coeffs': dist_coeffs,
            'reprojection_error': mean_error,
            'num_images': len(self.obj_points),
            'image_size': self.image_size,
            'board_size': self.board_size,
            'square_size_m': self.square_size_m
        }
    
    def get_calibration_data(self):
        """
        Retorna los datos de calibración en formato serializable
        
        Returns:
            dict: Datos de calibración para guardar en JSON
        """
        if self.camera_matrix is None:
            return None
        
        return {
            'camera_matrix': self.camera_matrix.tolist(),
            'distortion_coeffs': self.distortion_coeffs.tolist(),
            'reprojection_error': float(self.reprojection_error),
            'num_images': len(self.obj_points),
            'image_width': self.image_size[0],
            'image_height': self.image_size[1]
        }

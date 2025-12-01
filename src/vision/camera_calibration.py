#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramienta de Calibración de Cámaras Estereoscópicas
Genera un archivo de configuración con los parámetros calibrados

Uso: python -m src.vision.camera_calibration
"""

import cv2
import numpy as np
import os
import json
from pathlib import Path


class StereoCalibrator:
    """Calibrador estéreo interactivo para obtener parámetros de cámaras"""
    
    def __init__(self, checkerboard_size=(9, 6), square_size=0.025):
        """
        Args:
            checkerboard_size: (ancho, alto) del tablero de ajedrez
            square_size: Tamaño de cada cuadrado en metros (0.025 = 2.5cm)
        """
        self.checkerboard_size = checkerboard_size
        self.square_size = square_size
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        
    def calibrate_single_camera(self, camera_id, num_images=20):
        """
        Calibra una cámara individual capturando imágenes del tablero de ajedrez
        
        Args:
            camera_id: ID de la cámara (0, 1, 2, etc.)
            num_images: Número de imágenes a capturar
            
        Returns:
            Parámetros de calibración (matrix, distortion)
        """
        print(f"\n{'='*70}")
        print(f"CALIBRACIÓN - CÁMARA {camera_id}")
        print(f"{'='*70}")
        print(f"Se capturarán {num_images} imágenes del tablero de ajedrez")
        print(f"Tablero: {self.checkerboard_size[0]}x{self.checkerboard_size[1]}")
        print(f"Tamaño cuadrado: {self.square_size*100:.1f} cm")
        print("\nTeclas:")
        print("  ESPACIO - Capturar imagen")
        print("  'q'     - Salir y comenzar calibración")
        print(f"\n{'='*70}\n")
        
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print(f"✗ No se pudo abrir la cámara {camera_id}")
            return None, None
        
        # Configurar resolución
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        objpoints = []  # Puntos 3D en el mundo real
        imgpoints = []  # Puntos 2D en la imagen
        
        # Preparar puntos del tablero
        objp = np.zeros((self.checkerboard_size[0] * self.checkerboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.checkerboard_size[0], 0:self.checkerboard_size[1]].T.reshape(-1, 2)
        objp *= self.square_size
        
        captured = 0
        cv2.namedWindow(f'Cámara {camera_id} - Calibración', cv2.WINDOW_NORMAL)
        cv2.resizeWindow(f'Cámara {camera_id} - Calibración', 640, 480)
        
        while captured < num_images:
            ret, frame = cap.read()
            if not ret:
                print("✗ Error al leer frame")
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detectar esquinas del tablero
            ret_corners, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)
            
            display_frame = frame.copy()
            
            if ret_corners:
                # Refinar esquinas
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
                
                # Dibujar esquinas
                cv2.drawChessboardCorners(display_frame, self.checkerboard_size, corners2, ret_corners)
                
                # Información en pantalla
                cv2.putText(display_frame, f"Detectado: {captured+1}/{num_images}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(display_frame, "ESPACIO para capturar", (10, 470),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(display_frame, "Tablero no detectado", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            cv2.imshow(f'Cámara {camera_id} - Calibración', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and ret_corners:
                objpoints.append(objp)
                imgpoints.append(corners2)
                captured += 1
                print(f"✓ Imagen {captured}/{num_images} capturada")
            elif key == ord('q'):
                if captured < 3:
                    print("⚠ Se necesitan al menos 3 imágenes. Continúa...")
                    continue
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        if len(objpoints) < 3:
            print(f"✗ No hay suficientes imágenes ({len(objpoints)}) para calibración")
            return None, None
        
        print(f"\n✓ Calibrando con {len(objpoints)} imágenes...")
        
        # Calibrar
        ret, matrix, distortion, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, gray.shape[::-1], None, None)
        
        if ret:
            print(f"✓ Calibración exitosa (Error: {ret:.4f})")
            return matrix, distortion
        else:
            print("✗ Error en calibración")
            return None, None
    
    def calibrate_stereo_pair(self, cam_left_id, cam_right_id):
        """
        Calibra un par estéreo de cámaras
        
        Returns:
            Diccionario con parámetros calibrados
        """
        print("\n" + "="*70)
        print("CALIBRACIÓN ESTEREOSCÓPICA")
        print("="*70)
        
        # Calibrar cámaras individuales
        matrix_left, distortion_left = self.calibrate_single_camera(cam_left_id, num_images=15)
        
        if matrix_left is None:
            print("✗ Falló calibración de cámara izquierda")
            return None
        
        matrix_right, distortion_right = self.calibrate_single_camera(cam_right_id, num_images=15)
        
        if matrix_right is None:
            print("✗ Falló calibración de cámara derecha")
            return None
        
        print("\n✓ Ambas cámaras calibradas")
        
        # Asumir que las cámaras están aproximadamente horizontales
        # En una calibración real, usarías stereoCalibrate() con ambas cámaras simultáneamente
        
        return {
            'matrix_left': matrix_left.tolist(),
            'distortion_left': distortion_left.tolist(),
            'matrix_right': matrix_right.tolist(),
            'distortion_right': distortion_right.tolist(),
            'camera_left_id': cam_left_id,
            'camera_right_id': cam_right_id,
            'checkerboard_size': self.checkerboard_size,
            'square_size_m': self.square_size
        }


def measure_camera_separation():
    """
    Guía al usuario para medir la separación entre cámaras
    
    Returns:
        Distancia en cm
    """
    print("\n" + "="*70)
    print("MEDICIÓN DE SEPARACIÓN DE CÁMARAS")
    print("="*70)
    print("\nMide la distancia entre los centros de las dos cámaras")
    print("(de centro óptico a centro óptico)")
    print("\nPara las Logi C920s, es típicamente 5-8 cm entre lentes")
    
    while True:
        try:
            separation = float(input("\nDistancia entre cámaras (cm): "))
            if 1 < separation < 50:
                print(f"✓ Separación: {separation:.2f} cm")
                return separation
            else:
                print("⚠ Valor fuera de rango (1-50 cm). Intenta de nuevo.")
        except ValueError:
            print("⚠ Ingresa un número válido")


def measure_keyboard_distance():
    """
    Guía al usuario para medir la distancia del teclado
    
    Returns:
        Distancia en cm
    """
    print("\n" + "="*70)
    print("MEDICIÓN DE DISTANCIA DEL TECLADO")
    print("="*70)
    print("\nMide la distancia desde el centro de las cámaras")
    print("hasta donde estará el teclado virtual (típicamente donde trabajarán las manos)")
    print("\nValor típico: 60-80 cm")
    
    while True:
        try:
            distance = float(input("\nDistancia del teclado (cm): "))
            if 30 < distance < 200:
                print(f"✓ Distancia: {distance:.2f} cm")
                return distance
            else:
                print("⚠ Valor fuera de rango (30-200 cm). Intenta de nuevo.")
        except ValueError:
            print("⚠ Ingresa un número válido")


def save_calibration(calibration_data, output_path='camcalibration/calibration.json'):
    """
    Guarda los datos de calibración en un archivo JSON
    
    Args:
        calibration_data: Diccionario con parámetros calibrados
        output_path: Ruta donde guardar el archivo
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(calibration_data, f, indent=4)
    
    print(f"\n✓ Calibración guardada en: {output_path}")


def main():
    """Flujo principal de calibración"""
    
    print("\n" + "="*70)
    print("HERRAMIENTA DE CALIBRACIÓN ESTEREOSCÓPICA")
    print("="*70)
    print("\n1. Se calibrarán las cámaras")
    print("2. Se medirá la separación entre cámaras")
    print("3. Se medirá la distancia del teclado")
    print("4. Se guardarán los parámetros")
    print("\n" + "="*70)
    
    input("\nPresiona ENTER para comenzar...")
    
    # Calibrador
    calibrator = StereoCalibrator(checkerboard_size=(9, 6), square_size=0.025)
    
    # Calibración estéreo
    calib_data = calibrator.calibrate_stereo_pair(cam_left_id=1, cam_right_id=2)
    
    if calib_data is None:
        print("✗ Calibración fallida")
        return
    
    # Medir separación
    separation = measure_camera_separation()
    calib_data['camera_separation_cm'] = separation
    
    # Medir distancia del teclado
    kb_distance = measure_keyboard_distance()
    calib_data['keyboard_distance_cm'] = kb_distance
    
    # Guardar
    save_calibration(calib_data)
    
    print("\n" + "="*70)
    print("✓ CALIBRACIÓN COMPLETADA")
    print("="*70)
    print("\nAhora puedes ejecutar: python -m src.main")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()

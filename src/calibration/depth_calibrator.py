#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calibrador de Profundidad - Fase 3
Calcula el factor de corrección de profundidad específico del sistema
"""

import cv2
import numpy as np
import json
from pathlib import Path
from .calibration_config import CalibrationConfig

# Importar load_depth_estimator
try:
    from ..vision.depth_estimator import load_depth_estimator
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from vision.depth_estimator import load_depth_estimator



class DepthCalibrator:
    """
    Calibrador para determinar el factor de corrección de profundidad
    Mide a distancias conocidas y calcula el factor óptimo
    """
    
    # Tamaño del buffer para filtro de suavizado
    SMOOTHING_BUFFER_SIZE = 15
    
    def __init__(self, depth_estimator, width=None, height=None):
        """
        Args:
            depth_estimator: Instancia de DepthEstimator ya calibrado (Fase 1+2)
            width: Ancho de la imagen
            height: Alto de la imagen
        """
        self.depth_estimator = depth_estimator

        # Si no se especifica, usar la resolución real de calibración
        if width is None or height is None:
            if getattr(depth_estimator, 'image_size', None) is not None:
                self.width, self.height = depth_estimator.image_size
            else:
                self.width = width or 1280
                self.height = height or 720
        else:
            self.width = width
            self.height = height
        
        # Resultados de mediciones
        self.measurements = []  # [(distancia_real, distancia_medida), ...]
        
        # Factor calculado
        self.correction_factor = 1.0
        
        # Distancia del plano del teclado (calculada automáticamente)
        self.keyboard_distance = None
        self.keyboard_distance_samples = []  # Para promediar múltiples muestras
        
        # Distancia real ingresada por el usuario (para corrección)
        self.real_distance_cm = None
        
        # Buffer para filtro de suavizado (media móvil)
        self.depth_buffer = []
        self.smoothed_depth = None
    
    def set_real_distance(self, distance_cm: float):
        """
        Establece la distancia real medida manualmente por el usuario.
        
        Args:
            distance_cm: Distancia real en centímetros
        """
        self.real_distance_cm = distance_cm
        print(f"")
        print(f"========================================")
        print(f"[Fase 3] DISTANCIA REAL: {distance_cm} cm")
        print(f"========================================")
        print(f"")
        
    def calculate_depth(self, landmarks_left, landmarks_right):
        """
        Calcula la profundidad del dedo índice usando landmarks.
        Aplica filtro de suavizado para estabilizar lecturas.
        
        Args:
            landmarks_left: Landmarks de mano izquierda (MediaPipe)
            landmarks_right: Landmarks de mano derecha (MediaPipe)
            
        Returns:
            float: Profundidad suavizada en cm o None
        """
        if not landmarks_left or not landmarks_right:
            # Limpiar buffer si no hay detección
            self.depth_buffer.clear()
            self.smoothed_depth = None
            return None
            
        # Obtener índice de ambas cámaras (landmark 8)
        # MediaPipe landmarks object has a .landmark attribute which is the list
        try:
            index_left = landmarks_left.landmark[8]
            index_right = landmarks_right.landmark[8]
        except AttributeError:
            # Fallback in case it's already a list (though unlikely with MP)
            index_left = landmarks_left[8]
            index_right = landmarks_right[8]
        
        # Convertir a coordenadas de píxel
        x_left = index_left.x * self.width
        y_left = index_left.y * self.height
        x_right = index_right.x * self.width
        y_right = index_right.y * self.height
        
        # Triangular sin corrección (usar factor 1.0 temporalmente)
        original_factor = self.depth_estimator.DEPTH_CORRECTION_FACTOR
        self.depth_estimator.DEPTH_CORRECTION_FACTOR = 1.0
        
        point_3d = self.depth_estimator.triangulate_point_DLT(
            (x_left, y_left), (x_right, y_right)
        )
        
        self.depth_estimator.DEPTH_CORRECTION_FACTOR = original_factor
        
        if point_3d is not None:
            raw_depth = point_3d[2]  # Profundidad Z
            
            # Agregar al buffer de suavizado
            self.depth_buffer.append(raw_depth)
            
            # Mantener tamaño máximo del buffer
            if len(self.depth_buffer) > self.SMOOTHING_BUFFER_SIZE:
                self.depth_buffer.pop(0)
            
            # Calcular media móvil (ignorando outliers con mediana)
            if len(self.depth_buffer) >= 3:
                # Usar mediana para mayor estabilidad (menos sensible a outliers)
                self.smoothed_depth = float(np.median(self.depth_buffer))
            else:
                self.smoothed_depth = raw_depth
            
            return self.smoothed_depth
            
        return None

    def add_measurement(self, real_distance, measured_depth):
        """
        Agrega una medición válida
        
        Args:
            real_distance: Distancia real objetivo (cm)
            measured_depth: Profundidad medida por el sistema (cm)
        """
        self.measurements.append((real_distance, measured_depth))
        print(f"[OK] Medicion agregada: {real_distance}cm real -> {measured_depth:.2f}cm medido")

    def calculate_and_save(self):
        """
        Calcula el factor de corrección final y lo guarda
        
        Returns:
            float: Factor de corrección calculado o None si falla
        """
        if len(self.measurements) < 3:
            print(f"[ERROR] Se necesitan al menos 3 mediciones (tienes {len(self.measurements)})")
            return None
            
        self.correction_factor = self._calculate_correction_factor()
        self._save_correction_factor()
        
        return self.correction_factor
    
    def _calculate_correction_factor(self):
        """
        Calcula el factor de corrección óptimo usando regresión lineal
        
        Returns:
            float: Factor de corrección (slope de la regresión)
        """
        if not self.measurements:
            return 1.0
        
        real_distances = np.array([m[0] for m in self.measurements])
        measured_distances = np.array([m[1] for m in self.measurements])
        
        # Regresión lineal: real = factor * medido
        # factor = mean(real / medido)
        ratios = real_distances / measured_distances
        factor = np.mean(ratios)
        
        return factor
    
    def _save_correction_factor(self):
        """Guarda el factor de corrección y distancia del teclado en el archivo de calibración"""
        try:
            calib_file = CalibrationConfig.CALIBRATION_FILE
            
            # Leer calibración existente
            with open(calib_file, 'r') as f:
                calib_data = json.load(f)
            
            # Agregar sección de profundidad (Fase 3)
            calib_data['depth_correction'] = {
                'factor': self.correction_factor,
                'keyboard_distance_cm': self.keyboard_distance,
                'measurements': [
                    {'real_cm': real, 'measured_cm': measured}
                    for real, measured in self.measurements
                ],
                'num_samples': len(self.measurements)
            }
            
            # Guardar
            with open(calib_file, 'w') as f:
                json.dump(calib_data, f, indent=4)
            
            print(f"[OK] Factor de correccion guardado en: {calib_file}")
            print(f"[OK] Distancia del teclado: {self.keyboard_distance:.2f} cm")
            
        except Exception as e:
            print(f"⚠ Error al guardar factor de corrección: {e}")
    
    def add_keyboard_distance_sample(self, depth):
        """
        Agrega una muestra de distancia del teclado
        
        Args:
            depth: Profundidad medida cuando el dedo toca el plano del teclado
        """
        if depth is not None and depth > 0:
            self.keyboard_distance_samples.append(depth)
            print(f"  Muestra de teclado #{len(self.keyboard_distance_samples)}: {depth:.2f} cm")
    
    def calculate_keyboard_distance(self):
        """
        Calcula la distancia del teclado promediando las muestras.
        Si hay una distancia real establecida, calcula el factor de corrección.
        
        Returns:
            float: Distancia final del teclado en cm, o None si no hay muestras
        """
        if not self.keyboard_distance_samples:
            return None
        
        # Distancia medida por el sistema (mediana para robustez)
        measured_distance = float(np.median(self.keyboard_distance_samples))
        print(f"  Distancia medida por el sistema: {measured_distance:.2f} cm")
        
        # Si hay distancia real, calcular factor de corrección
        if self.real_distance_cm is not None and self.real_distance_cm > 0:
            # Factor = real / medido
            self.correction_factor = self.real_distance_cm / measured_distance
            
            # La distancia final es la real (la que el usuario midió)
            self.keyboard_distance = self.real_distance_cm
            
            # Calcular el error
            error_cm = abs(measured_distance - self.real_distance_cm)
            error_percent = (error_cm / self.real_distance_cm) * 100
            
            print(f"  Distancia real (usuario): {self.real_distance_cm:.2f} cm")
            print(f"  Factor de correccion: {self.correction_factor:.4f}")
            print(f"  Error de medicion: {error_cm:.2f} cm ({error_percent:.1f}%)")
            print(f"  Distancia del teclado (corregida): {self.keyboard_distance:.2f} cm")
        else:
            # Sin distancia real, usar la medida directamente
            self.keyboard_distance = measured_distance
            self.correction_factor = 1.0
            print(f"  Distancia del teclado: {self.keyboard_distance:.2f} cm (sin correccion)")
        
        return self.keyboard_distance
    
    def save_keyboard_distance_only(self):
        """Guarda la distancia del teclado y el factor de corrección"""
        if self.keyboard_distance is None:
            print("No hay distancia de teclado calculada")
            return False
        
        # DEBUG: Mostrar valores antes de guardar
        print(f"")
        print(f"======== GUARDANDO CALIBRACION ========")
        print(f"  keyboard_distance: {self.keyboard_distance}")
        print(f"  correction_factor: {self.correction_factor}")
        print(f"  real_distance_cm: {self.real_distance_cm}")
        print(f"  samples: {self.keyboard_distance_samples}")
        print(f"========================================")
        print(f"")
            
        try:
            calib_file = CalibrationConfig.CALIBRATION_FILE
            
            # Leer calibración existente
            with open(calib_file, 'r') as f:
                calib_data = json.load(f)
            
            # Agregar o actualizar sección de profundidad
            if 'depth_correction' not in calib_data:
                calib_data['depth_correction'] = {}
            
            calib_data['depth_correction']['keyboard_distance_cm'] = self.keyboard_distance
            calib_data['depth_correction']['keyboard_samples'] = len(self.keyboard_distance_samples)
            calib_data['depth_correction']['correction_factor'] = self.correction_factor
            
            # Si hay distancia real, guardarla también
            if self.real_distance_cm is not None:
                calib_data['depth_correction']['real_distance_cm'] = self.real_distance_cm
                calib_data['depth_correction']['measured_distance_cm'] = float(np.median(self.keyboard_distance_samples))
                
                # Calcular y guardar error
                measured = float(np.median(self.keyboard_distance_samples))
                error_cm = abs(measured - self.real_distance_cm)
                error_percent = (error_cm / self.real_distance_cm) * 100
                calib_data['depth_correction']['error_cm'] = error_cm
                calib_data['depth_correction']['error_percent'] = error_percent
            
            # Guardar
            with open(calib_file, 'w') as f:
                json.dump(calib_data, f, indent=4)
            
            print(f"Distancia del teclado guardada: {self.keyboard_distance:.2f} cm")
            print(f"Factor de correccion guardado: {self.correction_factor:.4f}")
            return True
            
        except Exception as e:
            print(f"Error al guardar distancia del teclado: {e}")
            return False

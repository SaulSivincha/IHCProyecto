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
        
        # Parámetros de regresión lineal (Real = slope * Medido + intercept)
        self.slope = 1.0
        self.intercept = 0.0
        self.correction_factor = 1.0  # Mantener por retrocompatibilidad
        
        # Distancia del plano del teclado (calculada automáticamente)
        self.keyboard_distance = None
        self.keyboard_distance_samples = []  # Para promediar múltiples muestras
        
        # Distancia real ingresada por el usuario (para corrección)
        self.real_distance_cm = None
        
        # Buffer para filtro de suavizado (media móvil)
        self.depth_buffer = []
        self.smoothed_depth = None
        
        # Métricas de validación
        self.r2 = 1.0
        self.mae = 0.0
    
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
        pt_L = (index_left.x * self.width, index_left.y * self.height)
        pt_R = (index_right.x * self.width, index_right.y * self.height)
        
        # --- CORRECCIÓN CRÍTICA: Forzar modo "RAW" absoluto ---
        # Guardar valores actuales
        original_factor = getattr(self.depth_estimator, 'DEPTH_CORRECTION_FACTOR', 1.0)
        original_slope = getattr(self.depth_estimator, 'depth_slope', 1.0)
        original_intercept = getattr(self.depth_estimator, 'depth_intercept', 0.0)
        
        # Eliminar cualquier corrección previa para medir el error crudo
        self.depth_estimator.DEPTH_CORRECTION_FACTOR = 1.0
        self.depth_estimator.depth_slope = 1.0
        self.depth_estimator.depth_intercept = 0.0
        
        try:
            from ..vision.stereo_config import StereoConfig
            
            # 1. Swap si es necesario
            if StereoConfig.CAMERAS_SWAPPED:
                raw_L = pt_R
                raw_R = pt_L
            else:
                raw_L = pt_L
                raw_R = pt_R
            
            # 2. Rectificar (Usando las matrices distorsionadas originales -> Rectificadas)
            rect_L = self.depth_estimator.rectify_point(raw_L, is_left=True)
            rect_R = self.depth_estimator.rectify_point(raw_R, is_left=False)
            
            # 3. Triangular SIMPLE (Igual que en Fase 4B)
            # Nota: triangulate_point con method='simple' usa internamente apply_depth_correction
            # Pero como acabamos de poner slope=1 e intercept=0, obtendremos Z crudo.
            point_3d = self.depth_estimator.triangulate_point(rect_L, rect_R, method='simple')
            
        except Exception as e:
            print(f"[DepthCalibrator] Error en cálculo unificado (RAW): {e}")
            point_3d = None
            
        finally:
            # Restaurar valores originales SIEMPRE
            self.depth_estimator.DEPTH_CORRECTION_FACTOR = original_factor
            self.depth_estimator.depth_slope = original_slope
            self.depth_estimator.depth_intercept = original_intercept
        
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
        Calcula la regresión lineal (m y b) o offset simple y la guarda.
        
        Returns:
            tuple: (slope, intercept) o None si falla
        """
        # CAMBIO: Permitir >= 1 en lugar de < 2
        if len(self.measurements) < 1:
            print(f"[ERROR] Se necesita al menos 1 medición")
            return None
            
        # Calcular regresión lineal y guardar
        self.slope, self.intercept, self.r2, self.mae = self._calculate_regression()
        
        # Mantener correction_factor por retrocompatibilidad (usar slope)
        self.correction_factor = self.slope
        
        self._save_calibration_params()
        
        return self.slope, self.intercept
    
    def _calculate_regression(self):
        """
        Calcula regresión lineal o offset simple.
        
        Returns:
            tuple: (slope, intercept, r2, mae)
        """
        if not self.measurements:
            return 1.0, 0.0, 1.0, 0.0
        
        # CASO 1 PUNTO: Asumir pendiente perfecta (1.0) y solo corregir el error constante (offset)
        if len(self.measurements) == 1:
            real_val = self.measurements[0][0]
            measured_val = self.measurements[0][1]
            
            slope = 1.0
            intercept = real_val - measured_val
            r2 = 1.0  # Con un punto la correlación es "perfecta" por definición
            mae = 0.0 # Error respecto al punto único es 0
            
            print(f"[DEBUG] Calibración de 1 punto:")
            print(f"  Pendiente fija: {slope:.4f}")
            print(f"  Offset calculado: {intercept:.4f} cm")
            return slope, intercept, r2, mae

        # CASO MULTIPLES PUNTOS (Regresión Lineal normal)
        x = np.array([m[1] for m in self.measurements])
        y = np.array([m[0] for m in self.measurements])
        
        # Ajuste lineal de grado 1 (y = mx + b)
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calcular R2 (Coeficiente de determinación)
        y_pred = slope * x + intercept
        y_mean = np.mean(y)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - y_mean)**2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 1.0
        
        # MAE (Mean Absolute Error)
        mae = np.mean(np.abs(y - y_pred))
        
        print(f"[DEBUG] Regresión calculada:")
        print(f"  Pendiente (m): {slope:.4f}")
        print(f"  Offset (b):    {intercept:.4f} cm")
        print(f"  R2:            {r2:.4f}")
        print(f"  MAE:           {mae:.4f} cm")
        
        return slope, intercept, float(r2), float(mae)

    def _save_calibration_params(self):
        """Guarda los parámetros m y b en el JSON"""
        try:
            calib_file = CalibrationConfig.CALIBRATION_FILE
            
            with open(calib_file, 'r') as f:
                calib_data = json.load(f)
            
            # Guardar estructura nueva con regresión lineal
            calib_data['depth_correction'] = {
                'method': 'linear_regression',
                'slope': self.slope,           # m
                'intercept': self.intercept,   # b
                'r2': self.r2,                 # R2
                'mae_cm': self.mae,            # MAE
                'correction_factor': self.slope,  # Retrocompatibilidad
                'keyboard_distance_cm': self.keyboard_distance,
                'measurements': [
                    {'real_cm': real, 'measured_cm': measured}
                    for real, measured in self.measurements
                ],
                'num_samples': len(self.measurements)
            }
            
            with open(calib_file, 'w') as f:
                json.dump(calib_data, f, indent=4)
            
            print(f"[OK] Calibración de profundidad guardada (Regresión Lineal)")
            print(f"  Fórmula: Real = {self.slope:.4f} * Medido + {self.intercept:.4f}")
            
        except Exception as e:
            print(f"Error al guardar: {e}")
    
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

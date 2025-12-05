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


class DepthCalibrator:
    """
    Calibrador para determinar el factor de corrección de profundidad
    Mide a distancias conocidas y calcula el factor óptimo
    """
    
    def __init__(self, depth_estimator, width=1280, height=720):
        """
        Args:
            depth_estimator: Instancia de DepthEstimator ya calibrado (Fase 1+2)
            width: Ancho de la imagen
            height: Alto de la imagen
        """
        self.depth_estimator = depth_estimator
        self.width = width
        self.height = height
        
        # Distancias de referencia para medir (en cm)
        # Ajustadas a un rango más cercano y práctico
        self.reference_distances = [25, 30, 35, 40]
        
        # Resultados de mediciones
        self.measurements = []  # [(distancia_real, distancia_medida), ...]
        
        # Factor calculado
        self.correction_factor = 1.0
        
    def run_depth_calibration(self, cam_left, cam_right, hand_detector_left, hand_detector_right):
        """
        Ejecuta el proceso de calibración de profundidad
        
        Args:
            cam_left: VideoThread de cámara izquierda
            cam_right: VideoThread de cámara derecha
            hand_detector_left: HandDetector para cámara izquierda
            hand_detector_right: HandDetector para cámara derecha
        
        Returns:
            float: Factor de corrección calculado (o None si cancelado)
        """
        print("\n[DEBUG] Entrando a run_depth_calibration...")
        print("\n" + "="*70)
        print("FASE 3: CALIBRACIÓN DE PROFUNDIDAD")
        print("="*70)
        print("\nEste proceso calculará el factor de corrección específico")
        print("para tu sistema de cámaras.\n")
        print("INSTRUCCIONES:")
        print("  1. Coloca tu DEDO ÍNDICE sobre una superficie plana")
        print("  2. Mide la distancia REAL con una regla (desde cámara a dedo)")
        print("  3. Mantén el dedo quieto y presiona ESPACIO para capturar")
        print("  4. Repite para diferentes distancias")
        print("\nDistancias a medir: 25cm, 30cm, 35cm, 40cm")
        print("\nPresiona ESPACIO en la ventana para comenzar cada medición")
        print("="*70 + "\n")
        
        print("[DEBUG] Creando ventana...")
        window_name = "Calibración de Profundidad - Fase 3"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.width * 2, self.height)
        print("[DEBUG] Ventana creada")
        
        # Mostrar pantalla de inicio
        print("[DEBUG] Mostrando pantalla de inicio...")
        intro_frame = np.zeros((self.height, self.width * 2, 3), dtype=np.uint8)
        cv2.putText(intro_frame, "FASE 3: CALIBRACION DE PROFUNDIDAD", 
                   (self.width - 350, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(intro_frame, "Coloca tu dedo a las distancias indicadas", 
                   (self.width - 330, 220),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(intro_frame, "y presiona ESPACIO para capturar", 
                   (self.width - 280, 260),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(intro_frame, "Distancias: 25cm, 30cm, 35cm, 40cm", 
                   (self.width - 320, 330),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        cv2.putText(intro_frame, "Presiona ESPACIO para comenzar...", 
                   (self.width - 280, self.height - 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(window_name, intro_frame)
        print("[DEBUG] Pantalla de inicio mostrada, esperando input...")
        
        # Esperar ESPACIO o ESC
        while True:
            key = cv2.waitKey(100) & 0xFF
            if key == 32:  # ESPACIO
                print("[DEBUG] ESPACIO presionado, iniciando calibración...")
                break
            elif key == 27:  # ESC
                print("\n✗ Calibración de profundidad cancelada")
                cv2.destroyWindow(window_name)
                return None
        
        print("[DEBUG] Iniciando bucle principal de mediciones...")
        current_distance_idx = 0
        captured_measurements = []
        
        try:
            print(f"[DEBUG] Objetivo: capturar {len(self.reference_distances)} mediciones")
            while current_distance_idx < len(self.reference_distances):
                # Leer frames de ambas cámaras
                _, frame_left = cam_left.next(black=False, wait=1)
                _, frame_right = cam_right.next(black=False, wait=1)
                
                if frame_left is None or frame_right is None:
                    print("[DEBUG] Frame None detectado, continuando...")
                    continue
                
                # Detectar manos
                hand_detector_left.findHands(frame_left)
                hand_detector_right.findHands(frame_right)
                
                # Obtener resultados
                results_left = hand_detector_left.results
                results_right = hand_detector_right.results
                
                # Dibujar detecciones
                hand_detector_left.drawHands(frame_left)
                hand_detector_right.drawHands(frame_right)
                
                # Calcular profundidad si ambas manos detectadas
                depth_z = None
                if results_left.multi_hand_landmarks and results_right.multi_hand_landmarks:
                    # Obtener índice de ambas cámaras (landmark 8)
                    landmarks_left = results_left.multi_hand_landmarks[0].landmark
                    landmarks_right = results_right.multi_hand_landmarks[0].landmark
                    
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
                        depth_z = point_3d[2]  # Profundidad sin corrección
                
                # Combinar frames
                combined = np.concatenate((frame_left, frame_right), axis=1)
                
                # Dibujar UI
                target_distance = self.reference_distances[current_distance_idx]
                combined = self._draw_calibration_ui(
                    combined, 
                    target_distance, 
                    depth_z,
                    current_distance_idx + 1,
                    len(self.reference_distances)
                )
                
                cv2.imshow(window_name, combined)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == 32:  # ESPACIO - Capturar medición
                    if depth_z is not None:
                        captured_measurements.append((target_distance, depth_z))
                        print(f"✓ Medición {current_distance_idx + 1}/{len(self.reference_distances)}: "
                              f"{target_distance}cm real → {depth_z:.2f}cm medido")
                        current_distance_idx += 1
                        
                        if current_distance_idx >= len(self.reference_distances):
                            print("[DEBUG] Todas las mediciones completadas, saliendo del bucle")
                            break
                    else:
                        print("✗ No se detecta dedo índice. Asegúrate de que ambas manos sean visibles.")
                
                elif key == 27:  # ESC - Cancelar
                    print("\n✗ Calibración de profundidad cancelada por usuario")
                    return None
        
        except Exception as e:
            print(f"[DEBUG] Excepción en bucle de mediciones: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        finally:
            print("[DEBUG] Saliendo del bucle, cerrando ventana...")
            try:
                cv2.destroyWindow(window_name)
            except:
                pass  # La ventana ya puede estar cerrada
        
        print(f"[DEBUG] Mediciones capturadas: {len(captured_measurements)}")
        
        # Calcular factor de corrección
        if len(captured_measurements) >= 3:
            self.measurements = captured_measurements
            self.correction_factor = self._calculate_correction_factor()
            
            print("\n" + "="*70)
            print("RESULTADOS DE CALIBRACIÓN DE PROFUNDIDAD")
            print("="*70)
            print(f"\nMediciones realizadas: {len(self.measurements)}")
            print("\nComparación:")
            for real, measured in self.measurements:
                error = measured - real
                error_pct = (error / real) * 100
                print(f"  {real:5.1f}cm real → {measured:6.2f}cm medido | Error: {error:+6.2f}cm ({error_pct:+5.1f}%)")
            
            print(f"\n✓ FACTOR DE CORRECCIÓN CALCULADO: {self.correction_factor:.4f}")
            print(f"  Este factor se aplicará a todas las mediciones de profundidad")
            print("="*70 + "\n")
            
            # Guardar en calibración
            self._save_correction_factor()
            
            return self.correction_factor
        else:
            print(f"\n✗ Error: Se necesitan al menos 3 mediciones (tienes {len(captured_measurements)})")
            return None
    
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
        
        # Validar que el factor esté en rango razonable
        if factor < 0.5 or factor > 1.5:
            print(f"\n⚠ ADVERTENCIA: Factor {factor:.4f} fuera de rango esperado (0.5-1.5)")
            print("  Esto puede indicar un problema con la calibración estéreo (Fase 2)")
            print("  Se recomienda re-calibrar Fase 2")
        
        return factor
    
    def _save_correction_factor(self):
        """Guarda el factor de corrección en el archivo de calibración"""
        try:
            calib_file = CalibrationConfig.CALIBRATION_FILE
            
            # Leer calibración existente
            with open(calib_file, 'r') as f:
                calib_data = json.load(f)
            
            # Agregar sección de profundidad (Fase 3)
            calib_data['depth_correction'] = {
                'factor': self.correction_factor,
                'measurements': [
                    {'real_cm': real, 'measured_cm': measured}
                    for real, measured in self.measurements
                ],
                'num_samples': len(self.measurements)
            }
            
            # Guardar
            with open(calib_file, 'w') as f:
                json.dump(calib_data, f, indent=4)
            
            print(f"✓ Factor de corrección guardado en: {calib_file}")
            
        except Exception as e:
            print(f"⚠ Error al guardar factor de corrección: {e}")
    
    def _draw_calibration_ui(self, frame, target_distance, measured_depth, step, total_steps):
        """Dibuja la interfaz de calibración de profundidad"""
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Panel superior con instrucciones
        cv2.rectangle(overlay, (0, 0), (w, 150), (30, 30, 30), -1)
        frame = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)
        
        # Título
        title = f"FASE 3: CALIBRACION DE PROFUNDIDAD ({step}/{total_steps})"
        cv2.putText(frame, title, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        
        # Instrucción
        instruction = f"Coloca tu dedo a {target_distance}cm de la camara"
        cv2.putText(frame, instruction, (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Estado de detección
        if measured_depth is not None:
            status = f"Profundidad detectada: {measured_depth:.2f} cm"
            color = (0, 255, 0)
            action = "Presiona ESPACIO para capturar"
        else:
            status = "Esperando deteccion del dedo indice..."
            color = (0, 165, 255)
            action = "Asegurate de que ambas manos sean visibles"
        
        cv2.putText(frame, status, (20, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, action, (20, 140),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Controles en la parte inferior
        cv2.rectangle(overlay, (0, h - 50), (w, h), (30, 30, 30), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        cv2.putText(frame, "[ESPACIO] Capturar | [ESC] Cancelar", (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame

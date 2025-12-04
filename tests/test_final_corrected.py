"""
Test con Factor de Corrección FORZADO
======================================
Este script aplica el factor de corrección manualmente para asegurar que funcione
"""

import cv2
import numpy as np
import sys
import os
from collections import deque

# Agregar directorio padre al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Forzar recarga del módulo
if 'src.vision.depth_estimator' in sys.modules:
    del sys.modules['src.vision.depth_estimator']

from src.vision.hand_detector import HandDetector
from src.vision.depth_estimator import DepthEstimator

class CorrectedDetectionFinal:
    def __init__(self):
        # Factor de corrección (basado en mediciones empíricas)
        self.CORRECTION_FACTOR = 0.74  # 43cm real / 58cm medido ≈ 0.74
        
        # Sistema de suavizado
        self.smoothing_window = 5
        self.position_history = {}
        
        # Inicializar detector de manos
        self.hand_detector = HandDetector(
            detectionCon=0.7,
            trackCon=0.7,
            maxHands=1
        )
        
        # Inicializar estimador de profundidad
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        calibration_path = os.path.join(project_root, 'camcalibration', 'calibration.json')
        
        self.depth_estimator = DepthEstimator(calibration_path)
        
        # Cámaras
        self.cap_left = cv2.VideoCapture(2)
        self.cap_right = cv2.VideoCapture(1)
        
        if not self.cap_left.isOpened() or not self.cap_right.isOpened():
            print("❌ Error abriendo cámaras")
            sys.exit(1)
        
        # Configurar resolución
        for cap in [self.cap_left, self.cap_right]:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("\n" + "="*60)
        print("✅ TEST FINAL CON CORRECCIÓN APLICADA")
        print("="*60)
        print(f"\n📏 Factor de corrección: {self.CORRECTION_FACTOR}")
        print(f"🔄 Suavizado: {self.smoothing_window} frames")
        print("\nControles:")
        print("  - 'q': Salir")
        print("="*60 + "\n")
    
    def smooth_position(self, position_3d, landmark_id=0):
        """Suaviza una posición 3D"""
        if position_3d is None:
            return None
        
        # Inicializar buffer si no existe
        if landmark_id not in self.position_history:
            self.position_history[landmark_id] = deque(maxlen=self.smoothing_window)
        
        # Agregar nueva posición
        self.position_history[landmark_id].append(position_3d)
        
        # Calcular promedio
        history = np.array(list(self.position_history[landmark_id]))
        smoothed = np.mean(history, axis=0)
        
        return tuple(smoothed)
    
    def run(self):
        """Loop principal"""
        cv2.namedWindow('Detección Corregida')
        
        frame_count = 0
        
        while True:
            ret_left, frame_left = self.cap_left.read()
            ret_right, frame_right = self.cap_right.read()
            
            if not ret_left or not ret_right:
                print("❌ Error capturando frames")
                break
            
            # Detectar manos
            self.hand_detector.findHands(frame_left)
            self.hand_detector.drawHands(frame_left)
            hands_left = self.hand_detector.results.multi_hand_landmarks if self.hand_detector.results else None
            
            self.hand_detector.findHands(frame_right)
            hands_right = self.hand_detector.results.multi_hand_landmarks if self.hand_detector.results else None
            
            display = frame_left.copy()
            
            # Si hay detección bilateral
            if hands_left and hands_right and len(hands_left) > 0 and len(hands_right) > 0:
                # Rectificar imágenes
                rect_left, rect_right = self.depth_estimator.rectify_images(
                    frame_left, frame_right
                )
                
                # Obtener landmarks
                landmarks_left = hands_left[0].landmark
                landmarks_right = hands_right[0].landmark
                
                # Procesar dedo índice (ID 8)
                lm_left = landmarks_left[8]
                lm_right = landmarks_right[8]
                
                # Convertir a coordenadas de imagen
                h, w = frame_left.shape[:2]
                point_left = (int(lm_left.x * w), int(lm_left.y * h))
                point_right = (int(lm_right.x * w), int(lm_right.y * h))
                
                # Rectificar puntos
                point_left_rect = self.depth_estimator.rectify_point(point_left, is_left=True)
                point_right_rect = self.depth_estimator.rectify_point(point_right, is_left=False)
                
                if point_left_rect and point_right_rect:
                    # Triangular (sin corrección automática)
                    point_3d_raw = self.depth_estimator.triangulate_point_DLT(
                        point_left_rect, point_right_rect
                    )
                    
                    if point_3d_raw:
                        x_raw, y_raw, z_raw = point_3d_raw
                        
                        # APLICAR CORRECCIÓN MANUALMENTE AQUÍ
                        x_corrected = x_raw
                        y_corrected = y_raw
                        z_corrected = z_raw * self.CORRECTION_FACTOR
                        
                        # Aplicar suavizado
                        point_3d_smooth = self.smooth_position(
                            (x_corrected, y_corrected, z_corrected), 
                            landmark_id=8
                        )
                        
                        x_smooth, y_smooth, z_smooth = point_3d_smooth
                        
                        # Mostrar en pantalla
                        y_offset = 30
                        
                        # Original (sin corrección)
                        cv2.putText(display, f"ORIGINAL: Z={z_raw:.1f} cm",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)
                        y_offset += 30
                        
                        # Corregido
                        cv2.putText(display, f"CORREGIDO: Z={z_corrected:.1f} cm",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                        y_offset += 30
                        
                        # Suavizado
                        cv2.putText(display, f"SUAVIZADO: X={x_smooth:.1f} Y={y_smooth:.1f} Z={z_smooth:.1f} cm",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        y_offset += 30
                        
                        # Factor aplicado
                        cv2.putText(display, f"Factor: x{self.CORRECTION_FACTOR}",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        # Imprimir en consola cada 10 frames
                        if frame_count % 10 == 0:
                            reduction = z_raw - z_smooth
                            print(f"Frame {frame_count}: "
                                  f"Z_original={z_raw:.1f}cm → "
                                  f"Z_corregido={z_corrected:.1f}cm → "
                                  f"Z_smooth={z_smooth:.1f}cm "
                                  f"[Reducción: {reduction:.1f}cm]")
            else:
                cv2.putText(display, "Sin detección bilateral",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Detección Corregida', display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
        
        self.cap_left.release()
        self.cap_right.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    test = CorrectedDetectionFinal()
    test.run()

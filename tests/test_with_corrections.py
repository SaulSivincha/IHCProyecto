"""
Test de Detección con Correcciones Aplicadas
============================================
Demuestra el uso de:
1. Factor de corrección de profundidad (0.74)
2. Suavizado temporal de coordenadas

Compara coordenadas sin procesar vs suavizadas
"""

import cv2
import numpy as np
import sys
import os

# Agregar directorio padre al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vision.hand_detector import HandDetector
from src.vision.depth_estimator import DepthEstimator

class CorrectedDetectionTest:
    def __init__(self):
        # Inicializar detector de manos
        self.hand_detector = HandDetector(
            detectionCon=0.7,
            trackCon=0.7,
            maxHands=1
        )
        
        # Inicializar estimador de profundidad con correcciones
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        calibration_path = os.path.join(project_root, 'camcalibration', 'calibration.json')
        
        self.depth_estimator = DepthEstimator(calibration_path)
        
        # Activar suavizado (ventana de 5 frames)
        self.depth_estimator.enable_smoothing(enabled=True, window_size=5)
        
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
        print("✅ TEST CON CORRECCIONES APLICADAS")
        print("="*60)
        print(f"\n📏 Factor de corrección Z: {self.depth_estimator.DEPTH_CORRECTION_FACTOR}")
        print(f"🔄 Suavizado temporal: ACTIVADO (ventana={self.depth_estimator.smoothing_window} frames)")
        print("\nInstrucciones:")
        print("  - Coloca tu mano frente a las cámaras")
        print("  - Observa coordenadas RAW vs SUAVIZADAS")
        print("  - 's': Toggle suavizado ON/OFF")
        print("  - 'q': Salir")
        print("="*60 + "\n")
    
    def run(self):
        """Loop principal"""
        cv2.namedWindow('Vista Izquierda - Con Correcciones')
        
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
                    # Triangular (ya incluye corrección de profundidad 0.74)
                    point_3d_raw = self.depth_estimator.triangulate_point_DLT(
                        point_left_rect, point_right_rect
                    )
                    
                    if point_3d_raw:
                        # Aplicar suavizado temporal
                        point_3d_smooth = self.depth_estimator.smooth_position(
                            point_3d_raw, landmark_id=8
                        )
                        
                        x_raw, y_raw, z_raw = point_3d_raw
                        x_smooth, y_smooth, z_smooth = point_3d_smooth
                        
                        # Calcular diferencia
                        diff_z = abs(z_smooth - z_raw)
                        
                        # Mostrar en pantalla
                        y_offset = 30
                        
                        # Estado de suavizado
                        status = "🟢 ON" if self.depth_estimator.smoothing_enabled else "🔴 OFF"
                        cv2.putText(display, f"Suavizado: {status}", 
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        y_offset += 30
                        
                        # Coordenadas RAW (sin suavizar)
                        cv2.putText(display, f"RAW: X={x_raw:.1f} Y={y_raw:.1f} Z={z_raw:.1f} cm",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)
                        y_offset += 25
                        
                        # Coordenadas SUAVIZADAS
                        cv2.putText(display, f"SMOOTH: X={x_smooth:.1f} Y={y_smooth:.1f} Z={z_smooth:.1f} cm",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        y_offset += 25
                        
                        # Diferencia
                        cv2.putText(display, f"Delta Z: {diff_z:.2f} cm",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                        
                        # Imprimir en consola cada 10 frames
                        if frame_count % 10 == 0:
                            print(f"Frame {frame_count}: "
                                  f"RAW=({x_raw:.1f}, {y_raw:.1f}, {z_raw:.1f}) → "
                                  f"SMOOTH=({x_smooth:.1f}, {y_smooth:.1f}, {z_smooth:.1f}) "
                                  f"[Δ={diff_z:.2f}cm]")
            else:
                cv2.putText(display, "Sin detección bilateral",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Vista Izquierda - Con Correcciones', display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Toggle suavizado
                current = self.depth_estimator.smoothing_enabled
                self.depth_estimator.enable_smoothing(not current)
                status = "ACTIVADO" if not current else "DESACTIVADO"
                print(f"\n{'='*40}")
                print(f"🔄 Suavizado {status}")
                print(f"{'='*40}\n")
            
            frame_count += 1
        
        self.cap_left.release()
        self.cap_right.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    test = CorrectedDetectionTest()
    test.run()

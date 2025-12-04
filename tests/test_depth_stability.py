"""
Test de Estabilidad de Detección
=================================
Mide la estabilidad de las coordenadas 3D cuando la mano está quieta.

Métricas:
- Desviación estándar de X, Y, Z
- Variación máxima (rango)
- Jitter promedio entre frames

Si los valores son inestables con mano quieta:
1. Problema de calibración (RMS alto)
2. Iluminación variable
3. Ruido en detección de landmarks
"""

import cv2
import numpy as np
import sys
import os
from collections import deque

# Agregar directorio padre al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vision.hand_detector import HandDetector
from src.vision.depth_estimator import DepthEstimator

class StabilityTester:
    def __init__(self):
        # Inicializar detector de manos
        self.hand_detector = HandDetector(
            detectionCon=0.7,  # Mayor confianza
            trackCon=0.7,
            maxHands=1
        )
        
        # Inicializar estimador de profundidad
        # Calcular ruta absoluta de calibración
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        calibration_path = os.path.join(project_root, 'camcalibration', 'calibration.json')
        
        try:
            self.depth_estimator = DepthEstimator(calibration_path)
        except Exception as e:
            print(f"❌ Error cargando calibración: {e}")
            sys.exit(1)
        
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
        
        # Buffer de mediciones (últimos 60 frames = 2 segundos @ 30fps)
        self.buffer_size = 60
        self.measurements = {
            8: deque(maxlen=self.buffer_size)  # Índice
        }
        
        # Estadísticas
        self.frame_count = 0
        self.recording = False
        
        print("\n" + "="*60)
        print("📊 TEST DE ESTABILIDAD DE DETECCIÓN")
        print("="*60)
        print("\nInstrucciones:")
        print("1. Coloca tu mano en una posición cómoda")
        print("2. Mantén el DEDO ÍNDICE COMPLETAMENTE QUIETO")
        print("3. Presiona ESPACIO para comenzar a grabar")
        print("4. Mantén quieto por 2 segundos")
        print("5. El sistema mostrará estadísticas de estabilidad")
        print("\nControles:")
        print("  - ESPACIO: Iniciar/detener grabación")
        print("  - 'r': Resetear estadísticas")
        print("  - 'q': Salir")
        print("="*60 + "\n")
    
    def calculate_statistics(self):
        """Calcula estadísticas de estabilidad"""
        if len(self.measurements[8]) < 10:
            return None
        
        data = np.array(list(self.measurements[8]))  # Shape: (N, 3) - X, Y, Z
        
        # Desviaciones estándar
        std_x, std_y, std_z = np.std(data, axis=0)
        
        # Rangos (max - min)
        range_x = np.max(data[:, 0]) - np.min(data[:, 0])
        range_y = np.max(data[:, 1]) - np.min(data[:, 1])
        range_z = np.max(data[:, 2]) - np.min(data[:, 2])
        
        # Jitter (diferencia promedio entre frames consecutivos)
        if len(data) > 1:
            diffs = np.abs(np.diff(data, axis=0))
            jitter_x, jitter_y, jitter_z = np.mean(diffs, axis=0)
        else:
            jitter_x = jitter_y = jitter_z = 0
        
        # Promedios
        mean_x, mean_y, mean_z = np.mean(data, axis=0)
        
        return {
            'mean': (mean_x, mean_y, mean_z),
            'std': (std_x, std_y, std_z),
            'range': (range_x, range_y, range_z),
            'jitter': (jitter_x, jitter_y, jitter_z),
            'samples': len(data)
        }
    
    def evaluate_stability(self, stats):
        """Evalúa si la estabilidad es aceptable"""
        if stats is None:
            return "INSUFICIENTES DATOS"
        
        std_x, std_y, std_z = stats['std']
        range_z = stats['range'][2]
        
        # Umbrales (en cm)
        EXCELLENT_STD_Z = 0.5   # < 0.5 cm std = Excelente
        GOOD_STD_Z = 1.0        # < 1.0 cm std = Bueno
        ACCEPTABLE_STD_Z = 2.0  # < 2.0 cm std = Aceptable
        
        EXCELLENT_RANGE_Z = 1.0  # < 1 cm rango = Excelente
        GOOD_RANGE_Z = 3.0       # < 3 cm rango = Bueno
        ACCEPTABLE_RANGE_Z = 5.0 # < 5 cm rango = Aceptable
        
        # Clasificar Z (el más crítico)
        if std_z < EXCELLENT_STD_Z and range_z < EXCELLENT_RANGE_Z:
            return "🟢 EXCELENTE"
        elif std_z < GOOD_STD_Z and range_z < GOOD_RANGE_Z:
            return "🟡 BUENO"
        elif std_z < ACCEPTABLE_STD_Z and range_z < ACCEPTABLE_RANGE_Z:
            return "🟠 ACEPTABLE"
        else:
            return "🔴 POBRE - Recalibrar recomendado"
    
    def run(self):
        """Loop principal"""
        cv2.namedWindow('Test Estabilidad')
        
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
                
                # Dedo índice (ID 8)
                lm_left = landmarks_left[8]
                lm_right = landmarks_right[8]
                
                # Convertir a coordenadas de imagen
                h, w = frame_left.shape[:2]
                point_left = (int(lm_left.x * w), int(lm_left.y * h))
                point_right = (int(lm_right.x * w), int(lm_right.y * h))
                
                # Rectificar puntos
                point_left_rect = self.depth_estimator.rectify_point(point_left, "left")
                point_right_rect = self.depth_estimator.rectify_point(point_right, "right")
                
                if point_left_rect and point_right_rect:
                    # Triangular
                    point_3d = self.depth_estimator.triangulate_point_DLT(
                        point_left_rect, point_right_rect
                    )
                    
                    if point_3d:
                        x, y, z = point_3d
                        
                        # Guardar si está grabando
                        if self.recording:
                            self.measurements[8].append([x, y, z])
                            self.frame_count += 1
                        
                        # Mostrar coordenadas actuales
                        cv2.putText(display, f"X: {x:.2f} cm", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(display, f"Y: {y:.2f} cm",
                                   (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(display, f"Z: {z:.2f} cm",
                                   (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Mostrar estado de grabación
            if self.recording:
                cv2.putText(display, f"🔴 GRABANDO ({self.frame_count} frames)",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(display, "⚪ Presiona ESPACIO para grabar",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            
            # Mostrar estadísticas si hay datos
            stats = self.calculate_statistics()
            if stats and stats['samples'] >= 10:
                y_offset = 150
                cv2.putText(display, f"=== ESTADISTICAS ({stats['samples']} muestras) ===",
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                y_offset += 25
                
                std_x, std_y, std_z = stats['std']
                cv2.putText(display, f"Std Dev: X={std_x:.2f} Y={std_y:.2f} Z={std_z:.2f} cm",
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 20
                
                range_x, range_y, range_z = stats['range']
                cv2.putText(display, f"Rango: X={range_x:.2f} Y={range_y:.2f} Z={range_z:.2f} cm",
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 20
                
                jitter_x, jitter_y, jitter_z = stats['jitter']
                cv2.putText(display, f"Jitter: X={jitter_x:.2f} Y={jitter_y:.2f} Z={jitter_z:.2f} cm",
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25
                
                # Evaluación
                evaluation = self.evaluate_stability(stats)
                cv2.putText(display, f"Calidad: {evaluation}",
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            cv2.imshow('Test Estabilidad', display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):  # ESPACIO
                self.recording = not self.recording
                if self.recording:
                    print("\n🔴 Iniciando grabación... mantén la mano QUIETA")
                    self.measurements[8].clear()
                    self.frame_count = 0
                else:
                    print("⚪ Grabación detenida")
                    self._print_detailed_stats()
            elif key == ord('r'):
                self.measurements[8].clear()
                self.frame_count = 0
                print("✓ Estadísticas reseteadas")
        
        self.cap_left.release()
        self.cap_right.release()
        cv2.destroyAllWindows()
    
    def _print_detailed_stats(self):
        """Imprime estadísticas detalladas en consola"""
        stats = self.calculate_statistics()
        if stats is None:
            return
        
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DETALLADAS")
        print("="*60)
        print(f"Muestras: {stats['samples']}")
        print(f"\nPosición promedio:")
        print(f"  X = {stats['mean'][0]:.2f} ± {stats['std'][0]:.2f} cm")
        print(f"  Y = {stats['mean'][1]:.2f} ± {stats['std'][1]:.2f} cm")
        print(f"  Z = {stats['mean'][2]:.2f} ± {stats['std'][2]:.2f} cm")
        print(f"\nRango (max - min):")
        print(f"  X: {stats['range'][0]:.2f} cm")
        print(f"  Y: {stats['range'][1]:.2f} cm")
        print(f"  Z: {stats['range'][2]:.2f} cm")
        print(f"\nJitter promedio (frame a frame):")
        print(f"  X: {stats['jitter'][0]:.2f} cm")
        print(f"  Y: {stats['jitter'][1]:.2f} cm")
        print(f"  Z: {stats['jitter'][2]:.2f} cm")
        print(f"\nEvaluación: {self.evaluate_stability(stats)}")
        print("="*60 + "\n")

if __name__ == "__main__":
    tester = StabilityTester()
    tester.run()

"""
Diagnóstico de Precisión de Profundidad
========================================
Mide objetos a distancias conocidas para calibrar factor de escala.

Uso:
1. Coloca un objeto plano (libro, caja) a distancias conocidas del sistema
2. Haz clic en el MISMO punto en ambas imágenes
3. El sistema reportará la profundidad estimada vs real
4. Calculará factor de corrección promedio
"""

import cv2
import numpy as np
import sys
import os

# Agregar directorio padre al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vision.depth_estimator import DepthEstimator

class DepthDiagnosticTool:
    def __init__(self):
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
        
        # Puntos seleccionados
        self.point_left = None
        self.point_right = None
        
        # Mediciones
        self.measurements = []  # [(distancia_real_cm, distancia_medida_cm), ...]
        
        print("\n" + "="*60)
        print("🔍 HERRAMIENTA DE DIAGNÓSTICO DE PROFUNDIDAD")
        print("="*60)
        print("\nInstrucciones:")
        print("1. Coloca un objeto a una distancia conocida")
        print("2. Haz clic en el MISMO punto en IZQUIERDA y luego DERECHA")
        print("3. Ingresa la distancia REAL en cm")
        print("4. Repite con 3-5 distancias diferentes (30-100 cm)")
        print("5. El sistema calculará el factor de corrección")
        print("\nControles:")
        print("  - Clic izquierdo: Seleccionar punto")
        print("  - 'c': Limpiar selección actual")
        print("  - 'q': Salir")
        print("="*60 + "\n")
    
    def mouse_callback_left(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.point_left = (x, y)
            print(f"✓ Punto IZQUIERDA seleccionado: ({x}, {y})")
    
    def mouse_callback_right(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.point_right = (x, y)
            print(f"✓ Punto DERECHA seleccionado: ({x}, {y})")
            
            # Si ambos puntos están seleccionados, triangular
            if self.point_left is not None:
                self.process_measurement()
    
    def process_measurement(self):
        """Procesa una medición completa"""
        # Rectificar puntos
        point_left_rect = self.depth_estimator.rectify_point(self.point_left, "left")
        point_right_rect = self.depth_estimator.rectify_point(self.point_right, "right")
        
        if point_left_rect is None or point_right_rect is None:
            print("❌ Error rectificando puntos")
            return
        
        # Triangular
        point_3d = self.depth_estimator.triangulate_point_DLT(
            point_left_rect, point_right_rect
        )
        
        if point_3d is None:
            print("❌ Error en triangulación")
            return
        
        x, y, z = point_3d
        
        print(f"\n📏 Medición:")
        print(f"   Punto 3D estimado: X={x:.2f} Y={y:.2f} Z={z:.2f} cm")
        print(f"   Disparidad: {point_left_rect[0] - point_right_rect[0]:.1f} px")
        
        # Pedir distancia real
        try:
            real_distance = float(input("\n➤ Ingresa la distancia REAL en cm: "))
            
            self.measurements.append((real_distance, z))
            
            error_cm = z - real_distance
            error_pct = (error_cm / real_distance) * 100
            
            print(f"   ✓ Distancia real: {real_distance:.2f} cm")
            print(f"   ✓ Error: {error_cm:+.2f} cm ({error_pct:+.1f}%)")
            
            # Calcular factor de corrección acumulado
            if len(self.measurements) >= 2:
                self._calculate_correction_factor()
            
            # Limpiar para siguiente medición
            self.point_left = None
            self.point_right = None
            print(f"\n✓ Medición {len(self.measurements)} guardada")
            print("   Haz clic en el siguiente punto o presiona 'q' para terminar\n")
            
        except ValueError:
            print("❌ Valor inválido, intenta de nuevo")
    
    def _calculate_correction_factor(self):
        """Calcula factor de corrección basado en todas las mediciones"""
        real_dists = np.array([m[0] for m in self.measurements])
        measured_dists = np.array([m[1] for m in self.measurements])
        
        # Regresión lineal: real = factor * measured
        # factor = sum(real * measured) / sum(measured^2)
        factor = np.sum(real_dists * measured_dists) / np.sum(measured_dists ** 2)
        
        # Error promedio
        corrected_dists = measured_dists * factor
        errors = corrected_dists - real_dists
        mae = np.mean(np.abs(errors))
        rmse = np.sqrt(np.mean(errors ** 2))
        
        print(f"\n{'='*60}")
        print(f"📊 ESTADÍSTICAS ({len(self.measurements)} mediciones):")
        print(f"{'='*60}")
        print(f"   Factor de corrección: {factor:.4f}")
        print(f"   Error absoluto medio: {mae:.2f} cm")
        print(f"   Error RMS: {rmse:.2f} cm")
        print(f"{'='*60}\n")
        
        # Mostrar tabla
        print("   Distancia Real | Medida | Corregida | Error")
        print("   " + "-"*50)
        for real, measured in self.measurements:
            corrected = measured * factor
            error = corrected - real
            print(f"   {real:6.1f} cm      | {measured:6.2f} | {corrected:6.2f}   | {error:+6.2f}")
        print()
    
    def run(self):
        """Loop principal"""
        cv2.namedWindow('Izquierda')
        cv2.namedWindow('Derecha')
        cv2.setMouseCallback('Izquierda', self.mouse_callback_left)
        cv2.setMouseCallback('Derecha', self.mouse_callback_right)
        
        while True:
            ret_left, frame_left = self.cap_left.read()
            ret_right, frame_right = self.cap_right.read()
            
            if not ret_left or not ret_right:
                print("❌ Error capturando frames")
                break
            
            # Dibujar puntos seleccionados
            display_left = frame_left.copy()
            display_right = frame_right.copy()
            
            if self.point_left is not None:
                cv2.circle(display_left, self.point_left, 8, (0, 255, 0), -1)
                cv2.putText(display_left, "SELECCIONADO", 
                           (self.point_left[0] + 15, self.point_left[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if self.point_right is not None:
                cv2.circle(display_right, self.point_right, 8, (0, 255, 0), -1)
                cv2.putText(display_right, "SELECCIONADO",
                           (self.point_right[0] + 15, self.point_right[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Mostrar número de mediciones
            cv2.putText(display_left, f"Mediciones: {len(self.measurements)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Izquierda', display_left)
            cv2.imshow('Derecha', display_right)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.point_left = None
                self.point_right = None
                print("✓ Selección limpiada")
        
        # Resumen final
        if len(self.measurements) >= 2:
            print("\n" + "="*60)
            print("📝 RESUMEN FINAL")
            print("="*60)
            self._calculate_correction_factor()
            
            # Guardar en archivo
            with open('depth_correction_factor.txt', 'w') as f:
                real_dists = np.array([m[0] for m in self.measurements])
                measured_dists = np.array([m[1] for m in self.measurements])
                factor = np.sum(real_dists * measured_dists) / np.sum(measured_dists ** 2)
                
                f.write(f"DEPTH_CORRECTION_FACTOR = {factor:.6f}\n")
                f.write(f"# Basado en {len(self.measurements)} mediciones\n")
                f.write(f"# Aplicar como: Z_corregido = Z_medido * {factor:.6f}\n")
            
            print(f"✓ Factor guardado en 'depth_correction_factor.txt'")
            print(f"  Úsalo en tu código: Z_corregido = Z_medido * {factor:.6f}\n")
        
        self.cap_left.release()
        self.cap_right.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    tool = DepthDiagnosticTool()
    tool.run()

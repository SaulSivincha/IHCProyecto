"""
Verificación de Factor de Corrección
=====================================
Script simple para verificar que el factor de corrección se está aplicando
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vision.depth_estimator import DepthEstimator

# Cargar estimador
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
calibration_path = os.path.join(project_root, 'camcalibration', 'calibration.json')

estimator = DepthEstimator(calibration_path)

print("\n" + "="*60)
print("🔍 VERIFICACIÓN DE CONFIGURACIÓN")
print("="*60)
print(f"\nFactor de corrección: {estimator.DEPTH_CORRECTION_FACTOR}")
print(f"Suavizado activado: {estimator.smoothing_enabled}")
print(f"Ventana de suavizado: {estimator.smoothing_window}")

# Test de triangulación
print("\n" + "="*60)
print("🧪 TEST DE TRIANGULACIÓN")
print("="*60)

# Simular dos puntos con disparidad conocida
point_left = (320.0, 240.0)  # Centro
point_right = (270.0, 240.0)  # Desplazado 50px (disparidad = 50)

result = estimator.triangulate_point_DLT(point_left, point_right)

if result:
    x, y, z = result
    print(f"\nPunto izquierdo: {point_left}")
    print(f"Punto derecho: {point_right}")
    print(f"Disparidad: {point_left[0] - point_right[0]:.1f} px")
    print(f"\nResultado:")
    print(f"  X = {x:.2f} cm")
    print(f"  Y = {y:.2f} cm")
    print(f"  Z = {z:.2f} cm (CON CORRECCIÓN 0.74)")
    print(f"\n⚠️ Si Z > 50 cm, el factor NO se está aplicando correctamente")
    print(f"✅ Si Z ≈ 30-40 cm, el factor SÍ se está aplicando")
else:
    print("❌ Error en triangulación")

print("\n" + "="*60)

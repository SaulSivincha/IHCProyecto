#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar triangulación DLT vs método Q
"""

import sys
from pathlib import Path
from src.vision.depth_estimator import DepthEstimator

def test_triangulation_methods():
    """Compara los dos métodos de triangulación"""
    
    # Cargar calibración
    calib_file = Path('camcalibration/calibration.json')
    
    if not calib_file.exists():
        print("❌ No se encontró calibration.json")
        print("   Ejecuta la calibración completa primero")
        return
    
    try:
        estimator = DepthEstimator(calib_file)
        print("\n" + "="*70)
        print("COMPARACIÓN DE MÉTODOS DE TRIANGULACIÓN")
        print("="*70)
        
        # Puntos de prueba en imágenes rectificadas
        # Estos son coordenadas de ejemplo - deberías usar puntos reales de tus dedos
        test_points = [
            ((320, 240), (280, 240)),  # Centro de imagen con disparidad 40px
            ((400, 300), (350, 300)),  # Punto desplazado con disparidad 50px
            ((200, 200), (170, 200)),  # Esquina con disparidad 30px
        ]
        
        print("\nPrueba con puntos de ejemplo:")
        print("-" * 70)
        
        for i, (pt_left, pt_right) in enumerate(test_points, 1):
            print(f"\nPunto {i}:")
            print(f"  Izquierda: {pt_left}")
            print(f"  Derecha:   {pt_right}")
            print(f"  Disparidad: {pt_left[0] - pt_right[0]}px")
            
            # Método DLT (nuevo)
            result_dlt = estimator.triangulate_point(pt_left, pt_right, method='DLT')
            
            # Método Q (original)
            result_q = estimator.triangulate_point(pt_left, pt_right, method='Q')
            
            print("\n  Método DLT:")
            if result_dlt:
                print(f"    X: {result_dlt[0]:7.2f} cm")
                print(f"    Y: {result_dlt[1]:7.2f} cm")
                print(f"    Z: {result_dlt[2]:7.2f} cm (profundidad)")
            else:
                print("    ❌ Falló")
            
            print("\n  Método Q (original):")
            if result_q:
                print(f"    X: {result_q[0]:7.2f} cm")
                print(f"    Y: {result_q[1]:7.2f} cm")
                print(f"    Z: {result_q[2]:7.2f} cm (profundidad)")
            else:
                print("    ❌ Falló")
            
            # Comparar resultados
            if result_dlt and result_q:
                diff_x = abs(result_dlt[0] - result_q[0])
                diff_y = abs(result_dlt[1] - result_q[1])
                diff_z = abs(result_dlt[2] - result_q[2])
                print("\n  Diferencia entre métodos:")
                print(f"    ΔX: {diff_x:.2f} cm")
                print(f"    ΔY: {diff_y:.2f} cm")
                print(f"    ΔZ: {diff_z:.2f} cm")
        
        print("\n" + "="*70)
        print("✓ Prueba completada")
        print("\n💡 Usa method='DLT' en triangulate_point() para mejor precisión")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_triangulation_methods()

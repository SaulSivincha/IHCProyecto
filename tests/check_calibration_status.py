#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el estado de la calibración estéreo
Muestra información detallada de Fase 1, Fase 2 y Fase 3
"""

import json
from pathlib import Path
import numpy as np


def check_calibration():
    """Verifica y muestra el estado de la calibración"""
    
    # Buscar el archivo en diferentes ubicaciones posibles
    possible_paths = [
        Path('camcalibration/calibration.json'),
        Path('../camcalibration/calibration.json'),
        Path(__file__).parent.parent / 'camcalibration' / 'calibration.json'
    ]
    
    calib_file = None
    for path in possible_paths:
        if path.exists():
            calib_file = path
            break
    
    if calib_file is None:
        print("❌ No se encontró archivo de calibración: camcalibration/calibration.json")
        print("   Ejecuta la calibración completa primero: python -m src.main")
        return
    
    try:
        with open(calib_file, 'r') as f:
            data = json.load(f)
        
        print("\n" + "="*70)
        print("ESTADO DE CALIBRACIÓN ESTÉREO")
        print("="*70)
        
        # Información general
        version = data.get('version', 'N/A')
        print(f"\nVersión: {version}")
        
        # Configuración del tablero
        if 'board_config' in data:
            board = data['board_config']
            print(f"\nTablero de calibración:")
            print(f"  Tamaño: {board['rows']+1}x{board['cols']+1} cuadrados")
            print(f"  Esquinas: {board['rows']}x{board['cols']}")
            print(f"  Tamaño cuadrado: {board['square_size_mm']} mm")
        
        # FASE 1: Calibración individual
        print("\n" + "-"*70)
        print("FASE 1: CALIBRACIÓN INDIVIDUAL DE CÁMARAS")
        print("-"*70)
        
        has_phase1 = False
        if 'left_camera' in data and 'camera_matrix' in data['left_camera']:
            left = data['left_camera']
            print(f"\n✓ Cámara Izquierda:")
            print(f"  Error de reproyección: {left['reprojection_error']:.6f} px")
            print(f"  Imágenes usadas: {left['num_images']}")
            print(f"  Resolución: {left['image_width']}x{left['image_height']}")
            
            K_left = np.array(left['camera_matrix'])
            print(f"  Matriz intrínseca K:")
            print(f"    fx: {K_left[0,0]:.2f}")
            print(f"    fy: {K_left[1,1]:.2f}")
            print(f"    cx: {K_left[0,2]:.2f}")
            print(f"    cy: {K_left[1,2]:.2f}")
            has_phase1 = True
        else:
            print("\n❌ Cámara Izquierda: NO CALIBRADA")
        
        if 'right_camera' in data and 'camera_matrix' in data['right_camera']:
            right = data['right_camera']
            print(f"\n✓ Cámara Derecha:")
            print(f"  Error de reproyección: {right['reprojection_error']:.6f} px")
            print(f"  Imágenes usadas: {right['num_images']}")
            print(f"  Resolución: {right['image_width']}x{right['image_height']}")
            
            K_right = np.array(right['camera_matrix'])
            print(f"  Matriz intrínseca K:")
            print(f"    fx: {K_right[0,0]:.2f}")
            print(f"    fy: {K_right[1,1]:.2f}")
            print(f"    cx: {K_right[0,2]:.2f}")
            print(f"    cy: {K_right[1,2]:.2f}")
        else:
            print("\n❌ Cámara Derecha: NO CALIBRADA")
            has_phase1 = False
        
        # FASE 2: Calibración estéreo
        print("\n" + "-"*70)
        print("FASE 2: CALIBRACIÓN ESTÉREO")
        print("-"*70)
        
        has_phase2 = False
        if 'stereo' in data and data['stereo'] is not None:
            stereo = data['stereo']
            
            print(f"\n✓ Calibración Estéreo COMPLETA:")
            print(f"  Baseline (separación cámaras): {stereo['baseline_cm']:.2f} cm")
            print(f"  Error RMS estéreo: {stereo['rms_error']:.6f}")
            print(f"  Pares capturados: {stereo['num_pairs']}")
            
            # Matriz de rotación
            R = np.array(stereo['rotation_matrix'])
            print(f"\n  Matriz de Rotación R:")
            for row in R:
                print(f"    [{row[0]:8.5f} {row[1]:8.5f} {row[2]:8.5f}]")
            
            # Vector de traslación
            T = np.array(stereo['translation_vector'])
            print(f"\n  Vector de Traslación T (metros):")
            print(f"    X: {T[0][0]:.6f} m ({T[0][0]*100:.2f} cm)")
            print(f"    Y: {T[1][0]:.6f} m ({T[1][0]*100:.2f} cm)")
            print(f"    Z: {T[2][0]:.6f} m ({T[2][0]*100:.2f} cm)")
            
            # Rectificación
            if 'rectification' in stereo:
                print(f"\n  ✓ Parámetros de rectificación disponibles")
                rect = stereo['rectification']
                Q = np.array(rect['Q'])
                print(f"\n  Matriz de reproyección Q:")
                for row in Q:
                    print(f"    [{row[0]:10.4f} {row[1]:10.4f} {row[2]:10.4f} {row[3]:10.4f}]")
                has_phase2 = True
            else:
                print(f"\n  ⚠️  Faltan parámetros de rectificación")
        else:
            print("\n❌ Calibración Estéreo: NO COMPLETADA")
            print("   Ejecuta Fase 2: python -m src.main → [S]")
        
        # FASE 3: Calibración de profundidad
        print("\n" + "-"*70)
        print("FASE 3: CALIBRACIÓN DE PROFUNDIDAD")
        print("-"*70)
        
        has_phase3 = False
        if 'depth_correction' in data and data['depth_correction'] is not None:
            depth = data['depth_correction']
            
            print(f"\n✓ Calibración de Profundidad COMPLETA:")
            print(f"  Factor de corrección: {depth['factor']:.4f}")
            print(f"  Mediciones realizadas: {depth['num_samples']}")
            
            if 'measurements' in depth and len(depth['measurements']) > 0:
                print(f"\n  Mediciones detalladas:")
                for i, (real_cm, measured_cm) in enumerate(depth['measurements'], 1):
                    error_cm = abs(real_cm - (measured_cm * depth['factor']))
                    error_pct = (error_cm / real_cm) * 100
                    print(f"    {i}. Real: {real_cm:.1f} cm | Medido: {measured_cm:.1f} cm | "
                          f"Corregido: {measured_cm * depth['factor']:.1f} cm | "
                          f"Error: {error_cm:.1f} cm ({error_pct:.1f}%)")
                
                # Estadísticas
                errors = [abs(real - (measured * depth['factor'])) 
                         for real, measured in depth['measurements']]
                avg_error = np.mean(errors)
                max_error = np.max(errors)
                print(f"\n  Estadísticas de error:")
                print(f"    Promedio: {avg_error:.2f} cm")
                print(f"    Máximo: {max_error:.2f} cm")
            
            has_phase3 = True
        else:
            print("\n❌ Calibración de Profundidad: NO COMPLETADA")
            print("   Se usará factor por defecto (0.74)")
            print("   Para mejor precisión, ejecuta: python -m src.main → [P]")
        
        # IDs de cámaras
        if 'camera_ids' in data:
            ids = data['camera_ids']
            print(f"\n" + "-"*70)
            print("IDs de Cámaras:")
            print(f"  Izquierda: {ids['left']}")
            print(f"  Derecha: {ids['right']}")
        
        # Resolución configurada
        if 'resolution' in data:
            res = data['resolution']
            print(f"\nResolución configurada: {res['width']}x{res['height']}")
        
        # RESUMEN FINAL
        print("\n" + "="*70)
        print("RESUMEN")
        print("="*70)
        
        if has_phase1 and has_phase2 and has_phase3:
            print("\n✅ CALIBRACIÓN 100% COMPLETA")
            print("   Fase 1: ✓ Cámaras individuales calibradas")
            print("   Fase 2: ✓ Calibración estéreo completada")
            print("   Fase 3: ✓ Factor de corrección de profundidad calculado")
            print("\n   🎯 Sistema completamente optimizado para detección 3D")
        elif has_phase1 and has_phase2:
            print("\n⚠️  CALIBRACIÓN FUNCIONAL (falta optimización)")
            print("   Fase 1: ✓ Cámaras individuales calibradas")
            print("   Fase 2: ✓ Calibración estéreo completada")
            print("   Fase 3: ❌ Falta calibración de profundidad")
            print("\n   📝 Para mayor precisión: python -m src.main → [P]")
            print("   ℹ️  Sistema funcionará con factor por defecto (0.74)")
        elif has_phase1:
            print("\n⚠️  CALIBRACIÓN INCOMPLETA")
            print("   Fase 1: ✓ Cámaras individuales calibradas")
            print("   Fase 2: ❌ Falta calibración estéreo")
            print("   Fase 3: ❌ Falta calibración de profundidad")
            print("\n   📝 Ejecuta: python -m src.main → [S]")
        else:
            print("\n❌ CALIBRACIÓN NO INICIADA")
            print("\n   📝 Ejecuta calibración completa: python -m src.main")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error al leer calibración: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_calibration()

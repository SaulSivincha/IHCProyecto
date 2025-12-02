#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el estado de la calibración
"""

import json
from pathlib import Path

calibration_file = Path("camcalibration/calibration.json")

print("\n" + "="*70)
print("VERIFICACIÓN DE ESTADO DE CALIBRACIÓN")
print("="*70 + "\n")

if not calibration_file.exists():
    print("❌ NO EXISTE archivo de calibración")
    print(f"   Ruta esperada: {calibration_file.absolute()}")
    print("\n💡 Solución: Ejecuta calibración completa")
    print("   python src/main.py → Opción 2: Nueva calibración")
    exit(1)

with open(calibration_file, 'r') as f:
    data = json.load(f)

# Verificar Fase 1
has_left = 'left_camera' in data and 'camera_matrix' in data['left_camera']
has_right = 'right_camera' in data and 'camera_matrix' in data['right_camera']

print("📋 FASE 1 - Calibración Individual:")
if has_left:
    print(f"   ✅ Cámara Izquierda:  Error {data['left_camera']['reprojection_error']:.6f} px")
else:
    print("   ❌ Cámara Izquierda:  NO calibrada")

if has_right:
    print(f"   ✅ Cámara Derecha:    Error {data['right_camera']['reprojection_error']:.6f} px")
else:
    print("   ❌ Cámara Derecha:    NO calibrada")

# Verificar Fase 2
print("\n📋 FASE 2 - Calibración Estéreo:")
has_stereo = 'stereo' in data and data['stereo'] is not None

if has_stereo:
    stereo = data['stereo']
    has_rectification = 'rectification' in stereo
    
    print(f"   ✅ Calibración Estéreo: COMPLETA")
    print(f"      - Baseline:      {stereo.get('baseline_cm', 'N/A')} cm")
    print(f"      - Error RMS:     {stereo.get('rms_error', 'N/A')}")
    print(f"      - Pares:         {stereo.get('num_pairs', 'N/A')}")
    
    if has_rectification:
        print(f"   ✅ Rectificación:       DISPONIBLE")
        print(f"      - Matriz Q guardada")
        print(f"      - Mapas de rectificación listos")
    else:
        print(f"   ⚠️  Rectificación:       NO DISPONIBLE")
        print(f"      - Calibración antigua (sin rectificación)")
        print(f"      💡 Re-calibra Fase 2 para agregar rectificación")
else:
    print(f"   ❌ Calibración Estéreo: INCOMPLETA")
    print(f"      - Archivo muestra: stereo = null")
    print(f"      - Solo se completó Fase 1")

# Resumen final
print("\n" + "="*70)
if has_left and has_right and has_stereo and has_rectification:
    print("✅ SISTEMA COMPLETO - Listo para usar DepthEstimator")
    print("="*70)
    print("\n🎹 Puedes ejecutar el piano con:")
    print("   python src/main.py")
    print("\n📊 Para verificar funcionamiento:")
    print("   python test_depth_estimator.py")
elif has_left and has_right and not has_stereo:
    print("⚠️  FASE 1 COMPLETA - Falta Fase 2")
    print("="*70)
    print("\n💡 Para completar calibración:")
    print("   python src/main.py")
    print("   → Opción 1: Usar calibración guardada")
    print("   → Presiona [S] para recalibrar SOLO Fase 2")
    print("   → Captura 15 pares con líneas rosadas ALINEADAS")
    print("   → Presiona ENTER en pantalla de estadísticas")
elif has_left and has_right and has_stereo and not has_rectification:
    print("⚠️  CALIBRACIÓN COMPLETA - Falta rectificación")
    print("="*70)
    print("\n💡 Para agregar rectificación:")
    print("   python src/main.py")
    print("   → Opción 1: Usar calibración guardada")
    print("   → Presiona [S] para recalibrar SOLO Fase 2")
else:
    print("❌ CALIBRACIÓN INCOMPLETA")
    print("="*70)
    print("\n💡 Ejecuta calibración completa:")
    print("   python src/main.py")
    print("   → Opción 2: Nueva calibración")

print("="*70 + "\n")

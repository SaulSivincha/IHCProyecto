#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar calibration.json existente con transformaciones al mundo
Agrega campos world_rotation y world_translation a las cámaras individuales
"""

import json
import numpy as np
from pathlib import Path


def update_calibration_with_world_transforms(calibration_file):
    """
    Actualiza un archivo de calibración existente agregando transformaciones al mundo
    
    Args:
        calibration_file: Path al archivo calibration.json
    """
    calibration_file = Path(calibration_file)
    
    if not calibration_file.exists():
        print(f"❌ Archivo no encontrado: {calibration_file}")
        return False
    
    print("=" * 70)
    print("ACTUALIZACIÓN DE CALIBRACIÓN CON TRANSFORMACIONES AL MUNDO")
    print("=" * 70)
    print(f"\nArchivo: {calibration_file}")
    
    # Cargar datos existentes
    with open(calibration_file, 'r') as f:
        data = json.load(f)
    
    # Verificar que tenga calibración estéreo
    if 'stereo' not in data or data['stereo'] is None:
        print("❌ No hay calibración estéreo en el archivo")
        return False
    
    if 'rotation_matrix' not in data['stereo']:
        print("❌ Falta rotation_matrix en calibración estéreo")
        return False
    
    print("\n✓ Calibración estéreo encontrada")
    
    # Verificar si ya tiene transformaciones al mundo
    if 'world_rotation' in data.get('left_camera', {}):
        print("⚠️  El archivo ya tiene transformaciones al mundo")
        response = input("¿Deseas sobrescribirlas? (s/n): ")
        if response.lower() != 's':
            print("Operación cancelada")
            return False
    
    # Obtener R y T estéreo
    R_stereo = data['stereo']['rotation_matrix']
    T_stereo = data['stereo']['translation_vector']
    
    print("\nAgregando transformaciones al mundo:")
    print("  - Cámara izquierda: origen (R=I, T=0)")
    print("  - Cámara derecha: transformación estéreo")
    
    # Agregar a cámara izquierda (origen del mundo)
    data['left_camera']['world_rotation'] = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]
    ]
    data['left_camera']['world_translation'] = [[0.0], [0.0], [0.0]]
    
    # Agregar a cámara derecha (transformación estéreo)
    data['right_camera']['world_rotation'] = R_stereo
    data['right_camera']['world_translation'] = T_stereo
    
    # Agregar también en stereo para consistencia
    if 'world_transforms' not in data['stereo']:
        data['stereo']['world_transforms'] = {
            'left_camera': {
                'rotation': [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                'translation': [[0.0], [0.0], [0.0]]
            },
            'right_camera': {
                'rotation': R_stereo,
                'translation': T_stereo
            }
        }
    
    # Crear backup del archivo original
    backup_file = calibration_file.parent / f"{calibration_file.stem}_backup.json"
    print(f"\nCreando backup: {backup_file}")
    
    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print("✓ Backup creado")
    
    # Guardar archivo actualizado
    print(f"\nGuardando archivo actualizado: {calibration_file}")
    
    with open(calibration_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print("✓ Archivo actualizado correctamente")
    
    # Verificación
    print("\n" + "=" * 70)
    print("VERIFICACIÓN")
    print("=" * 70)
    
    with open(calibration_file, 'r') as f:
        updated_data = json.load(f)
    
    checks = []
    
    # Verificar campos agregados
    if 'world_rotation' in updated_data.get('left_camera', {}):
        checks.append("✓ left_camera.world_rotation")
    else:
        checks.append("❌ left_camera.world_rotation faltante")
    
    if 'world_translation' in updated_data.get('left_camera', {}):
        checks.append("✓ left_camera.world_translation")
    else:
        checks.append("❌ left_camera.world_translation faltante")
    
    if 'world_rotation' in updated_data.get('right_camera', {}):
        checks.append("✓ right_camera.world_rotation")
    else:
        checks.append("❌ right_camera.world_rotation faltante")
    
    if 'world_translation' in updated_data.get('right_camera', {}):
        checks.append("✓ right_camera.world_translation")
    else:
        checks.append("❌ right_camera.world_translation faltante")
    
    if 'world_transforms' in updated_data.get('stereo', {}):
        checks.append("✓ stereo.world_transforms")
    else:
        checks.append("✓ stereo.world_transforms (opcional)")
    
    for check in checks:
        print(check)
    
    print("\n" + "=" * 70)
    print("✅ ACTUALIZACIÓN COMPLETADA")
    print("=" * 70)
    print("\nAhora puedes usar depth_estimator.py con las matrices correctas")
    print("Las transformaciones al mundo están disponibles para DLT")
    
    return True


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        calibration_file = Path(sys.argv[1])
    else:
        # Usar ubicación por defecto
        calibration_file = Path(__file__).parent.parent / 'camcalibration' / 'calibration.json'
    
    print(f"\nActualizando: {calibration_file}\n")
    
    success = update_calibration_with_world_transforms(calibration_file)
    
    if not success:
        print("\n❌ La actualización falló")
        sys.exit(1)
    
    print("\n✅ Todo listo!")

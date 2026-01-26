import sys
import os
import json
import numpy as np

# Asegurar que podemos importar los módulos de src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.vision.depth_estimator import DepthEstimator

def color_print(text, color="white"):
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def run_diagnostic():
    print("\n" + "="*60)
    print(" 🕵️‍♂️  DIAGNÓSTICO DE LÓGICA DEL TECLADO VIRTUAL")
    print("="*60 + "\n")

    # 1. VERIFICAR ARCHIVO DE CALIBRACIÓN
    calib_file = "camcalibration/calibration.json"
    if not os.path.exists(calib_file):
        color_print(f"[ERROR CRÍTICO] No se encuentra {calib_file}", "red")
        return

    try:
        with open(calib_file, 'r') as f:
            data = json.load(f)
        color_print(f"[OK] Archivo JSON cargado correctamente.", "green")
    except Exception as e:
        color_print(f"[ERROR] JSON corrupto: {e}", "red")
        return

    # 2. VERIFICAR PARÁMETROS DE CORRECCIÓN (FASE 3)
    print("\n--- Analizando Fase 3 (Profundidad) ---")
    depth_data = data.get('depth_correction', {})
    method = depth_data.get('method', 'Desconocido')
    
    slope = depth_data.get('slope', 1.0)
    intercept = depth_data.get('intercept', 0.0)
    
    print(f"Método guardado: {method}")
    print(f"Fórmula: Real = ({slope:.4f} * Medido) + {intercept:.4f}")

    if method != 'linear_regression':
        color_print(f"[ADVERTENCIA] No estás usando 'linear_regression'. El método actual es '{method}'.", "yellow")
        if slope == 1.0 and intercept == 0.0:
            color_print("[PELIGRO] Los valores son por defecto (1.0, 0.0). ¿Hiciste la Fase 3?", "red")
    else:
        color_print("[OK] Configuración de regresión lineal detectada.", "green")

    # 3. PRUEBA DE LÓGICA DE DEPTH_ESTIMATOR
    print("\n--- Probando DepthEstimator en Runtime ---")
    try:
        estimator = DepthEstimator(calib_file)
        
        # Simular una medición cruda (ej: el sistema mide 48cm)
        raw_depth_simulated = 48.0 
        corrected_depth = estimator.apply_depth_correction(raw_depth_simulated)
        
        print(f"Simulación:")
        print(f"  Entrada (Cámara ve): {raw_depth_simulated} cm")
        print(f"  Salida (Juego ve):   {corrected_depth:.4f} cm")
        
        diff = corrected_depth - raw_depth_simulated
        print(f"  Diferencia aplicada: {diff:.4f} cm")

        # Verificar si la corrección tiene sentido
        if abs(diff) < 0.1 and method == 'linear_regression':
            color_print("[SOSPECHOSO] La corrección es casi nula a pesar de usar regresión.", "yellow")
        elif corrected_depth < 0:
            color_print("[ERROR] La corrección generó una profundidad negativa.", "red")
        else:
            color_print("[OK] La matemática se está aplicando correctamente.", "green")

    except Exception as e:
        color_print(f"[FALLO] Error al inicializar DepthEstimator: {e}", "red")

    # 4. VERIFICAR DEFINICIÓN DEL TECLADO (FASE 4)
    print("\n--- Analizando Definición del Teclado (Fase 4) ---")
    table_def = data.get('table_definition', {})
    
    if not table_def:
        color_print("[ERROR FATAL] No hay definición de teclado ('table_definition').", "red")
        color_print("SOLUCIÓN: Ejecuta la Fase 4 (Definir Esquinas) en la calibración.", "yellow")
    else:
        corners = table_def.get('corners', [])
        depths = table_def.get('corner_depths', [])
        
        print(f"Esquinas 2D detectadas: {len(corners)}")
        print(f"Profundidades guardadas: {depths}")
        
        if not depths:
            color_print("[ERROR] Tienes esquinas 2D pero NO profundidades 3D.", "red")
            color_print("  El sistema no sabe a qué altura está la mesa.", "yellow")
        else:
            avg_table_depth = sum(depths) / len(depths)
            print(f"Altura promedio de la mesa: {avg_table_depth:.2f} cm")
            
            # Comparación crítica
            margin = 2.0 # cm de margen para tocar
            print(f"\n[ANÁLISIS DE JUGABILIDAD]")
            print(f"Si tu mano está en {corrected_depth:.2f} cm...")
            print(f"La mesa está en   {avg_table_depth:.2f} cm...")
            
            dist = corrected_depth - avg_table_depth
            print(f"Distancia Relativa: {dist:.2f} cm")
            
            if dist > margin:
                color_print("  -> DEDO EN EL AIRE (No tocaría)", "yellow")
            elif dist < -margin:
                color_print("  -> DEDO ATRAVESANDO MESA (Touch fuerte)", "green")
            else:
                color_print("  -> DEDO TOCANDO (Touch suave)", "green")

if __name__ == "__main__":
    run_diagnostic()
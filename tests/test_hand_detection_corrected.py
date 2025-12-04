#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rápido de detección de manos con las correcciones de matrices de proyección
Verifica que las coordenadas 3D tengan sentido después de las correcciones
"""

import sys
from pathlib import Path
import cv2
import mediapipe as mp
import numpy as np

# Configurar paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.vision.depth_estimator import DepthEstimator
from src.vision.hand_detector import HandDetector


def test_hand_detection_with_corrected_matrices():
    """
    Test de detección de manos usando las matrices de proyección corregidas
    """
    print("=" * 70)
    print("TEST: Detección de Manos con Matrices Corregidas")
    print("=" * 70)
    print()
    
    # Verificar calibración
    calibration_file = project_root / 'camcalibration' / 'calibration.json'
    
    if not calibration_file.exists():
        print("❌ No se encontró calibration.json")
        print(f"   Esperado en: {calibration_file}")
        return False
    
    print("✅ Calibración encontrada")
    
    # Cargar estimador de profundidad
    try:
        depth_estimator = DepthEstimator(calibration_file)
        print(f"✅ Depth Estimator cargado")
        print(f"   Baseline: {depth_estimator.baseline_cm:.2f} cm")
        print(f"   Resolución: {depth_estimator.image_size}")
        print()
    except Exception as e:
        print(f"❌ Error al cargar Depth Estimator: {e}")
        return False
    
    # Obtener dimensiones para el detector de manos
    width, height = depth_estimator.image_size
    
    # Inicializar detector de manos
    try:
        hand_detector = HandDetector(
            staticImageMode=False,
            maxHands=2,
            detectionCon=0.5,
            trackCon=0.5,
            img_width=width,
            img_height=height
        )
        print("✅ Hand Detector inicializado")
        print()
    except Exception as e:
        print(f"❌ Error al inicializar Hand Detector: {e}")
        return False
    
    # Abrir cámaras (usando los mismos IDs que main.py)
    # LEFT_CAMERA_SOURCE = 2, RIGHT_CAMERA_SOURCE = 1 (según stereo_config.py)
    print("Abriendo cámaras...")
    print("  Cámara izquierda: ID 2")
    print("  Cámara derecha: ID 1")
    cap_left = cv2.VideoCapture(2, cv2.CAP_DSHOW)
    cap_right = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    
    if not cap_left.isOpened() or not cap_right.isOpened():
        print("❌ No se pudieron abrir las cámaras")
        return False
    
    # Configurar resolución
    cap_left.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap_left.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap_right.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap_right.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    print(f"✅ Cámaras abiertas: {width}x{height}")
    print()
    print("=" * 70)
    print("INSTRUCCIONES:")
    print("=" * 70)
    print("1. Pon tu mano frente a las cámaras")
    print("2. Observa las coordenadas 3D en la consola")
    print("3. Verifica que:")
    print("   - X y Y estén cerca de 0 cuando la mano está centrada")
    print("   - Z esté entre 30-100 cm cuando tocas el teclado")
    print("   - Los valores cambien suavemente al mover la mano")
    print()
    print("Presiona 'q' para salir")
    print("=" * 70)
    print()
    
    frame_count = 0
    
    try:
        while True:
            ret_left, frame_left = cap_left.read()
            ret_right, frame_right = cap_right.read()
            
            if not ret_left or not ret_right:
                print("❌ Error al capturar frames")
                break
            
            frame_count += 1
            
            # Rectificar imágenes (rectifica ambas a la vez)
            rect_left, rect_right = depth_estimator.rectify_images(frame_left, frame_right)
            
            # Detectar manos en imagen izquierda
            found_left = hand_detector.findHands(rect_left)
            
            # Si hay manos detectadas
            if found_left and hand_detector.results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(hand_detector.results.multi_hand_landmarks):
                    # Tomar punto del dedo índice (landmark 8)
                    index_finger_tip = hand_landmarks.landmark[8]
                    
                    # Convertir a coordenadas de píxeles
                    h, w, _ = rect_left.shape
                    x_left = int(index_finger_tip.x * w)
                    y_left = int(index_finger_tip.y * h)
                    
                    # Buscar el mismo punto en imagen derecha
                    found_right = hand_detector.findHands(rect_right)
                    
                    if found_right and hand_detector.results.multi_hand_landmarks:
                        if len(hand_detector.results.multi_hand_landmarks) > hand_idx:
                            hand_landmarks_right = hand_detector.results.multi_hand_landmarks[hand_idx]
                            index_finger_tip_right = hand_landmarks_right.landmark[8]
                            
                            x_right = int(index_finger_tip_right.x * w)
                            y_right = int(index_finger_tip_right.y * h)
                            
                            # Triangular punto 3D usando DLT CORREGIDO
                            result_3d = depth_estimator.triangulate_point(
                                (x_left, y_left),
                                (x_right, y_right),
                                method='DLT'
                            )
                            
                            if result_3d is not None:
                                X, Y, Z = result_3d
                                disparidad = x_left - x_right
                                
                                # Mostrar información solo cada 10 frames
                                if frame_count % 10 == 0:
                                    print(f"✅ Dedo índice detectado:")
                                    print(f"   Left: ({x_left}, {y_left})")
                                    print(f"   Right: ({x_right}, {y_right})")
                                    print(f"   Disparidad: {disparidad} px")
                                    print(f"   3D: X={X:6.1f} Y={Y:6.1f} Z={Z:6.1f} cm")
                                    
                                    # Validar rangos razonables
                                    if -50 < X < 50 and -50 < Y < 50 and 10 < Z < 200:
                                        print(f"   ✅ Coordenadas parecen razonables")
                                    else:
                                        print(f"   ⚠️  Coordenadas fuera de rango esperado")
                                    print()
                                
                                # Dibujar en la imagen
                                cv2.circle(rect_left, (x_left, y_left), 5, (0, 255, 0), -1)
                                cv2.circle(rect_right, (x_right, y_right), 5, (0, 255, 0), -1)
                                
                                # Mostrar coordenadas en la imagen
                                text = f"Z: {Z:.1f}cm"
                                cv2.putText(rect_left, text, (x_left + 10, y_left - 10),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Mostrar imágenes
            combined = np.hstack([rect_left, rect_right])
            cv2.imshow('Test Detección - Izquierda | Derecha (q para salir)', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n✅ Test finalizado por el usuario")
                break
    
    except KeyboardInterrupt:
        print("\n✅ Test interrumpido por el usuario")
    
    except Exception as e:
        print(f"\n❌ Error durante el test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cap_left.release()
        cap_right.release()
        cv2.destroyAllWindows()
        print("\n✅ Recursos liberados")
    
    return True


if __name__ == '__main__':
    print("\n🚀 Iniciando test de detección con matrices corregidas...\n")
    test_hand_detection_with_corrected_matrices()

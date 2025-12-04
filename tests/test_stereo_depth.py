#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test y Calibración de Visión Estereoscópica
Herramienta interactiva para diagnosticar y ajustar parámetros de profundidad

Uso: python -m src.vision.test_stereo_depth
"""

import time
import cv2
import numpy as np
from src.vision import video_thread, angles
from src.vision.hand_detector import HandDetector
from src.vision.stereo_config import StereoConfig


def test_stereo_depth():
    """Test interactivo de visión estereoscópica con visualización de profundidad"""
    
    config = StereoConfig()
    
    print("\n" + "="*70)
    print("HERRAMIENTA DE TEST - VISIÓN ESTEREOSCÓPICA Y PROFUNDIDAD 3D")
    print("="*70)
    print(f"\nConfiguración cargada:")
    print(f"  Cámara izquierda: {config.LEFT_CAMERA_SOURCE}")
    print(f"  Cámara derecha: {config.RIGHT_CAMERA_SOURCE}")
    print(f"  Resolución: {config.PIXEL_WIDTH}x{config.PIXEL_HEIGHT}")
    print(f"  FPS: {config.FRAME_RATE}")
    print(f"  Separación cámaras: {config.CAMERA_SEPARATION} cm")
    print(f"  Distancia teclado: {config.VKB_CENTER_DISTANCE} cm")
    print(f"  Umbral de profundidad: {config.DEPTH_THRESHOLD} cm")
    print("\nTeclas disponibles:")
    print("  'q'     - Salir")
    print("  'd'     - Mostrar/ocultar datos de profundidad")
    print("  '+'     - Aumentar umbral de profundidad (+0.1 cm)")
    print("  '-'     - Disminuir umbral de profundidad (-0.1 cm)")
    print("  'c'     - Capturar frames actuales")
    print("  'r'     - Resetear umbral a valor por defecto")
    print("\n" + "="*70 + "\n")
    
    try:
        # Inicializar cámaras
        print("Inicializando cámaras...")
        cam_left = video_thread.VideoThread(
            video_source=config.LEFT_CAMERA_SOURCE,
            video_width=config.PIXEL_WIDTH,
            video_height=config.PIXEL_HEIGHT,
            video_frame_rate=config.FRAME_RATE,
            buffer_all=False,
            try_to_reconnect=False
        )
        
        cam_right = video_thread.VideoThread(
            video_source=config.RIGHT_CAMERA_SOURCE,
            video_width=config.PIXEL_WIDTH,
            video_height=config.PIXEL_HEIGHT,
            video_frame_rate=config.FRAME_RATE,
            buffer_all=False,
            try_to_reconnect=False
        )
        
        if not cam_left.is_available() or not cam_right.is_available():
            print("✗ Error: No se pudieron inicializar las cámaras")
            if not cam_left.is_available():
                print(f"  - Cámara izquierda ({config.LEFT_CAMERA_SOURCE}) no disponible")
            if not cam_right.is_available():
                print(f"  - Cámara derecha ({config.RIGHT_CAMERA_SOURCE}) no disponible")
            print("\nTip: Ejecuta 'python -m src.vision.camtest' para encontrar las cámaras correctas")
            return
        
        cam_left.start()
        cam_right.start()
        time.sleep(1)
        
        print("✓ Cámaras iniciadas correctamente")
        
        # Inicializar detectores de manos
        print("Inicializando detectores de manos...")
        left_detector = HandDetector(
            staticImageMode=False,
            maxHands=config.MAX_HANDS,
            detectionCon=config.HAND_DETECTION_CONFIDENCE,
            trackCon=config.HAND_TRACKING_CONFIDENCE
        )
        right_detector = HandDetector(
            staticImageMode=False,
            maxHands=config.MAX_HANDS,
            detectionCon=config.HAND_DETECTION_CONFIDENCE,
            trackCon=config.HAND_TRACKING_CONFIDENCE
        )
        
        # Inicializar calculadora de ángulos
        print("Inicializando calculadora de ángulos...")
        angler = angles.Frame_Angles(
            config.PIXEL_WIDTH,
            config.PIXEL_HEIGHT,
            config.ANGLE_WIDTH,
            config.ANGLE_HEIGHT
        )
        angler.build_frame()
        
        print("✓ Detectores y ángulos inicializados\n")
        
        # Variables de control
        display_dashboard = True
        depth_threshold = config.DEPTH_THRESHOLD
        default_threshold = config.DEPTH_THRESHOLD
        frame_count = 0
        fingers_detected_total = 0
        
        # Ventanas
        cv2.namedWindow('LEFT - Stereo Test', cv2.WINDOW_NORMAL)
        cv2.namedWindow('RIGHT - Stereo Test', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('LEFT - Stereo Test', config.PIXEL_WIDTH, config.PIXEL_HEIGHT)
        cv2.resizeWindow('RIGHT - Stereo Test', config.PIXEL_WIDTH, config.PIXEL_HEIGHT)
        cv2.moveWindow('LEFT - Stereo Test', 0, 0)
        cv2.moveWindow('RIGHT - Stereo Test', config.PIXEL_WIDTH + 50, 0)
        
        print("Iniciando captura de video...")
        print("Mueve las manos frente a las cámaras para comenzar...\n")
        
        while True:
            frame_count += 1
            
            # Capturar frames
            finished_left, frame_left = cam_left.next(black=True, wait=config.FRAME_WAIT_TIME_SETUP)
            finished_right, frame_right = cam_right.next(black=True, wait=config.FRAME_WAIT_TIME_SETUP)
            
            if finished_left or finished_right:
                print("✓ Captura completada")
                break
            
            # Flip (punto de vista selfie)
            frame_left = cv2.flip(frame_left, -1)
            frame_right = cv2.flip(frame_right, -1)
            
            hands_left = fingers_left = []
            hands_right = fingers_right = []
            
            # Detectar manos
            if left_detector.findHands(frame_left):
                left_detector.drawHands(frame_left)
                left_detector.drawTips(frame_left)
                hands_left, fingers_left = left_detector.getFingerTipsPos()
            
            if right_detector.findHands(frame_right):
                right_detector.drawHands(frame_right)
                right_detector.drawTips(frame_right)
                hands_right, fingers_right = right_detector.getFingerTipsPos()
            
            # Procesar profundidad si hay dedos en ambas cámaras
            if len(fingers_left) > 0 and len(fingers_right) > 0:
                depths_data = []
                
                for finger_left, finger_right in zip(fingers_left, fingers_right):
                    fingers_detected_total += 1
                    
                    # Calcular ángulos
                    xlangle, ylangle = angler.angles_from_center(
                        x=finger_left[2], y=finger_left[3],
                        top_left=True, degrees=True
                    )
                    xrangle, yrangle = angler.angles_from_center(
                        x=finger_right[2], y=finger_right[3],
                        top_left=True, degrees=True
                    )
                    
                    # Triangular
                    X_local, Y_local, Z_local, D_local = angler.location(
                        config.CAMERA_SEPARATION,
                        (xlangle, ylangle),
                        (xrangle, yrangle),
                        center=True,
                        degrees=True
                    )
                    
                    # Corrección de profundidad usando configuración centralizada
                    delta_y = (config.DEPTH_CORRECTION_A * X_local * X_local +
                               config.DEPTH_CORRECTION_B * -1 * X_local)
                    depth_corrected = D_local - delta_y
                    
                    hand_id = finger_left[0]
                    tip_id = finger_left[1]
                    x_screen = finger_left[2]
                    y_screen = finger_left[3]
                    
                    depths_data.append({
                        'hand_id': hand_id,
                        'tip_id': tip_id,
                        'x_screen': x_screen,
                        'y_screen': y_screen,
                        'X': X_local,
                        'Y': Y_local,
                        'Z': Z_local,
                        'D': D_local,
                        'delta_y': delta_y,
                        'D_corrected': depth_corrected
                    })
                    
                    # Visualizar umbral de profundidad
                    # Verde = presionando | Rojo = sin presión
                    if depth_corrected <= depth_threshold:
                        color = (0, 255, 0)  # Verde
                        thickness = 3
                        status = "✓ PRESIÓN"
                    else:
                        color = (0, 0, 255)  # Rojo
                        thickness = 2
                        status = "✗"
                    
                    cv2.circle(frame_left, (int(x_screen), int(y_screen)), 15, color, thickness)
                    
                    # Mostrar datos en consola cada 10 frames
                    if display_dashboard and frame_count % 10 == 0:
                        print(f"Dedo {hand_id}-{tip_id}: D={depth_corrected:.2f}cm "
                              f"(umbral={depth_threshold:.2f}cm) {status}")
            
            # Dashboard
            if display_dashboard:
                # Información superior
                fps_left = int(cam_left.current_frame_rate)
                fps_right = int(cam_right.current_frame_rate)
                text = f"FPS: L={fps_left} R={fps_right} | Umbral: {depth_threshold:.2f}cm | Frame: {frame_count}"
                
                cv2.putText(frame_left, text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame_right, text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Leyenda de colores
                cv2.putText(frame_left, "Verde=Presion  Rojo=Sin presion", (10, config.PIXEL_HEIGHT - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Cruces de referencia
                angler.frame_add_crosshairs(frame_left)
                angler.frame_add_crosshairs(frame_right)
            
            # Mostrar frames
            cv2.imshow('LEFT - Stereo Test', frame_left)
            cv2.imshow('RIGHT - Stereo Test', frame_right)
            
            # Control de teclas
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n✓ Saliendo del test...")
                break
            elif key == ord('d'):
                display_dashboard = not display_dashboard
                print(f"Dashboard: {'ACTIVADO' if display_dashboard else 'DESACTIVADO'}")
            elif key == ord('+'):
                depth_threshold += 0.1
                depth_threshold = min(depth_threshold, 10.0)
                print(f"↑ Umbral aumentado a: {depth_threshold:.2f} cm")
            elif key == ord('-'):
                depth_threshold = max(0.1, depth_threshold - 0.1)
                print(f"↓ Umbral disminuido a: {depth_threshold:.2f} cm")
            elif key == ord('c'):
                filename_l = f"stereo_test_left_{frame_count}.png"
                filename_r = f"stereo_test_right_{frame_count}.png"
                cv2.imwrite(filename_l, frame_left)
                cv2.imwrite(filename_r, frame_right)
                print(f"✓ Frames capturados: {filename_l}, {filename_r}")
            elif key == ord('r'):
                depth_threshold = default_threshold
                print(f"↻ Umbral reseteado a: {depth_threshold:.2f} cm")
        
        # Cleanup
        cam_left.stop()
        cam_right.stop()
        cv2.destroyAllWindows()
        
        print("\n" + "="*70)
        print("RESUMEN DEL TEST")
        print("="*70)
        print(f"Frames capturados: {frame_count}")
        print(f"Dedos totales detectados: {fingers_detected_total}")
        print(f"Umbral final: {depth_threshold:.2f} cm")
        print(f"Cambios hechos: {abs(depth_threshold - default_threshold):.2f} cm")
        
        if depth_threshold != default_threshold:
            print(f"\n📝 RECOMENDACIÓN: Actualiza stereo_config.py con:")
            print(f"   DEPTH_THRESHOLD = {depth_threshold:.2f}")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            cam_left.stop()
        except:
            pass
        try:
            cam_right.stop()
        except:
            pass
        cv2.destroyAllWindows()


if __name__ == '__main__':
    test_stereo_depth()

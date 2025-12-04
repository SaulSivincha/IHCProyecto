#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico para Detección de Tablero
Prueba diferentes configuraciones para encontrar el tablero
"""

import cv2
import numpy as np
import sys

def test_chessboard_detection():
    """Prueba detección del tablero con diferentes configuraciones"""
    
    print("="*70)
    print("DIAGNOSTICO DE DETECCION DE TABLERO")
    print("="*70)
    
    # Solicitar ID de cámara
    cam_id = int(input("\nIngresa ID de camara (0, 1, 2...): "))
    
    # TABLERO FIJO 8x8 = 7x7 esquinas
    print("\nConfiguracion del tablero:")
    print("Tablero estándar: 8x8 cuadrados = 7x7 esquinas internas")
    cols = 7
    rows = 7
    print(f"Usando: {cols}x{rows} esquinas")
    
    print(f"\n✓ Buscando tablero {cols}x{rows}")
    print("\nPresiona:")
    print("  ESPACIO - Probar deteccion con diferentes metodos")
    print("  1-5     - Cambiar resolucion")
    print("  'e'     - Ecualizar histograma")
    print("  'b'     - Aplicar blur")
    print("  'q'     - Salir")
    print("="*70 + "\n")
    
    # Abrir cámara
    cap = cv2.VideoCapture(cam_id)
    if not cap.isOpened():
        print(f"✗ No se pudo abrir la cámara {cam_id}")
        return
    
    # Configuración inicial
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Desactivar autofocus
    
    equalize = False
    apply_blur = False
    board_size = (cols, rows)
    
    window_name = f"Diagnostico - Camara {cam_id}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    detection_count = 0
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("✗ Error al leer frame")
            break
        
        frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Aplicar procesamiento opcional
        processed = gray.copy()
        if equalize:
            processed = cv2.equalizeHist(processed)
        if apply_blur:
            processed = cv2.GaussianBlur(processed, (5, 5), 0)
        
        display = frame.copy()
        
        # Método 1: Con FAST_CHECK
        flags1 = (cv2.CALIB_CB_ADAPTIVE_THRESH + 
                 cv2.CALIB_CB_NORMALIZE_IMAGE + 
                 cv2.CALIB_CB_FAST_CHECK)
        ret1, corners1 = cv2.findChessboardCorners(processed, board_size, flags1)
        
        # Método 2: Sin FAST_CHECK
        flags2 = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
        ret2, corners2 = cv2.findChessboardCorners(processed, board_size, flags2)
        
        # Método 3: Solo ADAPTIVE_THRESH
        flags3 = cv2.CALIB_CB_ADAPTIVE_THRESH
        ret3, corners3 = cv2.findChessboardCorners(processed, board_size, flags3)
        
        # Usar el mejor resultado
        if ret1:
            corners = corners1
            method = "Metodo 1 (FAST_CHECK)"
            color = (0, 255, 0)
            detection_count += 1
        elif ret2:
            corners = corners2
            method = "Metodo 2 (SIN FAST_CHECK)"
            color = (0, 255, 255)
            detection_count += 1
        elif ret3:
            corners = corners3
            method = "Metodo 3 (ADAPTIVE)"
            color = (255, 255, 0)
            detection_count += 1
        else:
            corners = None
            method = "NO DETECTADO"
            color = (0, 0, 255)
        
        # Dibujar resultado
        if corners is not None:
            cv2.drawChessboardCorners(display, board_size, corners, True)
            
            # Refinar esquinas
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            # Calcular calidad de detección
            mean_x = np.mean([c[0][0] for c in corners_refined])
            mean_y = np.mean([c[0][1] for c in corners_refined])
            
            cv2.circle(display, (int(mean_x), int(mean_y)), 10, (255, 0, 255), -1)
        
        # Información en pantalla
        y_pos = 30
        cv2.putText(display, f"Camara: {cam_id} | Buscando: {cols}x{rows}", 
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_pos += 35
        
        cv2.putText(display, f"Estado: {method}", 
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        y_pos += 35
        
        cv2.putText(display, f"Detecciones: {detection_count}/{frame_count} ({detection_count*100//max(1,frame_count)}%)", 
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        y_pos += 30
        
        # Opciones activas
        options = []
        if equalize:
            options.append("ECUALIZADO")
        if apply_blur:
            options.append("BLUR")
        
        if options:
            cv2.putText(display, f"Opciones: {', '.join(options)}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 255), 2)
            y_pos += 30
        
        # Controles
        cv2.putText(display, "ESPACIO: Test | E: Ecualizar | B: Blur | 1-5: Resolucion | Q: Salir", 
                   (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        cv2.imshow(window_name, display)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):
            print(f"\nFrame {frame_count}:")
            print(f"  Metodo 1 (FAST_CHECK): {'✓ DETECTADO' if ret1 else '✗ No detectado'}")
            print(f"  Metodo 2 (SIN FAST_CHECK): {'✓ DETECTADO' if ret2 else '✗ No detectado'}")
            print(f"  Metodo 3 (ADAPTIVE): {'✓ DETECTADO' if ret3 else '✗ No detectado'}")
            if corners is not None:
                print(f"  Esquinas encontradas: {len(corners)}")
                print(f"  Metodo usado: {method}")
        
        elif key == ord('e'):
            equalize = not equalize
            print(f"Ecualizacion: {'ACTIVADA' if equalize else 'DESACTIVADA'}")
        
        elif key == ord('b'):
            apply_blur = not apply_blur
            print(f"Blur: {'ACTIVADO' if apply_blur else 'DESACTIVADO'}")
        
        elif key == ord('1'):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            print("Resolucion: 320x240")
        
        elif key == ord('2'):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print("Resolucion: 640x480")
        
        elif key == ord('3'):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
            print("Resolucion: 800x600")
        
        elif key == ord('4'):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            print("Resolucion: 1280x720")
        
        elif key == ord('5'):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            print("Resolucion: 1920x1080")
        
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Frames totales: {frame_count}")
    print(f"Detecciones exitosas: {detection_count}")
    print(f"Tasa de deteccion: {detection_count*100//max(1,frame_count)}%")
    
    if detection_count == 0:
        print("\n⚠ RECOMENDACIONES:")
        print("  1. Verifica que el numero de esquinas sea correcto")
        print("     (Cuenta las esquinas INTERNAS, no los cuadrados)")
        print("  2. Mejora la iluminacion (sin sombras)")
        print("  3. Asegurate de que el tablero este completamente visible")
        print("  4. Prueba con ecualizacion (tecla 'e')")
        print("  5. Intenta diferentes distancias del tablero")
        print("  6. Verifica que el patron sea de ajedrez (no damero)")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    try:
        test_chessboard_detection()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 22 15:27:37 2021
Proyecto de Integracion: Virtual Piano Keyboard

Fuentes:
    OpenCV
    https://opencv.org/

    Clayton Darwin
    https://www.youtube.com/watch?v=sW4CVI51jDY

    Nicolai Høirup Nielsen  (The Coding Lib)
    https://github.com/niconielsen32/ComputerVision/tree/master/StereoVisionDepthEstimation
    https://www.youtube.com/watch?v=t3LOey68Xpg -


    Kaustubh Sadekar - Satya Mallick
    https://learnopencv.com/making-a-low-cost-stereo-camera-using-opencv/#steps-to-create-the-stereo-camera-setup

    Fernando Souza
    https://medium.com/vacatronics/3-ways-to-calibrate-your-camera-using-opencv-and-python-395528a51615

    Daniel Lee
    https://erget.wordpress.com/2014/02/28/calibrating-a-stereo-pair-with-python/
    https://erget.wordpress.com/2014/02/01/calibrating-a-stereo-camera-with-opencv/


    LearnTechWithUs
    https://github.com/LearnTechWithUs/Stereo-Vision/issues/10

    Najam R. Syed
    https://nrsyed.com/2018/07/05/multithreading-with-opencv-python-to-improve-video-processing-performance/

    Murtaza's Workshop - Robotics and AI
    https://www.youtube.com/watch?v=NZde8Xt78Iw

    Google -Mediapipe
    https://ai.googleblog.com/2019/08/on-device-real-time-hand-tracking-with.html


    Nathan Whitehead
    https://github.com/nwhitehead/pyfluidsynth

    y otros

    Referencias:
    Python
    https://www.python.org/dev/peps/pep-0008/#package-and-module-names


# TODOES:
# TODO1: Crear una cola (queue) para estabilizar con un promedio la posición xy de los dedos
# TODO2: Calcular distancia angular para detectar cuando un dedo está bajo el umbral para tocar la tecla virtual
# TODO3: Incluir todos los dedos al mapa de XY + Depth
# TODO4: Mejorar performance, primera opcion GPU, y optimización

@author: mherrera
"""

import time
import traceback
import cv2
import numpy as np
import fluidsynth
from collections import deque

# --- Vision ---
from src.vision import video_thread, angles
from src.vision.hand_detector import HandDetector
from src.vision import keyboard_mapper as kbm
from src.vision import load_depth_estimator
from src.vision.stereo_config import StereoConfig

# --- Calibration ---
from src.calibration import CalibrationManager

# --- Piano ---
from src.piano import virtual_keyboard as vkb
from src.piano.virtual_keyboard import VirtualKeyboard

# --- Gameplay ---
from src.gameplay.rythm_game import RhythmGame
from src.gameplay.song_chart import TUTORIAL_FACIL

# --- UI ---
from src.ui.ui_helper import UIHelper

# --- Theory ---
from src.theory import get_lesson_manager, TheoryUI

# --- Config UI ---
from src.ui.config_ui import ConfigUI

# --- Common ---
from src.common.toolbox import round_half_up

def frame_add_crosshairs(frame,
                         x,
                         y,
                         r=20,
                         lc=(0, 0, 255),
                         cc=(0, 0, 255),
                         lw=2,
                         cw=1):

    x = int(round(x, 0))
    y = int(round(y, 0))
    r = int(round(r, 0))

    cv2.line(frame, (x, y-r*2), (x, y+r*2), lc, lw)
    cv2.line(frame, (x-r*2, y), (x+r*2, y), lc, lw)

    cv2.circle(frame, (x, y), r, cc, cw)

def show_calibration_menu(ui_helper, pixel_width, pixel_height):
    """Muestra menú de configuración inicial y retorna la opción seleccionada"""
    window_name = 'Configuración Inicial'
    cv2.namedWindow(window_name)
    cv2.moveWindow(window_name, (pixel_width//2), (pixel_height//2))
    
    while True:
        # Frame negro para el menú
        menu_frame = np.zeros((pixel_height, pixel_width * 2, 3), dtype=np.uint8)
        menu_frame = ui_helper.draw_setup_menu(menu_frame)
        cv2.imshow(window_name, menu_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('1'):
            cv2.destroyWindow(window_name)
            return 1  # Usar calibración guardada
        elif key == ord('2'):
            cv2.destroyWindow(window_name)
            return 2  # Nueva calibración
        elif key == ord('3'):
            cv2.destroyWindow(window_name)
            return 3  # Saltar (valores por defecto)
        elif key == ord('q'):
            cv2.destroyWindow(window_name)
            return None  # Salir

def run_calibration_process(ui_helper, pixel_width, pixel_height, config):
    """Ejecuta el proceso de calibración con el nuevo sistema profesional"""
    from src.calibration.calibration_config import CalibrationConfig
    
    try:
        # ========== VERIFICAR QUÉ FASES ESTÁN COMPLETAS ==========
        has_phase1 = False
        has_phase2 = False
        summary = None
        force_recalibration = False  # Flag para forzar re-calibración
        recalibrate_phase2_only = False  # Flag para re-calibrar solo Fase 2
        
        if CalibrationConfig.calibration_exists():
            summary = CalibrationConfig.get_calibration_summary()
            has_phase1 = summary is not None
            has_phase2 = summary.get('tiene_estereo', False) if summary else False
            
            # Debug: Mostrar datos de Fase 2
            if has_phase2 and summary:
                print("\n[DEBUG] Datos Fase 2 detectados:")
                print(f"  - Baseline: {summary.get('baseline_cm', 'N/A')}")
                print(f"  - Error RMS: {summary.get('error_stereo', 'N/A')}")
                print(f"  - Pares: {summary.get('pares_stereo', 'N/A')}")
        
        # ========== CASO 1: AMBAS FASES COMPLETAS ==========
        if has_phase1 and has_phase2 and not force_recalibration:
            # Mostrar interfaz detallada de calibración completa
            window_name = 'Calibracion Completa - Detalles'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 950, 700)
            cv2.moveWindow(window_name, 100, 50)
            
            info_frame = np.zeros((700, 950, 3), dtype=np.uint8)
            
            while True:
                display_frame = info_frame.copy()
                
                # ============ ENCABEZADO ============
                cv2.rectangle(display_frame, (0, 0), (950, 100), (40, 80, 40), -1)
                cv2.rectangle(display_frame, (0, 0), (950, 100), (0, 255, 0), 3)
                
                cv2.putText(display_frame, "CALIBRACION COMPLETA", 
                           (250, 45),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
                
                cv2.putText(display_frame, f"Fecha: {summary['fecha']}    Version: {summary.get('version', '2.0')}", 
                           (180, 75),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 1)
                
                # ============ SECCIÓN FASE 1 ============
                y_pos = 120
                cv2.putText(display_frame, "FASE 1: CALIBRACION INDIVIDUAL", 
                           (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 255), 2)
                
                y_pos += 5
                cv2.line(display_frame, (20, y_pos), (930, y_pos), (100, 100, 100), 2)
                
                # Cámara Izquierda
                y_pos += 30
                cv2.putText(display_frame, "Camara IZQUIERDA:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                if isinstance(summary['error_left'], float):
                    cv2.putText(display_frame, f"Error: {summary['error_left']:.6f} px", 
                               (300, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    cv2.putText(display_frame, f"Imgs: {summary['imagenes_left']}", 
                               (600, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    quality_color = (0, 255, 0) if summary['error_left'] < 0.5 else (0, 255, 255) if summary['error_left'] < 1.0 else (0, 200, 255)
                    cv2.circle(display_frame, (750, y_pos-7), 7, quality_color, -1)
                
                # Cámara Derecha
                y_pos += 30
                cv2.putText(display_frame, "Camara DERECHA:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                if isinstance(summary['error_right'], float):
                    cv2.putText(display_frame, f"Error: {summary['error_right']:.6f} px", 
                               (300, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    cv2.putText(display_frame, f"Imgs: {summary['imagenes_right']}", 
                               (600, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    quality_color = (0, 255, 0) if summary['error_right'] < 0.5 else (0, 255, 255) if summary['error_right'] < 1.0 else (0, 200, 255)
                    cv2.circle(display_frame, (750, y_pos-7), 7, quality_color, -1)
                
                # ============ SECCIÓN FASE 2 ============
                y_pos += 45
                cv2.putText(display_frame, "FASE 2: CALIBRACION ESTEREO", 
                           (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 100), 2)
                
                y_pos += 5
                cv2.line(display_frame, (20, y_pos), (930, y_pos), (100, 100, 100), 2)
                
                # Baseline
                y_pos += 30
                cv2.putText(display_frame, "Baseline (distancia camaras):", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                baseline_val = summary.get('baseline_cm', 'N/A')
                if baseline_val != 'N/A' and baseline_val is not None:
                    try:
                        baseline_float = float(baseline_val)
                        cv2.putText(display_frame, f"{baseline_float:.2f} cm", 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 255), 2)
                    except:
                        cv2.putText(display_frame, str(baseline_val), 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 255), 2)
                else:
                    cv2.putText(display_frame, "N/A", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                
                # Error RMS
                y_pos += 30
                cv2.putText(display_frame, "Error RMS:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                error_stereo_val = summary.get('error_stereo', 'N/A')
                if error_stereo_val != 'N/A' and error_stereo_val is not None:
                    try:
                        error_float = float(error_stereo_val)
                        cv2.putText(display_frame, f"{error_float:.4f}", 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                        
                        # Indicador de calidad
                        if error_float < 0.3:
                            quality_text = "EXCELENTE"
                            quality_color = (0, 255, 0)
                        elif error_float < 0.6:
                            quality_text = "BUENA"
                            quality_color = (0, 255, 255)
                        elif error_float < 1.0:
                            quality_text = "ACEPTABLE"
                            quality_color = (0, 200, 255)
                        else:
                            quality_text = "MEJORABLE"
                            quality_color = (0, 165, 255)
                        
                        cv2.putText(display_frame, quality_text, 
                                   (650, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, quality_color, 2)
                    except:
                        cv2.putText(display_frame, str(error_stereo_val), 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                else:
                    cv2.putText(display_frame, "N/A", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                
                # Pares capturados
                y_pos += 30
                cv2.putText(display_frame, "Pares capturados:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                pares_val = summary.get('pares_stereo', 'N/A')
                if pares_val != 'N/A' and pares_val is not None:
                    cv2.putText(display_frame, f"{pares_val}", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                else:
                    cv2.putText(display_frame, "N/A", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                
                # ============ CONFIGURACIÓN TABLERO ============
                y_pos += 45
                cv2.putText(display_frame, "CONFIGURACION TABLERO", 
                           (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 100), 2)
                
                y_pos += 5
                cv2.line(display_frame, (20, y_pos), (930, y_pos), (100, 100, 100), 2)
                
                y_pos += 30
                cv2.putText(display_frame, f"Tablero: {summary.get('tablero', 'N/A')}", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                cv2.putText(display_frame, f"Cuadrado: {summary.get('square_size', 'N/A')} mm", 
                           (300, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                # ============ MENSAJE IMPORTANTE ============
                y_pos += 50
                cv2.rectangle(display_frame, (15, y_pos - 10), (935, y_pos + 75), (60, 60, 60), -1)
                cv2.rectangle(display_frame, (15, y_pos - 10), (935, y_pos + 75), (100, 255, 100), 3)
                
                cv2.putText(display_frame, "ESTA CALIBRACION ES VALIDA PARA:", 
                           (220, y_pos + 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 100), 2)
                
                cv2.putText(display_frame, "- La misma ubicacion fisica de las camaras", 
                           (150, y_pos + 45),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                
                cv2.putText(display_frame, "- Si moviste las camaras, RE-CALIBRA", 
                           (150, y_pos + 68),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 100), 1)
                
                # ============ OPCIONES ============
                y_pos += 100
                cv2.line(display_frame, (15, y_pos), (935, y_pos), (100, 255, 100), 2)
                
                y_pos += 30
                cv2.putText(display_frame, "[ENTER] Usar esta calibracion y arrancar juego", 
                           (180, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                y_pos += 35
                cv2.putText(display_frame, "[S] Re-calibrar SOLO Fase 2 (mejorar baseline/error)", 
                           (130, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
                
                y_pos += 35
                cv2.putText(display_frame, "[R] Re-calibrar TODO (Fase 1 + Fase 2)", 
                           (190, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)
                
                y_pos += 30
                cv2.putText(display_frame, "[ESC] Volver al menu principal", 
                           (260, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 255), 1)
                
                cv2.imshow(window_name, display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == 13:  # ENTER - Usar existente y arrancar
                    cv2.destroyWindow(window_name)
                    print("\n✓ Usando calibración existente - Iniciando juego...")
                    return True
                
                elif key == ord('s') or key == ord('S'):  # Re-calibrar SOLO Fase 2
                    cv2.destroyWindow(window_name)
                    print("\n⚡ Re-calibrando SOLO FASE 2...")
                    print("  (Manteniendo calibración de Fase 1 existente)")
                    
                    # IMPORTANTE: Eliminar stereo del JSON ANTES de salir
                    import json
                    try:
                        with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                            calib_data = json.load(f)
                        
                        # Eliminar solo sección stereo
                        calib_data['stereo'] = None
                        
                        # Guardar JSON modificado
                        with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
                            json.dump(calib_data, f, indent=4)
                        
                        print("✓ Preparando re-calibración de Fase 2...\n")
                    except Exception as e:
                        print(f"⚠ Error al modificar calibración: {e}")
                    
                    # Actualizar variables de estado
                    force_recalibration = True
                    recalibrate_phase2_only = True
                    has_phase2 = False  # ← CRUCIAL: Marcar que NO hay Fase 2
                    break  # Salir del while para continuar con calibración
                
                elif key == ord('r') or key == ord('R'):  # Re-calibrar TODO
                    cv2.destroyWindow(window_name)
                    print("\n⚠ Iniciando RE-CALIBRACIÓN COMPLETA...")
                    print("  (Fase 1 + Fase 2 desde cero)")
                    force_recalibration = True
                    recalibrate_phase2_only = False
                    break  # Salir del while para continuar con calibración
                
                elif key == 27:  # ESC
                    cv2.destroyWindow(window_name)
                    return False
        
        # ========== EJECUTAR CALIBRACIÓN SI ES NECESARIO ==========
        # Solo si: no hay fase 1, no hay fase 2, o se forzó re-calibración
        if not has_phase1 or not has_phase2 or force_recalibration:
            # Mostrar interfaz detallada de calibración completa
            window_name = 'Calibracion Completa - Detalles'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 950, 700)
            cv2.moveWindow(window_name, 100, 50)
            
            info_frame = np.zeros((700, 950, 3), dtype=np.uint8)
            
            while True:
                display_frame = info_frame.copy()
                
                # ============ ENCABEZADO ============
                cv2.rectangle(display_frame, (0, 0), (950, 100), (40, 80, 40), -1)
                cv2.rectangle(display_frame, (0, 0), (950, 100), (0, 255, 0), 3)
                
                cv2.putText(display_frame, "CALIBRACION COMPLETA", 
                           (250, 45),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
                
                cv2.putText(display_frame, f"Fecha: {summary['fecha']}    Version: {summary.get('version', '2.0')}", 
                           (180, 75),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 1)
                
                # ============ SECCIÓN FASE 1 ============
                y_pos = 120
                cv2.putText(display_frame, "FASE 1: CALIBRACION INDIVIDUAL", 
                           (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 255), 2)
                
                y_pos += 5
                cv2.line(display_frame, (20, y_pos), (930, y_pos), (100, 100, 100), 2)
                
                # Cámara Izquierda
                y_pos += 30
                cv2.putText(display_frame, "Camara IZQUIERDA:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                if isinstance(summary['error_left'], float):
                    cv2.putText(display_frame, f"Error: {summary['error_left']:.6f} px", 
                               (300, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    cv2.putText(display_frame, f"Imgs: {summary['imagenes_left']}", 
                               (600, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    quality_color = (0, 255, 0) if summary['error_left'] < 0.5 else (0, 255, 255) if summary['error_left'] < 1.0 else (0, 200, 255)
                    cv2.circle(display_frame, (750, y_pos-7), 7, quality_color, -1)
                
                # Cámara Derecha
                y_pos += 30
                cv2.putText(display_frame, "Camara DERECHA:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                if isinstance(summary['error_right'], float):
                    cv2.putText(display_frame, f"Error: {summary['error_right']:.6f} px", 
                               (300, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    cv2.putText(display_frame, f"Imgs: {summary['imagenes_right']}", 
                               (600, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    quality_color = (0, 255, 0) if summary['error_right'] < 0.5 else (0, 255, 255) if summary['error_right'] < 1.0 else (0, 200, 255)
                    cv2.circle(display_frame, (750, y_pos-7), 7, quality_color, -1)
                
                # ============ SECCIÓN FASE 2 ============
                y_pos += 45
                cv2.putText(display_frame, "FASE 2: CALIBRACION ESTEREO", 
                           (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 100), 2)
                
                y_pos += 5
                cv2.line(display_frame, (20, y_pos), (930, y_pos), (100, 100, 100), 2)
                
                # Baseline
                y_pos += 30
                cv2.putText(display_frame, "Baseline (distancia camaras):", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                baseline_val = summary.get('baseline_cm', 'N/A')
                if baseline_val != 'N/A' and baseline_val is not None:
                    try:
                        baseline_float = float(baseline_val)
                        cv2.putText(display_frame, f"{baseline_float:.2f} cm", 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 255), 2)
                    except:
                        cv2.putText(display_frame, str(baseline_val), 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 255), 2)
                else:
                    cv2.putText(display_frame, "N/A", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                
                # Error RMS
                y_pos += 30
                cv2.putText(display_frame, "Error RMS:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                error_stereo_val = summary.get('error_stereo', 'N/A')
                if error_stereo_val != 'N/A' and error_stereo_val is not None:
                    try:
                        error_float = float(error_stereo_val)
                        cv2.putText(display_frame, f"{error_float:.4f}", 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                        
                        # Indicador de calidad
                        if error_float < 0.3:
                            quality_text = "EXCELENTE"
                            quality_color = (0, 255, 0)
                        elif error_float < 0.6:
                            quality_text = "BUENA"
                            quality_color = (0, 255, 255)
                        elif error_float < 1.0:
                            quality_text = "ACEPTABLE"
                            quality_color = (0, 200, 255)
                        else:
                            quality_text = "MEJORABLE"
                            quality_color = (0, 165, 255)
                        
                        cv2.putText(display_frame, quality_text, 
                                   (650, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, quality_color, 2)
                    except:
                        cv2.putText(display_frame, str(error_stereo_val), 
                                   (450, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                else:
                    cv2.putText(display_frame, "N/A", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                
                # Pares capturados
                y_pos += 30
                cv2.putText(display_frame, "Pares capturados:", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 200, 255), 2)
                
                pares_val = summary.get('pares_stereo', 'N/A')
                if pares_val != 'N/A' and pares_val is not None:
                    cv2.putText(display_frame, f"{pares_val}", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                else:
                    cv2.putText(display_frame, "N/A", 
                               (450, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                
                # ============ CONFIGURACIÓN TABLERO ============
                y_pos += 45
                cv2.putText(display_frame, "CONFIGURACION TABLERO", 
                           (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 100), 2)
                
                y_pos += 5
                cv2.line(display_frame, (20, y_pos), (930, y_pos), (100, 100, 100), 2)
                
                y_pos += 30
                cv2.putText(display_frame, f"Tablero: {summary.get('tablero', 'N/A')}", 
                           (40, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                cv2.putText(display_frame, f"Cuadrado: {summary.get('square_size', 'N/A')} mm", 
                           (300, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                # ============ MENSAJE IMPORTANTE ============
                y_pos += 50
                cv2.rectangle(display_frame, (15, y_pos - 10), (935, y_pos + 75), (60, 60, 60), -1)
                cv2.rectangle(display_frame, (15, y_pos - 10), (935, y_pos + 75), (100, 255, 100), 3)
                
                cv2.putText(display_frame, "ESTA CALIBRACION ES VALIDA PARA:", 
                           (220, y_pos + 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 100), 2)
                
                cv2.putText(display_frame, "- La misma ubicacion fisica de las camaras", 
                           (150, y_pos + 45),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                
                cv2.putText(display_frame, "- Si moviste las camaras, RE-CALIBRA", 
                           (150, y_pos + 68),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 100), 1)
                
                # ============ OPCIONES ============
                y_pos += 100
                cv2.line(display_frame, (15, y_pos), (935, y_pos), (100, 255, 100), 2)
                
                y_pos += 30
                cv2.putText(display_frame, "[ENTER] Usar esta calibracion y arrancar juego", 
                           (180, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                y_pos += 35
                cv2.putText(display_frame, "[R] Re-calibrar (camaras movidas o nueva ubicacion)", 
                           (150, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)
                
                y_pos += 30
                cv2.putText(display_frame, "[ESC] Volver al menu principal", 
                           (260, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 255), 1)
                
                cv2.imshow(window_name, display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == 13:  # ENTER - Usar existente y arrancar
                    cv2.destroyWindow(window_name)
                    print("\n✓ Usando calibración existente - Iniciando juego...")
                    return True
                
                elif key == ord('r') or key == ord('R'):  # Re-calibrar
                    cv2.destroyWindow(window_name)
                    print("\n⚠ Iniciando RE-CALIBRACIÓN completa...")
                    print("  (Las cámaras pueden haber sido movidas de su posición original)")
                    break  # Continuar con calibración
                
                elif key == 27:  # ESC
                    cv2.destroyWindow(window_name)
                    return False
        # ========== EJECUTAR CALIBRACIÓN SI ES NECESARIO ==========
        # Solo si: no hay fase 1, no hay fase 2, o se forzó re-calibración
        if not has_phase1 or not has_phase2 or force_recalibration:
            
            # ========== CASO 2A: RE-CALIBRAR SOLO FASE 2 ==========
            if recalibrate_phase2_only and has_phase1:
                print("\n" + "="*70)
                print("⚡ RE-CALIBRANDO SOLO FASE 2")
                print("="*70)
                print("✓ Fase 1 existente se mantendrá")
                print(f"  Izquierda: {summary['error_left']:.4f} px" if isinstance(summary['error_left'], float) else "  Izquierda: OK")
                print(f"  Derecha: {summary['error_right']:.4f} px" if isinstance(summary['error_right'], float) else "  Derecha: OK")
                print("\n⚡ Iniciando SOLO captura de pares estéreo...")
                print("💡 TIP: Captura 15 pares y mantén tablero INMÓVIL")
                print("="*70 + "\n")
                
                from src.calibration.calibration_manager_v2 import CalibrationManager
                
                # Crear gestor (detectará automáticamente Fase 1 completa del JSON)
                calibration_manager = CalibrationManager(
                    cam_left_id=config.LEFT_CAMERA_SOURCE,
                    cam_right_id=config.RIGHT_CAMERA_SOURCE,
                    resolution=(pixel_width, pixel_height)
                )
                
                # Ejecutar calibración (detectará Fase 1 completa y ejecutará SOLO Fase 2)
                success = calibration_manager.run_full_calibration()
                
                if not success:
                    print("✗ Re-calibración de Fase 2 fallida o cancelada")
                    return False
                
                print("\n" + "="*70)
                print("✓ FASE 2 RE-CALIBRADA EXITOSAMENTE")
                print("="*70)
                print("   Datos guardados correctamente")
                print("   Puedes cerrar esta ventana y ejecutar el piano")
                print("="*70)
                
                # NO RETORNAR - Continuar para que el usuario vea el mensaje
                # El usuario debe presionar una tecla para continuar
                input("\nPresiona ENTER para cerrar...")
                
                return True
            
            # ========== CASO 2B: SOLO FASE 1 COMPLETA, FALTA FASE 2 ==========
            elif has_phase1 and not has_phase2 and not force_recalibration:
                print("\n" + "="*70)
                print("✓ FASE 1 COMPLETA - Saltando a Fase 2")
                print("="*70)
                print(f"  Izquierda: {summary['error_left']:.4f} px" if isinstance(summary['error_left'], float) else "  Izquierda: OK")
                print(f"  Derecha: {summary['error_right']:.4f} px" if isinstance(summary['error_right'], float) else "  Derecha: OK")
                print("\n⚡ Iniciando Fase 2 directamente...")
                print("="*70 + "\n")
            
            # ========== CASO 3: NADA COMPLETO O RE-CALIBRACIÓN COMPLETA SOLICITADA ==========
            else:
                print("\n" + "="*70)
                print("INICIANDO CALIBRACIÓN COMPLETA (FASE 1 + FASE 2)")
                print("="*70)
            
            # Importar el manager v2 (si no se hizo antes)
            if not recalibrate_phase2_only:
                from src.calibration.calibration_manager_v2 import CalibrationManager
                
                # Crear gestor de calibración
                calibration_manager = CalibrationManager(
                    cam_left_id=config.LEFT_CAMERA_SOURCE,
                    cam_right_id=config.RIGHT_CAMERA_SOURCE,
                    resolution=(pixel_width, pixel_height)
                )
                
                # Ejecutar calibración (inteligente: salta fases ya completadas)
                success = calibration_manager.run_full_calibration()
                
                if not success:
                    print("✗ Calibración fallida o cancelada")
                    return False
                
                print("\n" + "="*70)
                print("✓ CALIBRACIÓN COMPLETA EXITOSA")
                print("="*70)
            
            return True
        
    except Exception as e:
        print(f"✗ Error durante calibración: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():

    try:
        # Cargar configuración estéreo centralizada
        config = StereoConfig()
        
        # Dimensiones para la interfaz
        pixel_width = config.PIXEL_WIDTH
        pixel_height = config.PIXEL_HEIGHT
        
        # Inicializar UI Helper para menú de configuración
        ui_helper_menu = UIHelper(pixel_width * 2, pixel_height)
        ui_helper_menu.show_instructions = False  # No mostrar bienvenida aún
        
        # Mostrar menú de configuración
        setup_option = show_calibration_menu(ui_helper_menu, pixel_width, pixel_height)
        
        if setup_option is None:
            print("Saliendo...")
            return
        elif setup_option == 1:
            # Usar calibración guardada
            print("Cargando calibración guardada...")
            loaded = config.load_calibration()
            if not loaded:
                print("⚠ No se pudo cargar calibración. Usando valores por defecto.")
            # NO RETORNAR - Continuar con el programa
        elif setup_option == 2:
            # Nueva calibración
            print("Iniciando proceso de calibración...")
            success = run_calibration_process(ui_helper_menu, pixel_width, pixel_height, config)
            if not success:
                print("⚠ Calibración cancelada. Usando valores por defecto.")
        else:  # setup_option == 3
            print("Usando valores por defecto (sin calibración)")
        
        config.print_config()

        # ------------------------------
        # set up cameras
        # ------------------------------

        # cameras variables
        left_camera_source = config.LEFT_CAMERA_SOURCE
        right_camera_source = config.RIGHT_CAMERA_SOURCE
        pixel_width = config.PIXEL_WIDTH
        pixel_height = config.PIXEL_HEIGHT

        # Logi C920s HD Pro Webcam - Calibración óptica
        camera_hFoV = config.CAMERA_H_FOV
        camera_vFoV = config.CAMERA_V_FOV
        hFoV_angle_rectification = config.H_FOV_RECTIFICATION
        vFoV_angle_rectification = config.V_FOV_RECTIFICATION

        angle_width = config.ANGLE_WIDTH
        angle_height = config.ANGLE_HEIGHT

        # FPS
        frame_rate = config.FRAME_RATE
        camera_separation = config.CAMERA_SEPARATION

        camera_in_front_of_you = config.CAMERA_IN_FRONT_OF_YOU

        # Virtual Keyboard Center point distance (cms)
        vkb_center_point_camera_dist = config.VKB_CENTER_DISTANCE

            # cam_resource = video_thread.VideoThread(
            #     video_source=c_id,
            #     video_width=pixel_width,
            #     video_height=pixel_height,
            #     video_frame_rate=frame_rate,
            #     buffer_all=False,
            #     try_to_reconnect=False
            # )
        # left camera 1
        cam_left = video_thread.VideoThread(
            video_source=left_camera_source,
            video_width=pixel_width,
            video_height=pixel_height,
            video_frame_rate=frame_rate,
            buffer_all=False,
            try_to_reconnect=False)

        # right camera 2
        cam_right = video_thread.VideoThread(
            video_source=right_camera_source,
            video_width=pixel_width,
            video_height=pixel_height,
            video_frame_rate=frame_rate,
            buffer_all=False,
            try_to_reconnect=False)

        # start cameras
        cam_left.start()
        cam_right.start()

        time.sleep(1)
        
        # Intentar cargar DepthEstimator si existe calibración completa
        depth_estimator = None
        use_stereo_calibration = False
        try:
            from src.calibration.calibration_config import CalibrationConfig
            depth_estimator = load_depth_estimator(CalibrationConfig.CALIBRATION_FILE)
            use_stereo_calibration = True
            print("\n" + "="*70)
            print("✓ CALIBRACIÓN ESTÉREO CARGADA")
            print("="*70)
            print(f"  Baseline: {depth_estimator.baseline_cm:.2f} cm")
            print(f"  Modo: Triangulación precisa con rectificación")
            print("="*70 + "\n")
        except (FileNotFoundError, ValueError) as e:
            print("\n" + "="*70)
            print("⚠ CALIBRACIÓN ESTÉREO NO DISPONIBLE")
            print("="*70)
            print(f"  {e}")
            print(f"  Modo: Triangulación basada en ángulos (menos preciso)")
            print("="*70 + "\n")
        
        if camera_in_front_of_you:
            main_window_name = 'In fron of you: rigth+left cam'
        else:
            main_window_name = 'Same Point of View: left+rigth cam'

        cv2.namedWindow(main_window_name)
        cv2.moveWindow(main_window_name,
                       (pixel_width//2),
                       (pixel_height//2))        
        
        if cam_left.is_available():
            print('Name:{}'.format(main_window_name))
            print('cam_left.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE:{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE)))
            print('cam_left.resource.get(cv2.CAP_PROP_EXPOSURE:{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_EXPOSURE)))
            print('cam_left.resource.get(cv2.CAP_PROP_AUTOFOCUS):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_AUTOFOCUS)))
            print('cam_left.resource.get(cv2.CAP_PROP_BUFFERSIZE):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_BUFFERSIZE)))
            print('cam_left.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)))

            print('cam_left.resource.get(cv2.CAP_PROP_HW_DEVICE):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_HW_DEVICE)))
            print('cam_left.resource.get(cv2.CAP_PROP_FRAME_COUNT):{:03f}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_FRAME_COUNT)))
                

        if cam_right.is_available():
            print('Name:{}'.format(main_window_name))
            print('cam_right.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE:{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE)))
            print('cam_right.resource.get(cv2.CAP_PROP_EXPOSURE:{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_EXPOSURE)))
            print('cam_right.resource.get(cv2.CAP_PROP_AUTOFOCUS):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_AUTOFOCUS)))
            print('cam_right.resource.get(cv2.CAP_PROP_BUFFERSIZE):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_BUFFERSIZE)))
            print('cam_right.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)))

            print('cam_right.resource.get(cv2.CAP_PROP_HW_DEVICE):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_HW_DEVICE)))
            print('cam_right.resource.get(cv2.CAP_PROP_FRAME_COUNT):{:03f}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_FRAME_COUNT)))


        # left_window_name = 'frame left'
        # cv2.namedWindow(left_window_name)
        # cv2.moveWindow(left_window_name,
        #                (pixel_width//2),
        #                (pixel_height//2))

        # right_window_name = 'frame right'
        # cv2.namedWindow(right_window_name)
        # cv2.moveWindow(right_window_name,
        #                (pixel_width//2)+640,
        #                (pixel_height//2))



        # ------------------------------
        # set up virtual keyboards
        # ------------------------------

        N_BANK = 0
        N_MAYOR_NOTES_X_BANK = 0

        KEYBOARD_WHIITE_N_KEYS = config.KEYBOARD_WHITE_KEYS

        KEYBOARD_TOT_KEYS = config.KEYBOARD_TOTAL_KEYS
        print('KEYBOARD_TOT_KEYS:{}'.format(KEYBOARD_TOT_KEYS))
        octave_base = config.OCTAVE_BASE

        vk_left = vkb.VirtualKeyboard(pixel_width, pixel_height,
                                      KEYBOARD_WHIITE_N_KEYS)
        vk_right = vkb.VirtualKeyboard(pixel_width, pixel_height,
                                      KEYBOARD_WHIITE_N_KEYS)
        # Inicializar juego de ritmo
        rhythm_game = RhythmGame(num_keys=KEYBOARD_TOT_KEYS)
        game_mode = False  # False = modo libre, True = modo juego
        
        # Inicializar módulo de teoría
        lesson_manager = get_lesson_manager()
        theory_ui = TheoryUI(pixel_width * 2, pixel_height)
        theory_mode = False  # False = otros modos, True = modo teoría
        in_lesson = False  # True cuando está dentro de una lección
        current_lesson = None
        current_lesson_id = None
        
        # Inicializar UI de configuración
        config_ui = ConfigUI(pixel_width * 2, pixel_height)
        config_mode = False  # False = otros modos, True = modo configuración

        # ------------------------------
        # set up keyboards map
        # -----------------------------
        km = kbm.KeyboardMap(depth_threshold=config.DEPTH_THRESHOLD)

        # ------------------------------
        # set up angles
        # ------------------------------
        # cameras are the same, so only 1 needed
        angler = angles.Frame_Angles(pixel_width, pixel_height, angle_width,
                                     angle_height)
        angler.build_frame()

        left_detector = HandDetector(staticImageMode=False,
                                                  detectionCon=config.HAND_DETECTION_CONFIDENCE,
                                                  trackCon=config.HAND_TRACKING_CONFIDENCE)
        right_detector = HandDetector(staticImageMode=False,
                                                   detectionCon=config.HAND_DETECTION_CONFIDENCE,
                                                   trackCon=config.HAND_TRACKING_CONFIDENCE)

        # ------------------------------
        # set up synth
        # ------------------------------

        fs = fluidsynth.Synth()
        fs.start(driver='dsound') # Windows
        sfid = fs.sfload(config.SOUNDFONT_PATH)


        # 000-000 Yamaha Grand Piano
        fs.program_select(chan=0, sfid=sfid, bank=0, preset=0)

        # # 008-014 Church Bell
        # fs.program_select(chan=0, sfid=sfid, bank=8, preset=14)
        # # 008-026 Hawaiian Guitar
        # fs.program_select(chan=0, sfid=sfid, bank=8, preset=26)
        # # Standard
        # fs.program_select(chan=0, sfid=sfid, bank=128, preset=0)
        # # 000-103 Star Theme
        # fs.program_select(chan=0, sfid=sfid, bank=0, preset=103)

        # ------------------------------
        # stabilize
        # ------------------------------
        time.sleep(0.5)

        # variables
        # ------------------------------

        # length of target queues, positive target frames required
        # to reset set X,Y,Z,D
        queue_len = 3

        # target queues
        #fingers_left_queue, y1k = [], []
        #fingers_right_queue, y2k = [], []
        x_left_finger_screen_pos = 0
        y_left_finger_screen_pos = 0
        

        # mean values to stabilize the coordinates
        # x1m, y1m, x2m, y2m = 0, 0, 0, 0
        # X1_left_hand_ref, Y1_left_hand_ref = 0, 0
        
        # last positive target
        # from camera baseline midpoint
        X, Y, Z, D, = 0, 0, 0, 0
        delta_y = 0

        cycles = 0
        fps = 0
        start = time.time()
        display_dashboard = config.DISPLAY_DASHBOARD_DEFAULT
        finger_depths_dict = {}  # Inicializar para evitar referencias no definidas
        
        # Inicializar UI Helper
        ui_helper = UIHelper(pixel_width * 2, pixel_height)  # Ancho total de ambas cámaras
        
        # Optimización: cachear transformaciones de flip
        while True:
            cycles += 1
            # get frames - reducir wait en modo juego para mejor respuesta
            wait_time = 0.0 if game_mode else 0.1  # Sin delay en modo juego
            finished_left, frame_left = cam_left.next(black=True, wait=wait_time)
            finished_right, frame_right = cam_right.next(black=True, wait=wait_time)

            # Aplicar flip una sola vez al principio (Selfie point of view)
            frame_left = cv2.flip(frame_left, -1)
            frame_right = cv2.flip(frame_right, -1)

            hands_left_image = fingers_left_image = []
            hands_right_image = fingers_right_image = []

            # Detect Hands PRIMERO (sin dibujar todavía)
            hands_detected_left = left_detector.findHands(frame_left)
            if hands_detected_left:
                hands_left_image, fingers_left_image = \
                    left_detector.getFingerTipsPos()
            else:
                hands_left_image = fingers_left_image = []

            hands_detected_right = right_detector.findHands(frame_right)
            if hands_detected_right:
                hands_right_image, fingers_right_image = \
                    right_detector.getFingerTipsPos()

            # Dibujar teclado PRIMERO (debajo de las manos)
            vk_left.draw_virtual_keyboard(frame_left)
            
            # En modo juego: dibujar notas cayendo DESPUÉS del teclado pero ANTES de las manos
            if game_mode:
                rhythm_game.update()
                frame_left = rhythm_game.draw(
                    frame_left, 
                    vk_left.kb_x0, 
                    vk_left.kb_x1,
                    vk_left.white_key_width
                )
            
            # Dibujar manos AL FINAL (encima del teclado y notas)
            if hands_detected_left:
                left_detector.drawHands(frame_left)
                left_detector.drawTips(frame_left)

            if hands_detected_right:
                #vk_right.draw_virtual_keyboard(frame_right)
                right_detector.drawHands(frame_right)
                right_detector.drawTips(frame_right)

            # check 1: motion in both frames:
            if (len(fingers_left_image) > 0 and len(fingers_right_image) > 0):

                fingers_dist = []
                finger_depths_dict = {}  # Dict para pasar profundidades a KeyboardMap
                
                # Rectificar imágenes si usamos calibración estéreo
                if use_stereo_calibration and depth_estimator:
                    frame_left_rect, frame_right_rect = depth_estimator.rectify_images(frame_left, frame_right)
                else:
                    frame_left_rect, frame_right_rect = frame_left, frame_right
                
                for finger_left, finger_right in \
                    zip(fingers_left_image, fingers_right_image):
                    
                    if use_stereo_calibration and depth_estimator:
                        # ========== MÉTODO PRECISO: Calibración Estéreo ==========
                        try:
                            # Obtener posiciones de dedos
                            point_left = (finger_left[2], finger_left[3])
                            point_right = (finger_right[2], finger_right[3])
                            
                            # Triangular con calibración completa
                            result_3d = depth_estimator.triangulate_point(point_left, point_right)
                            
                            if result_3d is not None:
                                X_raw, Y_raw, Z_raw = result_3d
                                
                                # APLICAR FACTOR DE CORRECCIÓN DE PROFUNDIDAD (0.74)
                                # Basado en mediciones empíricas (43cm real / 58cm medido)
                                DEPTH_CORRECTION_FACTOR = 0.74
                                X_local = X_raw
                                Y_local = Y_raw
                                Z_local = Z_raw * DEPTH_CORRECTION_FACTOR
                                
                                # APLICAR SUAVIZADO TEMPORAL para reducir jitter
                                # Obtener ID único del dedo
                                finger_id = (finger_left[0], finger_left[1])
                                
                                # Inicializar buffer de suavizado si no existe
                                if not hasattr(depth_estimator, 'finger_position_history'):
                                    depth_estimator.finger_position_history = {}
                                if finger_id not in depth_estimator.finger_position_history:
                                    depth_estimator.finger_position_history[finger_id] = deque(maxlen=5)
                                
                                # Agregar posición actual al buffer
                                depth_estimator.finger_position_history[finger_id].append(
                                    (X_local, Y_local, Z_local)
                                )
                                
                                # Calcular promedio de últimas 5 posiciones
                                if len(depth_estimator.finger_position_history[finger_id]) > 0:
                                    history = np.array(list(depth_estimator.finger_position_history[finger_id]))
                                    X_local, Y_local, Z_local = np.mean(history, axis=0)
                                
                                D_local = Z_local  # Profundidad = coordenada Z
                                depth_corrected = D_local
                            else:
                                # Fallback si falla triangulación
                                X_local = Y_local = Z_local = D_local = 0
                                depth_corrected = 0
                        except Exception as e:
                            print(f"⚠ Error en triangulación estéreo: {e}")
                            X_local = Y_local = Z_local = D_local = 0
                            depth_corrected = 0
                    else:
                        # ========== MÉTODO ANTIGUO: Triangulación por ángulos ==========
                        # get angles from camera centers
                        xlangle, ylangle = angler.angles_from_center(
                            x = finger_left[2], y = finger_left[3],
                            top_left=True, degrees=True)
                        xrangle, yrangle = angler.angles_from_center(
                            x = finger_right[2], y = finger_right[3],
                            top_left=True, degrees=True)

                        # triangulate
                        X_local, Y_local, Z_local, D_local = angler.location(
                            camera_separation,
                            (xlangle, ylangle),
                            (xrangle, yrangle),
                            center=True,
                            degrees=True)
                        # angle normalization
                        delta_y = 0.006509695290859 * X_local * X_local + \
                            0.039473684210526 * -1 * X_local # + vkb_center_point_camera_dist
                        depth_corrected = D_local - delta_y
                    
                    fingers_dist.append(depth_corrected)
                    
                    # Guardar profundidad corregida para cada dedo
                    finger_id = (finger_left[0], finger_left[1])
                    finger_depths_dict[finger_id] = depth_corrected
                    
                    # if finger_left[0] == 0 and 
                    if finger_left[0] == 0 and finger_left[1] == left_detector.mpHands.HandLandmark.INDEX_FINGER_TIP:
                        x_left_finger_screen_pos =  finger_left[2]
                        y_left_finger_screen_pos = finger_left[3]
                        X = X_local
                        Y = Y_local
                        Z = Z_local
                        D = D_local
                        

                on_map, off_map = km.get_kayboard_map(
                    virtual_keyboard=vk_left,
                    fingertips_pos=fingers_left_image,
                    finger_depths=finger_depths_dict,  # Pasar profundidades 3D
                    keyboard_n_key=KEYBOARD_TOT_KEYS)
                
                if game_mode:
                    # Verificar aciertos cuando se presiona una tecla - optimizado
                    # Solo verificar teclas que están activas (más eficiente)
                    active_keys = np.where(on_map)[0]
                    for k_pos in active_keys:
                        hit_result = rhythm_game.check_hit(k_pos)
                        if hit_result:
                            print(f"Tecla {k_pos}: {hit_result}")
                            # Reproducir audio solo en modo juego
                            fs.noteon(
                                chan=0,
                                key=vk_left.note_from_key(k_pos)+octave_base,
                                vel=127*2//3)
                    
                    # NOTA: El dibujo del juego ya se hace arriba, antes de las manos
                else:
                    # Modo libre: reproducir audio en todas las teclas
                    if np.any(on_map):
                        for k_pos, on_key in enumerate(on_map):
                            if on_key:
                                fs.noteon(
                                    chan=0,
                                    key=vk_left.note_from_key(k_pos)+octave_base,
                                    vel=127*2//3)

                    if np.any(off_map):
                        for k_pos, off_key in enumerate(off_map):
                            if off_key:
                                fs.noteoff(
                                    chan=0,
                                    key=vk_left.note_from_key(k_pos)+octave_base
                                    )

            # display camera centers
            angler.frame_add_crosshairs(frame_left)
            angler.frame_add_crosshairs(frame_right)

            # Actualizar UI Helper
            ui_helper.update()
            
            # === MODO CONFIGURACIÓN ===
            if config_mode:
                # Mostrar panel de configuración
                if camera_in_front_of_you:
                    h_frames = np.concatenate((frame_right, frame_left), axis=1)
                else:
                    h_frames = np.concatenate((frame_left, frame_right), axis=1)
                
                h_frames = config_ui.draw_config_panel(h_frames)
                cv2.imshow(main_window_name, h_frames)
                
                # Manejar teclas del panel de configuración
                key = cv2.waitKey(1) & 0xFF
                
                # Navegación
                if key == 82 or key == ord('w') or key == ord('W'):  # Arriba
                    config_ui.navigate_up()
                elif key == 84 or key == ord('s') or key == ord('S'):  # Abajo
                    config_ui.navigate_down()
                
                # Ajustar valores
                elif key == 83 or key == ord('d') or key == ord('D'):  # Derecha (aumentar)
                    config_ui.increase_value()
                    # Aplicar cambios en tiempo real
                    km.depth_threshold = AppConfig.DEPTH_THRESHOLD
                    km.velocity_threshold = AppConfig.VELOCITY_THRESHOLD
                    km.velocity_enabled = AppConfig.VELOCITY_ENABLED
                    km.velocity_history_size = AppConfig.VELOCITY_HISTORY_SIZE
                elif key == 81 or key == ord('a') or key == ord('A'):  # Izquierda (disminuir)
                    config_ui.decrease_value()
                    # Aplicar cambios en tiempo real
                    km.depth_threshold = AppConfig.DEPTH_THRESHOLD
                    km.velocity_threshold = AppConfig.VELOCITY_THRESHOLD
                    km.velocity_enabled = AppConfig.VELOCITY_ENABLED
                    km.velocity_history_size = AppConfig.VELOCITY_HISTORY_SIZE
                
                # Presets (teclas 1-4)
                elif 49 <= key <= 52:  # Teclas 1-4
                    preset_idx = key - 49
                    if preset_idx < len(config_ui.presets):
                        preset_key = config_ui.presets[preset_idx]['key']
                        config_ui.apply_preset(preset_key)
                        config_ui.selected_preset = preset_idx
                        print(f"✓ Preset aplicado: {config_ui.presets[preset_idx]['name']}")
                        # Aplicar cambios en tiempo real
                        km.depth_threshold = AppConfig.DEPTH_THRESHOLD
                        km.velocity_threshold = AppConfig.VELOCITY_THRESHOLD
                        km.velocity_enabled = AppConfig.VELOCITY_ENABLED
                        km.velocity_history_size = AppConfig.VELOCITY_HISTORY_SIZE
                
                # Salir
                elif key == ord('q') or key == ord('Q') or key == 27:  # Q o ESC
                    config_mode = False
                    config_ui.reset_selection()
                    print("Modo configuración desactivado")
                
                continue  # Saltar el resto del loop principal
            
            # === MODO TEORÍA ===
            if theory_mode:
                if in_lesson and current_lesson:
                    # Ejecutar lección activa
                    frame_left, frame_right, continue_lesson = current_lesson.run(
                        frame_left, frame_right, vk_left, fs,
                        left_detector, right_detector
                    )
                    
                    if not continue_lesson:
                        # Salir de la lección
                        current_lesson.stop()
                        in_lesson = False
                        current_lesson = None
                        print("Saliendo de la lección...")
                else:
                    # Mostrar menú de lecciones
                    lessons = lesson_manager.get_all_lessons()
                    if camera_in_front_of_you:
                        h_frames = np.concatenate((frame_right, frame_left), axis=1)
                    else:
                        h_frames = np.concatenate((frame_left, frame_right), axis=1)
                    
                    h_frames = theory_ui.draw_lesson_menu(h_frames, lessons)
                    cv2.imshow(main_window_name, h_frames)
                    
                    # Manejar teclas del menú
                    key = cv2.waitKey(1) & 0xFF
                    # Flecha arriba (múltiples códigos para compatibilidad)
                    if key == 82 or key == ord('w') or key == ord('W'):  # Flecha arriba o W
                        theory_ui.navigate_up(len(lessons))
                        print(f"Navegando: lección {theory_ui.get_selected_index() + 1}/{len(lessons)}")
                    # Flecha abajo
                    elif key == 84 or key == ord('s') or key == ord('S'):  # Flecha abajo o S
                        theory_ui.navigate_down(len(lessons))
                        print(f"Navegando: lección {theory_ui.get_selected_index() + 1}/{len(lessons)}")
                    # Números 1-9 para selección directa
                    elif 49 <= key <= 57:  # Teclas 1-9
                        selected_idx = key - 49  # Convertir a índice (0-8)
                        if 0 <= selected_idx < len(lessons):
                            lesson_id, lesson = lessons[selected_idx]
                            current_lesson = lesson
                            current_lesson_id = lesson_id
                            current_lesson.start()
                            in_lesson = True
                            print(f"Iniciando lección: {lesson.name}")
                    # ENTER
                    elif key == 13:  # ENTER
                        selected_idx = theory_ui.get_selected_index()
                        if 0 <= selected_idx < len(lessons):
                            lesson_id, lesson = lessons[selected_idx]
                            current_lesson = lesson
                            current_lesson_id = lesson_id
                            current_lesson.start()
                            in_lesson = True
                            print(f"Iniciando lección: {lesson.name}")
                    elif key == ord('q') or key == ord('Q'):
                        theory_mode = False
                        theory_ui.reset_selection()
                        print("Saliendo del modo teoría...")
                    elif key == 27:  # ESC
                        theory_mode = False
                        theory_ui.reset_selection()
                    elif key != 255:  # Mostrar código de cualquier otra tecla para debug
                        print(f"Tecla presionada en menú teoría: código {key}")
                    continue  # Saltar el resto del loop principal
            
            # Combinar frames antes de procesar UI
            if camera_in_front_of_you:
                h_frames = np.concatenate((frame_right, frame_left), axis=1)
            else:
                h_frames = np.concatenate((frame_left, frame_right), axis=1)
            
            # Mostrar pantalla de bienvenida si es necesario
            if ui_helper.show_instructions:
                welcome_frame = np.zeros((pixel_height, pixel_width * 2, 3), dtype=np.uint8)
                welcome_frame = ui_helper.draw_welcome_screen(welcome_frame)
                cv2.imshow(main_window_name, welcome_frame)
                
                # Esperar a que se presione una tecla para continuar
                key = cv2.waitKey(1) & 0xFF
                if key != 255:  # Cualquier tecla
                    ui_helper.show_instructions = False
                    ui_helper.frame_count = ui_helper.instructions_timeout  # No volver a mostrar
                continue

            if display_dashboard:
                # Display dashboard data
                fps1 = int(cam_left.current_frame_rate)
                fps2 = int(cam_right.current_frame_rate)
                cps_avg = int(round_half_up(fps))  # Average Cycles per second
                text = 'X: {:3.1f}\nY: {:3.1f}\nZ: {:3.1f}\nD: {:3.1f}\nDr: {:3.1f}\nDepth Thr: {:.2f}\nFPS:{}/{}\nCPS:{}'.format(X, Y, Z, D, D-delta_y, km.depth_threshold, fps1, fps2, cps_avg)
                lineloc = 0
                lineheight = 30
                for t in text.split('\n'):
                    lineloc += lineheight
                    cv2.putText(frame_left,
                                t,
                                (10, lineloc),              # location
                                cv2.FONT_HERSHEY_PLAIN,     # font
                                # cv2.FONT_HERSHEY_SIMPLEX, # font
                                1.5,                        # size
                                (0, 255, 0),                # color
                                2,                          # line width
                                cv2.LINE_AA,
                                False)
                
                # Re-combinar frames después de actualizar el izquierdo
                if camera_in_front_of_you:
                    h_frames = np.concatenate((frame_right, frame_left), axis=1)
                else:
                    h_frames = np.concatenate((frame_left, frame_right), axis=1)

            # Display current target
            # if fingers_left_queue:
            #     frame_add_crosshairs(frame_left, x1m, y1m, 24)
            #     frame_add_crosshairs(frame_right, x2m, y2m, 24)

            # if fingers_left_queue:
            #     frame_add_crosshairs(frame_left, x1m, y1m, 24)
            #     frame_add_crosshairs(frame_right, x2m, y2m, 24)
            # if X > 0 and Y > 0:
            frame_add_crosshairs(frame_left, x_left_finger_screen_pos, y_left_finger_screen_pos, 24)
            # Pendiente : ...frame_add_crosshairs(frame_right, x_left_finger_screen_pos, y_left_finger_screen_pos, 24)



            # Display frames
            cv2.imshow(main_window_name, h_frames)



            if (cycles % 10 == 0):
                # End time
                end = time.time()
                # Time elapsed
                seconds = end - start
                # print ("Time taken : {0} seconds".format(seconds))
                # Calculate frames per second
                fps = 10 / seconds
                start = time.time()

            # Detect control keys
            key = cv2.waitKey(1) & 0xFF
            if cv2.getWindowProperty(
                main_window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
            elif key == ord('q'):
                break
            elif key == ord('c') or key == ord('C'):  # ========== MODO CONFIGURACIÓN ==========
                # Solo toggle si NO estamos en config_mode, theory_mode o game_mode
                if not config_mode and not theory_mode and not game_mode:
                    config_mode = True
                    print("\n=== MODO CONFIGURACIÓN ACTIVADO ===")
                    print("Controles:")
                    print("  W/S o ↑/↓: Navegar parámetros")
                    print("  A/D o ←/→: Disminuir/Aumentar valor")
                    print("  1-4: Aplicar preset (Suave/Normal/Estricto/Clásico)")
                    print("  Q/ESC: Salir")
                    print("=====================================\n")
            elif key == ord('d'):
                if display_dashboard:
                    display_dashboard = False
                else:
                    display_dashboard = True
            elif key == ord('g'):  # ========== NUEVA TECLA ==========
                game_mode = True
                rhythm_game.start_game(TUTORIAL_FACIL)
                print("¡Juego de ritmo iniciado! Presiona 'f' para volver al modo libre")
                ui_helper.reset_instructions()  # Mostrar instrucciones del juego
            elif key == ord('f'):  # ========== NUEVA TECLA ==========
                # Detener juego si está activo
                if game_mode and rhythm_game.is_playing:
                    rhythm_game.stop_game()
                game_mode = False
                theory_mode = False
                print("Modo libre activado")
                ui_helper.reset_instructions()  # Mostrar instrucciones del modo libre
            elif key == ord('l'):  # ========== MODO TEORÍA ==========
                theory_mode = True
                game_mode = False
                if rhythm_game.is_playing:
                    rhythm_game.stop_game()
                theory_ui.reset_selection()
                print("¡Modo Teoría activado! Selecciona una lección. Presiona Q para salir.")
            elif key == ord('t'):  # Subir nivel de mesa (ESTÉREO: aumentar umbral de profundidad)
                new_threshold = km.depth_threshold + 0.2
                km.set_depth_threshold(new_threshold)
                print(f"Umbral de profundidad aumentado a: {new_threshold:.2f} cm")
            elif key == ord('b'):  # Bajar nivel de mesa (ESTÉREO: disminuir umbral de profundidad)
                new_threshold = max(0.5, km.depth_threshold - 0.2)
                km.set_depth_threshold(new_threshold)
                print(f"Umbral de profundidad disminuido a: {new_threshold:.2f} cm")
            elif key == ord('p'):  # Mostrar profundidades detectadas
                if display_dashboard:
                    print(f"Profundidades detectadas (D - delta_y):")
                    for fid, depth in finger_depths_dict.items():
                        print(f"  Dedo {fid}: {depth:.2f} cm")
            elif key == 27 and in_lesson:  # ESC dentro de lección
                if current_lesson:
                    current_lesson.stop()
                in_lesson = False
                current_lesson = None
                print("Volviendo al menú de lecciones...")
            elif in_lesson and current_lesson:  # Pasar teclas a la lección activa
                current_lesson.handle_key(key, fs, octave_base)
            elif key != 255:
                print('KEY PRESS:', [chr(key)])

    # ------------------------------
    # full error catch
    # ------------------------------
    except Exception:
        print(traceback.format_exc())

    # ------------------------------
    # close all
    # ------------------------------

    # Fluidsynth
    try:
        fs.delete()
    except Exception:
        pass
    # close camera1
    try:
        cam_left.stop()
    except Exception:
        pass

    # close camera2
    try:
        cam_right.stop()
    except Exception:
        pass

    # kill frames
    cv2.destroyAllWindows()

    # done
    print('DONE')


# ------------------------------
# Call to Main
# ------------------------------

if __name__ == '__main__':
    main()

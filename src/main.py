#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import traceback
import cv2
import numpy as np
import fluidsynth
from collections import deque
import sys
import os

# --- Vision ---
from src.vision import video_thread, angles
from src.vision.hand_detector import HandDetector
from src.vision import keyboard_mapper as kbm
from src.vision import load_depth_estimator
from src.vision.stereo_config import StereoConfig

# --- Core (Recursos Persistentes) ---
from src.core.persistent_resources import get_resources, initialize_resources, cleanup_resources

# --- Calibration ---
from src.calibration import run_qt_calibration
from src.calibration.calibration_config import CalibrationConfig
from src.calibration.qt_calibration_summary import show_calibration_summary, CalibrationSummaryDialog

# --- Piano ---
from src.piano import virtual_keyboard as vkb
from src.piano.virtual_keyboard import VirtualKeyboard

# --- Gameplay ---
from src.gameplay.rythm_game import RhythmGame
from src.gameplay.song_chart import TUTORIAL_FACIL

# --- UI ---
from src.ui.ui_helper import UIHelper
#from src.ui.qt_initial_menu import show_initial_menu
from src.ui.qt_main_menu import show_main_menu
from src.ui.qt_theory_menu import show_theory_menu
from src.ui.qt_lesson_window import show_lesson_window
from src.ui.qt_songs_menu import show_songs_menu
from src.ui.qt_song_window import show_song_window
from src.ui.qt_free_mode_window import show_free_mode_window

# --- Theory ---
from src.theory import get_lesson_manager
# --- Songs ---
from src.songs.song_manager import get_all_songs, get_song_manager

# --- Config UI ---
# ConfigUI removed
from src.config.app_config import AppConfig

# --- Common ---
from src.utils import round_half_up

# ========== CARGAR CONFIGURACIÓN DE CÁMARAS ==========
# IMPORTANTE: Debe ejecutarse ANTES de crear instancia de StereoConfig
# para aplicar los IDs configurados por el usuario en la UI
StereoConfig.load_camera_ids_from_calibration()
# ======================================================

def frame_add_crosshairs(frame, x, y, r=20, lc=(0, 0, 255), cc=(0, 0, 255), lw=2, cw=1):

    x = int(round(x, 0))
    y = int(round(y, 0))
    r = int(round(r, 0))

    cv2.line(frame, (x, y-r*2), (x, y+r*2), lc, lw)
    cv2.line(frame, (x-r*2, y), (x+r*2, y), lc, lw)

    cv2.circle(frame, (x, y), r, cc, cw)

def show_calibration_menu(ui_helper, pixel_width, pixel_height):
    return show_initial_menu()

def run_calibration_process(ui_helper, pixel_width, pixel_height, config, force_recalibration=False):
    """Ejecuta el proceso de calibración con el nuevo sistema profesional"""
    # CalibrationConfig ya está importado globalmente
    try:
        # ========== VERIFICAR QUÉ FASES ESTÁN COMPLETAS ==========
        has_phase1 = False
        has_phase2 = False
        summary = None
        # force_recalibration ya viene como argumento
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
            # Mostrar interfaz PyQt6
            action = show_calibration_summary(summary)
            
            if action == CalibrationSummaryDialog.ACTION_START:
                print("\n[EXITO] Usando calibración existente - Iniciando juego...")
                return True
            elif action == CalibrationSummaryDialog.ACTION_RECALIBRATE_ALL:
                print("\n[INFO] Iniciando recalibración...")
                success = run_qt_calibration(
                    cam_left_id=config.LEFT_CAMERA_SOURCE,
                    cam_right_id=config.RIGHT_CAMERA_SOURCE
                )
                return success
                    
            else: # EXIT
                return False
            
            # OLD CODE DISABLED
            if False:
                pass
                
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
                    print("\n[INFO] Re-calibrando SOLO FASE 2...")
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
                        print(f"[ALERTA] Error al modificar calibración: {e}")
                    
                    # Actualizar variables de estado
                    force_recalibration = True
                    recalibrate_phase2_only = True
                    has_phase2 = False  # ← CRUCIAL: Marcar que NO hay Fase 2
                    pass  # Salir del while para continuar con calibración
                
                elif key == ord('r') or key == ord('R'):  # Re-calibrar TODO
                    cv2.destroyWindow(window_name)
                    print("\n[ALERTA] Iniciando RE-CALIBRACIÓN COMPLETA...")
                    print("  (Fase 1 + Fase 2 desde cero)")
                    force_recalibration = True
                    recalibrate_phase2_only = False
                    pass  # Salir del while para continuar con calibración
                
                elif key == 27:  # ESC
                    cv2.destroyWindow(window_name)
                    return False
        
        # DUPLICATE BLOCK DISABLED
        if False and (not has_phase1 or not has_phase2 or force_recalibration):
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
                print("[INFO] RE-CALIBRANDO SOLO FASE 2")
                print("="*70)
                print("[INFO] Fase 1 existente se mantendrá")
                print(f"  Izquierda: {summary['error_left']:.4f} px" if isinstance(summary['error_left'], float) else "  Izquierda: OK")
                print(f"  Derecha: {summary['error_right']:.4f} px" if isinstance(summary['error_right'], float) else "  Derecha: OK")
                print("\n[INFO] Iniciando SOLO captura de pares estéreo...")
                print("[TIP] TIP: Captura 15 pares y mantén tablero INMÓVIL")
                print("="*70 + "\n")
                
                from src.calibration import run_qt_calibration
                
                # Ejecutar calibración con PyQt6
                success = run_qt_calibration(
                    cam_left_id=config.LEFT_CAMERA_SOURCE,
                    cam_right_id=config.RIGHT_CAMERA_SOURCE
                )
                
                if not success:
                    print("[ERROR] Re-calibración de Fase 2 fallida o cancelada")
                    return False
                
                print("\n" + "="*70)
                print("✓ FASE 2 RE-CALIBRADA EXITOSAMENTE")
                print("="*70)
                print("   Datos guardados correctamente")
                print("   Puedes cerrar esta ventana y ejecutar el piano")
                print("="*70)
                
                # NO RETORNAR - Continuar para que el usuario vea el mensaje
                # El usuario debe presionar una tecla para continuar
                # input("\nPresiona ENTER para cerrar...")
                
                return True
            
            # ========== CASO 2B: SOLO FASE 1 COMPLETA, FALTA FASE 2 ==========
            elif has_phase1 and not has_phase2 and not force_recalibration:
                print("\n" + "="*70)
                print("[EXITO] FASE 1 COMPLETA - Saltando a Fase 2")
                print("="*70)
                print(f"  Izquierda: {summary['error_left']:.4f} px" if isinstance(summary['error_left'], float) else "  Izquierda: OK")
                print(f"  Derecha: {summary['error_right']:.4f} px" if isinstance(summary['error_right'], float) else "  Derecha: OK")
                print("\n[INFO] Iniciando Fase 2 directamente...")
                print("="*70 + "\n")
            
            # ========== CASO 3: NADA COMPLETO O RE-CALIBRACIÓN COMPLETA SOLICITADA ==========
            else:
                print("\n" + "="*70)
                print("INICIANDO CALIBRACIÓN COMPLETA (FASE 1 + FASE 2)")
                print("="*70)
            
            # Importar el manager v2 (si no se hizo antes)
            if not recalibrate_phase2_only:
                from src.calibration import run_qt_calibration
                
                # Ejecutar calibración con PyQt6
                success = run_qt_calibration(
                    cam_left_id=config.LEFT_CAMERA_SOURCE,
                    cam_right_id=config.RIGHT_CAMERA_SOURCE
                )
                
                if not success:
                    print("[ERROR] Calibración fallida o cancelada")
                    return False
                
                print("\n" + "="*70)
                print("✓ CALIBRACIÓN COMPLETA EXITOSA")
                print("="*70)
            
            return True
        
    except Exception as e:
        print(f"[ERROR] Error durante calibración: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Crear QApplication una sola vez para todo el programa
    from PyQt6.QtWidgets import QApplication
    import sys
    qt_app = QApplication.instance()
    if qt_app is None:
        qt_app = QApplication(sys.argv)
    
    # Cargar configuración estéreo centralizada (UNA VEZ)
    config = StereoConfig()
    
    # Dimensiones para la interfaz
    pixel_width = config.PIXEL_WIDTH
    pixel_height = config.PIXEL_HEIGHT
    
    # Inicializar UI Helper
    ui_helper_menu = UIHelper(pixel_width * 2, pixel_height)
    ui_helper_menu.show_instructions = False
    
    # ====== INICIALIZAR RECURSOS PERSISTENTES ANTES DEL MENÚ ======
    print("\n" + "="*60)
    print("[INFO] PIANO VIRTUAL - INICIANDO")
    print("="*60)
    
    resources = get_resources()
    
    # Intentar inicializar recursos ANTES de mostrar el menú
    resources_initialized = initialize_resources(config)
    
    if not resources_initialized:
        print("\nADVERTENCIA: Algunos recursos no estan disponibles")
        print("   Puedes ir a Configuracion > Camaras para ajustar")
        print("   El programa continuara con funcionalidad limitada\n")
    else:
        print("\nSistema listo. Abriendo menu principal...\n")
    
    while True:  # <--- BUCLE GLOBAL
        try:
            print("\n--- Menú Principal ---")
            # MENÚ PRINCIPAL (PyQt6)
            start_mode = show_main_menu()   # "rhythm", "free", "theory", "config", "exit"
            print(f"--- DEBUG: Modo seleccionado: {start_mode} ---")
            
            # Inicializar lesson_manager y variables de teoría
            lesson_manager_instance = get_lesson_manager()
            theory_mode = False
            in_lesson = False
            in_lesson = False
            current_lesson = None
            current_lesson_index = None
            
            # Inicializar song_manager y variables de rhythm
            song_manager_instance = get_song_manager()
            rhythm_mode = False
            in_song = False
            current_song = None
            
            # Manejar selección de teoría con menú PyQt6
            if start_mode and start_mode.startswith("theory_"):
                # Si viene desde el menú principal con lección específica
                target_lesson_id = start_mode.replace("theory_", "")
                lesson = lesson_manager_instance.get_lesson(target_lesson_id)
                
                if lesson:
                    current_lesson = lesson
                    current_lesson.start()
                    in_lesson = True
                    theory_mode = True
                    
                    # Calcular index
                    try:
                        current_lesson_index = lesson_manager_instance._lesson_order.index(target_lesson_id)
                    except:
                        current_lesson_index = None
                        
                    print(f"[EXITO] Modo TEORÍA iniciado: Lección '{lesson.name}'")
                else:
                    print(f"[ALERTA] Lección '{target_lesson_id}' no encontrada.")
            
            # Si solo se seleccionó "theory" sin lección específica, mostrar menú PyQt6
            elif start_mode == "theory":
                # RECARGAR LECCIONES para detectar archivos nuevos (05, 06...)
                lesson_manager_instance.reload_lessons()
                lessons = lesson_manager_instance.get_all_lessons()
                
                if lessons:
                    selected_lesson_id = show_theory_menu(lessons)
                    
                    if selected_lesson_id:
                        lesson = lesson_manager_instance.get_lesson(selected_lesson_id)
                        if lesson:
                            current_lesson = lesson
                            current_lesson.start()
                            in_lesson = True
                            theory_mode = True
                            
                            # Calcular index
                            try:
                                current_lesson_index = lesson_manager_instance._lesson_order.index(selected_lesson_id)
                            except:
                                current_lesson_index = None
                                
                            print(f"[EXITO] Lección seleccionada: '{lesson.name}'")
                    else:
                        print("Regresando al menú principal...")
                        continue  # Volver al inicio del loop global
                else:
                    print("[ALERTA] No hay lecciones disponibles.")
            
            # Manejar selección de rhythm con menú PyQt6
            elif start_mode == "rhythm":
                songs_dict = song_manager_instance.get_all_songs()
                
                if songs_dict:
                    selected_song_name = show_songs_menu(songs_dict)
                    
                    if selected_song_name:
                        song = song_manager_instance.get_song(selected_song_name)
                        if song:
                            current_song = song
                            in_song = True
                            rhythm_mode = True
                            print(f"[EXITO] Canción seleccionada: '{song.name}'")
                    else:
                        print("Regresando al menú principal...")
                        continue  # Volver al inicio del loop global
                else:
                    print("[ALERTA] No hay canciones disponibles.")
                    continue
            
            if start_mode is None or start_mode == "exit":
                print("Saliendo desde el menú principal...")
                break

            # Modo inicial por defecto (rhythm / free / theory / config)
            initial_mode = start_mode

            # Si eligió opciones de configuración
            if start_mode == "config_calibration":
                print("Abriendo calibracion...")
                # Usamos imports globales (CalibrationConfig, CalibrationSummaryDialog, show_calibration_summary)
                if CalibrationConfig.calibration_exists():
                    # Hay calibración existente: mostrar resumen
                    summary = CalibrationConfig.get_calibration_summary()
                    action = show_calibration_summary(summary)
                    
                    if action == CalibrationSummaryDialog.ACTION_RECALIBRATE_ALL:
                        print("Iniciando re-calibracion...")
                        # 1. DETENER CÁMARAS ACTUALES
                        if resources_initialized:
                            resources.stop_cameras()
                            
                        # 2. EJECUTAR CALIBRACIÓN
                        success = run_calibration_process(ui_helper_menu, pixel_width, pixel_height, config, force_recalibration=True)
                        
                        # 3. REINICIAR CÁMARAS
                        if resources_initialized:
                            print("Reiniciando cámaras y profundidad...")
                            resources.restart_cameras(config)
                            if success:
                                resources.reload_depth_estimator()
                        
                        if not success:
                            print("Calibracion cancelada.")
                else:
                    # No hay calibración: iniciar proceso de calibración
                    print("No hay calibracion guardada. Iniciando proceso...")
                    # 1. DETENER CÁMARAS ACTUALES
                    if resources_initialized:
                        resources.stop_cameras()
                        
                    # 2. EJECUTAR CALIBRACIÓN
                    success = run_calibration_process(ui_helper_menu, pixel_width, pixel_height, config, force_recalibration=True)
                    
                    # 3. REINICIAR CÁMARAS
                    if resources_initialized:
                        print("Reiniciando cámaras y profundidad...")
                        resources.restart_cameras(config)
                        if success:
                            resources.reload_depth_estimator()
                            
                    if not success:
                        print("Calibracion cancelada.")
                
                # Volver al menú principal
                continue
                
            elif start_mode == "config_skip":
                print("Usando valores por defecto (sin calibración)")
                continue
                
            elif start_mode == "config_advanced":
                print("Abriendo configuración avanzada de algoritmos...")
                from src.ui.qt_advanced_config import show_advanced_config
                from src.vision.algorithms import sync_algorithms_from_config
                
                # Callback para sincronizar cambios
                def on_algo_config_change(new_config):
                    sync_algorithms_from_config()
                    print("Configuracion de algoritmos actualizada")
                
                show_advanced_config(on_config_change=on_algo_config_change)
                continue
            
            elif start_mode == "config_cameras":
                print("Abriendo configuracion de camaras...")
                from src.ui.qt_camera_config import show_camera_config
                
                if show_camera_config():
                    # Recargar la configuración desde calibration.json
                    StereoConfig.load_calibration()
                    print(f"Camaras: LEFT={StereoConfig.LEFT_CAMERA_SOURCE}, RIGHT={StereoConfig.RIGHT_CAMERA_SOURCE}")
                    
                    # Reiniciar las cámaras con la nueva configuración
                    if resources_initialized:
                        print("Reiniciando camaras con nueva configuracion...")
                        resources.restart_cameras(config)
                        print("OK Camaras reiniciadas")
                continue
                
            # ------------------------------
            # OBTENER RECURSOS PERSISTENTES (ya inicializados)
            # ------------------------------
            cam_left, cam_right = resources.get_cameras()
            left_detector, right_detector = resources.get_detectors()
            fs = resources.get_synth()
            depth_estimator = resources.depth_estimator
            use_stereo_calibration = resources.use_stereo_calibration
            
            # [CRITICAL UPDATE] Actualizar dimensiones con la resolución REAL de la cámara
            if cam_left and cam_left.is_available():
                real_w = cam_left.get_curr_config_widht()
                real_h = cam_left.get_curr_config_height()
                if real_w > 0 and real_h > 0:
                    print(f"[INFO] Actualizando resolución a: {real_w}x{real_h}")
                    pixel_width = real_w
                    pixel_height = real_h
            
            # Configuración de cámaras
            camera_separation = config.CAMERA_SEPARATION
            camera_in_front_of_you = config.CAMERA_IN_FRONT_OF_YOU
            vkb_center_point_camera_dist = config.VKB_CENTER_DISTANCE
            angle_width = config.ANGLE_WIDTH
            angle_height = config.ANGLE_HEIGHT
            
            if camera_in_front_of_you:
                main_window_name = 'In fron of you: rigth+left cam'
            else:
                main_window_name = 'Same Point of View: left+rigth cam'

            # cv2.namedWindow(main_window_name)
            # cv2.moveWindow(main_window_name, (pixel_width//2), (pixel_height//2))



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

            # ==============================================================================
            # [AR MODE] APLICAR CALIBRACIÓN AR AL MODO JUEGO
            # Esto transporta la perspectiva 3D de la Fase 4C al juego real
            # ==============================================================================
            try:
                calib_data = CalibrationConfig()
                
                if calib_data.virtual_table_corners and len(calib_data.virtual_table_corners) == 4:
                    print("[MAIN] 🔮 Aplicando Perspectiva AR al Teclado de Juego...")
                    
                    # 1. Obtener esquinas guardadas y ajustarlas a la resolución actual
                    corners = [StereoConfig.transform_point_for_display(p, pixel_width, pixel_height) 
                              for p in calib_data.virtual_table_corners]
                    
                    # 2. Calcular la Matriz de Transformación
                    #    Origen: Rectángulo plano perfecto del software
                    src_pts = np.float32([
                        [vk_left.kb_x0, vk_left.kb_y0],
                        [vk_left.kb_x1, vk_left.kb_y0],
                        [vk_left.kb_x1, vk_left.kb_y1],
                        [vk_left.kb_x0, vk_left.kb_y1]
                    ])
                    #    Destino: Trapezoide real de tu mesa
                    dst_pts = np.float32(corners)
                    
                    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    
                    # 3. Aplicar a los teclados de juego
                    for vk in [vk_left, vk_right]:
                        vk.M_inv = np.linalg.inv(matrix)
                        vk.ar_mode_active = True
                        
                        # Generar los polígonos visuales para dibujar
                        vk.screen_key_polygons = []
                        for k in vk.generate_logical_key_geometries():
                            pts_dst = cv2.perspectiveTransform(k['pts'], matrix)[0]
                            vk.screen_key_polygons.append({
                                'id': k['id'], 
                                'black': k['black'], 
                                'contour': pts_dst.astype(np.int32)
                            })
                    print("[MAIN] ✓ Teclado alineado con la mesa real.")
                else:
                    print("[MAIN] ⚠️ No se encontró calibración AR. Usando teclado plano estándar.")
            except Exception as e:
                print(f"[MAIN] ⚠️ Error aplicando AR: {e}")
                # import traceback (Removed to fix UnboundLocalError)
                traceback.print_exc()
            # ==============================================================================
            
            # Inicializar sistemas
            rhythm_game = RhythmGame(num_keys=KEYBOARD_TOT_KEYS)
            lesson_manager = lesson_manager_instance  # Usar la instancia ya creada
            # config_ui removed
            km = kbm.KeyboardMap(depth_threshold=config.DEPTH_THRESHOLD)
            
            # Inicializar AlgorithmManager (singleton global para algoritmos)
            from src.vision.algorithms import get_algorithm_manager
            algorithm_manager = get_algorithm_manager()
            
            # Inicializar ángulos
            angler = angles.Frame_Angles(pixel_width, pixel_height, angle_width,
                                        angle_height)
            angler.build_frame()

            # Variables de estado (algunas ya inicializadas arriba)
            game_mode = False
            # theory_mode ya inicializado arriba
            # in_lesson ya inicializado arriba
            # current_lesson ya inicializado arriba
            config_mode = False
            
            # Variables de módulo de teoría (ya no necesarias, se usan las de arriba)
            # theory_mode, in_lesson, current_lesson ya están definidos
            
            # Inicializar UI de configuración
            # config_ui removed
            config_mode = False  # False = otros modos, True = modo configuración

            # ACTIVAR MODO INICIAL

            if initial_mode == "free":
                game_mode = False
                theory_mode = False
                rhythm_mode = False
                print("Modo LIBRE iniciado desde el menú principal.")

            elif initial_mode == "config":
                game_mode = False
                print("Configuración terminada. Iniciando en modo libre.")

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
            ui_helper.show_instructions = False

            
            print("--- DEBUG: Entrando al bucle de video (While True) ---")
            # Optimización: cachear transformaciones de flip
            while True:
                cycles += 1
                if cycles % 100 == 0:
                    print(f"--- DEBUG: Ciclo {cycles} - Ejecutando... ---")

                # IMPORTANTE: Cambia 0.0 por 0.001. 
                # 0.0 puede causar bloqueo total si la cámara demora un milisegundo.
                wait_time = 0.001  # Siempre rápido para evitar lag en UI
                
                if cam_left and cam_right:
                    finished_left, frame_left = cam_left.next(black=True, wait=wait_time)
                    finished_right, frame_right = cam_right.next(black=True, wait=wait_time)
                else:
                    # Fallback si no hay cámaras: generar frames negros
                    time.sleep(0.03) # Simular 30 FPS
                    frame_left = np.zeros((pixel_height, pixel_width, 3), np.uint8)
                    frame_right = frame_left.copy()
                    finished_left = True
                    finished_right = True

                # Aplicar rotación/espejo para VISUALIZACIÓN
                # IMPORTANTE: Usar apply_display_transform() para consistencia con calibración
                # La Fase 4 (TABLE_CORNERS) se calibró con frame rotado 180°
                
                # Solo aplicar si tenemos frames validos
                if frame_left is not None and frame_right is not None:
                    # SIEMPRE aplicar rotación 180° para coincidir con calibración
                    # Esto asegura que las coordenadas de dedos coincidan con TABLE_CORNERS
                    frame_left = StereoConfig.apply_display_transform(frame_left)
                    frame_right = StereoConfig.apply_display_transform(frame_right)

                hands_left_image = fingers_left_image = []
                hands_right_image = fingers_right_image = []

                # Detect Hands PRIMERO (sin dibujar todavía)
                if left_detector:
                    hands_detected_left = left_detector.findHands(frame_left)
                else:
                    hands_detected_left = None
                    
                # Obtener dimensiones actuales
                h_curr, w_curr = frame_left.shape[:2]
                
                if hands_detected_left:
                    # Pasar dimensiones explícitas
                    hands_left_image, fingers_left_image = \
                        left_detector.getFingerTipsPos(img_width=w_curr, img_height=h_curr)
                else:
                    hands_left_image = fingers_left_image = []

                if right_detector:
                    hands_detected_right = right_detector.findHands(frame_right)
                else:
                    hands_detected_right = None
                if hands_detected_right:
                    # Pasar dimensiones explícitas
                    hands_right_image, fingers_right_image = \
                        right_detector.getFingerTipsPos(img_width=w_curr, img_height=h_curr)

                # Dibujar teclado PRIMERO (debajo de las manos)
                vk_left.draw_virtual_keyboard(frame_left)
                
                # En modo juego: dibujar notas cayendo DESPUÉS del teclado pero ANTES de las manos
                if game_mode:
                    if cycles % 100 == 0: print("--- DEBUG: Actualizando lógica de RHYTHM GAME ---")
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
                                
                                # 1. Rectificar puntos
                                pt_l_rect = depth_estimator.rectify_point(point_left, 'left')
                                pt_r_rect = depth_estimator.rectify_point(point_right, 'right')
                                
                                # Triangular con calibración completa
                                result_3d = depth_estimator.triangulate_point(pt_l_rect, pt_r_rect, method='DLT')
                                
                                if result_3d is not None:
                                    X_raw, Y_raw, Z_raw = result_3d
                                    
                                    # NOTA: El factor de corrección ya se aplica dentro de DepthEstimator
                                    X_local = X_raw
                                    Y_local = Y_raw
                                    Z_local = Z_raw 
                                    
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
                        
                        # Guardar profundidad RELATIVA para cada dedo
                        # FIX: Convertir de absoluta (distancia desde cámara) a relativa (distancia desde mesa)
                        finger_id = (finger_left[0], finger_left[1])
                        
                        # Obtener distancia del teclado desde calibración (Fase 3)
                        keyboard_distance = None
                        if depth_estimator and hasattr(depth_estimator, 'keyboard_distance_cm'):
                            keyboard_distance = depth_estimator.keyboard_distance_cm
                        
                        if keyboard_distance is not None:
                            # Calcular profundidad relativa: positivo = en el aire, negativo = presionando
                            rel_depth = depth_corrected - keyboard_distance
                            finger_depths_dict[finger_id] = rel_depth
                        else:
                            # Sin calibración de profundidad: usar valor por defecto (42cm típico)
                            rel_depth = depth_corrected - 42.0
                            finger_depths_dict[finger_id] = rel_depth
                        
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
                
                # === MODO TEORÍA (LECCIONES) ===
                if theory_mode and in_lesson and current_lesson:
                    # Abrir ventana PyQt6 para la lección (bloquea hasta que termine)
                    print(f"Iniciando ventana de lección: {current_lesson.name}")
                    
                    # Llamar a la ventana PyQt6 (esto bloquea hasta que termine la lección)
                    lesson_completed = show_lesson_window(
                        lesson=current_lesson,
                        camera_left=cam_left,
                        camera_right=cam_right,
                        synth=fs,
                        virtual_keyboard=vk_left,
                        hand_detector_left=left_detector,
                        hand_detector_right=right_detector,
                        keyboard_mapper=km,
                        angler=angler,
                        depth_estimator=depth_estimator,
                        octave_base=octave_base,
                        keyboard_total_keys=KEYBOARD_TOT_KEYS,
                        camera_separation=camera_separation,
                        lesson_index=current_lesson_index # Nuevo argumento para guardar progreso
                    )
                    # Cuando la ventana se cierre, limpiar estado
                    current_lesson.stop()
                    in_lesson = False
                    current_lesson = None
                    
                    print("Lección terminada. Volviendo al Roadmap...")
                    
                    # VOLVER A MOSTRAR EL MAPA (Recargar para asegurar consistencia)
                    lesson_manager_instance.reload_lessons()
                    lessons = lesson_manager_instance.get_all_lessons()
                    selected_lesson_id = show_theory_menu(lessons)
                    
                    if selected_lesson_id:
                        # Usuario seleccionó otra lección
                        lesson = lesson_manager_instance.get_lesson(selected_lesson_id)
                        if lesson:
                            current_lesson = lesson
                            current_lesson.start()
                            in_lesson = True
                            theory_mode = True
                            
                            # Actualizar índice
                            try:
                                current_lesson_index = lesson_manager_instance._lesson_order.index(selected_lesson_id)
                            except ValueError:
                                current_lesson_index = 0
                                
                            print(f"[EXITO] Nueva lección seleccionada: '{lesson.name}'")
                            continue
                    
                    # Si no seleccionó nada (canceló o volvió), salir al menú principal
                    theory_mode = False
                    print("Regresando al menú principal...")
                    break  # Salir del loop de OpenCV para volver al menú principal
                
                # === MODO RITMO (CANCIONES) ===
                if rhythm_mode and in_song and current_song:
                    # Abrir ventana PyQt6 para la canción (bloquea hasta que termine)
                    print(f"Iniciando ventana de canción: {current_song.name}")
                    
                    # Llamar a la ventana PyQt6 (retorna: 'retry', 'songs', o 'menu')
                    song_result = show_song_window(
                        song=current_song,
                        camera_left=cam_left,
                        camera_right=cam_right,
                        synth=fs,
                        virtual_keyboard=vk_left,
                        hand_detector_left=left_detector,
                        hand_detector_right=right_detector,
                        keyboard_mapper=km,
                        angler=angler,
                        depth_estimator=depth_estimator,
                        octave_base=octave_base,
                        keyboard_total_keys=KEYBOARD_TOT_KEYS,
                        camera_separation=camera_separation
                    )
                    
                    # Manejar resultado
                    if song_result == 'retry':
                        # Reiniciar la misma canción
                        print("Reintentando canción...")
                        current_song.stop()
                        # No cambiar in_song ni current_song, se reiniciará en el siguiente ciclo
                        continue
                    elif song_result == 'songs':
                        # Ir al menú de canciones
                        print("Volviendo al menú de canciones...")
                        current_song.stop()
                        in_song = False
                        current_song = None
                        # Mostrar menú de canciones
                        songs_dict = song_manager_instance.get_all_songs()
                        if songs_dict:
                            selected_song_name = show_songs_menu(songs_dict)
                            if selected_song_name:
                                new_song = song_manager_instance.get_song(selected_song_name)
                                if new_song:
                                    current_song = new_song
                                    in_song = True
                                    continue
                        rhythm_mode = False
                        break
                    else:
                        # Volver al menú principal
                        current_song.stop()
                        in_song = False
                        current_song = None
                        rhythm_mode = False
                        print("Canción terminada. Regresando al menú principal...")
                        break

                if initial_mode == "free" and not theory_mode and not rhythm_mode:
                    print("Iniciando Ventana de Modo Libre...")
                    
                    # Llamamos a la nueva ventana PyQt6
                    show_free_mode_window(
                        camera_left=cam_left,
                        camera_right=cam_right,
                        synth=fs,
                        virtual_keyboard=vk_left,
                        hand_detector_left=left_detector,
                        hand_detector_right=right_detector,
                        keyboard_mapper=km,
                        angler=angler,
                        depth_estimator=depth_estimator,
                        octave_base=octave_base,
                        keyboard_total_keys=KEYBOARD_TOT_KEYS,
                        camera_separation=camera_separation
                    )
                    
                    print("Regresando al menú principal...")
                    break  # ROMPEMOS el bucle para volver al menú principal
                
                # === MODO CONFIGURACIÓN ===
                # Config mode removed

                if initial_mode == "free" and not theory_mode and not rhythm_mode:
                    h_frame, w_frame = frame_left.shape[:2]
                    
                    # --- CONFIGURACIÓN DE ESTILO ---
                    # Colores (B, G, R)
                    bg_color = (30, 30, 30)       # Gris oscuro casi negro
                    border_color = (255, 191, 0)  # Cian/Deep Sky Blue (Acento)
                    text_color = (255, 255, 255)  # Blanco
                    key_bg_color = (80, 80, 80)   # Gris más claro para la "tecla"
                    
                    # Dimensiones
                    panel_w = 220
                    panel_h = 70
                    margin = 20
                    x_start = w_frame - panel_w - margin
                    y_start = margin
                    x_end = w_frame - margin
                    y_end = margin + panel_h

                    # --- 1. FONDO SEMI-TRANSPARENTE (Glass look) ---
                    # Creamos una copia para la transparencia (overlay)
                    sub_img = frame_left[y_start:y_end, x_start:x_end]
                    white_rect = np.full(sub_img.shape, bg_color, dtype=np.uint8)
                    
                    # Mezclamos: 0.3 imagen original + 0.7 color de fondo (bastante oscuro para legibilidad)
                    res = cv2.addWeighted(sub_img, 0.3, white_rect, 0.7, 1.0)
                    frame_left[y_start:y_end, x_start:x_end] = res

                    # --- 2. BORDE DECORATIVO (Solo a la izquierda o completo) ---
                    # Opción elegante: Borde fino alrededor
                    cv2.rectangle(frame_left, (x_start, y_start), (x_end, y_end), border_color, 1, cv2.LINE_AA)
                    # Opción extra: Una barra de acento más gruesa a la izquierda
                    cv2.rectangle(frame_left, (x_start, y_start), (x_start + 4, y_end), border_color, -1)

                    # --- 3. TEXTO PRINCIPAL ("MENU") ---
                    main_text = "MENU PRINCIPAL"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.55
                    thickness = 1
                    
                    # Calcular tamaño para centrar
                    (text_w, text_h), _ = cv2.getTextSize(main_text, font, font_scale, thickness)
                    text_x = x_start + (panel_w - text_w) // 2
                    text_y = y_start + 25
                    
                    cv2.putText(frame_left, main_text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)

                    # --- 4. VISUALIZACIÓN DE TECLAS [ M ] / [ ESC ] ---
                    # Vamos a dibujar "teclas" falsas
                    key_text_1 = "[ M ]"
                    key_text_2 = "[ ESC ]"
                    
                    # Config fuente pequeña
                    k_font_scale = 0.4
                    
                    # Calcular posiciones
                    (k1_w, k1_h), _ = cv2.getTextSize(key_text_1, font, k_font_scale, 1)
                    (k2_w, k2_h), _ = cv2.getTextSize(key_text_2, font, k_font_scale, 1)
                    
                    total_keys_w = k1_w + 15 + k2_w # 15px de espacio entre ellos
                    start_keys_x = x_start + (panel_w - total_keys_w) // 2
                    keys_y = y_start + 55

                    # Dibujar tecla M
                    # Fondo tecla (rectángulo relleno gris claro)
                    # cv2.rectangle(frame_left, (start_keys_x - 4, keys_y - k1_h - 4), (start_keys_x + k1_w + 4, keys_y + 4), key_bg_color, -1)
                    cv2.putText(frame_left, key_text_1, (start_keys_x, keys_y), font, k_font_scale, border_color, 1, cv2.LINE_AA)

                    # Dibujar tecla ESC
                    esc_x = start_keys_x + k1_w + 15
                    # cv2.rectangle(frame_left, (esc_x - 4, keys_y - k2_h - 4), (esc_x + k2_w + 4, keys_y + 4), key_bg_color, -1)
                    cv2.putText(frame_left, key_text_2, (esc_x, keys_y), font, k_font_scale, (180, 180, 180), 1, cv2.LINE_AA)

                    # --- PANEL DE ALGORITMOS (debajo del menú) ---
                    algo_panel_h = 50
                    algo_y_start = y_end + 10
                    algo_y_end = algo_y_start + algo_panel_h
                    
                    # Fondo semi-transparente
                    algo_sub_img = frame_left[algo_y_start:algo_y_end, x_start:x_end]
                    algo_rect = np.full(algo_sub_img.shape, (40, 40, 40), dtype=np.uint8)
                    algo_res = cv2.addWeighted(algo_sub_img, 0.3, algo_rect, 0.7, 1.0)
                    frame_left[algo_y_start:algo_y_end, x_start:x_end] = algo_res
                    
                    # Borde con color diferente (naranja para algoritmos)
                    algo_border_color = (0, 165, 255)  # Naranja
                    cv2.rectangle(frame_left, (x_start, algo_y_start), (x_end, algo_y_end), algo_border_color, 1, cv2.LINE_AA)
                    cv2.rectangle(frame_left, (x_start, algo_y_start), (x_start + 4, algo_y_end), algo_border_color, -1)
                    
                    # Texto "ALGORITMOS"
                    algo_text = "ALGORITMOS"
                    (algo_tw, algo_th), _ = cv2.getTextSize(algo_text, font, 0.5, 1)
                    algo_tx = x_start + (panel_w - algo_tw) // 2
                    algo_ty = algo_y_start + 20
                    cv2.putText(frame_left, algo_text, (algo_tx, algo_ty), font, 0.5, text_color, 1, cv2.LINE_AA)
                    
                    # Tecla [A]
                    key_a_text = "[ A ]"
                    (ka_w, ka_h), _ = cv2.getTextSize(key_a_text, font, k_font_scale, 1)
                    ka_x = x_start + (panel_w - ka_w) // 2
                    ka_y = algo_y_start + 40
                    cv2.putText(frame_left, key_a_text, (ka_x, ka_y), font, k_font_scale, algo_border_color, 1, cv2.LINE_AA)

                # Combinar frames antes de procesar UI
                if camera_in_front_of_you:
                    h_frames = np.concatenate((frame_right, frame_left), axis=1)
                else:
                    h_frames = np.concatenate((frame_left, frame_right), axis=1)
                
                # Mostrar pantalla de bienvenida si es necesario
                # Welcome screen removed
                if display_dashboard:
                    # Display dashboard data
                    fps1 = int(cam_left.current_frame_rate)
                    fps2 = int(cam_right.current_frame_rate)
                    cps_avg = int(round_half_up(fps))
                    text = 'X: {:3.1f}\nY: {:3.1f}\nZ: {:3.1f}\nD: {:3.1f}\nDr: {:3.1f}\nDepth Thr: {:.2f}\nFPS:{}/{}\nCPS:{}'.format(X, Y, Z, D, D-delta_y, km.depth_threshold, fps1, fps2, cps_avg)
                    lineloc = 0
                    lineheight = 30
                    for t in text.split('\n'):
                        lineloc += lineheight
                        cv2.putText(frame_left,
                                    t,
                                    (10, lineloc),
                                    cv2.FONT_HERSHEY_PLAIN,
                                    1.5,
                                    (0, 255, 0),
                                    2,
                                    cv2.LINE_AA,
                                    False)
                    
                    # Re-combinar frames si se modificó frame_left con texto
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
                    end = time.time()
                    seconds = end - start
                    if seconds > 0:
                        fps = 10 / seconds
                    start = time.time()
                # Detect control keys
                key = cv2.waitKey(1) & 0xFF
                #if cv2.getWindowProperty(
                    #main_window_name, cv2.WND_PROP_VISIBLE) < 1:
                    #break
                if cycles > 20 and cv2.getWindowProperty(main_window_name, cv2.WND_PROP_VISIBLE) < 1:
                    print("--- DEBUG: Ventana cerrada por el usuario. Saliendo... ---")
                    break
                if key == ord('q'):
                    break
                # Tecla 'M' o ESC para volver al menú principal (solo en modo libre)
                elif (key == ord('m') or key == ord('M') or key == 27) and initial_mode == "free" and not theory_mode and not rhythm_mode:
                    print("Volviendo al menú principal...")
                    break  # Salir del bucle para volver al menú
                # Tecla 'A' para abrir configuración de algoritmos (solo en modo libre)
                elif (key == ord('a') or key == ord('A')) and initial_mode == "free" and not theory_mode and not rhythm_mode:
                    print("Abriendo configuración de algoritmos...")
                    from src.ui.qt_advanced_config import show_advanced_config
                    from src.vision.algorithms import sync_algorithms_from_config
                    
                    def on_algo_config_change_quick(new_config):
                        sync_algorithms_from_config()
                        # Reconfigurar el KeyboardMapper con los nuevos algoritmos
                        km._initialize_algorithms()
                        print("✓ Algoritmos actualizados en tiempo real")
                    
                    show_advanced_config(on_config_change=on_algo_config_change_quick)
                    print("Configuración de algoritmos cerrada. Continuando...")
                # Legacy key c removed
                elif key == ord('d'):
                    if display_dashboard:
                        display_dashboard = False
                    else:
                        display_dashboard = True
                # Legacy keys n, g, f, l removed
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
        # Solo cerrar ventanas (NO recursos - son persistentes)
        # ------------------------------
        cv2.destroyAllWindows()
        print('--- Volviendo al menú principal ---')
    
    # ====== LIMPIEZA FINAL (al salir del programa) ======
    print("\n🛑 Cerrando programa...")
    cleanup_resources()
    cv2.destroyAllWindows()
    print('✓ Programa finalizado')


# ------------------------------
# Call to Main
# ------------------------------

if __name__ == '__main__':
    main()
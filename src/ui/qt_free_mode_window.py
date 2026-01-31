#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ventana de Modo Libre (Free Mode)
Permite tocar libremente visualizando notas, historial y acordes.
"""

import sys
import cv2
import numpy as np
from collections import deque
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QColor

# Importamos utilidades del proyecto
from src.piano.keyboard_processor import KeyboardProcessor
from src.vision.stereo_config import StereoConfig
from src.config.app_config import AppConfig
from src.config.theme import Theme
from src.vision.depth_logger import DepthLogger

# --- CONFIGURACIÓN DE LOGS ---
DEBUG_MODE = False

class FreeModeWindow(QMainWindow):
    """
    Ventana para tocar libremente.
    Incluye:
    1. Feed de cámaras.
    2. Visualización de última nota tocada.
    3. Historial de notas.
    4. Detector de acordes básicos.
    """
    
    def __init__(self, camera_left, camera_right, synth, 
                 virtual_keyboard, hand_detector_left=None, hand_detector_right=None,
                 keyboard_mapper=None, angler=None, depth_estimator=None, 
                 octave_base=60, keyboard_total_keys=24, camera_separation=9.07):
        super().__init__()
        
        # Referencias a sistemas
        self.camera_left = camera_left
        self.camera_right = camera_right
        self.synth = synth
        self.virtual_keyboard = virtual_keyboard
        self.hand_detector_left = hand_detector_left
        self.hand_detector_right = hand_detector_right
        self.keyboard_mapper = keyboard_mapper
        self.angler = angler
        self.depth_estimator = depth_estimator
        self.octave_base = octave_base
        self.keyboard_total_keys = keyboard_total_keys
        self.camera_separation = camera_separation
        
        # Estado
        self.is_running = True
        self.active_notes = set() # Notas sonando actualmente
        self.timer = QTimer()
        
        # --- NUEVO: Inicializar Logger ---
        self.logger = DepthLogger()
        self.logger.start() # Empieza a grabar al abrir la ventana
        
        # Configuración de ventana
        self.setWindowTitle("Piano Virtual - Modo Libre")
        self.setMinimumSize(1024, 768)
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {Theme.to_hex(Theme.BG_MAIN)}; color: {Theme.to_hex(Theme.TEXT_PRIMARY)}; }}
            QLabel#Title {{ font-size: 24px; font-weight: bold; color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)}; margin-bottom: 10px; }}
            QLabel#NoteDisplay {{ font-size: 48px; font-weight: bold; color: {Theme.to_hex(Theme.SUCCESS)}; }}
            QLabel#ChordDisplay {{ font-size: 22px; color: {Theme.to_hex(Theme.INFO)}; font-style: italic; }}
            QLabel#SectionHeader {{ font-size: 16px; font-weight: bold; color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; margin-top: 15px; }}
            QListWidget {{ 
                background-color: {Theme.to_hex(Theme.BG_PANEL)}; 
                border: 1px solid {Theme.to_hex(Theme.BORDER_DEFAULT)}; 
                font-size: 14px; 
                border-radius: 5px;
            }}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 10px;
                padding: 10px 18px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{ 
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)}; 
                color: #FFFFFF;
            }}
            QPushButton#ExitBtn {{
                background-color: {Theme.to_hex(Theme.BTN_DANGER_BG)}; 
                color: {Theme.to_hex(Theme.BTN_DANGER_TEXT)}; 
                font-weight: bold;
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 10px; 
                padding: 10px 18px;
            }}
            QPushButton#ExitBtn:hover {{ 
                background-color: {Theme.to_hex(Theme.RED_VIVID)}; 
            }}
            QFrame#CameraContainer {{ border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)}; border-radius: 8px; background-color: #000; }}
        """)
        
        self._build_ui()
        self._start_camera_feed()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- IZQUIERDA: CÁMARA ---
        camera_container = QFrame()
        camera_container.setObjectName("CameraContainer")
        camera_layout = QVBoxLayout(camera_container)
        camera_layout.setContentsMargins(0,0,0,0)
        
        self.camera_label = QLabel("Inicializando cámara...")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setScaledContents(False)
        self.camera_label.setMinimumSize(640, 480)
        
        camera_layout.addWidget(self.camera_label)
        main_layout.addWidget(camera_container, 70) # 70% del ancho
        
        # --- DERECHA: PANEL DE INFORMACIÓN ---
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(20, 10, 20, 10)
        
        # 1. Título
        title = QLabel("MODO LIBRE")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(title)
        
        # 2. Última Nota (Grande)
        lbl_last = QLabel("Nota Actual")
        lbl_last.setObjectName("SectionHeader")
        lbl_last.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(lbl_last)
        
        self.note_display = QLabel("--")
        self.note_display.setObjectName("NoteDisplay")
        self.note_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_display.setFixedHeight(80)
        info_layout.addWidget(self.note_display)
        
        # 3. Detector de Acordes (Idea Extra)
        lbl_chord = QLabel("Acorde Detectado")
        lbl_chord.setObjectName("SectionHeader")
        lbl_chord.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(lbl_chord)
        
        self.chord_display = QLabel("...")
        self.chord_display.setObjectName("ChordDisplay")
        self.chord_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chord_display.setFixedHeight(40)
        info_layout.addWidget(self.chord_display)
        
        # 4. Historial
        lbl_hist = QLabel("Historial")
        lbl_hist.setObjectName("SectionHeader")
        info_layout.addWidget(lbl_hist)
        
        self.history_list = QListWidget()
        self.history_list.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Para no robar foco del teclado
        info_layout.addWidget(self.history_list)
        
        # 5. Botones de Control
        info_layout.addStretch()
        
        # BOTÓN PARA GUARDAR LO APRENDIDO (Fase 4c)
        self.btn_save_leveling = QPushButton("💾 Guardar Nivelación")
        self.btn_save_leveling.clicked.connect(self.save_leveling_data)
        self.btn_save_leveling.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        info_layout.addWidget(self.btn_save_leveling)
        
        btn_algo = QPushButton("ALGORITMOS")
        # Estilo heredado del stylesheet global
        btn_algo.clicked.connect(self._open_algorithm_config)
        info_layout.addWidget(btn_algo)
        
        # 6. Botón Salir
        btn_exit = QPushButton("VOLVER AL MENÚ")
        btn_exit.setObjectName("ExitBtn")
        btn_exit.clicked.connect(self.close)
        info_layout.addWidget(btn_exit)
        
        main_layout.addWidget(info_panel, 30) # 30% del ancho

    def _start_camera_feed(self):
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30) # ~33 FPS
        
        # DEBUG: Mostrar una vez qué cámaras se están usando
        print(f"[FreeModeWindow] camera_left source: {getattr(self.camera_left, 'video_source', 'unknown')}")
        print(f"[FreeModeWindow] camera_right source: {getattr(self.camera_right, 'video_source', 'unknown')}")

    def _update_frame(self):
        if not self.is_running:
            return
            
        # 1. Capturar Frames
        wait_t = getattr(StereoConfig, 'FRAME_WAIT_TIME', 0.01)
        finished_left, frame_left = self.camera_left.next(black=True, wait=wait_t)
        finished_right, frame_right = self.camera_right.next(black=True, wait=wait_t)
        
        if frame_left is None: return

        # === CORREGIDO: ARQUITECTURA DE TRANSFORMACIONES ===
        # ESTRATEGIA NUEVA: Detectar en frames RAW para estéreo, rotar solo para display
        
        # Aplicar transformaciones de cámara (corrección de distorsión, etc.)
        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)
        
        # 2. PROCESAMIENTO PERSONALIZADO 
        try:
            # A. Detección de manos EN FRAMES RAW (antes de rotar)
            # Esto es CRÍTICO para que la triangulación estéreo funcione correctamente
            if self.hand_detector_left and self.hand_detector_right:
                # CORREGIDO: Detectar en frames RAW (sin rotar) para ambas cámaras
                # Esto asegura que las coordenadas estén en el mismo sistema de referencia
                self.hand_detector_left.findHands(frame_left)   # RAW
                self.hand_detector_right.findHands(frame_right) # RAW
                
                # Obtener dimensiones reales del frame actual
                h_raw, w_raw = frame_left.shape[:2]
                
                # CORREGIDO: Pasar dimensiones explícitas para evitar escalado erróneo a 640x480
                hl_hands, hl_tips_raw = self.hand_detector_left.getFingerTipsPos(
                    rotate_180=False, 
                    img_width=w_raw, 
                    img_height=h_raw
                )
                hr_hands, hr_tips_raw = self.hand_detector_right.getFingerTipsPos(
                    rotate_180=False, 
                    img_width=w_raw, 
                    img_height=h_raw
                )
                
                # AHORA rotar frame izquierdo para display
                frame_left_display = StereoConfig.apply_display_transform(frame_left)
                h_frame, w_frame = frame_left_display.shape[:2]
                
                # Transformar coordenadas de hl_tips_raw al espacio rotado para display
                # Rotación 180° con cv2.ROTATE_180 = (x, y) → (w - 1 - x, h - 1 - y)
                hl_tips_display = []
                for tip in hl_tips_raw:
                    hand_id, tip_id, x_raw, y_raw = tip
                    x_rot = w_frame - 1 - x_raw
                    y_rot = h_frame - 1 - y_raw
                    hl_tips_display.append([hand_id, tip_id, x_rot, y_rot])
                
                # === CORRECCIÓN DE CÁMARAS INVERTIDAS (SOLO PARA ESTÉREO) ===
                # Si los camera_ids están invertidos respecto a la calibración,
                # intercambiamos los datos de tips SOLO para el matching estéreo
                if StereoConfig.CAMERAS_SWAPPED:
                    hl_tips_stereo, hr_tips_stereo = hr_tips_raw, hl_tips_raw
                    hl_hands, hr_hands = hr_hands, hl_hands
                else:
                    hl_tips_stereo, hr_tips_stereo = hl_tips_raw, hr_tips_raw
                
                # DEBUG VISUAL: Mostrar coordenadas de dedo índice en pantalla
                # Usar hl_tips_stereo/hr_tips_stereo para el cálculo de disparidad
                if len(hl_tips_stereo) > 0 and len(hr_tips_stereo) > 0:
                    # Buscar dedo índice (tip_id=8) en ambas cámaras
                    idx_left = next((t for t in hl_tips_stereo if t[1] == 8), None)
                    idx_right = next((t for t in hr_tips_stereo if t[1] == 8), None)
                    if idx_left and idx_right:
                        xl, yl = int(idx_left[2]), int(idx_left[3])
                        xr, yr = int(idx_right[2]), int(idx_right[3])
                        disp = xl - xr
                        info = f"L:({xl},{yl}) R:({xr},{yr}) disp={disp}"
                        cv2.putText(frame_left_display, info, (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        # Indicar si la disparidad tiene el signo correcto
                        if disp > 0:
                            cv2.putText(frame_left_display, "DISP OK", (10, 60), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        else:
                            cv2.putText(frame_left_display, "DISP INVERTIDA!", (10, 60), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Dibujar manos en frame ROTADO
                # IMPORTANTE: Necesitamos dibujar usando las coordenadas RAW en el frame RAW,
                # luego MediaPipe internamente las dibujará correctamente
                # PERO como el frame ya está rotado, necesitamos crear un detector temporal
                # o dibujar manualmente los puntos transformados
                
                # Dibujar esqueleto de manos manualmente usando coordenadas transformadas
                # (MediaPipe drawHands no funciona bien con coordenadas transformadas)
                for tip in hl_tips_display:
                    hand_id, tip_id, x, y = tip
                    # Dibujar punto azul (MediaPipe)
                    cv2.circle(frame_left_display, (int(x), int(y)), 8, (255, 0, 0), -1)
                    cv2.putText(frame_left_display, f"{tip_id}", (int(x)+10, int(y)),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            else:
                # Si no hay detectores, crear frame_left_display de todos modos
                frame_left_display = StereoConfig.apply_display_transform(frame_left)
                hl_hands, hl_tips_raw = [], []
                hr_hands, hr_tips_raw = [], []
                hl_tips_display = []
                hl_tips_stereo, hr_tips_stereo = [], []
            
            # --- NUEVO: Diccionario para este frame (Logger) ---
            frame_finger_data = {}
            
            # C. Dibujar teclado en frame ROTADO
            # C. Dibujar teclado en frame ROTADO
            # CORREGIDO: Usar modo AR (draw_perspective) si TABLE_CORNERS está disponible
            
            if StereoConfig.TABLE_CORNERS is not None and len(StereoConfig.TABLE_CORNERS) == 4:
                # Modo AR: Dibujar con perspectiva usando las esquinas calibradas
                h_frame, w_frame = frame_left_display.shape[:2]
                
                # Obtener resolución de calibración
                calib_w = getattr(StereoConfig, 'CALIB_PIXEL_WIDTH', 1280) or 1280
                calib_h = getattr(StereoConfig, 'CALIB_PIXEL_HEIGHT', 720) or 720
                
                # Transformar esquinas de RAW a DISPLAY (Rotación)
                # Esto es crucial porque TABLE_CORNERS está en RAW, pero dibujamos sobre frame_left_display
                
                # 1. Obtener esquinas RAW
                raw_corners = StereoConfig.TABLE_CORNERS
                
                # 2. Transformar a DISPLAY usando resolución de calibración
                display_corners_calib = [
                    StereoConfig.transform_point_for_display(p, calib_w, calib_h)
                    for p in raw_corners
                ]
                
                # 3. Escalar a resolución actual del frame
                scale_x = w_frame / calib_w
                scale_y = h_frame / calib_h
                
                scaled_corners = []
                for corner in display_corners_calib:
                    scaled_x = int(corner[0] * scale_x)
                    scaled_y = int(corner[1] * scale_y)
                    scaled_corners.append([scaled_x, scaled_y])
                
                if not hasattr(self, '_corners_scale_logged'):
                    print(f"[DEBUG] AR Transform & Scale:")
                    print(f"  Calib Res: {calib_w}x{calib_h} -> Frame: {w_frame}x{h_frame}")
                    print(f"  Raw Corners: {raw_corners}")
                    print(f"  Disp Corners: {display_corners_calib}")
                    print(f"  Final Scaled: {scaled_corners}")
                    self._corners_scale_logged = True
                
                self.virtual_keyboard.draw_perspective(
                    frame_left_display, 
                    scaled_corners,
                    active_keys=list(self.active_notes) if hasattr(self, 'active_notes') else None
                )
            else:
                # Fallback: Modo plano
                if not hasattr(self, '_flat_mode_logged'):
                    print(f"[DEBUG] TABLE_CORNERS no disponible, usando modo plano")
                    self._flat_mode_logged = True
                self.virtual_keyboard.draw_virtual_keyboard(frame_left_display, rotated_display=True)
            
            # D. Procesar teclas y audio
            # CORREGIDO: Usar hl_tips_display para detección de teclas (coordenadas correctas para display)
            if len(hl_tips_display) > 0:
                finger_depths_dict = {}
                
                # Obtener distancia del teclado desde la calibración (Fase 3)
                keyboard_distance = None
                if self.depth_estimator and hasattr(self.depth_estimator, 'keyboard_distance_cm'):
                    keyboard_distance = self.depth_estimator.keyboard_distance_cm
                
                # CORREGIDO: Si no hay Fase 3, usar fallback con valor por defecto
                if keyboard_distance is None:
                    if not hasattr(self, '_calibration_warning_shown'):
                        print("[ALERTA] Fase 3 no completada - usando distancia por defecto (42cm)")
                        print("  Para mejor precisión, ejecuta Recalibrar → Fase 3")
                        self._calibration_warning_shown = True
                    # CORREGIDO: Usar valor por defecto en lugar de saltar
                    keyboard_distance = 42.0  # Distancia típica mesa-cámara
                
                # Cálculo de profundidad (Triangulación)
                # CORREGIDO: depth_rel > 0 = tocando, depth_rel < 0 = aire
                
                # Contador para debug opcional
                if not hasattr(self, '_diag_counter'): self._diag_counter = 0
                self._diag_counter += 1

                # === GEOMETRIC MATCHING STRATEGY (PARA TRIANGULACIÓN ESTÉREO) ===
                # Usar hl_tips_stereo y hr_tips_stereo que tienen coordenadas coherentes para estéreo
                
                # 1. Agrupar tips por mano
                def group_by_hand(tips_list):
                    groups = {}
                    for t in tips_list:
                        h_id = t[0]
                        if h_id not in groups: groups[h_id] = []
                        groups[h_id].append(t)
                    return groups

                l_hands_dict = group_by_hand(hl_tips_stereo)
                r_hands_dict = group_by_hand(hr_tips_stereo)
                
                l_hand_ids = sorted(list(l_hands_dict.keys()))
                r_hand_ids = sorted(list(r_hands_dict.keys()))
                
                hand_correspondence = {} # {id_izq: id_der}
                
                # Heurística 1: Single Match (1vs1) - La más común y robusta
                if len(l_hand_ids) == 1 and len(r_hand_ids) == 1:
                    hand_correspondence[l_hand_ids[0]] = r_hand_ids[0]
                    # if self._diag_counter % 30 == 0:
                    #     print(f"[MATCH] 1v1 Force: L{l_hand_ids[0]} <-> R{r_hand_ids[0]}")
                    
                # Heurística 2: Sorting por X (Izquierda a Derecha)
                elif len(l_hand_ids) > 0 and len(r_hand_ids) > 0:
                    # Calcular centroide X promedio para cada mano izquierda
                    l_centers = []
                    for hid in l_hand_ids:
                        tips = l_hands_dict[hid]
                        avg_x = sum([t[2] for t in tips]) / len(tips)
                        l_centers.append((avg_x, hid))
                    l_centers.sort() # Ordenar por X
                    
                    # Calcular centroide X para derecha
                    r_centers = []
                    for hid in r_hand_ids:
                        tips = r_hands_dict[hid]
                        avg_x = sum([t[2] for t in tips]) / len(tips)
                        r_centers.append((avg_x, hid))
                    r_centers.sort()
                    
                    # Emparejar en orden (0 con 0, 1 con 1...)
                    min_hands = min(len(l_centers), len(r_centers))
                    for i in range(min_hands):
                        id_l = l_centers[i][1]
                        id_r = r_centers[i][1]
                        hand_correspondence[id_l] = id_r
                
                # Crear mapeo de profundidades usando tips estéreo para triangulación
                # pero indexados por tip_id para luego asociar con hl_tips_display
                depth_by_tip_id = {}
                        
                # 2. PROCESAMIENTO HÍBRIDO (Stereo -> Mono Fallback)
                for hand_idx, id_l in enumerate(l_hand_ids):
                    tips_l = l_hands_dict[id_l]
                    
                    # Buscar par derecho (si existe)
                    id_r = hand_correspondence.get(id_l, None)
                    dict_tips_r = {}
                    if id_r is not None:
                         tips_r = r_hands_dict.get(id_r, [])
                         dict_tips_r = {t[1]: t for t in tips_r}
                    
                    for fl in tips_l:
                        tip_id = fl[1] # 4, 8, 12, 16, 20
                        pt_left = (fl[2], fl[3])
                        
                        final_depth = None
                        
                        # A. Intento Estéreo (Prioritario)
                        stereo_attempted = False
                        stereo_reason = "no_match"
                        
                        if tip_id in dict_tips_r:
                            stereo_attempted = True
                            fr = dict_tips_r[tip_id]
                            pt_right = (fr[2], fr[3])
                            
                            # Triangular si tenemos estimador
                            if self.depth_estimator:
                                try:
                                    # VALIDACIÓN: Verificar que los puntos sean coherentes
                                    y_diff = abs(pt_left[1] - pt_right[1])
                                    x_diff = pt_left[0] - pt_right[0]  # Debería ser POSITIVO
                                    
                                    # DEBUG: Ver valores crudos (cada 60 frames)
                                    if DEBUG_MODE and self._diag_counter % 60 == 0:
                                        print(f"[TRIANGULATE] tip={tip_id}: pt_L=({pt_left[0]:.0f},{pt_left[1]:.0f}), pt_R=({pt_right[0]:.0f},{pt_right[1]:.0f}), x_diff={x_diff:.0f}, y_diff={y_diff:.0f}")
                                    
                                    # --- CORRECCIÓN CLAVE: ELIMINAR BLOQUEO DE DISPARIDAD NEGATIVA ---
                                    # Antes: if y_diff > 80 or x_diff < 0:
                                    # Ahora: Permitimos x_diff negativo porque el usuario tiene cámaras invertidas
                                    if y_diff > 80: 
                                        stereo_reason = f"bad_match(yd={y_diff:.0f},xd={x_diff:.0f})"
                                    else:
                                        # AHORA: Rectificar primero para precisión milimétrica
                                        # 1. Ajustar si hay swap
                                        raw_L = pt_right if StereoConfig.CAMERAS_SWAPPED else pt_left
                                        raw_R = pt_left if StereoConfig.CAMERAS_SWAPPED else pt_right

                                        # 2. Rectificar
                                        rect_L = self.depth_estimator.rectify_point(raw_L, is_left=True)
                                        rect_R = self.depth_estimator.rectify_point(raw_R, is_left=False)

                                        # 3. Triangular
                                        point_3d = self.depth_estimator.triangulate_point(rect_L, rect_R, method='simple')
                                        
                                        if point_3d:
                                            depth_abs = point_3d[2]
                                            depth_method = "FIJA"
                                            
                                            if hasattr(self.depth_estimator, 'has_bilinear_interpolation') and self.depth_estimator.has_bilinear_interpolation():
                                                raw_rel = self.depth_estimator.get_depth_relative_bilinear(
                                                    pt_left[0], pt_left[1], depth_abs
                                                )
                                                # --- AÑADIR SUAVIZADO AQUÍ ---
                                                # Usamos el ID del dedo (tip_id) para mantener historia separada
                                                # smooth_position espera (x,y,z), le pasamos (0,0,depth) solo para suavizar Z
                                                _, _, depth_rel = self.depth_estimator.smooth_position((0, 0, raw_rel), landmark_id=tip_id)
                                                # -----------------------------
                                                depth_method = "BILINEAR"
                                            elif hasattr(self.depth_estimator, 'table_plane') and self.depth_estimator.table_plane is not None:
                                                depth_rel = self.depth_estimator.get_depth_relative_to_plane(
                                                    pt_left[0], pt_left[1], depth_abs
                                                )
                                                depth_method = "PLANO"
                                                if depth_rel is None:
                                                    dist_mesa_eff = keyboard_distance + StereoConfig.KEYBOARD_OFFSET_CM
                                                    depth_rel = dist_mesa_eff - depth_abs
                                                    depth_method = "FIJA"
                                            else:
                                                dist_mesa_eff = keyboard_distance + StereoConfig.KEYBOARD_OFFSET_CM
                                                depth_rel = dist_mesa_eff - depth_abs
                                            
                                            if DEBUG_MODE and self._diag_counter % 30 == 0:
                                                print(f"[DEPTH-{depth_method}] tip={tip_id}: abs={depth_abs:.1f}cm, rel={depth_rel:.1f}cm, X={pt_left[0]}")
                                            
                                            if abs(depth_rel) < 200: # Rango ampliado para debug
                                                final_depth = depth_rel
                                                stereo_reason = "ok"
                                            else:
                                                stereo_reason = f"out_of_range({depth_rel:.1f})"
                                        else:
                                            stereo_reason = "triangulate_null"
                                except Exception as e:
                                    stereo_reason = f"exception({str(e)[:20]})"
                            else:
                                stereo_reason = "no_estimator"
                        
                        # B. Fallback Monocular
                        if final_depth is None:
                            final_depth = 50.0  # Muy por encima del umbral = no activa
                            if DEBUG_MODE and self._diag_counter % 30 == 0:
                                print(f"[STEREO FAIL] tip={tip_id}, attempted={stereo_attempted}, reason={stereo_reason}") 
                        
                        # --- NUEVO: GUARDAR DATOS RAW EN LOGGER ---
                        if stereo_attempted: 
                            # Si intentamos estéreo, logueamos aunque haya fallado (final_depth puede ser 50.0)
                            # Si no intentamos, no tenemos datos estéreo para loguear
                            
                            # Preparar datos
                            z_abs_val = point_3d[2] if 'point_3d' in locals() and point_3d else 0.0
                            # Usar el valor calculado si existe, sino el fallback
                            z_rel_val = final_depth 
                            if 'depth_rel' in locals() and depth_rel is not None:
                                z_rel_val = depth_rel
                            
                            frame_finger_data[(id_l, tip_id)] = {
                                'z_abs': float(z_abs_val),
                                'z_rel': float(z_rel_val),
                                'xl': int(pt_left[0]), 'yl': int(pt_left[1]),
                                'xr': int(pt_right[0]) if 'pt_right' in locals() else 0, 
                                'yr': int(pt_right[1]) if 'pt_right' in locals() else 0,
                                'disp': float(pt_left[0] - pt_right[0]) if 'pt_right' in locals() else 0.0,
                                'reason': stereo_reason
                            }
                        
                        # Guardar profundidad por tip_id (para asociar con hl_tips_display después)
                        depth_by_tip_id[tip_id] = final_depth

                # 3. Crear finger_depths_dict usando hl_tips_display (coordenadas de display)
                for t in hl_tips_display:
                    hand_id = t[0]
                    tip_id = t[1]
                    # Obtener profundidad calculada por estéreo (o fallback)
                    depth = depth_by_tip_id.get(tip_id, 50.0)
                    finger_depths_dict[(hand_id, tip_id)] = depth

                # 4. Asignar mapa de teclas
                # CORREGIDO: En modo AR, NO escalar coordenadas (ya están en espacio del frame)
                # En modo plano, SÍ escalar al canvas
                
                if StereoConfig.TABLE_CORNERS is not None and len(StereoConfig.TABLE_CORNERS) == 4:
                    # MODO AR: Usar coordenadas directas del frame (sin escalar)
                    hl_tips_transformed = hl_tips_display
                    
                    if not hasattr(self, '_ar_coords_logged'):
                        if DEBUG_MODE:
                            print(f"[DEBUG] Modo AR: Usando coordenadas directas del frame (sin escalar)")
                        self._ar_coords_logged = True
                else:
                    # MODO PLANO: Escalar al canvas
                    h_frame, w_frame = frame_left_display.shape[:2]
                    canvas_w = self.virtual_keyboard.canvas_w
                    canvas_h = self.virtual_keyboard.canvas_h
                    scale_x = canvas_w / w_frame
                    scale_y = canvas_h / h_frame
                    
                    hl_tips_transformed = []
                    for t in hl_tips_display:
                        tx = t[2] * scale_x
                        ty = t[3] * scale_y
                        hl_tips_transformed.append([t[0], t[1], tx, ty])
                
                # DEBUG VISUAL: Comparar coordenadas del sistema vs MediaPipe
                # Círculo ROJO = donde el sistema busca teclas (coordenadas transformadas)
                # Círculo AMARILLO = coordenadas de hl_tips_display (antes de escalar)
                # Círculo AZUL = puntos de MediaPipe drawTips (referencia visual)
                # OBJETIVO: ROJO debe coincidir con AZUL cuando rotate_180=True funciona correctamente
                for t_idx, t in enumerate(hl_tips_transformed):
                    # Punto ROJO: donde el sistema busca teclas (transformado + escalado)
                    cv2.circle(frame_left_display, (int(t[2]), int(t[3])), 12, (0, 0, 255), 2)
                    cv2.putText(frame_left_display, "MAP", (int(t[2])-15, int(t[3])-15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                    
                    # Punto AMARILLO: coordenadas de hl_tips_display (sin escalar)
                    # Estas son las coordenadas correctas del frame rotado
                    orig_tip = hl_tips_display[t_idx]
                    cv2.circle(frame_left_display, (int(orig_tip[2]), int(orig_tip[3])), 8, (0, 255, 255), -1)
                    cv2.putText(frame_left_display, "DSP", (int(orig_tip[2])+10, int(orig_tip[3])),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                
                # DEBUG: Mostrar coordenadas vs rango del teclado
                if DEBUG_MODE and self._diag_counter % 60 == 0 and len(hl_tips_transformed) > 0:
                    tip = hl_tips_transformed[0]
                    kb_x0, kb_x1 = self.virtual_keyboard.kb_x0, self.virtual_keyboard.kb_x1
                    kb_y0, kb_y1 = self.virtual_keyboard.kb_y0, self.virtual_keyboard.kb_y1
                    
                    print(f"\n[DIAG] Dedo transform: ({tip[2]:.1f}, {tip[3]:.1f})")
                    print(f"[DIAG] Teclado: X=[{kb_x0}, {kb_x1}], Y=[{kb_y0}, {kb_y1}]")
                    print(f"[DIAG] Dedo en teclado: {'SI' if kb_x0 <= tip[2] <= kb_x1 and kb_y0 <= tip[3] <= kb_y1 else 'NO'}")
                
                # Obtener teclas presionadas (usando coordenadas transformadas)
                on_map, off_map = self.keyboard_mapper.get_kayboard_map(
                    self.virtual_keyboard, hl_tips_transformed, finger_depths_dict, self.keyboard_total_keys
                )
                
                # E. Reproducir Audio y ACTUALIZAR UI
                if np.any(on_map):
                    for k_pos, is_on in enumerate(on_map):
                        if is_on:
                            # 1. Audio
                            midi_note = self.virtual_keyboard.note_from_key(k_pos) + self.octave_base
                            self.synth.noteon(0, midi_note, 90)
                            
                            # 2. UI Updates
                            self._on_note_played(k_pos, midi_note)
                            self.active_notes.add(k_pos)
                
                if np.any(off_map):
                    for k_pos, is_off in enumerate(off_map):
                        if is_off:
                            midi_note = self.virtual_keyboard.note_from_key(k_pos) + self.octave_base
                            self.synth.noteoff(0, midi_note)
                            if k_pos in self.active_notes:
                                self.active_notes.remove(k_pos)
            
            # Actualizar detector de acordes en cada frame
            self._update_chord_display()
            
            # F. Crosshairs (en frame rotado)
            if self.angler:
                self.angler.frame_add_crosshairs(frame_left_display)

        except Exception as e:
            print(f"Error en loop de modo libre: {e}")
            import traceback
            traceback.print_exc()

        # 3. Mostrar Frame FINAL (ya rotado con todo dibujado)
        # 3. Mostrar Frame FINAL (ya rotado con todo dibujado)
        if self.logger.is_recording:
             research_fingers = {}
             for finger_id, data in frame_finger_data.items():
                 # Obtener nombre del dedo
                 # finger_id es (hand_id, tip_id) -> usamos tip_id
                 tip_id = finger_id[1]
                 name = self.logger.finger_names.get(tip_id, str(tip_id))

                 # Obtener nota que este dedo está "pisando" (si existe)
                 # Usamos xl/yl que son coordenadas de cámara izquierda (rectificada)
                 # find_key espera coordenadas de espacio de dibujo.
                 # En AR, dibujo se alinea con cámara izq (si no hay escalado raro).
                 
                 # NOTA: Asumimos data['xl'] es int.
                 current_key = self.virtual_keyboard.find_key(data['xl'], data['yl'])

                 # Verificar si esa nota está realmente activa (sonando)
                 is_active = False
                 if current_key is not None:
                      is_active = current_key in self.active_notes

                 research_fingers[name] = {
                     "x": round(data['xl'], 1),
                     "y": round(data['yl'], 1),
                     "z": round(data['z_rel'], 2),
                     "note": current_key if is_active else None 
                 }

             # Llamar al nuevo logger modular
             self.logger.log_frame(research_fingers, list(self.active_notes))
        self._display_frame(frame_left_display)

    def _display_frame(self, frame):
        """Convierte y muestra el frame de OpenCV en PyQt - Optimizado para evitar parpadeo"""
        # Convertir BGR a RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Hacer copia contigua para evitar problemas de memoria
        rgb_frame = np.ascontiguousarray(rgb_frame)
        
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        # Crear QImage con copia de datos (evita parpadeo)
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(q_img)
        
        # Escalar con transformación rápida para mejor rendimiento
        scaled = pixmap.scaled(
            self.camera_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.FastTransformation
        )
        self.camera_label.setPixmap(scaled)

    def _on_note_played(self, key_index, midi_note):
        """Callback cuando se detecta una nueva nota"""
        
        # 1. Obtener nombre de la nota (Do, Re, Mi...)
        # Usamos el array de nombres de virtual_keyboard si es posible
        note_names = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
        # Calcular índice cromático desde Do (C)
        # Asumiendo octave_base=60 (C4), midi_note 60 es Do
        chromatic_index = (midi_note - 60) % 12
        octave = (midi_note // 12) - 1
        
        note_str = f"{note_names[chromatic_index]} {octave}"
        
        # 2. Actualizar Display Principal
        self.note_display.setText(note_str)
        
        # 3. Añadir al historial
        self.history_list.insertItem(0, f"♪ {note_str}")
        if self.history_list.count() > 15:
            self.history_list.takeItem(15)

    def _update_chord_display(self):
        """Analiza self.active_notes y muestra el acorde posible"""
        if len(self.active_notes) < 3:
            self.chord_display.setText("...")
            return

        # Convertir índices de teclas a índices cromáticos (0-11)
        # active_notes tiene índices de teclas (0, 1, 2...)
        # virtual_keyboard.note_from_key(k) da MIDI relativo a la octava base
        
        notes_chromatic = set()
        root_candidates = []
        
        for k in self.active_notes:
            midi_rel = self.virtual_keyboard.note_from_key(k)
            chroma = midi_rel % 12
            notes_chromatic.add(chroma)
            root_candidates.append(chroma)
            
        # Algoritmo muy simple de detección de acordes Mayores y Menores
        # Mayor: Raíz + 4 + 7
        # Menor: Raíz + 3 + 7
        
        detected_chord = ""
        note_names = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
        
        for root in root_candidates:
            # Mayor
            third_maj = (root + 4) % 12
            fifth = (root + 7) % 12
            
            if third_maj in notes_chromatic and fifth in notes_chromatic:
                detected_chord = f"{note_names[root]} Mayor"
                break
            
            # Menor
            third_min = (root + 3) % 12
            if third_min in notes_chromatic and fifth in notes_chromatic:
                detected_chord = f"{note_names[root]} Menor"
                break
                
        if detected_chord:
            self.chord_display.setText(detected_chord)
        else:
            self.chord_display.setText("...")

    def _open_algorithm_config(self):
        """Abre el panel de configuración de algoritmos"""
        # Pausar el timer mientras se configura
        was_running = self.timer.isActive()
        if was_running:
            self.timer.stop()
        
        try:
            from src.ui.qt_advanced_config import show_advanced_config
            from src.vision.algorithms import sync_algorithms_from_config
            
            def on_config_change(new_config):
                sync_algorithms_from_config()
                # Reinicializar algoritmos en el keyboard_mapper
                if self.keyboard_mapper:
                    self.keyboard_mapper._initialize_algorithms()
                print("[INFO] Algoritmos actualizados")
            
            show_advanced_config(on_config_change=on_config_change)
            
        except Exception as e:
            print(f"Error abriendo configuración: {e}")
        
        # Reanudar el timer
        if was_running:
            self.timer.start(30)

    def closeEvent(self, event):
        # --- NUEVO: Guardar log al cerrar ---
        self.logger.stop_and_save()
        
        self.is_running = False
        self.timer.stop()
        event.accept()

    def save_leveling_data(self):
        """Guardar mapa de alturas aprendido por la física"""
        # Accedemos al config a través del video thread o detector si es posible
        if self.camera_left and hasattr(self.camera_left, 'calibration_config') and self.camera_left.calibration_config:
             # Necesitamos disparar el guardado en TriggerSystem primero para actualizar config,
             # pero TriggerSystem ya actualiza calibration_config.key_floors en tiempo real.
             # Solo necesitamos pedirle al config que guarde.
             self.camera_left.calibration_config.save_key_floors()
             self.btn_save_leveling.setText("¡Guardado!")
             print("[UI] Nivelación guardada exitosamente.")
        else:
            print("[UI] No se encontró configuración de calibración para guardar.")

# Función helper para lanzar la ventana desde main.py
def show_free_mode_window(camera_left, camera_right, synth, 
                         virtual_keyboard, hand_detector_left, hand_detector_right,
                         keyboard_mapper, angler, depth_estimator, **kwargs):
    
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv)
        owns_app = True
        
    window = FreeModeWindow(
        camera_left, camera_right, synth, virtual_keyboard,
        hand_detector_left, hand_detector_right,
        keyboard_mapper, angler, depth_estimator,
        **kwargs
    )
    window.show()
    
    if owns_app:
        app.exec()
    else:
        # Loop modal para esperar a que cierre
        while window.isVisible():
            app.processEvents()
            
    return True
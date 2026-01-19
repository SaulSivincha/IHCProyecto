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
from src.config.app_config import AppConfig
from src.config.theme import Theme

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
        
        # 5. Botón Algoritmos
        info_layout.addStretch()
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
        finished_left, frame_left = self.camera_left.next(black=True, wait=1)
        finished_right, frame_right = self.camera_right.next(black=True, wait=1)
        
        if frame_left is None: return

        # Importar configuración estéreo (compartida por todos los modos)
        from src.vision.stereo_config import StereoConfig

        # === CORREGIDO: ARQUITECTURA DE TRANSFORMACIONES ===
        # ESTRATEGIA: Rotar frame PRIMERO, luego dibujar con coordenadas transformadas
        
        # Aplicar transformaciones para DETECCIÓN (geometría correcta)
        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)
        
        # ROTAR frame para display ANTES de dibujar
        frame_left_display = StereoConfig.apply_display_transform(frame_left)
        
        # 2. PROCESAMIENTO PERSONALIZADO 
        try:
            # A. Detección de manos en frames RAW (sin rotar)
            if self.hand_detector_left and self.hand_detector_right:
                self.hand_detector_left.findHands(frame_left)
                self.hand_detector_right.findHands(frame_right)
                
                hl_hands, hl_tips = self.hand_detector_left.getFingerTipsPos()
                hr_hands, hr_tips = self.hand_detector_right.getFingerTipsPos()
                
                # === CORRECCIÓN DE CÁMARAS INVERTIDAS ===
                # Si los camera_ids están invertidos respecto a la calibración,
                # intercambiamos los datos de tips para que el matching estéreo funcione
                if StereoConfig.CAMERAS_SWAPPED:
                    hl_tips, hr_tips = hr_tips, hl_tips
                    hl_hands, hr_hands = hr_hands, hl_hands
                
                # DEBUG VISUAL: Mostrar coordenadas de dedo índice en pantalla
                if len(hl_tips) > 0 and len(hr_tips) > 0:
                    # Buscar dedo índice (tip_id=8) en ambas cámaras
                    idx_left = next((t for t in hl_tips if t[1] == 8), None)
                    idx_right = next((t for t in hr_tips if t[1] == 8), None)
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
                
                # Dibujar manos en frame ROTADO con coordenadas transformadas
                self.hand_detector_left.drawHands(frame_left_display, rotate_180=True)
                self.hand_detector_left.drawTips(frame_left_display, rotate_180=True)
            else:
                hl_hands, hl_tips = [], []
                hr_hands, hr_tips = [], []
            
            # C. Dibujar teclado en frame ROTADO
            # El método ahora maneja la transformación de coordenadas internamente
            self.virtual_keyboard.draw_virtual_keyboard(frame_left_display, rotated_display=True)
            
            # D. Procesar teclas y audio
            # CORREGIDO: Procesar incluso con solo cámara izquierda (fallback monocular)
            if len(hl_tips) > 0:
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

                # === GEOMETRIC MATCHING STRATEGY (NUEVO) ===
                # Reemplazamos el matching por ID estricto con heurísticas posicionales
                
                # 1. Agrupar tips por mano
                def group_by_hand(tips_list):
                    groups = {}
                    for t in tips_list:
                        h_id = t[0]
                        if h_id not in groups: groups[h_id] = []
                        groups[h_id].append(t)
                    return groups

                l_hands_dict = group_by_hand(hl_tips)
                r_hands_dict = group_by_hand(hr_tips)
                
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
                        
                # 2. PROCESAMIENTO HÍBRIDO (Stereo -> Mono Fallback)
                # Iteramos sobre todas las manos izquierdas detectadas (Cámara primaria)
                # Esto permite detectar dedos incluso si la cámara derecha no los ve (Fallback Monocular)
                
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
                                    # SIMPLIFICADO: Usar método 'simple' que no requiere rectificación
                                    # y es más robusto para nuestro caso de uso
                                    
                                    # VALIDACIÓN: Verificar que los puntos sean coherentes
                                    # En estéreo, X_right < X_left (el punto se ve más a la izquierda en cam derecha)
                                    # Y debería ser similar (< 50px diferencia después de rectificación)
                                    y_diff = abs(pt_left[1] - pt_right[1])
                                    x_diff = pt_left[0] - pt_right[0]  # Debería ser POSITIVO
                                    
                                    # DEBUG: Ver valores crudos (cada 60 frames)
                                    if self._diag_counter % 60 == 0:
                                        print(f"[TRIANGULATE] tip={tip_id}: pt_L=({pt_left[0]:.0f},{pt_left[1]:.0f}), pt_R=({pt_right[0]:.0f},{pt_right[1]:.0f}), x_diff={x_diff:.0f}, y_diff={y_diff:.0f}")
                                    
                                    # VALIDAR matching: Y similar y X_L > X_R
                                    if y_diff > 80 or x_diff < 0:
                                        # Matching incorrecto - no triangular
                                        stereo_reason = f"bad_match(yd={y_diff:.0f},xd={x_diff:.0f})"
                                    else:
                                        point_3d = self.depth_estimator.triangulate_point(pt_left, pt_right, method='simple')
                                        
                                        if point_3d:
                                            depth_abs = point_3d[2]
                                            # CORREGIDO: Sumar offset (+ = subir mesa hacia cámara)
                                            dist_mesa_eff = keyboard_distance + StereoConfig.KEYBOARD_OFFSET_CM
                                            
                                            # LÓGICA CORREGIDA:
                                            # depth_abs = distancia del dedo a la cámara (cm)
                                            # dist_mesa_eff = distancia de la mesa a la cámara (cm)
                                            # 
                                            # Si dedo EN EL AIRE (más cerca de cámara): depth_abs < dist_mesa_eff
                                            #   → depth_rel = dist_mesa_eff - depth_abs > 0 (POSITIVO = AIRE)
                                            # Si dedo TOCANDO (en la mesa): depth_abs ≈ dist_mesa_eff
                                            #   → depth_rel ≈ 0 (CERCA DE CERO = TOCANDO)
                                            # Si dedo DEBAJO de mesa (imposible pero por ruido): depth_abs > dist_mesa_eff
                                            #   → depth_rel < 0 (NEGATIVO = TOCANDO)
                                            #
                                            # Activación: depth_rel <= threshold (ej: 3cm)
                                            #   - Si dedo está a 0-3cm sobre la mesa → TOCA
                                            #   - Si dedo está a >3cm sobre la mesa → AIRE
                                            depth_rel = dist_mesa_eff - depth_abs  # INVERTIDO: ahora + = aire, cerca de 0 o - = toque
                                            
                                            # DEBUG: Ver valores de triangulación
                                            if self._diag_counter % 30 == 0:
                                                print(f"[DEPTH] tip={tip_id}: depth_abs={depth_abs:.1f}cm, mesa={dist_mesa_eff:.1f}cm, depth_rel={depth_rel:.1f}cm")
                                            
                                            # Filtro de rango razonable (ajustado)
                                            if abs(depth_rel) < 30:
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
                        
                        # B. Fallback Monocular (Si falló estéreo o no hay par)
                        if final_depth is None:
                            # NO asumir toque - usar valor GRANDE positivo para indicar "aire/desconocido"
                            # Con la nueva lógica: depth_rel > threshold = AIRE
                            final_depth = 50.0  # Muy por encima del umbral = no activa
                            
                            # DEBUG: Mostrar por qué falló (cada 30 frames)
                            if self._diag_counter % 30 == 0:
                                print(f"[STEREO FAIL] tip={tip_id}, attempted={stereo_attempted}, reason={stereo_reason}") 
                        
                        # Guardar resultado
                        
                        # IMPORTANTE: KeyboardMapper espera clave TUPLA (hand_id, tip_id)
                        # Recuperamos hand_id original
                        hand_id = fl[0]
                        
                        # Fix TypeError: KeyboardMapper espera float, no dict
                        finger_depths_dict[(hand_id, tip_id)] = final_depth

                # Actualizar VirtualKeyboard
                # (La actualización visual ocurre al dibujar con prev_active_keys en el siguiente frame)
                # if len(finger_depths_dict) > 0:
                #    self.virtual_keyboard.update_keys_with_depth(finger_depths_dict)

                # 4. Asignar mapa de teclas
                # CORREGIDO: Transformar coordenadas RAW a espacio ROTADO
                # porque el teclado se dibuja en frame_left_display (rotado 180°)
                h_frame, w_frame = frame_left.shape[:2]
                hl_tips_transformed = []
                for t in hl_tips:
                    # t = [hand_id, tip_id, x, y]
                    # Aplicar rotación 180°: (x,y) -> (w-x, h-y)
                    tx = w_frame - t[2]
                    ty = h_frame - t[3]
                    hl_tips_transformed.append([t[0], t[1], tx, ty])
                
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
        self.is_running = False
        self.timer.stop()
        event.accept()

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
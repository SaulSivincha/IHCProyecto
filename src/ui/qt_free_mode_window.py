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

    def _update_frame(self):
        if not self.is_running:
            return
            
        # 1. Capturar Frames
        finished_left, frame_left = self.camera_left.next(black=True, wait=1)
        finished_right, frame_right = self.camera_right.next(black=True, wait=1)
        
        if frame_left is None: return

        # Importar configuración estéreo (compartida por todos los modos)
        from src.vision.stereo_config import StereoConfig

        # === NUEVA ARQUITECTURA DE TRANSFORMACIONES ===
        # 1. apply_camera_transforms: Para detección (imágenes RAW, geometría correcta)
        # 2. apply_display_transform: Para visualización (efecto espejo/selfie)
        
        # Aplicar transformaciones para DETECCIÓN (no afecta geometría)
        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)
        
        # Guardamos referencia a frames sin espejo para visualización después
        # (el espejo se aplica al final, después de dibujar todo)
        
        # frame_right se usa para profundidad, no visualización directa
        
        # 2. PROCESAMIENTO PERSONALIZADO 
        # (Replicamos lógica de KeyboardProcessor para poder extraer datos para la UI)
        # B. APLICAR ESPEJO PARA VISUALIZACIÓN (Hacerlo ANTES del try para asegurar que existe)
        frame_left_display = StereoConfig.apply_display_transform(frame_left)
        
        # 2. PROCESAMIENTO PERSONALIZADO 
        try:
            # A. Detección de manos (Solo si hay detectores)
            if self.hand_detector_left and self.hand_detector_right:
                self.hand_detector_left.findHands(frame_left)
                self.hand_detector_right.findHands(frame_right)
                
                hl_hands, hl_tips = self.hand_detector_left.getFingerTipsPos()
                hr_hands, hr_tips = self.hand_detector_right.getFingerTipsPos()
                
                # Dibujar manos (con rotate_180=True)
                self.hand_detector_left.drawHands(frame_left_display, rotate_180=True)
                self.hand_detector_left.drawTips(frame_left_display, rotate_180=True)
            else:
                hl_hands, hl_tips = [], []
                hr_hands, hr_tips = [], []
            
            # C. DIBUJAR SOBRE EL FRAME ESPEJADO
            # 1. Dibujar teclado (se dibuja normal sobre frame espejado)
            self.virtual_keyboard.draw_virtual_keyboard(frame_left_display)
            
            # D. Procesar teclas y audio
            if len(hl_tips) > 0 and len(hr_tips) > 0:
                finger_depths_dict = {}
                
                # Obtener distancia del teclado desde la calibración (Fase 3)
                # Esta es la referencia para determinar si un dedo "toca" el teclado
                keyboard_distance = None
                if self.depth_estimator and hasattr(self.depth_estimator, 'keyboard_distance_cm'):
                    keyboard_distance = self.depth_estimator.keyboard_distance_cm
                
                # Si no hay distancia calibrada, no podemos detectar notas correctamente
                if keyboard_distance is None:
                    # Mostrar advertencia una sola vez
                    if not hasattr(self, '_calibration_warning_shown'):
                        print("[ALERTA] Fase 3 no completada - la deteccion de notas no funcionara")
                        print("  Ejecuta: Recalibrar → Fase 3 para calibrar la distancia del teclado")
                        self._calibration_warning_shown = True
                    # Continuar sin procesar notas
                else:
                    # Cálculo de profundidad (Triangulación)
                    # depth_relative > 0: dedo ha pasado el plano del teclado (tocar)
                    # depth_relative < 0: dedo está antes del plano del teclado (no tocar)
                    for fl in hl_tips:
                        for fr in hr_tips:
                            if fl[0] == fr[0] and fl[1] == fr[1]: # Mismo dedo
                                # Usar DepthEstimator si está disponible
                                if self.depth_estimator:
                                    # 1. Rectificar puntos
                                    pt_left = (fl[2], fl[3])
                                    pt_right = (fr[2], fr[3])
                                    pt_l_rect = self.depth_estimator.rectify_point(pt_left, 'left')
                                    pt_r_rect = self.depth_estimator.rectify_point(pt_right, 'right')
                                    
                                    # 2. Triangular
                                    point_3d = self.depth_estimator.triangulate_point(pt_l_rect, pt_r_rect)
                                    
                                    if point_3d:
                                        depth_absolute = point_3d[2]  # Z = distancia desde cámaras (cm)
                                        # Profundidad relativa al teclado calibrado
                                        depth_relative = keyboard_distance - depth_absolute
                                        finger_depths_dict[(fl[0], fl[1])] = depth_relative
                                        
                                        # Filtrar valores absurdos de profundidad
                                        if depth_relative < -100 or depth_relative > 100:
                                            continue  # Saltar, valor no confiable
                                        
                                        # DEBUG: Mostrar info de profundidad
                                        if not hasattr(self, '_debug_counter'):
                                            self._debug_counter = 0
                                            # Mostrar configuración al inicio
                                            print(f"\\n=== CONFIGURACIÓN DE DETECCIÓN ===")
                                            print(f"Distancia calibrada (keyboard_distance): {keyboard_distance:.1f}cm")
                                            print(f"Umbral de activación: depth_relative <= 2.0cm")
                                            print(f"NOTA: Activa cuando el dedo está CERCA del teclado calibrado")
                                            print(f"  - Relativo NEGATIVO = dedo MÁS LEJOS de cámaras que el teclado")
                                            print(f"  - Relativo POSITIVO = dedo MÁS CERCA de cámaras que el teclado")
                                            print(f"==================================\\n")
                                        self._debug_counter += 1
                                        if self._debug_counter % 30 == 0:  # Cada 30 frames
                                            # Lógica corregida: activa cuando el dedo está sobre la mesa
                                            activation_threshold = 2.0
                                            activate = depth_relative <= activation_threshold
                                            
                                            # Determinar RAZÓN de no activación
                                            if activate:
                                                reason = "[TOCANDO]"
                                            elif depth_relative < -5.0:
                                                reason = f"(dedo {abs(depth_relative):.1f}cm DEBAJO del teclado)"
                                            elif depth_relative > 5.0:
                                                reason = f"(dedo {depth_relative:.1f}cm ARRIBA del teclado)"
                                            else:
                                                reason = "(en zona intermedia)"
                                            
                                            status = "SI" if activate else "NO"
                                            print(f"[DEBUG] Dedo {fl[0]},{fl[1]}: Z={depth_absolute:.1f}cm, Rel={depth_relative:.1f}cm -> {status} {reason}")

                                # Fallback a lógica antigua si no hay DepthEstimator
                                elif self.angler and keyboard_distance:
                                    xl, yl = self.angler.angles_from_center(x=fl[2], y=fl[3], top_left=True, degrees=True)
                                    xr, yr = self.angler.angles_from_center(x=fr[2], y=fr[3], top_left=True, degrees=True)
                                    _, _, Z, D = self.angler.location(
                                        self.camera_separation, (xl, yl), (xr, yr), center=True, degrees=True
                                    )
                                    delta_y = 0.0065 * Z * Z + 0.039 * -1 * Z
                                    depth_absolute = D - delta_y
                                    depth_relative = keyboard_distance - depth_absolute
                                    finger_depths_dict[(fl[0], fl[1])] = depth_relative
                
                # 4. Asignar mapa de teclas
                # IMPORTANTE: Transformar coordenadas RAW a VISUALES para que coincidan con el teclado dibujado
                h_frame, w_frame = frame_left.shape[:2]
                hl_tips_visual = []
                for t in hl_tips:
                    # t = [hand_id, tip_id, x, y]
                    vx, vy = StereoConfig.transform_point_for_display((t[2], t[3]), w_frame, h_frame)
                    hl_tips_visual.append([t[0], t[1], vx, vy])

                # Obtener teclas presionadas (usando coordenadas visuales transformadas)
                on_map, off_map = self.keyboard_mapper.get_kayboard_map(
                    self.virtual_keyboard, hl_tips_visual, finger_depths_dict, self.keyboard_total_keys
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
            
            # F. Crosshairs
            if self.angler:
                self.angler.frame_add_crosshairs(frame_left_display)

        except Exception as e:
            print(f"Error en loop de modo libre: {e}")
            import traceback
            traceback.print_exc()

        # 3. Mostrar Frame FINAL (que ya está espejado y con dibujos)
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
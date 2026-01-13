#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ventana PyQt6 para lecciones de teoría musical
Embebe feed de cámaras OpenCV y muestra UI de la lección
"""

import sys
import cv2
import numpy as np
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont, QLinearGradient, QPainter, QColor
from src.piano.keyboard_processor import KeyboardProcessor
from src.config.theme import Theme

class LessonWindow(QMainWindow):
    """
    Ventana principal para ejecutar lecciones de teoría musical.
    Muestra el feed de las cámaras y la UI de la lección en una sola ventana.
    """
    
    def __init__(self, lesson, camera_left, camera_right, synth, 
                 virtual_keyboard, hand_detector_left=None, hand_detector_right=None,
                 keyboard_mapper=None, angler=None, depth_estimator=None, octave_base=60,
                 keyboard_total_keys=24, camera_separation=9.07, lesson_index=None):
        super().__init__()
        
        self.lesson = lesson
        self.lesson_index = lesson_index
        self.camera_left = camera_left
        self.camera_right = camera_right
        self.synth = synth
        self.virtual_keyboard = virtual_keyboard
        self.hand_detector_left = hand_detector_left
        self.hand_detector_right = hand_detector_right
        
        # Crear procesador de teclado centralizado
        if keyboard_mapper and angler:
            self.keyboard_processor = KeyboardProcessor(
                keyboard_mapper=keyboard_mapper,
                angler=angler,
                depth_estimator=depth_estimator,
                synth=synth,
                octave_base=octave_base,
                keyboard_total_keys=keyboard_total_keys,
                camera_separation=camera_separation
            )
        else:
            self.keyboard_processor = None
        
        self.continue_lesson = True
        self.timer = QTimer()
        
        # Configuración de ventana
        self.setWindowTitle(f"Teoría Musical - {lesson.name}")
        self.setMinimumSize(1100, 700)
        
        # El estilo base se maneja aquí, el gradiente en paintEvent
        self.setStyleSheet(f"""
            QLabel {{
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QLabel#title {{
                color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
                font-size: 28px;
                font-weight: bold;
                padding: 10px;
                background-color: transparent;
            }}
            QLabel#subtitle {{
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
                background-color: transparent;
            }}
            QLabel#instruction {{
                color: {Theme.to_hex(Theme.TEXT_SECONDARY)};
                font-size: 14px;
                padding: 3px;
                background-color: transparent;
            }}
            QTextEdit {{
                background-color: rgba(255, 255, 255, 0.9);
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 10px;
                font-family: 'Comic Sans MS', 'Arial';
                font-size: 16px;
                padding: 10px;
            }}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                font-family: 'Comic Sans MS', 'Arial';
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
            QPushButton#exitButton {{
                background-color: {Theme.to_hex(Theme.BTN_DANGER_BG)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                color: {Theme.to_hex(Theme.BTN_DANGER_TEXT)};
            }}
            QPushButton#exitButton:hover {{
                background-color: {Theme.to_hex(Theme.RED_VIVID)};
            }}
            QProgressBar {{
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 5px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.5);
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.to_hex(Theme.SUCCESS)};
                border-radius: 3px;
            }}
            QFrame#cameraFrame {{
                border: 4px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 15px;
                background-color: #000000;
            }}
        """)
        
        self._build_ui()
        
        # --- CORRECCIÓN CLAVE: Asegurar que la ventana tenga el foco ---
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        
        self._start_camera_feed()
    
    def paintEvent(self, event):
        """Dibuja el fondo con gradiente del tema"""
        painter = QPainter(self)
        
        grad_start = QColor(Theme.to_hex(Theme.BG_GRADIENT_START))
        grad_end = QColor(Theme.to_hex(Theme.BG_GRADIENT_END))
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, grad_start)
        gradient.setColorAt(1, grad_end)
        painter.fillRect(self.rect(), gradient)
    
    def _build_ui(self):
        """Construye la interfaz de usuario"""
        central_widget = QWidget()
        central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # ========== ENCABEZADO ==========
        header_layout = QHBoxLayout()
        
        title_label = QLabel(self.lesson.name)
        title_label.setObjectName("title")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        difficulty_label = QLabel(f"Dificultad: {self.lesson.difficulty}")
        difficulty_label.setObjectName("subtitle")
        header_layout.addWidget(difficulty_label)
        
        main_layout.addLayout(header_layout)
        
        # ========== CONTENIDO PRINCIPAL (Cámaras + Panel) ==========
        content_layout = QHBoxLayout()
        
        # --- Panel Izquierdo: Cámara ---
        camera_container = QVBoxLayout()
        
        # Frame para la cámara
        self.camera_frame = QFrame()
        self.camera_frame.setObjectName("cameraFrame")
        camera_frame_layout = QVBoxLayout(self.camera_frame)
        camera_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(640, 480) 
        self.camera_label.setScaledContents(False)
        self.camera_label.setStyleSheet("background-color: #000000; border-radius: 11px;")
        camera_frame_layout.addWidget(self.camera_label)
        
        camera_container.addWidget(self.camera_frame)
        content_layout.addLayout(camera_container, 3)
        
        # --- Panel Derecho: Información de la Lección ---
        info_panel = QVBoxLayout()
        info_panel.setSpacing(15)
        
        # Descripción
        desc_label = QLabel("Descripción:")
        desc_label.setObjectName("subtitle")
        info_panel.addWidget(desc_label)
        
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(80)
        self.description_text.setText(self.lesson.description)
        # EVITAR QUE ROBE FOCO (ESPACIO)
        self.description_text.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        info_panel.addWidget(self.description_text)
        
        # Instrucciones (área dinámica)
        inst_label = QLabel("Instrucciones:")
        inst_label.setObjectName("subtitle")
        info_panel.addWidget(inst_label)
        
        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMinimumHeight(200)
        # EVITAR QUE ROBE FOCO (ESPACIO)
        self.instructions_text.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        info_panel.addWidget(self.instructions_text)
        
        # Progreso
        progress_label = QLabel("Progreso:")
        progress_label.setObjectName("subtitle")
        info_panel.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        info_panel.addWidget(self.progress_bar)
        
        # Info adicional de la lección
        self.custom_info_label = QLabel("")
        self.custom_info_label.setObjectName("instruction")
        self.custom_info_label.setWordWrap(True)
        info_panel.addWidget(self.custom_info_label)
        
        info_panel.addStretch()
        
        # Botones de control
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        self.exit_button = QPushButton("SALIR DE LA LECCIÓN")
        self.exit_button.setObjectName("exitButton")
        self.exit_button.clicked.connect(self._exit_lesson)
        # EVITAR QUE ROBE FOCO
        self.exit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.exit_button)
        
        info_panel.addLayout(button_layout)
        
        content_layout.addLayout(info_panel, 2)
        
        main_layout.addLayout(content_layout)
        
        # ========== PIE DE PÁGINA ==========
        footer_label = QLabel("Presiona ESC o Q para salir | Sigue las instrucciones de la lección")
        footer_label.setObjectName("instruction")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_label)
    
    def _start_camera_feed(self):
        """Inicia el timer para actualizar el feed de las cámaras"""
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)  # ~33 FPS
    
    def _update_frame(self):
        """Actualiza el frame de las cámaras y ejecuta la lección"""
        if not self.continue_lesson:
            self.close()
            return
        
        # Obtener frames de las cámaras
        finished_left, frame_left = self.camera_left.next(black=True, wait=1)
        finished_right, frame_right = self.camera_right.next(black=True, wait=1)
        
        if frame_left is None or frame_right is None:
            return
        
        # Importar configuración estéreo (compartida)
        from src.vision.stereo_config import StereoConfig

        # Lógica de visualización unificada - PASO A: Crear frames de visualización 180°
        # Usamos apply_display_transform para asegurar consistencia con Modo Libre
        frame_left_display = StereoConfig.apply_display_transform(frame_left)
        frame_right_display = StereoConfig.apply_display_transform(frame_right)
        
        # Procesar teclado virtual (usando frame display para dibujo, raw para detección)
        if self.keyboard_processor and self.hand_detector_left and self.hand_detector_right:
            try:
                # IMPORTANTE: Pasamos los frames de display para que dibuje sobre la imagen rotada
                # y activamos rotate_hands=True para que ajuste las coordenadas de las manos
                frame_left_display, _ = self.keyboard_processor.process_and_play(
                    frame_left=frame_left,
                    frame_right=frame_right,
                    virtual_keyboard=self.virtual_keyboard,
                    hand_detector_left=self.hand_detector_left,
                    hand_detector_right=self.hand_detector_right,
                    game_mode=False,
                    rhythm_game=None,
                    display_frame_left=frame_left_display, # DIBUJAR AQUI
                    rotate_hands=True # Ajustar proyección de manos
                )
                
                # frame_right no lo estamos mostrando en la UI, así que no es crítico actualizarlo,
                # pero el processor podría devolverlo modificado si quisiéramos mostrarlo.
            except Exception as e:
                print(f"Error procesando teclado: {e}")
        
        # Ejecutar lógica de la lección
        try:
            # La lección también debe dibujar sobre los frames de visualización (overlays)
            frame_left_display, frame_right_display, _ = self.lesson.run(
                frame_left_display, frame_right_display, 
                self.virtual_keyboard, self.synth,
                self.hand_detector_left, self.hand_detector_right
            )
            
            # Obtener estado para UI (Texto)
            lesson_data = self.lesson.get_lesson_state()
            
            if 'instructions' in lesson_data:
                new_instructions = lesson_data['instructions']
                if self.instructions_text.toPlainText() != new_instructions:
                    self.instructions_text.setText(new_instructions)
            
            if 'progress' in lesson_data:
                self.progress_bar.setValue(lesson_data['progress'])
            
            if 'custom_info' in lesson_data:
                self.custom_info_label.setText(lesson_data['custom_info'])
            
        except Exception as e:
            print(f"Error ejecutando lección: {e}")
                
        # Mostrar solo frame izquierdo (el de visualización)
        self._display_frame(frame_left_display)
    
    def _display_frame(self, frame):
        """Convierte frame OpenCV a QPixmap y lo muestra"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            scaled_pixmap = pixmap.scaled(
                self.camera_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.camera_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Error mostrando frame: {e}")
    
    def _exit_lesson(self):
        """Maneja el botón de salir"""
        self.continue_lesson = False
        self.lesson.stop()
        
        # GUARDAR PROGRESO si la barra está al 100% o si el usuario sale
        # (Para facilitar pruebas, guardamos al salir ahora mismo)
        if self.lesson_index is not None:
             # Importar aquí para evitar ciclos si fuera necesario, o arriba
             from src.theory.progress_manager import ProgressManager
             pm = ProgressManager()
             pm.save_completion(self.lesson_index)
            #  print(f"Progreso guardado para lección índice: {self.lesson_index}")
        
        self.close()
    
    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        key = event.key()
        
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self._exit_lesson()
            return
        
        try:
            if key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z:
                char_code = ord('a') + (key - Qt.Key.Key_A)
                self.lesson.handle_key(char_code, self.synth)
            elif key >= Qt.Key.Key_0 and key <= Qt.Key.Key_9:
                char_code = ord('0') + (key - Qt.Key.Key_0)
                self.lesson.handle_key(char_code, self.synth)
            elif key == Qt.Key.Key_Space:
                # El espacio debería llegar aquí ahora que los cuadros de texto no tienen foco
                self.lesson.handle_key(ord(' '), self.synth)
            elif key == Qt.Key.Key_Left:
                self.lesson.handle_key(81, self.synth)
            elif key == Qt.Key.Key_Right:
                self.lesson.handle_key(83, self.synth)
            elif key == Qt.Key.Key_Up:
                self.lesson.handle_key(82, self.synth)
            elif key == Qt.Key.Key_Down:
                self.lesson.handle_key(84, self.synth)
            elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.lesson.handle_key(ord('+'), self.synth)
            elif key == Qt.Key.Key_Minus:
                self.lesson.handle_key(ord('-'), self.synth)
            
        except Exception as e:
            print(f"Error manejando tecla: {e}")
    
    def closeEvent(self, event):
        self.timer.stop()
        self.continue_lesson = False
        if self.lesson:
            self.lesson.stop()
        event.accept()


def show_lesson_window(lesson, camera_left, camera_right, synth, 
                      virtual_keyboard, hand_detector_left=None, hand_detector_right=None,
                      keyboard_mapper=None, angler=None, depth_estimator=None,
                      octave_base=60, keyboard_total_keys=24, camera_separation=9.07,
                      lesson_index=None):
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv)
        owns_app = True
    
    window = LessonWindow(lesson, camera_left, camera_right, synth,
                         virtual_keyboard, hand_detector_left, hand_detector_right,
                         keyboard_mapper, angler, depth_estimator, octave_base,
                         keyboard_total_keys, camera_separation, lesson_index)
    window.show()
    
    if owns_app:
        app.exec()
    else:
        while window.isVisible():
            app.processEvents()
    
    return window.continue_lesson
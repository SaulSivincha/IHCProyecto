#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ventana PyQt6 para Calibración Estereoscópica
Interfaz gráfica que muestra feeds de cámaras y guía el proceso
"""

import cv2
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QProgressBar, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont, QLinearGradient, QPainter, QColor
from src.config.theme import Theme

class ClickableLabel(QLabel):
    """QLabel que emite señales para click, drag y release"""
    clicked = pyqtSignal(int, int)  # x, y (click simple)
    drag_started = pyqtSignal(int, int)  # x, y (inicio de arrastre)
    drag_moved = pyqtSignal(int, int)  # x, y (movimiento durante arrastre)
    drag_ended = pyqtSignal(int, int)  # x, y (fin de arrastre)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging = False
        self._drag_start = None
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = (event.pos().x(), event.pos().y())
            self.drag_started.emit(event.pos().x(), event.pos().y())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._dragging:
            self.drag_moved.emit(event.pos().x(), event.pos().y())
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.drag_ended.emit(event.pos().x(), event.pos().y())
            # También emitir clicked para compatibilidad con otras fases
            self.clicked.emit(event.pos().x(), event.pos().y())
        super().mouseReleaseEvent(event)


class CalibrationWindow(QMainWindow):
    """
    Ventana principal para calibración con PyQt6
    Muestra feeds de cámaras y controla el proceso
    """
    
    # Señales para comunicación con el manager
    capture_requested = pyqtSignal()  # Usuario presionó capturar
    cancel_requested = pyqtSignal()   # Usuario presionó cancelar
    continue_requested = pyqtSignal() # Usuario presionó continuar
    retry_requested = pyqtSignal()    # Usuario presionó reintentar
    frame_clicked = pyqtSignal(str, int, int)  # camera_name, x, y (Nuevo para AR)
    # Nuevas señales para drag (arrastrar)
    frame_drag_started = pyqtSignal(str, int, int)  # camera_name, x, y
    frame_drag_moved = pyqtSignal(str, int, int)    # camera_name, x, y
    frame_drag_ended = pyqtSignal(str, int, int)    # camera_name, x, y
    # Señal para teclas de flecha (ajuste de línea guía)
    arrow_key_pressed = pyqtSignal(str)  # 'up' o 'down'
    
    def __init__(self, width=1280, height=720):
        super().__init__()
        self.width = width
        self.height = height
        
        # Estado
        self.current_phase = "init"  # init, config, capture_left, capture_right, stereo, depth
        self.is_waiting_input = False
        self.user_input = None
        
        self._setup_ui()
    
    def paintEvent(self, event):
        """Dibuja el fondo con gradiente del tema"""
        painter = QPainter(self)
        
        grad_start = QColor(Theme.to_hex(Theme.BG_GRADIENT_START))
        grad_end = QColor(Theme.to_hex(Theme.BG_GRADIENT_END))
        
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, grad_start)
        gradient.setColorAt(1, grad_end)
        painter.fillRect(self.rect(), gradient)
        
    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        self.setWindowTitle("Calibración Estereoscópica - Piano Virtual")
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ========== TÍTULO ==========
        self.title_label = QLabel("CALIBRACIÓN ESTEREOSCÓPICA")
        self.title_label.setStyleSheet(f"""
            color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
            font-size: 24px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            background: transparent;
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)
        
        # ========== ÁREA DE VIDEO ==========
        video_layout = QHBoxLayout()
        video_layout.setSpacing(5)
        
        # Cámara izquierda
        self.camera_left_label = ClickableLabel()
        self.camera_left_label.clicked.connect(lambda x, y: self.frame_clicked.emit("left", x, y))
        self.camera_left_label.drag_started.connect(lambda x, y: self.frame_drag_started.emit("left", x, y))
        self.camera_left_label.drag_moved.connect(lambda x, y: self.frame_drag_moved.emit("left", x, y))
        self.camera_left_label.drag_ended.connect(lambda x, y: self.frame_drag_ended.emit("left", x, y))
        self.camera_left_label.setStyleSheet(f"""
            border: 3px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
            border-radius: 10px;
            background-color: rgba(0,0,0,0.3);
        """)
        self.camera_left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_left_label.setMinimumSize(self.width // 2, self.height // 2)
        self.camera_left_label.setScaledContents(True)
        video_layout.addWidget(self.camera_left_label)
        
        # Cámara derecha
        self.camera_right_label = ClickableLabel()
        self.camera_right_label.clicked.connect(lambda x, y: self.frame_clicked.emit("right", x, y))
        self.camera_right_label.drag_started.connect(lambda x, y: self.frame_drag_started.emit("right", x, y))
        self.camera_right_label.drag_moved.connect(lambda x, y: self.frame_drag_moved.emit("right", x, y))
        self.camera_right_label.drag_ended.connect(lambda x, y: self.frame_drag_ended.emit("right", x, y))
        self.camera_right_label.setStyleSheet(f"""
            border: 3px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
            border-radius: 10px;
            background-color: rgba(0,0,0,0.3);
        """)
        self.camera_right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_right_label.setMinimumSize(self.width // 2, self.height // 2)
        self.camera_right_label.setScaledContents(True)
        video_layout.addWidget(self.camera_right_label)
        
        main_layout.addLayout(video_layout)
        
        # ========== BARRA DE PROGRESO ==========
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("Progreso: 0/25")
        self.progress_label.setStyleSheet(f"""
            color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
            font-size: 14px;
            font-weight: bold;
            background: transparent;
        """)
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 8px;
                text-align: center;
                background-color: rgba(255,255,255,0.3);
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-size: 12px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.to_hex(Theme.SUCCESS)};
                border-radius: 6px;
            }}
        """)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # ========== PANEL DE INSTRUCCIONES ==========
        self.instructions_panel = QTextEdit()
        self.instructions_panel.setReadOnly(True)
        self.instructions_panel.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(255,255,255,0.9);
                border: 2px solid {Theme.to_hex(Theme.ORANGE_VIVID)};
                border-radius: 10px;
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-size: 13px;
                padding: 10px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
        """)
        self.instructions_panel.setMaximumHeight(150)
        main_layout.addWidget(self.instructions_panel)
        
        # ========== ESTADO DE DETECCIÓN ==========
        self.status_label = QLabel("Preparando cámaras...")
        self.status_label.setStyleSheet(f"""
            color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
            font-size: 16px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            background: transparent;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # ========== BOTONES DE CONTROL ==========
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.capture_button = QPushButton("CAPTURAR [ESPACIO]")
        self.capture_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.SUCCESS)};
                color: #000000;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 20px;
                border: 3px solid #FFFFFF;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.GREEN_SOFT)};
            }}
            QPushButton:disabled {{
                background-color: {Theme.to_hex(Theme.GRAY)};
                color: #888888;
            }}
        """)
        self.capture_button.clicked.connect(self._on_capture_clicked)
        self.capture_button.setEnabled(False)
        button_layout.addWidget(self.capture_button)
        
        self.continue_button = QPushButton("CONTINUAR [ENTER]")
        self.continue_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_SUCCESS_BG)};
                color: {Theme.to_hex(Theme.BTN_SUCCESS_TEXT)};
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 20px;
                border: 3px solid #FFFFFF;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.GREEN_VIVID)};
            }}
            QPushButton:disabled {{
                background-color: {Theme.to_hex(Theme.GRAY)};
                color: #888888;
            }}
        """)
        self.continue_button.clicked.connect(self._on_continue_clicked)
        self.continue_button.setVisible(False)
        button_layout.addWidget(self.continue_button)
        
        self.retry_button = QPushButton("REINTENTAR [R]")
        self.retry_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 20px;
                border: 3px solid #FFFFFF;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
        """)
        self.retry_button.clicked.connect(self._on_retry_clicked)
        self.retry_button.setVisible(False)
        button_layout.addWidget(self.retry_button)
        
        self.cancel_button = QPushButton("CANCELAR [ESC]")
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.ERROR)};
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 20px;
                border: 3px solid #FFFFFF;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.RED_SOFT)};
            }}
        """)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Configurar teclas
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        key = event.key()
        
        # Flechas arriba/abajo para ajustar línea guía
        if key == Qt.Key.Key_Up:
            self.arrow_key_pressed.emit('up')
            return
        elif key == Qt.Key.Key_Down:
            self.arrow_key_pressed.emit('down')
            return
        
        # Permitir Enter para capturar también
        if (key == Qt.Key.Key_Space or key == Qt.Key.Key_Return) and self.capture_button.isEnabled():
            self._on_capture_clicked()
        elif key == Qt.Key.Key_Return and self.continue_button.isVisible():
            self._on_continue_clicked()
        elif (key == Qt.Key.Key_R) and self.retry_button.isVisible():
            self._on_retry_clicked()
        elif key == Qt.Key.Key_Escape:
            self._on_cancel_clicked()
    
    def _on_capture_clicked(self):
        """Emite señal de captura"""
        self.capture_requested.emit()
    
    def _on_continue_clicked(self):
        """Emite señal de continuar"""
        self.continue_requested.emit()
    
    def _on_cancel_clicked(self):
        """Emite señal de cancelar"""
        self.cancel_requested.emit()
    
    def _on_retry_clicked(self):
        """Emite señal de reintentar"""
        self.retry_requested.emit()
    
    def set_phase(self, phase_name, title=None):
        """
        Cambia la fase actual
        
        Args:
            phase_name: Nombre de la fase (config, capture_left, capture_right, stereo, depth)
            title: Título opcional para la ventana
        """
        self.current_phase = phase_name
        if title:
            self.title_label.setText(title)
    
    def update_frames(self, frame_left=None, frame_right=None):
        """
        Actualiza los feeds de las cámaras
        
        Args:
            frame_left: Frame de cámara izquierda (BGR)
            frame_right: Frame de cámara derecha (BGR)
        """
        # Importar configuración estéreo
        from src.vision.stereo_config import StereoConfig

        # Aplicar transformación según configuración (igual que en UIs)
        if hasattr(StereoConfig, 'ROTATE_CAMERAS_180') and StereoConfig.ROTATE_CAMERAS_180:
            if frame_left is not None:
                frame_left = cv2.flip(frame_left, -1)
            if frame_right is not None:
                frame_right = cv2.flip(frame_right, -1)
        elif hasattr(StereoConfig, 'MIRROR_HORIZONTAL') and StereoConfig.MIRROR_HORIZONTAL:
            if frame_left is not None:
                frame_left = cv2.flip(frame_left, 1)
            if frame_right is not None:
                frame_right = cv2.flip(frame_right, 1)

        if frame_left is not None:
            self._display_frame(frame_left, self.camera_left_label)
        
        if frame_right is not None:
            self._display_frame(frame_right, self.camera_right_label)
    
    def _display_frame(self, frame, label):
        """Convierte frame OpenCV a QPixmap y lo muestra"""
        # Convertir BGR a RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convertir a QImage
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        q_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Convertir a QPixmap y mostrar
        pixmap = QPixmap.fromImage(q_image)
        label.setPixmap(pixmap)
    
    def update_progress(self, current, total, text=None):
        """
        Actualiza la barra de progreso
        
        Args:
            current: Valor actual
            total: Valor total
            text: Texto opcional para el label
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        
        if text:
            self.progress_label.setText(text)
        else:
            self.progress_label.setText(f"Progreso: {current}/{total}")

    def show_progress(self, show=True):
        """Muestra/oculta la barra de progreso y su etiqueta"""
        self.progress_label.setVisible(show)
        self.progress_bar.setVisible(show)
    
    def set_instructions(self, instructions_html):
        """
        Actualiza el panel de instrucciones
        
        Args:
            instructions_html: Texto con formato HTML
        """
        self.instructions_panel.setHtml(instructions_html)
    
    def set_status(self, status_text, color=None):
        """
        Actualiza el texto de estado
        
        Args:
            status_text: Texto del estado
            color: Color en formato hex (opcional, usa Theme por defecto)
        """
        if color is None:
            color = Theme.to_hex(Theme.TEXT_HIGHLIGHT)
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"""
            color: {color};
            font-size: 16px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            background: transparent;
        """)
    
    def enable_capture(self, enabled=True):
        """Habilita/deshabilita el botón de captura"""
        self.capture_button.setEnabled(enabled)
    
    def show_continue_button(self, show=True):
        """Muestra/oculta el botón de continuar"""
        self.continue_button.setVisible(show)
        self.capture_button.setVisible(not show)
    
    def show_retry_button(self, show=True):
        """Muestra/oculta el botón de reintentar"""
        self.retry_button.setVisible(show)
    
    def show_intro_screen(self, phase_title, instructions):
        """
        Muestra pantalla de introducción de una fase
        
        Args:
            phase_title: Título de la fase
            instructions: Lista de instrucciones
        """
        self.title_label.setText(phase_title)
        
        # Colores del tema para instrucciones
        highlight_color = Theme.to_hex(Theme.ORANGE_VIVID)
        text_color = Theme.to_hex(Theme.TEXT_PRIMARY)
        success_color = Theme.to_hex(Theme.SUCCESS)
        
        html = f"<h3 style='color: {highlight_color};'>INSTRUCCIONES:</h3><ul>"
        for instruction in instructions:
            html += f"<li style='margin: 5px 0; color: {text_color};'>{instruction}</li>"
        html += "</ul>"
        html += f"<p style='color: {success_color}; margin-top: 10px;'><b>Presiona CONTINUAR o ENTER cuando estés listo</b></p>"
        
        self.set_instructions(html)
        self.set_status("Esperando confirmación...", Theme.to_hex(Theme.ORANGE_VIVID))
        self.show_continue_button(True)
    
    def show_capture_instructions(self, category_title, specific_instruction, objective, photo_num, total_photos):
        """
        Muestra instrucciones específicas para una captura
        
        Args:
            category_title: Título de la categoría
            specific_instruction: Instrucción específica
            objective: Objetivo de esta captura
            photo_num: Número de foto actual
            total_photos: Total de fotos
        """
        highlight_color = Theme.to_hex(Theme.ORANGE_VIVID)
        text_color = Theme.to_hex(Theme.TEXT_PRIMARY)
        success_color = Theme.to_hex(Theme.SUCCESS)
        
        html = f"<h3 style='color: {highlight_color};'>{category_title}</h3>"
        html += f"<p style='font-size: 14px; margin: 10px 0; color: {text_color};'><b>{specific_instruction}</b></p>"
        html += f"<p style='color: {success_color}; font-size: 12px;'><i>Objetivo: {objective}</i></p>"
        
        self.set_instructions(html)
        self.update_progress(photo_num, total_photos, f"Foto {photo_num + 1} de {total_photos}")
    
    def show_stereo_instructions(self, pair_num, total_pairs):
        """
        Muestra instrucciones para captura estéreo
        
        Args:
            pair_num: Número de par actual
            total_pairs: Total de pares necesarios
        """
        highlight_color = Theme.to_hex(Theme.ORANGE_VIVID)
        text_color = Theme.to_hex(Theme.TEXT_PRIMARY)
        
        html = f"<h3 style='color: {highlight_color};'>CALIBRACIÓN ESTÉREO</h3>"
        html += f"<p style='color: {text_color};'><b>Coloca el tablero visible en AMBAS cámaras</b></p>"
        html += "<ul>"
        html += f"<li style='color: {text_color};'>El tablero debe verse COMPLETO en ambas vistas</li>"
        html += f"<li style='color: {text_color};'>Varía la posición y orientación del tablero</li>"
        html += f"<li style='color: {text_color};'>Mantén buena iluminación</li>"
        html += "</ul>"
        
        self.set_instructions(html)
        self.update_progress(pair_num, total_pairs, f"Par {pair_num + 1} de {total_pairs}")
    
    def show_depth_instructions(self, target_distance, step, total_steps):
        """
        Muestra instrucciones para calibración de profundidad
        
        Args:
            target_distance: Distancia objetivo en cm
            step: Paso actual
            total_steps: Total de pasos
        """
        highlight_color = Theme.to_hex(Theme.SUCCESS)
        text_color = Theme.to_hex(Theme.TEXT_PRIMARY)
        
        html = f"<h3 style='color: {highlight_color};'>CALIBRACIÓN DE PROFUNDIDAD</h3>"
        html += f"<p style='font-size: 16px; margin: 10px 0; color: {text_color};'><b>Coloca tu DEDO ÍNDICE a {target_distance} cm de la CÁMARA IZQUIERDA</b></p>"
        html += "<ul>"
        html += f"<li style='color: {text_color};'>Usa una regla para medir la distancia exacta desde el lente izquierdo</li>"
        html += f"<li style='color: {text_color};'>Mantén el dedo quieto</li>"
        html += f"<li style='color: {text_color};'>Presiona CAPTURAR cuando esté en posición</li>"
        html += "</ul>"
        
        self.set_instructions(html)
        self.update_progress(step, total_steps, f"Medición {step + 1} de {total_steps}")
    
    def show_summary_screen(self, summary_data):
        """
        Muestra pantalla de resumen con resultados
        
        Args:
            summary_data: Diccionario con resultados de calibración
        """
        self.title_label.setText("CALIBRACIÓN COMPLETADA")
        
        success_color = Theme.to_hex(Theme.SUCCESS)
        text_color = Theme.to_hex(Theme.TEXT_PRIMARY)
        muted_color = Theme.to_hex(Theme.TEXT_SECONDARY)
        
        html = f"<h3 style='color: {success_color};'>RESULTADOS:</h3>"
        html += f"<table style='width: 100%; color: {text_color};'>"
        
        if 'board_config' in summary_data:
            html += f"<tr><td><b>Configuración:</b></td><td>{summary_data['board_config']}</td></tr>"
        
        if 'left_error' in summary_data:
            html += f"<tr><td><b>Error cámara izquierda:</b></td><td>{summary_data['left_error']:.6f} px</td></tr>"
        
        if 'right_error' in summary_data:
            html += f"<tr><td><b>Error cámara derecha:</b></td><td>{summary_data['right_error']:.6f} px</td></tr>"
        
        if 'stereo_error' in summary_data:
            html += f"<tr><td><b>Error estéreo:</b></td><td>{summary_data['stereo_error']:.6f}</td></tr>"
        
        if 'baseline' in summary_data:
            html += f"<tr><td><b>Baseline:</b></td><td>{summary_data['baseline']:.2f} cm</td></tr>"
        
        if 'correction_factor' in summary_data:
            html += f"<tr><td><b>Factor de corrección:</b></td><td>{summary_data['correction_factor']:.4f}</td></tr>"
        
        html += "</table>"
        html += f"<p style='color: {success_color}; margin-top: 20px;'><b>¡Calibración guardada exitosamente!</b></p>"
        html += f"<p style='color: {muted_color}; font-size: 12px;'>Presiona CONTINUAR o ENTER para finalizar</p>"
        
        self.set_instructions(html)
        self.set_status("Proceso completado", Theme.to_hex(Theme.SUCCESS))
        self.show_continue_button(True)
        self.progress_bar.setValue(100)

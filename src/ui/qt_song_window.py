#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ventana PyQt6 para jugar canciones en modo ritmo
Diseno visual mejorado y coherente con la interfaz principal
"""

import sys
import cv2
import numpy as np
import time
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFrame, QGridLayout, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont, QLinearGradient, QPainter, QColor
from src.piano.keyboard_processor import KeyboardProcessor
from src.config.theme import Theme


class ResultsDialog(QDialog):
    """Dialogo de resultados al finalizar la cancion"""
    
    def __init__(self, stats, song_name, parent=None):
        super().__init__(parent)
        self.result_action = 'menu'  # Por defecto volver al menu
        
        self.setWindowTitle("Resultados")
        self.setModal(True)
        self.setFixedSize(450, 500)
        # self.setWindowState(Qt.WindowState.WindowMaximized) # Dialogo pequeño, no maximizar
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.to_hex(Theme.BG_MAIN)};
            }}
            QLabel {{
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
            QPushButton#retry {{
                background-color: {Theme.to_hex(Theme.BTN_SUCCESS_BG)};
                color: {Theme.to_hex(Theme.BTN_SUCCESS_TEXT)};
            }}
            QPushButton#retry:hover {{
                background-color: {Theme.to_hex(Theme.GREEN_VIVID)};
            }}
            QPushButton#songs {{
                background-color: {Theme.to_hex(Theme.BTN_WARNING_BG)};
                color: {Theme.to_hex(Theme.BTN_SECONDARY_TEXT)}; 
            }}
            QPushButton#songs:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                color: #FFFFFF;
            }}
        """)
        
        self._build_ui(stats, song_name)
    
    def paintEvent(self, event):
        """Dibuja el fondo con gradiente del tema"""
        painter = QPainter(self)
        
        grad_start = QColor(Theme.to_hex(Theme.BG_GRADIENT_START))
        grad_end = QColor(Theme.to_hex(Theme.BG_GRADIENT_END))
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, grad_start)
        gradient.setColorAt(1, grad_end)
        painter.fillRect(self.rect(), gradient)
        
    def _build_ui(self, stats, song_name):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Titulo
        title = QLabel("RESULTADOS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)}; background: transparent;")
        layout.addWidget(title)
        
        # Nombre de cancion
        song_label = QLabel(song_name)
        song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        song_label.setStyleSheet(f"font-size: 18px; color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; background: transparent;")
        layout.addWidget(song_label)
        
        layout.addSpacing(20)
        
        # Calificacion
        accuracy = stats.get('accuracy', 0)
        if accuracy >= 95:
            grade, grade_color = "S", Theme.to_hex(Theme.ORANGE_VIVID)
        elif accuracy >= 90:
            grade, grade_color = "A", Theme.to_hex(Theme.SUCCESS)
        elif accuracy >= 80:
            grade, grade_color = "B", Theme.to_hex(Theme.INFO)
        elif accuracy >= 70:
            grade, grade_color = "C", Theme.to_hex(Theme.WARNING)
        else:
            grade, grade_color = "D", Theme.to_hex(Theme.ERROR)
        
        grade_label = QLabel(grade)
        grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grade_label.setStyleSheet(f"font-size: 72px; font-weight: bold; color: {grade_color}; background: transparent;")
        layout.addWidget(grade_label)
        
        # Estadisticas
        stats_widget = QWidget()
        stats_widget.setStyleSheet("background: rgba(255, 255, 255, 0.5); border-radius: 10px;")
        stats_layout = QGridLayout(stats_widget)
        stats_layout.setSpacing(10)
        
        self._add_stat(stats_layout, 0, "Puntaje:", f"{stats.get('score', 0):,}", Theme.to_hex(Theme.ORANGE_VIVID))
        self._add_stat(stats_layout, 1, "Max Combo:", f"{stats.get('combo', 0)}x", Theme.to_hex(Theme.BLUE_SOFT))
        self._add_stat(stats_layout, 2, "PERFECT:", str(stats.get('perfect', 0)), Theme.to_hex(Theme.SUCCESS))
        self._add_stat(stats_layout, 3, "GOOD:", str(stats.get('good', 0)), Theme.to_hex(Theme.WARNING))
        self._add_stat(stats_layout, 4, "MISS:", str(stats.get('miss', 0)), Theme.to_hex(Theme.ERROR))
        self._add_stat(stats_layout, 5, "Precision:", f"{accuracy:.1f}%", grade_color)
        
        layout.addWidget(stats_widget)
        
        layout.addSpacing(20)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        songs_btn = QPushButton("OTRA CANCION")
        songs_btn.setObjectName("songs")
        songs_btn.clicked.connect(lambda: self._select_action('songs'))
        btn_layout.addWidget(songs_btn)
        
        menu_btn = QPushButton("REGRESAR")
        menu_btn.clicked.connect(lambda: self._select_action('menu'))
        btn_layout.addWidget(menu_btn)
        
        layout.addLayout(btn_layout)
    
    def _add_stat(self, layout, row, label, value, color):
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 14px; color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; background: transparent;")
        layout.addWidget(lbl, row, 0)
        
        val = QLabel(value)
        val.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; background: transparent;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(val, row, 1)
    
    def _select_action(self, action):
        self.result_action = action
        self.accept()


class SongWindow(QMainWindow):
    """Ventana principal para jugar canciones en modo ritmo"""
    
    def __init__(self, song, camera_left, camera_right, synth, 
                 virtual_keyboard, hand_detector_left=None, hand_detector_right=None,
                 keyboard_mapper=None, angler=None, depth_estimator=None, octave_base=60,
                 keyboard_total_keys=24, camera_separation=9.07):
        super().__init__()
        
        self.song = song
        self.camera_left = camera_left
        self.camera_right = camera_right
        self.synth = synth
        self.virtual_keyboard = virtual_keyboard
        self.hand_detector_left = hand_detector_left
        self.hand_detector_right = hand_detector_right
        self.keyboard_total_keys = keyboard_total_keys
        
        # Crear procesador de teclado
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
        
        self.continue_song = True
        self.result_action = 'menu'
        self.game_ended = False
        self.timer = QTimer()
        
        # Configuracion visual
        self.setWindowTitle(f"Modo Ritmo - {song.name}")
        self.setMinimumSize(1400, 800)
        
        self.setStyleSheet(f"""
            QLabel {{
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QLabel#title {{
                color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#score {{
                color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                font-size: 36px;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#combo {{
                color: {Theme.to_hex(Theme.BLUE_SOFT)};
                font-size: 28px;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#perfect {{ color: {Theme.to_hex(Theme.SUCCESS)}; font-size: 14px; background: transparent;}}
            QLabel#good {{ color: {Theme.to_hex(Theme.WARNING)}; font-size: 14px; background: transparent;}}
            QLabel#miss {{ color: {Theme.to_hex(Theme.ERROR)}; font-size: 14px; background: transparent;}}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BG_PANEL)};
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: bold;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.LIGHT_GRAY)};
            }}
            QPushButton#exit {{
                background-color: {Theme.to_hex(Theme.BTN_DANGER_BG)};
                color: {Theme.to_hex(Theme.BTN_DANGER_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
            }}
            QPushButton#exit:hover {{
                background-color: {Theme.to_hex(Theme.RED_VIVID)};
            }}
            QProgressBar {{
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.5);
                text-align: center;
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-weight: bold;
                min-height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.to_hex(Theme.SUCCESS)};
                border-radius: 6px;
            }}
            QFrame#camera {{
                border: 4px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 15px;
                background-color: #000000;
            }}
            QFrame#stats {{
                background-color: rgba(255, 255, 255, 0.6);
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 15px;
            }}
        """)
        
        self._build_ui()
        self._start_game()
        
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
        central = QWidget()
        central.setStyleSheet("background: transparent;") # Para que se vea el gradiente
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        # Encabezado
        header = QHBoxLayout()
        title = QLabel(self.song.name)
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        
        mode_label = QLabel("MODO RITMO")
        mode_label.setStyleSheet(f"color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; font-size: 16px; background: transparent;")
        header.addWidget(mode_label)
        main_layout.addLayout(header)
        
        # Contenido
        content = QHBoxLayout()
        
        # Camara
        camera_frame = QFrame()
        camera_frame.setObjectName("camera")
        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setContentsMargins(5, 5, 5, 5)
        
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(800, 500)
        self.camera_label.setStyleSheet("background-color: #000000;")
        camera_layout.addWidget(self.camera_label)
        content.addWidget(camera_frame, 3)
        
        # Panel de estadisticas
        stats_frame = QFrame()
        stats_frame.setObjectName("stats")
        stats_frame.setMaximumWidth(320)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setSpacing(15)
        stats_layout.setContentsMargins(20, 20, 20, 20)
        
        # Score
        score_title = QLabel("PUNTAJE")
        score_title.setStyleSheet(f"color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; font-size: 14px; background: transparent;")
        stats_layout.addWidget(score_title)
        
        self.score_label = QLabel("0")
        self.score_label.setObjectName("score")
        stats_layout.addWidget(self.score_label)
        
        # Combo
        combo_title = QLabel("COMBO")
        combo_title.setStyleSheet(f"color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; font-size: 14px; background: transparent;")
        stats_layout.addWidget(combo_title)
        
        self.combo_label = QLabel("0x")
        self.combo_label.setObjectName("combo")
        stats_layout.addWidget(self.combo_label)
        
        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {Theme.to_hex(Theme.BORDER_DEFAULT)};")
        stats_layout.addWidget(sep)
        
        # Estadisticas
        self.perfect_label = QLabel("PERFECT: 0")
        self.perfect_label.setObjectName("perfect")
        stats_layout.addWidget(self.perfect_label)
        
        self.good_label = QLabel("GOOD: 0")
        self.good_label.setObjectName("good")
        stats_layout.addWidget(self.good_label)
        
        self.miss_label = QLabel("MISS: 0")
        self.miss_label.setObjectName("miss")
        stats_layout.addWidget(self.miss_label)
        
        # Precision
        self.accuracy_label = QLabel("Precision: 0%")
        self.accuracy_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Theme.to_hex(Theme.TEXT_PRIMARY)}; background: transparent;")
        stats_layout.addWidget(self.accuracy_label)
        
        # Progreso
        progress_title = QLabel("PROGRESO")
        progress_title.setStyleSheet(f"color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; font-size: 14px; margin-top: 10px; background: transparent;")
        stats_layout.addWidget(progress_title)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        stats_layout.addWidget(self.progress_bar)
        
        stats_layout.addStretch()
        
        # Boton salir
        exit_btn = QPushButton("SALIR")
        exit_btn.setObjectName("exit")
        exit_btn.clicked.connect(self._exit_song)
        stats_layout.addWidget(exit_btn)
        
        content.addWidget(stats_frame)
        main_layout.addLayout(content)
        
        # Footer
        footer = QLabel("ESC para salir | Toca las teclas cuando las notas lleguen a la linea")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {Theme.to_hex(Theme.TEXT_SECONDARY)}; font-size: 14px; background: transparent;")
        main_layout.addWidget(footer)
    
    def _start_game(self):
        self.song.start(
            virtual_keyboard=self.virtual_keyboard,
            num_keys=self.keyboard_total_keys
        )
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)
    
    def _update_frame(self):
        if not self.continue_song:
            return
        
        # Verificar si termino el juego
        if self.song.rhythm_game and self.song.rhythm_game.is_game_finished():
            if not self.game_ended:
                self.game_ended = True
                self._show_results()
            return
        
        if not self.song.running:
            self.close()
            return
        
        # Obtener frames
        _, frame_left = self.camera_left.next(black=True, wait=1)
        _, frame_right = self.camera_right.next(black=True, wait=1)
        
        if frame_left is None or frame_right is None:
            return
        
        # Transformaciones
        from src.vision.stereo_config import StereoConfig
        if getattr(StereoConfig, 'ROTATE_CAMERAS_180', False):
            frame_left = cv2.flip(frame_left, -1)
            frame_right = cv2.flip(frame_right, -1)
        elif getattr(StereoConfig, 'MIRROR_HORIZONTAL', False):
            frame_left = cv2.flip(frame_left, 1)
            frame_right = cv2.flip(frame_right, 1)
        
        # Procesar teclado
        if self.keyboard_processor and self.hand_detector_left and self.hand_detector_right:
            try:
                frame_left, frame_right = self.keyboard_processor.process_and_play(
                    frame_left=frame_left,
                    frame_right=frame_right,
                    virtual_keyboard=self.virtual_keyboard,
                    hand_detector_left=self.hand_detector_left,
                    hand_detector_right=self.hand_detector_right,
                    game_mode=True,
                    rhythm_game=self.song.rhythm_game if self.song.rhythm_game else None
                )
            except Exception as e:
                print(f"Error procesando teclado: {e}")
        
        # Ejecutar cancion
        try:
            frame_left, frame_right, continue_running = self.song.run(
                frame_left, frame_right, self.virtual_keyboard, self.synth
            )
            
            if not continue_running:
                self.continue_song = False
            
            # Actualizar UI
            state = self.song.get_song_state()
            stats = state.get('stats', {})
            
            self.score_label.setText(f"{state['score']:,}")
            self.combo_label.setText(f"{state['combo']}x")
            self.perfect_label.setText(f"PERFECT: {stats.get('perfect', 0)}")
            self.good_label.setText(f"GOOD: {stats.get('good', 0)}")
            self.miss_label.setText(f"MISS: {stats.get('miss', 0)}")
            
            accuracy = stats.get('accuracy', 0)
            if accuracy >= 90:
                acc_color = Theme.to_hex(Theme.SUCCESS)
            elif accuracy >= 70:
                acc_color = Theme.to_hex(Theme.WARNING)
            else:
                acc_color = Theme.to_hex(Theme.ERROR)
            
            self.accuracy_label.setText(f"Precision: {accuracy:.1f}%")
            self.accuracy_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {acc_color}; background: transparent;")
            
            self.progress_bar.setValue(state['progress'])
            
        except Exception as e:
            print(f"Error ejecutando cancion: {e}")
        
        self._display_frame(frame_left)
    
    def _display_frame(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb = np.ascontiguousarray(rgb)
            h, w, ch = rgb.shape
            
            q_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(q_img)
            
            scaled = pixmap.scaled(
                self.camera_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.camera_label.setPixmap(scaled)
        except Exception as e:
            print(f"Error mostrando frame: {e}")
    
    def _show_results(self):
        """Muestra el dialogo de resultados"""
        self.timer.stop()
        
        # Obtener estadisticas finales
        if self.song.rhythm_game:
            stats = self.song.rhythm_game.get_final_score()
        else:
            stats = {}
        
        # Mostrar dialogo
        dialog = ResultsDialog(stats, self.song.name, self)
        dialog.exec()
        
        self.result_action = dialog.result_action
        self.continue_song = False
        self.close()
    
    def _exit_song(self):
        self.continue_song = False
        self.result_action = 'menu'
        self.song.stop()
        self.close()
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self._exit_song()
    
    def closeEvent(self, event):
        self.timer.stop()
        self.continue_song = False
        if self.song:
            self.song.stop()
        event.accept()


def show_song_window(song, camera_left, camera_right, synth, 
                     virtual_keyboard, hand_detector_left=None, hand_detector_right=None,
                     keyboard_mapper=None, angler=None, depth_estimator=None, 
                     octave_base=60, keyboard_total_keys=24, camera_separation=9.07):
    """
    Muestra la ventana de juego de cancion
    
    Returns:
        str: 'retry', 'songs', o 'menu'
    """
    try:
        app = QApplication.instance()
        owns_app = False
        if app is None:
            app = QApplication(sys.argv)
            owns_app = True
        
        window = SongWindow(song, camera_left, camera_right, synth,
                           virtual_keyboard, hand_detector_left, hand_detector_right,
                           keyboard_mapper, angler, depth_estimator, octave_base, 
                           keyboard_total_keys, camera_separation)
        window.show()
        
        if owns_app:
            app.exec()
        else:
            while window.isVisible():
                app.processEvents()
        
        return window.result_action
    except Exception as e:
        import traceback
        from PyQt6.QtWidgets import QMessageBox
        error_msg = traceback.format_exc()
        print(f"ERROR lanzando SongWindow: {e}")
        print(error_msg)
        
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error")
            msg.setText("Error al iniciar el Juego de Ritmo")
            msg.setDetailedText(error_msg)
            msg.exec()
        except:
            pass
        return 'menu'

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Menú de selección de canciones con PyQt6
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpacerItem, QSizePolicy, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor
from src.config.theme import Theme

class SongsMenuDialog(QDialog):
    """
    Diálogo para seleccionar una canción para el modo ritmo
    """

    def __init__(self, songs):
        """
        Args:
            songs: Diccionario {name: song_instance}
        """
        super().__init__()
        
        self.songs = songs
        self.songs_list = list(songs.values())
        self.selected_song_name: Optional[str] = None
        self.selected_index = 0
        
        self.setWindowTitle("Modo Ritmo - Selección de Canción")
        self.setMinimumSize(900, 600)
        
        # El estilo principal se maneja en paintEvent para el gradiente
        self.setStyleSheet(f"""
            QLabel {{
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QLabel#title {{
                color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
                font-size: 32px;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#subtitle {{
                color: {Theme.to_hex(Theme.TEXT_SECONDARY)};
                font-size: 16px;
                background: transparent;
            }}
            QLabel#songName {{
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-size: 18px;
                font-weight: bold;
            }}
            QLabel#songInfo {{
                color: {Theme.to_hex(Theme.TEXT_SECONDARY)};
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                font-size: 14px;
                padding: 10px 18px;
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 10px;
                font-family: 'Comic Sans MS', 'Arial';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
            QPushButton#playButton {{
                background-color: {Theme.to_hex(Theme.BTN_SUCCESS_BG)};
                border: 3px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                color: {Theme.to_hex(Theme.BTN_SUCCESS_TEXT)};
                font-size: 18px;
                border-radius: 20px;
                padding: 12px 30px;
            }}
            QPushButton#playButton:hover {{
                background-color: {Theme.to_hex(Theme.GREEN_VIVID)};
            }}
            QPushButton#backButton {{
                background-color: {Theme.to_hex(Theme.BTN_WARNING_BG)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                color: {Theme.to_hex(Theme.BTN_SECONDARY_TEXT)};
            }}
            QPushButton#backButton:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                color: {Theme.to_hex(Theme.WHITE)};
            }}
            QWidget#songCard {{
                background-color: rgba(255, 255, 255, 0.6);
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 12px;
            }}
            QWidget#songCardSelected {{
                background-color: rgba(255, 255, 255, 0.9);
                border: 3px solid {Theme.to_hex(Theme.ORANGE_VIVID)};
                border-radius: 12px;
            }}
        """)
        
        self._build_ui()
    
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
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)
        
        # ========== TÍTULO ==========
        title = QLabel("MODO RITMO")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        subtitle = QLabel("Selecciona una canción")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)
        
        main_layout.addSpacing(10)
        
        # ========== ÁREA DE SCROLL PARA CANCIONES ==========
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.songs_layout = QVBoxLayout(scroll_content)
        self.songs_layout.setSpacing(10)
        
        # Crear tarjeta para cada canción
        self.song_buttons = []
        for idx, song in enumerate(self.songs_list):
            card = self._create_song_card(song, idx)
            self.songs_layout.addWidget(card)
            self.song_buttons.append(card)
        
        self.songs_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # ========== BOTONES DE ACCIÓN ==========
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        back_btn = QPushButton("← Volver")
        back_btn.setObjectName("backButton")
        back_btn.clicked.connect(self._on_back)
        button_layout.addWidget(back_btn)
        
        button_layout.addStretch()
        
        play_btn = QPushButton("▶ JUGAR")
        play_btn.setObjectName("playButton")
        play_btn.clicked.connect(self._on_play)
        button_layout.addWidget(play_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Seleccionar primera canción por defecto
        if self.song_buttons:
            self._select_song(0)
    
    def _create_song_card(self, song, index):
        """Crea una tarjeta para una canción"""
        card = QPushButton()
        card.setObjectName("songCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.clicked.connect(lambda: self._select_song(index))
        
        # Layout interno
        card_layout = QVBoxLayout()
        card_layout.setSpacing(5)
        
        # Nombre
        name_label = QLabel(f"{index + 1}. {song.name}")
        name_label.setObjectName("songName")
        name_label.setStyleSheet("background: transparent; border: none;")
        card_layout.addWidget(name_label)
        
        # Info (BPM, dificultad, tonalidad)
        info_text = f"{song.bpm} BPM  •  {song.difficulty}  •  Tonalidad: {song.music_key}"
        info_label = QLabel(info_text)
        info_label.setObjectName("songInfo")
        info_label.setStyleSheet("background: transparent; border: none;")
        card_layout.addWidget(info_label)
        
        card.setLayout(card_layout)
        card.setMinimumHeight(90)
        
        return card
    
    def _select_song(self, index):
        """Selecciona una canción"""
        # Deseleccionar anterior
        if 0 <= self.selected_index < len(self.song_buttons):
            self.song_buttons[self.selected_index].setObjectName("songCard")
            # Forzar actualización de estilo
            self.song_buttons[self.selected_index].style().unpolish(self.song_buttons[self.selected_index])
            self.song_buttons[self.selected_index].style().polish(self.song_buttons[self.selected_index])
        
        # Seleccionar nueva
        self.selected_index = index
        self.song_buttons[index].setObjectName("songCardSelected")
        # Forzar actualización de estilo
        self.song_buttons[index].style().unpolish(self.song_buttons[index])
        self.song_buttons[index].style().polish(self.song_buttons[index])
        
        # Guardar nombre
        self.selected_song_name = self.songs_list[index].name
        # print(f"Seleccionada: {self.selected_song_name}")
    
    def _on_play(self):
        """Inicia la canción seleccionada"""
        if self.selected_song_name:
            self.accept()
    
    def _on_back(self):
        """Vuelve al menú anterior"""
        self.selected_song_name = None
        self.reject()
    
    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self._on_back()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._on_play()
        elif key == Qt.Key.Key_Up or key == Qt.Key.Key_W:
            new_idx = max(0, self.selected_index - 1)
            self._select_song(new_idx)
        elif key == Qt.Key.Key_Down or key == Qt.Key.Key_S:
            new_idx = min(len(self.songs_list) - 1, self.selected_index + 1)
            self._select_song(new_idx)


def show_songs_menu(songs):
    """
    Muestra el menú de selección de canciones
    
    Args:
        songs: Diccionario {name: song_instance}
    
    Returns:
        str or None: Nombre de la canción seleccionada, o None si canceló
    """
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        dialog = SongsMenuDialog(songs)
        result = dialog.exec()
        
        selected = dialog.selected_song_name if result == QDialog.DialogCode.Accepted else None
        
        return selected
    except Exception as e:
        import traceback
        from PyQt6.QtWidgets import QMessageBox
        error_msg = traceback.format_exc()
        print(f"ERROR lanzando SongsMenu: {e}")
        print(error_msg)
        
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error")
            msg.setText("Error al abrir el Menú de Canciones")
            msg.setDetailedText(error_msg)
            msg.exec()
        except:
            pass
        return None

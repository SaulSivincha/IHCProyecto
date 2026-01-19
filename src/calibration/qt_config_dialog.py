#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diálogo de configuración para parámetros de calibración
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QLinearGradient, QPainter, QColor
from src.config.theme import Theme

class CalibrationConfigDialog(QDialog):
    """
    Diálogo modal para configurar parámetros del tablero antes de calibrar
    """
    
    def __init__(self, parent=None, default_rows=7, default_cols=7, default_size_mm=24.0,
                 enable_phase2=False, enable_phase3=False, enable_phase4=False):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Calibración")
        self.setModal(True)
        
        # Asegurar que el diálogo aparezca al frente
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self.rows = default_rows
        self.cols = default_cols
        self.size_mm = default_size_mm
        self.enable_phase2 = enable_phase2
        self.enable_phase3 = enable_phase3
        self.enable_phase4 = enable_phase4
        self.selected_phase = 1
        
        self._setup_ui()
    
    def paintEvent(self, event):
        """Dibuja el fondo con gradiente del tema"""
        painter = QPainter(self)
        
        grad_start = QColor(Theme.to_hex(Theme.BG_GRADIENT_START))
        grad_end = QColor(Theme.to_hex(Theme.BG_GRADIENT_END))
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, grad_start)
        gradient.setColorAt(1, grad_end)
        painter.fillRect(self.rect(), gradient)
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Colores del tema
        colors = {
            "text": Theme.to_hex(Theme.TEXT_PRIMARY),
            "highlight": Theme.to_hex(Theme.TEXT_HIGHLIGHT),
            "muted": Theme.to_hex(Theme.TEXT_SECONDARY),
            "border": Theme.to_hex(Theme.BORDER_DEFAULT),
            "bg": "rgba(255,255,255,0.8)",
            "bg_input": "rgba(255,255,255,0.9)",
        }
        
        # Título
        title = QLabel("Parámetros del Tablero de Ajedrez")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {colors['highlight']};
            font-family: 'Comic Sans MS', 'Arial';
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Grupo de dimensiones
        dim_group = QGroupBox("Dimensiones (Esquinas Internas)")
        dim_group.setStyleSheet(f"""
            QGroupBox {{
                color: {colors['highlight']};
                font-weight: bold;
                border: 2px solid {colors['border']};
                border-radius: 10px;
                margin-top: 10px;
                background-color: {colors['bg']};
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
            }}
        """)
        dim_layout = QVBoxLayout()
        
        # Filas
        row_layout = QHBoxLayout()
        row_label = QLabel("Filas (Alto):")
        row_label.setStyleSheet(f"color: {colors['text']}; font-size: 14px; background: transparent;")
        self.row_spin = QSpinBox()
        self.row_spin.setRange(3, 20)
        self.row_spin.setValue(self.rows)
        self.row_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {colors['bg_input']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }}
        """)
        row_layout.addWidget(row_label)
        row_layout.addWidget(self.row_spin)
        dim_layout.addLayout(row_layout)
        
        # Columnas
        col_layout = QHBoxLayout()
        col_label = QLabel("Columnas (Ancho):")
        col_label.setStyleSheet(f"color: {colors['text']}; font-size: 14px; background: transparent;")
        self.col_spin = QSpinBox()
        self.col_spin.setRange(3, 20)
        self.col_spin.setValue(self.cols)
        self.col_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {colors['bg_input']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }}
        """)
        col_layout.addWidget(col_label)
        col_layout.addWidget(self.col_spin)
        dim_layout.addLayout(col_layout)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        # Grupo de tamaño físico
        size_group = QGroupBox("Tamaño Físico")
        size_group.setStyleSheet(f"""
            QGroupBox {{
                color: {colors['highlight']};
                font-weight: bold;
                border: 2px solid {colors['border']};
                border-radius: 10px;
                margin-top: 10px;
                background-color: {colors['bg']};
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
            }}
        """)
        size_layout = QVBoxLayout()
        
        size_h_layout = QHBoxLayout()
        size_label = QLabel("Tamaño de cuadro (mm):")
        size_label.setStyleSheet(f"color: {colors['text']}; font-size: 14px; background: transparent;")
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(5.0, 100.0)
        self.size_spin.setSingleStep(0.5)
        self.size_spin.setDecimals(2)
        self.size_spin.setValue(self.size_mm)
        self.size_spin.valueChanged.connect(self._on_size_changed)
        self.size_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {colors['bg_input']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }}
        """)
        size_h_layout.addWidget(size_label)
        size_h_layout.addWidget(self.size_spin)
        size_layout.addLayout(size_h_layout)
        
        # Nota informativa
        note = QLabel("Nota: Mide el lado de un cuadrado negro con una regla.")
        note.setStyleSheet(f"color: {colors['muted']}; font-style: italic; font-size: 12px; background: transparent;")
        note.setWordWrap(True)
        size_layout.addWidget(note)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # Grupo de Fase de Inicio
        phase_group = QGroupBox("Iniciar desde")
        phase_group.setStyleSheet(f"""
            QGroupBox {{
                color: {colors['highlight']};
                font-weight: bold;
                border: 2px solid {colors['border']};
                border-radius: 10px;
                margin-top: 10px;
                background-color: {colors['bg']};
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
            }}
        """)
        phase_layout = QVBoxLayout()
        
        self.phase_combo = QComboBox()
        self.phase_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {colors['bg_input']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: rgba(255,255,255,0.95);
                color: {colors['text']};
                selection-background-color: {colors['highlight']};
            }}
        """)
        
        self.phase_combo.addItem("Fase 0: Rectificación de Cámaras", 0)
        self.phase_combo.addItem("Fase 1: Calibración Individual (Completa)", 1)
        
        if self.enable_phase2:
            self.phase_combo.addItem("Fase 2: Calibración Estéreo", 2)
            
        if self.enable_phase3:
            self.phase_combo.addItem("Fase 3: Calibración de Profundidad", 3)
            
        if self.enable_phase4:
            self.phase_combo.addItem("Fase 4: Definición de Mesa (AR)", 4)
            
        phase_layout.addWidget(self.phase_combo)
        phase_group.setLayout(phase_layout)
        layout.addWidget(phase_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_DANGER_BG)};
                color: {Theme.to_hex(Theme.BTN_DANGER_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 15px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.RED_VIVID)};
            }}
            QPushButton:pressed {{
                background-color: #8B0000;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setAutoDefault(False)
        
        accept_btn = QPushButton("Iniciar Calibración")
        accept_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                border: 3px solid #FFFFFF;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 15px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QPushButton:pressed {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                border-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
        """)
        accept_btn.clicked.connect(self.accept_values)
        accept_btn.setDefault(True)
        accept_btn.setAutoDefault(True)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(accept_btn)
        
        layout.addLayout(btn_layout)
        
        # Conectar spinboxes para que Enter llame a accept_values
        self.row_spin.editingFinished.connect(lambda: None)
        self.col_spin.editingFinished.connect(lambda: None)
        self.size_spin.editingFinished.connect(lambda: None)
        
    def _on_size_changed(self, value):
        """Actualiza el valor interno cuando cambia el spinbox"""
        print(f"[DEBUG] Tamaño de cuadro cambiado a: {value}")
        self.size_mm = value
        
    def accept_values(self):
        """Guarda los valores y acepta el diálogo"""
        print(f"[DEBUG] accept_values() llamado")
        
        # Forzar que los spinboxes actualicen su valor interno
        self.row_spin.interpretText()
        self.col_spin.interpretText()
        self.size_spin.interpretText()
        
        self.rows = self.row_spin.value()
        self.cols = self.col_spin.value()
        self.size_mm = self.size_spin.value()
        self.selected_phase = self.phase_combo.currentData()
        
        print(f"[DEBUG] Valores obtenidos: rows={self.rows}, cols={self.cols}, size_mm={self.size_mm}, phase={self.selected_phase}")
        
        self.accept()
        
    def get_values(self):
        print(f"[DEBUG] get_values() llamado: rows={self.rows}, cols={self.cols}, size_mm={self.size_mm}, phase={self.selected_phase}")
        return self.rows, self.cols, self.size_mm, self.selected_phase

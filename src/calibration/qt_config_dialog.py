#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diálogo de configuración para parámetros de calibración
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt

class CalibrationConfigDialog(QDialog):
    """
    Diálogo modal para configurar parámetros del tablero antes de calibrar
    """
    
    def __init__(self, parent=None, default_rows=7, default_cols=7, default_size_mm=24.0,
                 enable_phase2=False, enable_phase3=False):
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
        self.selected_phase = 1
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QGroupBox {
                color: #00C8FF;
                font-weight: bold;
                border: 1px solid #00C8FF;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #00C8FF;
                color: #000000;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #33D6FF;
            }
            QPushButton#cancelButton {
                background-color: #555555;
                color: #ffffff;
            }
            QPushButton#cancelButton:hover {
                background-color: #777777;
            }
        """)
        
        self.rows = default_rows
        self.cols = default_cols
        self.size_mm = default_size_mm
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("Parámetros del Tablero de Ajedrez")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00C8FF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Grupo de dimensiones
        dim_group = QGroupBox("Dimensiones (Esquinas Internas)")
        dim_layout = QVBoxLayout()
        
        # Filas
        row_layout = QHBoxLayout()
        row_label = QLabel("Filas (Alto):")
        self.row_spin = QSpinBox()
        self.row_spin.setRange(3, 20)
        self.row_spin.setValue(self.rows)
        row_layout.addWidget(row_label)
        row_layout.addWidget(self.row_spin)
        dim_layout.addLayout(row_layout)
        
        # Columnas
        col_layout = QHBoxLayout()
        col_label = QLabel("Columnas (Ancho):")
        self.col_spin = QSpinBox()
        self.col_spin.setRange(3, 20)
        self.col_spin.setValue(self.cols)
        col_layout.addWidget(col_label)
        col_layout.addWidget(self.col_spin)
        dim_layout.addLayout(col_layout)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        # Grupo de tamaño físico
        size_group = QGroupBox("Tamaño Físico")
        size_layout = QVBoxLayout()
        
        size_h_layout = QHBoxLayout()
        size_label = QLabel("Tamaño de cuadro (mm):")
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(5.0, 100.0)
        self.size_spin.setSingleStep(0.5)
        self.size_spin.setDecimals(2)  # Asegurar 2 decimales
        self.size_spin.setValue(self.size_mm)
        # Conectar señal para actualizar valor interno inmediatamente
        self.size_spin.valueChanged.connect(self._on_size_changed)
        size_h_layout.addWidget(size_label)
        size_h_layout.addWidget(self.size_spin)
        size_layout.addLayout(size_h_layout)
        
        # Nota informativa
        note = QLabel("Nota: Mide el lado de un cuadrado negro con una regla.")
        note.setStyleSheet("color: #aaaaaa; font-style: italic; font-size: 12px;")
        note.setWordWrap(True)
        size_layout.addWidget(note)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # Grupo de Fase de Inicio
        phase_group = QGroupBox("Iniciar desde")
        phase_layout = QVBoxLayout()
        
        self.phase_combo = QComboBox()
        self.phase_combo.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3b3b3b;
                color: #ffffff;
                selection-background-color: #00C8FF;
            }
        """)
        
        self.phase_combo.addItem("Fase 1: Calibración Individual (Completa)", 1)
        
        if self.enable_phase2:
            self.phase_combo.addItem("Fase 2: Calibración Estéreo", 2)
            
        if self.enable_phase3:
            self.phase_combo.addItem("Fase 3: Calibración de Profundidad", 3)
            
        # Seleccionar la fase más avanzada disponible por defecto
        # self.phase_combo.setCurrentIndex(self.phase_combo.count() - 1)
        
        phase_layout.addWidget(self.phase_combo)
        phase_group.setLayout(phase_layout)
        layout.addWidget(phase_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setAutoDefault(False)  # Evitar que se active con Enter
        
        accept_btn = QPushButton("Iniciar Calibración")
        accept_btn.clicked.connect(self.accept_values)
        accept_btn.setDefault(True)  # Este es el botón principal
        accept_btn.setAutoDefault(True)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(accept_btn)
        
        layout.addLayout(btn_layout)
        
        # Conectar spinboxes para que Enter llame a accept_values
        self.row_spin.editingFinished.connect(lambda: None)  # Solo actualizar valor
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

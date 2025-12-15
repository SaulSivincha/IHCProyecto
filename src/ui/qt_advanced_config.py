#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ventana de Configuración Avanzada - Parámetros de Algoritmos
Permite ajustar algoritmos de detección en tiempo real
"""

import sys
from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QCheckBox, QSlider, QDoubleSpinBox, QSpinBox,
    QGroupBox, QScrollArea, QWidget, QComboBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Importar configuración de algoritmos
from src.vision.algorithms.algorithms_config import (
    ALGORITHMS_CONFIG, PRESETS, EXECUTION_ORDER,
    apply_preset, get_active_algorithms
)


class AlgorithmWidget(QGroupBox):
    """Widget individual para configurar un algoritmo"""
    
    config_changed = pyqtSignal(str, dict)  # (nombre_algo, {param: valor})
    enabled_changed = pyqtSignal(str, bool)  # (nombre_algo, enabled)
    
    # Descripciones de cada algoritmo
    ALGORITHM_DESCRIPTIONS = {
        'Una Nota Por Dedo': {
            'icon': '☝️',
            'short': 'CRÍTICO: Un dedo = Una tecla',
            'detail': 'Garantiza que cada dedo físico solo pueda activar UNA tecla a la vez. '
                     'Resuelve el problema de dedos que activan múltiples teclas por imprecisión. '
                     'SIEMPRE debe estar habilitado para una detección correcta.'
        },
        'Antirebote': {
            'icon': '🔄',
            'short': 'Previene activaciones múltiples rápidas',
            'detail': 'Evita que una misma tecla se active varias veces cuando el dedo '
                     'está en el límite de detección. Útil para evitar notas "fantasma" '
                     'o repeticiones no deseadas.'
        },
        'Histéresis': {
            'icon': '📊',
            'short': 'Umbrales diferentes para presionar/soltar',
            'detail': 'Usa un umbral más bajo para activar la tecla y uno más alto para '
                     'soltarla. Esto crea una "zona muerta" que evita el titubeo cuando '
                     'el dedo está cerca del punto de activación.'
        },
        'Suavizado': {
            'icon': '〰️',
            'short': 'Promedia mediciones para estabilizar',
            'detail': 'Calcula el promedio de las últimas N mediciones de profundidad. '
                     'Reduce el ruido y las variaciones bruscas, haciendo la detección '
                     'más suave pero ligeramente más lenta.'
        },
        'Multi-nota': {
            'icon': '🎹',
            'short': 'Detecta acordes (teclas simultáneas)',
            'detail': 'Agrupa teclas presionadas dentro de una ventana de tiempo como '
                     'un acorde. Permite tocar múltiples notas a la vez de forma más '
                     'natural, sin que se interpreten como notas separadas.'
        },
        'Filtro Espacial': {
            'icon': '📍',
            'short': 'Evita activaciones de teclas adyacentes',
            'detail': 'Previene que dedos muy cercanos activen múltiples teclas por error. '
                     'Útil cuando los dedos están juntos y podrían detectarse en teclas '
                     'vecinas accidentalmente.'
        },
        'Zona Salida': {
            'icon': '🚪',
            'short': 'Maneja la salida del área del teclado',
            'detail': 'Cuando un dedo sale del área del teclado por el borde inferior, '
                     'espera un tiempo de gracia antes de liberar la tecla. Evita cortes '
                     'abruptos cuando el dedo se mueve fuera del teclado.'
        }
    }
    
    def __init__(self, algo_name: str, algo_config: dict, parent=None):
        super().__init__(algo_name, parent)
        self.algo_name = algo_name
        self.algo_config = algo_config
        self.param_widgets = {}
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header con checkbox de activación
        header_layout = QHBoxLayout()
        
        self.enable_check = QCheckBox("Activado")
        self.enable_check.setChecked(self.algo_config.get('enabled', False))
        self.enable_check.stateChanged.connect(self._on_enabled_changed)
        self.enable_check.setStyleSheet("QCheckBox { color: #00FF00; font-weight: bold; }")
        
        header_layout.addWidget(self.enable_check)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Descripción del algoritmo
        desc_info = self.ALGORITHM_DESCRIPTIONS.get(self.algo_name, {})
        if desc_info:
            # Descripción corta con icono
            short_label = QLabel(f"{desc_info.get('icon', '⚙️')} {desc_info.get('short', '')}")
            short_label.setStyleSheet("""
                color: #88CCFF; 
                font-size: 12px; 
                font-weight: bold;
                padding: 2px 0;
            """)
            layout.addWidget(short_label)
            
            # Descripción detallada
            detail_label = QLabel(desc_info.get('detail', ''))
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("""
                color: #888888; 
                font-size: 11px; 
                font-style: italic;
                padding: 4px 8px;
                background-color: #252525;
                border-radius: 4px;
            """)
            layout.addWidget(detail_label)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #555555;")
        layout.addWidget(line)
        
        # Parámetros
        params = self.algo_config.get('params', {})
        for param_name, param_value in params.items():
            param_layout = self._create_param_widget(param_name, param_value)
            layout.addLayout(param_layout)
        
        # Estilo del grupo
        self.setStyleSheet("""
            QGroupBox {
                color: #00C8FF;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #444444;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2b2b2b;
            }
            QLabel {
                color: #cccccc;
                font-size: 12px;
            }
        """)
        
    def _create_param_widget(self, param_name: str, param_value) -> QHBoxLayout:
        """Crea el widget apropiado según el tipo de parámetro"""
        layout = QHBoxLayout()
        
        # Etiqueta del parámetro
        label = QLabel(self._format_param_name(param_name) + ":")
        label.setMinimumWidth(180)
        layout.addWidget(label)
        
        # Determinar tipo de widget según el valor
        if isinstance(param_value, float):
            widget = QDoubleSpinBox()
            widget.setDecimals(3)
            
            # Rangos específicos según el parámetro
            ranges = self._get_param_range(param_name)
            widget.setRange(ranges[0], ranges[1])
            widget.setSingleStep(ranges[2])
            widget.setValue(param_value)
            widget.valueChanged.connect(lambda v: self._on_param_changed(param_name, v))
            
        elif isinstance(param_value, int):
            widget = QSpinBox()
            ranges = self._get_param_range(param_name)
            widget.setRange(int(ranges[0]), int(ranges[1]))
            widget.setValue(param_value)
            widget.valueChanged.connect(lambda v: self._on_param_changed(param_name, v))
        elif isinstance(param_value, str):
            # Para parámetros string, usar ComboBox si hay opciones conocidas
            widget = QComboBox()
            options = self._get_string_options(param_name)
            widget.addItems(options)
            if param_value in options:
                widget.setCurrentText(param_value)
            widget.currentTextChanged.connect(lambda v: self._on_param_changed(param_name, v))
            widget.setStyleSheet("""
                QComboBox {
                    background-color: #3b3b3b;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 4px 8px;
                    min-width: 100px;
                }
            """)
        else:
            # Fallback: mostrar como texto (no editable)
            widget = QLabel(str(param_value))
            widget._is_label = True  # Marcar para ignorar en update_config
        
        widget.setStyleSheet("""
            QSpinBox, QDoubleSpinBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #00C8FF;
            }
        """)
        
        self.param_widgets[param_name] = widget
        layout.addWidget(widget)
        
        # Slider para ajuste visual (solo para valores numéricos)
        if isinstance(param_value, (int, float)):
            slider = QSlider(Qt.Orientation.Horizontal)
            ranges = self._get_param_range(param_name)
            
            if isinstance(param_value, float):
                # Convertir a enteros para el slider (multiplicar por 1000)
                slider.setRange(int(ranges[0] * 1000), int(ranges[1] * 1000))
                slider.setValue(int(param_value * 1000))
                slider.valueChanged.connect(
                    lambda v, w=widget: w.setValue(v / 1000.0)
                )
                widget.valueChanged.connect(
                    lambda v, s=slider: s.setValue(int(v * 1000))
                )
            else:
                slider.setRange(int(ranges[0]), int(ranges[1]))
                slider.setValue(param_value)
                slider.valueChanged.connect(
                    lambda v, w=widget: w.setValue(v)
                )
                widget.valueChanged.connect(
                    lambda v, s=slider: s.setValue(v)
                )
            
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    background: #3b3b3b;
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #00C8FF;
                    width: 16px;
                    margin: -5px 0;
                    border-radius: 8px;
                }
                QSlider::sub-page:horizontal {
                    background: #00C8FF;
                    border-radius: 3px;
                }
            """)
            slider.setMinimumWidth(150)
            layout.addWidget(slider)
        
        layout.addStretch()
        return layout
    
    def _format_param_name(self, name: str) -> str:
        """Formatea el nombre del parámetro para mostrar"""
        formatted = name.replace('_', ' ').title()
        
        # Añadir unidades si es conocido
        units = {
            'debounce_time': '(segundos)',
            'press_threshold': '(cm)',
            'release_threshold': '(cm)',
            'smoothing_window': '(frames)',
            'simultaneous_window': '(segundos)',
            'min_finger_distance': '(píxeles)',
            'adjacent_keys_threshold': '(teclas)',
            'exit_zone_margin': '(píxeles)',
            'exit_grace_time': '(segundos)'
        }
        
        if name in units:
            formatted += f" {units[name]}"
        
        return formatted
    
    def _get_param_range(self, param_name: str) -> tuple:
        """Retorna (min, max, step) para cada parámetro"""
        ranges = {
            'debounce_time': (0.01, 0.20, 0.01),
            'press_threshold': (1.0, 6.0, 0.1),
            'release_threshold': (2.0, 8.0, 0.1),
            'smoothing_window': (3, 15, 1),
            'simultaneous_window': (0.02, 0.15, 0.01),
            'min_finger_distance': (15, 60, 1),
            'adjacent_keys_threshold': (1, 5, 1),
            'exit_zone_margin': (10, 80, 5),
            'exit_grace_time': (0.1, 1.0, 0.05),
            # Parámetros de "Una Nota Por Dedo"
            'min_depth_advantage': (0.1, 1.0, 0.1),
            'sticky_time': (0.05, 0.3, 0.05),
        }
        return ranges.get(param_name, (0, 100, 1))
    
    def _get_string_options(self, param_name: str) -> list:
        """Retorna opciones para parámetros de tipo string"""
        options = {
            'selection_mode': ['depth', 'center'],
        }
        return options.get(param_name, [str(param_name)])
    
    def _on_enabled_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.enabled_changed.emit(self.algo_name, enabled)
        
    def _on_param_changed(self, param_name: str, value):
        self.config_changed.emit(self.algo_name, {param_name: value})
        
    def update_config(self, config: dict):
        """Actualiza la UI con nueva configuración"""
        self.enable_check.blockSignals(True)
        self.enable_check.setChecked(config.get('enabled', False))
        self.enable_check.blockSignals(False)
        
        for param_name, value in config.get('params', {}).items():
            if param_name in self.param_widgets:
                widget = self.param_widgets[param_name]
                widget.blockSignals(True)
                
                # Manejar diferentes tipos de widgets
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.setValue(value)
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QLabel):
                    widget.setText(str(value))
                # Ignorar otros tipos
                
                widget.blockSignals(False)


class AdvancedConfigDialog(QDialog):
    """
    Diálogo de configuración avanzada para algoritmos de detección.
    Los cambios se aplican en tiempo real.
    """
    
    config_updated = pyqtSignal(dict)  # Emite toda la configuración actualizada
    
    def __init__(self, parent=None, on_config_change: Callable = None):
        super().__init__(parent)
        self.on_config_change = on_config_change
        self.algorithm_widgets = {}
        
        self.setWindowTitle("Configuración Avanzada - Algoritmos")
        self.setMinimumSize(700, 600)
        self.setModal(False)  # No modal para permitir cambios en tiempo real
        
        self._setup_style()
        self._setup_ui()
        
    def _setup_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #00C8FF;
                color: #000000;
                border: none;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #33D6FF;
            }
            QPushButton:pressed {
                background-color: #0099CC;
            }
            QPushButton#secondary {
                background-color: #444444;
                color: #ffffff;
            }
            QPushButton#secondary:hover {
                background-color: #555555;
            }
            QComboBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #00C8FF;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #3b3b3b;
                color: #ffffff;
                selection-background-color: #00C8FF;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2b2b2b;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00C8FF;
            }
        """)
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === HEADER ===
        header = QLabel("⚙️ CONFIGURACIÓN DE ALGORITMOS")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #00C8FF; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Descripción
        desc = QLabel("Ajusta los parámetros de detección en tiempo real.\n"
                     "Los cambios se aplican inmediatamente.")
        desc.setStyleSheet("color: #888888; font-size: 12px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(desc)
        
        # === PRESETS ===
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset rápido:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Seleccionar Preset --", None)
        self.preset_combo.addItem("🎯 Default (Equilibrado)", "default")
        self.preset_combo.addItem("⚡ Sensible (Respuesta rápida)", "sensitive")
        self.preset_combo.addItem("🛡️ Estable (Menos errores)", "stable")
        self.preset_combo.addItem("📦 Mínimo (Solo esenciales)", "minimal")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)
        
        preset_layout.addStretch()
        
        # Botón de reset
        reset_btn = QPushButton("🔄 Reset")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self._reset_to_default)
        preset_layout.addWidget(reset_btn)
        
        main_layout.addLayout(preset_layout)
        
        # === ÁREA DE SCROLL PARA ALGORITMOS ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.algorithms_layout = QVBoxLayout(scroll_content)
        self.algorithms_layout.setSpacing(15)
        
        # Crear widgets para cada algoritmo en orden de ejecución
        for algo_name in EXECUTION_ORDER:
            if algo_name in ALGORITHMS_CONFIG:
                widget = AlgorithmWidget(algo_name, ALGORITHMS_CONFIG[algo_name])
                widget.config_changed.connect(self._on_algo_config_changed)
                widget.enabled_changed.connect(self._on_algo_enabled_changed)
                self.algorithm_widgets[algo_name] = widget
                self.algorithms_layout.addWidget(widget)
        
        self.algorithms_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # === FOOTER ===
        footer_layout = QHBoxLayout()
        
        # Info de algoritmos activos
        self.active_label = QLabel()
        self._update_active_count()
        footer_layout.addWidget(self.active_label)
        
        footer_layout.addStretch()
        
        # Botón cerrar
        close_btn = QPushButton("✓ Cerrar")
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        main_layout.addLayout(footer_layout)
        
    def _on_preset_selected(self, index):
        preset_name = self.preset_combo.currentData()
        if preset_name:
            apply_preset(preset_name)
            self._refresh_all_widgets()
            self._notify_config_change()
            
            # Reset combo a selección vacía
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)
    
    def _on_algo_config_changed(self, algo_name: str, params: dict):
        """Cuando cambia un parámetro de algoritmo"""
        if algo_name in ALGORITHMS_CONFIG:
            ALGORITHMS_CONFIG[algo_name]['params'].update(params)
            self._notify_config_change()
            
    def _on_algo_enabled_changed(self, algo_name: str, enabled: bool):
        """Cuando se activa/desactiva un algoritmo"""
        if algo_name in ALGORITHMS_CONFIG:
            ALGORITHMS_CONFIG[algo_name]['enabled'] = enabled
            self._update_active_count()
            self._notify_config_change()
            
    def _notify_config_change(self):
        """Notifica cambios de configuración"""
        self.config_updated.emit(ALGORITHMS_CONFIG.copy())
        
        if self.on_config_change:
            self.on_config_change(ALGORITHMS_CONFIG)
            
    def _refresh_all_widgets(self):
        """Refresca todos los widgets con la configuración actual"""
        for algo_name, widget in self.algorithm_widgets.items():
            if algo_name in ALGORITHMS_CONFIG:
                widget.update_config(ALGORITHMS_CONFIG[algo_name])
        self._update_active_count()
        
    def _update_active_count(self):
        active = len(get_active_algorithms())
        total = len(ALGORITHMS_CONFIG)
        self.active_label.setText(f"Algoritmos activos: {active}/{total}")
        self.active_label.setStyleSheet(
            f"color: {'#00FF00' if active > 0 else '#FF6666'}; font-weight: bold;"
        )
        
    def _reset_to_default(self):
        """Resetea a configuración por defecto"""
        apply_preset('default')
        self._refresh_all_widgets()
        self._notify_config_change()


# === SINGLETON PARA ACCESO GLOBAL ===
_advanced_config_dialog: Optional[AdvancedConfigDialog] = None


def get_advanced_config_dialog(on_config_change: Callable = None) -> AdvancedConfigDialog:
    """
    Obtiene o crea el diálogo de configuración avanzada (singleton).
    
    Args:
        on_config_change: Callback llamado cuando cambia la configuración
        
    Returns:
        Instancia del diálogo
    """
    global _advanced_config_dialog
    
    if _advanced_config_dialog is None or not _advanced_config_dialog.isVisible():
        _advanced_config_dialog = AdvancedConfigDialog(on_config_change=on_config_change)
    
    return _advanced_config_dialog


def show_advanced_config(on_config_change: Callable = None) -> None:
    """
    Muestra el diálogo de configuración avanzada (bloqueante).
    
    Args:
        on_config_change: Callback llamado cuando cambia la configuración
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Crear nuevo diálogo cada vez (modal)
    dialog = AdvancedConfigDialog(on_config_change=on_config_change)
    dialog.setModal(True)
    dialog.exec()  # Bloqueante: espera hasta que se cierre


if __name__ == '__main__':
    # Test independiente
    def on_change(config):
        print(f"\n[CONFIG CHANGE] Algoritmos activos: {get_active_algorithms()}")
        for name, cfg in config.items():
            if cfg['enabled']:
                print(f"  ✓ {name}: {cfg['params']}")
    
    app = QApplication(sys.argv)
    dialog = AdvancedConfigDialog(on_config_change=on_change)
    dialog.show()
    sys.exit(app.exec())


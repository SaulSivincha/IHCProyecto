#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diálogo de configuración de cámaras.
Permite seleccionar qué cámara será izquierda y cuál derecha.
Simple y rápido - sin filtros ni modificaciones de cámara.
"""

import sys
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QLinearGradient, QPainter, QColor
from src.config.theme import Theme


class CameraConfigDialog(QDialog):
    """Diálogo para configurar las cámaras izquierda y derecha."""
    
    # Lista fija de cámaras disponibles (sin detección)
    CAMERA_LIST = [0, 1, 2, 3, 4, 5]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuracion de Camaras")
        self.setMinimumSize(750, 550)
        self.setModal(True)
        
        # Cargar configuración actual
        self._load_current_config()
        
        self._setup_style()
        self._setup_ui()
        
        # Tomar fotos iniciales
        self._take_left_photo()
        self._take_right_photo()
    
    def paintEvent(self, event):
        """Dibuja el fondo con gradiente del tema"""
        painter = QPainter(self)
        
        grad_start = QColor(Theme.to_hex(Theme.BG_GRADIENT_START))
        grad_end = QColor(Theme.to_hex(Theme.BG_GRADIENT_END))
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, grad_start)
        gradient.setColorAt(1, grad_end)
        painter.fillRect(self.rect(), gradient)
        
    def _load_current_config(self):
        """Carga la configuración actual de cámaras desde calibration.json."""
        calib_path = Path("camcalibration/calibration.json")
        
        self.left_camera_id = 1
        self.right_camera_id = 2
        
        try:
            if calib_path.exists():
                with open(calib_path, 'r') as f:
                    data = json.load(f)
                
                if 'camera_ids' in data:
                    self.left_camera_id = data['camera_ids'].get('left', 1)
                    self.right_camera_id = data['camera_ids'].get('right', 2)
        except:
            pass
    
    def _setup_style(self):
        """Configura el estilo del diálogo."""
        self.setStyleSheet(f"""
            QLabel {{
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                font-size: 14px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QLabel#title {{
                color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
                font-size: 24px;
                font-weight: bold;
            }}
            QLabel#subtitle {{
                color: {Theme.to_hex(Theme.TEXT_SECONDARY)};
                font-size: 14px;
            }}
            QLabel#preview {{
                background-color: rgba(0, 0, 0, 0.1);
                border: 3px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 10px;
            }}
            QGroupBox {{
                color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                font-weight: bold;
                font-size: 16px;
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 0.6);
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
            }}
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.9);
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                border: 1px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 14px;
                min-width: 100px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QComboBox:hover {{
                border-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: rgba(255, 255, 255, 0.95);
                color: {Theme.to_hex(Theme.TEXT_PRIMARY)};
                selection-background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                font-size: 14px;
                font-weight: bold;
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 15px;
                padding: 10px 24px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QPushButton:pressed {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                border-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
            QPushButton#cancelButton {{
                background-color: {Theme.to_hex(Theme.BTN_DANGER_BG)};
                color: {Theme.to_hex(Theme.BTN_DANGER_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
            }}
            QPushButton#cancelButton:hover {{
                background-color: {Theme.to_hex(Theme.RED_VIVID)};
            }}
            QPushButton#cancelButton:pressed {{
                background-color: #8B0000;
            }}
            QPushButton#swapButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                padding: 8px 16px;
                border-radius: 18px;
            }}
            QPushButton#swapButton:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QPushButton#swapButton:pressed {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                border-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
            QPushButton#photoButton {{
                background-color: {Theme.to_hex(Theme.BTN_SUCCESS_BG)};
                color: {Theme.to_hex(Theme.BTN_SUCCESS_TEXT)};
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 15px;
            }}
            QPushButton#photoButton:hover {{
                background-color: {Theme.to_hex(Theme.GREEN_VIVID)};
            }}
            QPushButton#photoButton:pressed {{
                background-color: #2E7D32;
            }}
        """)
    
    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Título
        title = QLabel("Configuracion de Camaras")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"background: transparent;")
        layout.addWidget(title)
        
        subtitle = QLabel("Selecciona que camara sera la izquierda y cual la derecha")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"background: transparent;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(8)
        
        # Contenedor de cámaras
        cameras_layout = QHBoxLayout()
        cameras_layout.setSpacing(16)
        
        # === Cámara Izquierda ===
        left_group = QGroupBox("CAMARA IZQUIERDA")
        left_layout = QVBoxLayout(left_group)
        left_layout.setSpacing(10)
        
        self.left_preview = QLabel()
        self.left_preview.setObjectName("preview")
        self.left_preview.setFixedSize(280, 210)
        self.left_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_preview.setText("Presiona 'Foto'")
        left_layout.addWidget(self.left_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        
        left_controls = QHBoxLayout()
        label_l = QLabel("Camara:")
        label_l.setStyleSheet("background: transparent;")
        left_controls.addWidget(label_l)
        
        self.left_combo = QComboBox()
        self._populate_combo(self.left_combo, self.left_camera_id)
        self.left_combo.currentIndexChanged.connect(self._on_left_changed)
        left_controls.addWidget(self.left_combo)
        
        self.left_photo_btn = QPushButton("Foto")
        self.left_photo_btn.setObjectName("photoButton")
        self.left_photo_btn.clicked.connect(self._take_left_photo)
        left_controls.addWidget(self.left_photo_btn)
        
        left_layout.addLayout(left_controls)
        cameras_layout.addWidget(left_group)
        
        # === Botón Intercambiar ===
        swap_layout = QVBoxLayout()
        swap_layout.addStretch()
        self.swap_btn = QPushButton("<->")
        self.swap_btn.setObjectName("swapButton")
        self.swap_btn.setFixedSize(60, 40)
        self.swap_btn.setToolTip("Intercambiar camaras")
        self.swap_btn.clicked.connect(self._swap_cameras)
        swap_layout.addWidget(self.swap_btn)
        swap_layout.addStretch()
        cameras_layout.addLayout(swap_layout)
        
        # === Cámara Derecha ===
        right_group = QGroupBox("CAMARA DERECHA")
        right_layout = QVBoxLayout(right_group)
        right_layout.setSpacing(10)
        
        self.right_preview = QLabel()
        self.right_preview.setObjectName("preview")
        self.right_preview.setFixedSize(280, 210)
        self.right_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_preview.setText("Presiona 'Foto'")
        right_layout.addWidget(self.right_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        
        right_controls = QHBoxLayout()
        label_r = QLabel("Camara:")
        label_r.setStyleSheet("background: transparent;")
        right_controls.addWidget(label_r)
        
        self.right_combo = QComboBox()
        self._populate_combo(self.right_combo, self.right_camera_id)
        self.right_combo.currentIndexChanged.connect(self._on_right_changed)
        right_controls.addWidget(self.right_combo)
        
        self.right_photo_btn = QPushButton("Foto")
        self.right_photo_btn.setObjectName("photoButton")
        self.right_photo_btn.clicked.connect(self._take_right_photo)
        right_controls.addWidget(self.right_photo_btn)
        
        right_layout.addLayout(right_controls)
        cameras_layout.addWidget(right_group)
        
        layout.addLayout(cameras_layout)
        
        # Información
        info_label = QLabel(
            "Presiona 'Foto' para ver la imagen. Despues de cambiar, recalibra el sistema."
        )
        info_label.setObjectName("subtitle")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background: transparent;")
        layout.addWidget(info_label)
        
        layout.addSpacing(8)
        
        # Botones
        # Botones
        buttons_layout = QHBoxLayout()
        # Spacer izquierdo para centrar
        buttons_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self.reject)
        # Estilo directo para asegurar que se aplique, ya que el stylesheet global puede tener problemas
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_DANGER_BG)};
                color: {Theme.to_hex(Theme.BTN_DANGER_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                padding: 10px 20px;
                border-radius: 15px;
                font-family: 'Comic Sans MS', 'Arial';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.RED_VIVID)};
            }}
            QPushButton:pressed {{
                background-color: #8B0000;
            }}
        """)
        buttons_layout.addWidget(self.cancel_btn)
        
        buttons_layout.addSpacing(20)
        
        self.save_btn = QPushButton("Guardar Configuracion")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.clicked.connect(self._save_and_close)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                padding: 10px 20px;
                border-radius: 15px;
                font-family: 'Comic Sans MS', 'Arial';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QPushButton:pressed {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                border-color: {Theme.to_hex(Theme.BLUE_VIVID)};
            }}
        """)
        buttons_layout.addWidget(self.save_btn)
        
        # Spacer derecho para centrar
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def _populate_combo(self, combo: QComboBox, selected_id: Optional[int]):
        """Llena un combo con TODAS las cámaras (0-5) sin filtrar."""
        combo.blockSignals(True)
        combo.clear()
        
        for cam_id in self.CAMERA_LIST:
            combo.addItem(f"Camara {cam_id}", cam_id)
        
        if selected_id is not None:
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        
        combo.blockSignals(False)
    
    def _take_photo_fast(self, cam_id: int) -> Optional[np.ndarray]:
        """Toma una foto de la cámara sin modificar configuración."""
        try:
            cap = cv2.VideoCapture(cam_id)
            if not cap.isOpened():
                return None
            
            # Leer varios frames para que la cámara se estabilice
            frame = None
            for _ in range(15):
                ret, frame = cap.read()
            
            cap.release()
            
            if ret and frame is not None and frame.size > 0:
                # IMPORTANTE: Aplicar las mismas transformaciones que en runtime
                # para que la vista previa coincida con lo que verá durante el uso
                from src.vision.stereo_config import StereoConfig
                frame = StereoConfig.apply_camera_transforms(frame)
                return frame
            return None
        except:
            return None
    
    def _display_frame(self, frame, label: QLabel):
        """Muestra un frame en un QLabel."""
        if frame is None:
            label.setText("Camara no disponible")
            return
        
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            
            q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            
            scaled = q_img.scaled(
                label.width() - 4, label.height() - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            label.setPixmap(QPixmap.fromImage(scaled))
        except:
            label.setText("Error mostrando imagen")
    
    def _take_left_photo(self):
        """Toma foto de la cámara izquierda."""
        cam_id = self.left_combo.currentData()
        frame = self._take_photo_fast(cam_id)
        self._display_frame(frame, self.left_preview)
    
    def _take_right_photo(self):
        """Toma foto de la cámara derecha."""
        cam_id = self.right_combo.currentData()
        frame = self._take_photo_fast(cam_id)
        self._display_frame(frame, self.right_preview)
    
    def _on_left_changed(self, index):
        """Cuando cambia la cámara izquierda."""
        self._check_conflict()
    
    def _on_right_changed(self, index):
        """Cuando cambia la cámara derecha."""
        self._check_conflict()
    
    def _check_conflict(self):
        """Verifica si hay conflicto (misma cámara)."""
        left_id = self.left_combo.currentData()
        right_id = self.right_combo.currentData()
        
        if left_id == right_id:
            self.save_btn.setEnabled(False)
            self.save_btn.setToolTip("No puedes usar la misma camara")
        else:
            self.save_btn.setEnabled(True)
            self.save_btn.setToolTip("")
    
    def _swap_cameras(self):
        """Intercambia las cámaras izquierda y derecha."""
        left_idx = self.left_combo.currentIndex()
        right_idx = self.right_combo.currentIndex()
        
        self.left_combo.blockSignals(True)
        self.right_combo.blockSignals(True)
        
        self.left_combo.setCurrentIndex(right_idx)
        self.right_combo.setCurrentIndex(left_idx)
        
        self.left_combo.blockSignals(False)
        self.right_combo.blockSignals(False)
        
        # Intercambiar fotos también
        left_pixmap = self.left_preview.pixmap()
        right_pixmap = self.right_preview.pixmap()
        
        if left_pixmap and right_pixmap:
            self.left_preview.setPixmap(right_pixmap)
            self.right_preview.setPixmap(left_pixmap)
    
    def _save_and_close(self):
        """Guarda la configuración y cierra el diálogo."""
        left_id = self.left_combo.currentData()
        right_id = self.right_combo.currentData()
        
        if left_id == right_id:
            QMessageBox.warning(
                self, "Error",
                "No puedes usar la misma camara para izquierda y derecha."
            )
            return
        
        self._save_to_calibration_file(left_id, right_id)
        
        QMessageBox.information(
            self, "Guardado",
            f"Camaras configuradas:\n"
            f"  Izquierda: Camara {left_id}\n"
            f"  Derecha: Camara {right_id}"
        )
        
        self.accept()
    
    def _save_to_calibration_file(self, left_id: int, right_id: int):
        """Guarda la configuración de cámaras en calibration.json."""
        calib_path = Path("camcalibration/calibration.json")
        
        try:
            if calib_path.exists():
                with open(calib_path, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            data['camera_ids'] = {
                'left': left_id,
                'right': right_id
            }
            
            calib_path.parent.mkdir(parents=True, exist_ok=True)
            with open(calib_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"[CameraConfig] Guardado: LEFT={left_id}, RIGHT={right_id}")
        except Exception as e:
            print(f"[CameraConfig] Error: {e}")


def show_camera_config() -> bool:
    """Muestra el diálogo de configuración de cámaras."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        dialog = CameraConfigDialog()
        result = dialog.exec()
        
        return result == QDialog.DialogCode.Accepted
    except Exception as e:
        import traceback
        from PyQt6.QtWidgets import QMessageBox
        error_msg = traceback.format_exc()
        print(f"ERROR lanzando CameraConfig: {e}")
        print(error_msg)
        
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error")
            msg.setText("Error al abrir Configuración de Cámaras")
            msg.setDetailedText(error_msg)
            msg.exec()
        except:
            pass
        return False


if __name__ == "__main__":
    result = show_camera_config()
    print(f"Resultado: {'Guardado' if result else 'Cancelado'}")

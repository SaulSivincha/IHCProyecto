import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSpacerItem, QSizePolicy, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter
from src.config.theme import Theme

class CalibrationSummaryDialog(QDialog):
    # Return codes
    ACTION_START = 1
    ACTION_RECALIBRATE_STEREO = 2
    ACTION_RECALIBRATE_DEPTH = 4  # Nuevo código para Fase 3
    ACTION_RECALIBRATE_ALL = 3
    ACTION_EXIT = 0

    def __init__(self, summary_data):
        super().__init__()
        self.summary = summary_data
        self.result_action = self.ACTION_EXIT
        
        self.setWindowTitle("Resumen de Calibración")
        self.setMinimumSize(900, 700)
        
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
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(15)
        
        # Colors from theme
        text_color = Theme.to_hex(Theme.TEXT_PRIMARY)
        highlight_color = Theme.to_hex(Theme.TEXT_HIGHLIGHT)
        success_color = Theme.to_hex(Theme.SUCCESS)
        warning_color = Theme.to_hex(Theme.WARNING)
        muted_color = Theme.to_hex(Theme.TEXT_SECONDARY)
        
        # Header
        header_layout = QVBoxLayout()
        title = QLabel("CALIBRACIÓN COMPLETA")
        title.setStyleSheet(f"""
            color: {highlight_color};
            font-size: 28px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel(f"Fecha: {self.summary.get('fecha', 'N/A')}   |   Versión: {self.summary.get('version', '2.0')}")
        subtitle.setStyleSheet(f"""
            color: {muted_color};
            font-size: 14px;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)
        
        self._add_separator(main_layout)
        
        # Phase 1 Section
        lbl_p1 = QLabel("FASE 1: CALIBRACIÓN INDIVIDUAL")
        lbl_p1.setStyleSheet(f"""
            color: {highlight_color};
            font-size: 20px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            margin-top: 10px;
            background: transparent;
        """)
        main_layout.addWidget(lbl_p1)
        
        p1_layout = QVBoxLayout()
        p1_layout.setSpacing(5)
        
        # Left Camera
        row_left = QHBoxLayout()
        lbl_left = QLabel("Cámara IZQUIERDA:")
        lbl_left.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_left.addWidget(lbl_left)
        err_left = self.summary.get('error_left', 'N/A')
        val_left = f"{err_left:.6f} px" if isinstance(err_left, float) else str(err_left)
        lbl_val_left = QLabel(val_left)
        lbl_val_left.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_left.addWidget(lbl_val_left)
        row_left.addStretch()
        p1_layout.addLayout(row_left)
        
        # Right Camera
        row_right = QHBoxLayout()
        lbl_right = QLabel("Cámara DERECHA:")
        lbl_right.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_right.addWidget(lbl_right)
        err_right = self.summary.get('error_right', 'N/A')
        val_right = f"{err_right:.6f} px" if isinstance(err_right, float) else str(err_right)
        lbl_val_right = QLabel(val_right)
        lbl_val_right.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_right.addWidget(lbl_val_right)
        row_right.addStretch()
        p1_layout.addLayout(row_right)
        
        main_layout.addLayout(p1_layout)
        
        self._add_separator(main_layout)
        
        # Phase 2 Section
        lbl_p2 = QLabel("FASE 2: CALIBRACIÓN ESTÉREO")
        lbl_p2.setStyleSheet(f"""
            color: {highlight_color};
            font-size: 20px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            margin-top: 10px;
            background: transparent;
        """)
        main_layout.addWidget(lbl_p2)
        
        p2_layout = QVBoxLayout()
        
        # Baseline
        row_base = QHBoxLayout()
        lbl_base_title = QLabel("Baseline (distancia):")
        lbl_base_title.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_base.addWidget(lbl_base_title)
        base_val = self.summary.get('baseline_cm', 'N/A')
        val_base = f"{base_val:.2f} cm" if isinstance(base_val, float) else str(base_val)
        lbl_base = QLabel(val_base)
        lbl_base.setStyleSheet(f"color: {highlight_color}; font-weight: bold; font-size: 18px; background: transparent;")
        row_base.addWidget(lbl_base)
        row_base.addStretch()
        p2_layout.addLayout(row_base)
        
        # RMS Error
        row_rms = QHBoxLayout()
        lbl_rms_title = QLabel("Error RMS:")
        lbl_rms_title.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_rms.addWidget(lbl_rms_title)
        rms_val = self.summary.get('error_stereo', 'N/A')
        val_rms = f"{rms_val:.4f}" if isinstance(rms_val, float) else str(rms_val)
        lbl_rms = QLabel(val_rms)
        lbl_rms.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_rms.addWidget(lbl_rms)
        
        # Quality indicator
        if isinstance(rms_val, float):
            quality = "EXCELENTE" if rms_val < 0.3 else "BUENA" if rms_val < 0.5 else "REGULAR" if rms_val < 1.0 else "MALA"
            color = success_color if rms_val < 0.5 else warning_color if rms_val < 1.0 else Theme.to_hex(Theme.ERROR)
            lbl_qual = QLabel(quality)
            lbl_qual.setStyleSheet(f"color: {color}; font-weight: bold; margin-left: 20px; background: transparent;")
            row_rms.addWidget(lbl_qual)
            
        row_rms.addStretch()
        p2_layout.addLayout(row_rms)
        
        main_layout.addLayout(p2_layout)
        
        self._add_separator(main_layout)
        
        # Phase 3 Section (NEW)
        lbl_p3 = QLabel("FASE 3: PROFUNDIDAD")
        lbl_p3.setStyleSheet(f"""
            color: {success_color};
            font-size: 20px;
            font-weight: bold;
            font-family: 'Comic Sans MS', 'Arial';
            margin-top: 10px;
            background: transparent;
        """)
        main_layout.addWidget(lbl_p3)
        
        p3_layout = QVBoxLayout()
        
        # Distancia del teclado calibrada
        row_distance = QHBoxLayout()
        lbl_dist_title = QLabel("Distancia del Teclado:")
        lbl_dist_title.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
        row_distance.addWidget(lbl_dist_title)
        
        keyboard_dist = self.summary.get('keyboard_distance_cm', 'N/A')
        keyboard_samples = self.summary.get('keyboard_samples', 'N/A')
             
        if isinstance(keyboard_dist, (int, float)):
            val_dist = f"{keyboard_dist:.2f} cm"
            lbl_dist = QLabel(val_dist)
            lbl_dist.setStyleSheet(f"color: {success_color}; font-weight: bold; font-size: 16px; background: transparent;")
        else:
            lbl_dist = QLabel("N/A")
            lbl_dist.setStyleSheet(f"color: {warning_color}; font-weight: bold; font-size: 16px; background: transparent;")
        
        row_distance.addWidget(lbl_dist)
        
        # Muestras usadas
        if isinstance(keyboard_samples, int) and keyboard_samples > 0:
            lbl_samples = QLabel(f"({keyboard_samples} muestras)")
            lbl_samples.setStyleSheet(f"color: {muted_color}; font-size: 14px; background: transparent;")
            row_distance.addWidget(lbl_samples)
        
        row_distance.addStretch()
        p3_layout.addLayout(row_distance)
        
        # Factor de corrección (si existe)
        correction_factor = self.summary.get('correction_factor', None)
        if correction_factor is not None and correction_factor != 1.0:
            row_factor = QHBoxLayout()
            lbl_factor_title = QLabel("Factor de Correccion:")
            lbl_factor_title.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
            row_factor.addWidget(lbl_factor_title)
            lbl_factor = QLabel(f"{correction_factor:.4f}")
            lbl_factor.setStyleSheet(f"color: {highlight_color}; font-weight: bold; font-size: 16px; background: transparent;")
            row_factor.addWidget(lbl_factor)
            row_factor.addStretch()
            p3_layout.addLayout(row_factor)
        
        # Error de medición (si existe distancia real)
        real_dist = self.summary.get('real_distance_cm', None)
        measured_dist = self.summary.get('measured_distance_cm', None)
        error_percent = self.summary.get('depth_error_percent', None)
        
        if real_dist is not None and measured_dist is not None:
            row_comparison = QHBoxLayout()
            lbl_meas = QLabel("Medicion del Sistema:")
            lbl_meas.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
            row_comparison.addWidget(lbl_meas)
            lbl_measured = QLabel(f"{measured_dist:.2f} cm")
            lbl_measured.setStyleSheet(f"color: {muted_color}; font-size: 14px; background: transparent;")
            row_comparison.addWidget(lbl_measured)
            
            lbl_vs = QLabel("  vs  Distancia Real:")
            lbl_vs.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
            row_comparison.addWidget(lbl_vs)
            lbl_real = QLabel(f"{real_dist:.2f} cm")
            lbl_real.setStyleSheet(f"color: {highlight_color}; font-size: 14px; background: transparent;")
            row_comparison.addWidget(lbl_real)
            row_comparison.addStretch()
            p3_layout.addLayout(row_comparison)
            
            if error_percent is not None:
                row_error = QHBoxLayout()
                lbl_err_title = QLabel("Error de Medicion:")
                lbl_err_title.setStyleSheet(f"color: {text_color}; font-size: 14px; background: transparent;")
                row_error.addWidget(lbl_err_title)
                
                # Color según el error
                if error_percent < 5:
                    error_color = success_color  # Verde - excelente
                    quality = "EXCELENTE"
                elif error_percent < 10:
                    error_color = warning_color  # Amarillo - bueno
                    quality = "BUENO"
                elif error_percent < 20:
                    error_color = Theme.to_hex(Theme.ORANGE_VIVID)  # Naranja - regular
                    quality = "REGULAR"
                else:
                    error_color = Theme.to_hex(Theme.ERROR)  # Rojo - malo
                    quality = "ALTO"
                
                lbl_error = QLabel(f"{error_percent:.1f}%")
                lbl_error.setStyleSheet(f"color: {error_color}; font-weight: bold; font-size: 16px; background: transparent;")
                row_error.addWidget(lbl_error)
                
                lbl_quality = QLabel(f"({quality})")
                lbl_quality.setStyleSheet(f"color: {error_color}; font-size: 14px; margin-left: 10px; background: transparent;")
                row_error.addWidget(lbl_quality)
                
                row_error.addStretch()
                p3_layout.addLayout(row_error)
        
        main_layout.addLayout(p3_layout)
        
        self._add_separator(main_layout)
        
        # Warning Box
        warn_frame = QFrame()
        warn_frame.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {highlight_color};
                border-radius: 10px;
                background-color: rgba(255,255,255,0.9);
                padding: 10px;
            }}
        """)
        warn_layout = QVBoxLayout(warn_frame)
        
        lbl_warn_title = QLabel("ESTA CALIBRACIÓN ES VÁLIDA PARA:")
        lbl_warn_title.setStyleSheet(f"color: {highlight_color}; font-weight: bold; background: transparent;")
        lbl_warn_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_warn1 = QLabel("- La misma ubicación física de las cámaras")
        lbl_warn1.setStyleSheet(f"color: {text_color}; background: transparent;")
        lbl_warn1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_warn2 = QLabel("- Si moviste las cámaras, RE-CALIBRA")
        lbl_warn2.setStyleSheet(f"color: {Theme.to_hex(Theme.ORANGE_VIVID)}; font-weight: bold; background: transparent;")
        lbl_warn2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        warn_layout.addWidget(lbl_warn_title)
        warn_layout.addWidget(lbl_warn1)
        warn_layout.addWidget(lbl_warn2)
        
        main_layout.addWidget(warn_frame)
        
        main_layout.addStretch()
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        btn_recalibrate = QPushButton("RE-CALIBRAR")
        btn_recalibrate.setStyleSheet(f"""
            QPushButton {{
                background-color: {highlight_color};
                color: #FFFFFF;
                border: 3px solid #FFFFFF;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 20px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.SELECTION_BG)};
            }}
        """)
        btn_recalibrate.clicked.connect(lambda: self._finish(self.ACTION_RECALIBRATE_ALL))
        btn_layout.addWidget(btn_recalibrate)
        
        btn_exit = QPushButton("VOLVER")
        btn_exit.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.3);
                color: {text_color};
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 20px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton:hover {{
                background-color: rgba(255,255,255,0.5);
            }}
        """)
        btn_exit.clicked.connect(lambda: self._finish(self.ACTION_EXIT))
        btn_layout.addWidget(btn_exit)
        
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)

    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"background-color: {Theme.to_hex(Theme.BORDER_DEFAULT)}; max-height: 2px;")
        layout.addWidget(line)

    def _finish(self, action):
        self.result_action = action
        self.accept()

def show_calibration_summary(summary_data):
    """
    Muestra el diálogo de resumen y retorna la acción seleccionada
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    dialog = CalibrationSummaryDialog(summary_data)
    dialog.exec()
    
    return dialog.result_action

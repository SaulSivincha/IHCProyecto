"""
Calibration Summary Dialog - Adventure Mode High-Fidelity Design
Implementing professional UI with animations, ripple effects, and modern typography.
"""
import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QWidget, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, QPointF, QSize, pyqtProperty
from PyQt6.QtGui import QColor, QLinearGradient, QRadialGradient, QPainter, QFont, QFontDatabase, QPen
from src.config.theme import Theme

class AnimatedLabel(QLabel):
    """Label that supports numeric counting animation"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._value = 0.0
        self._format = "{:.2f}"
        self._final_value = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_text)
        self._steps = 40
        self._current_step = 0
        self._increment = 0.0

    def animate_to(self, target_value, duration=1000, fmt="{:.2f}"):
        try:
            self._final_value = float(target_value)
        except (ValueError, TypeError):
            self.setText(str(target_value))
            return

        self._format = fmt
        self._value = 0.0
        self._current_step = 0
        self._increment = self._final_value / self._steps
        
        interval = max(16, duration // self._steps)
        self._timer.start(interval)

    def _update_text(self):
        self._current_step += 1
        self._value += self._increment
        
        if self._current_step >= self._steps:
            self._value = self._final_value
            self._timer.stop()
            
        self.setText(self._format.format(self._value))

class RippleButton(QPushButton):
    """Button with ripple effect and hover scaling"""
    def __init__(self, text="", color="#FB8C00", parent=None):
        super().__init__(text, parent)
        self._ripple_pos = QPoint()
        self._ripple_radius = 0
        self._color = QColor(color)
        self._hover_scale = 1.0
        self._animation = QPropertyAnimation(self, b"ripple_radius")
        self._scale_anim = QPropertyAnimation(self, b"hover_scale")
        
        # Style
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)

    @pyqtProperty(int)
    def ripple_radius(self): return self._ripple_radius
    @ripple_radius.setter
    def ripple_radius(self, radius):
        self._ripple_radius = radius
        self.update()

    @pyqtProperty(float)
    def hover_scale(self): return self._hover_scale
    @hover_scale.setter
    def hover_scale(self, scale):
        self._hover_scale = scale
        self.update()

    def mousePressEvent(self, event):
        self._ripple_pos = event.pos()
        self._animation.stop()
        self._animation.setDuration(600)
        self._animation.setStartValue(0)
        self._animation.setEndValue(max(self.width(), self.height()) * 2)
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._animation.start()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._scale_anim.stop()
        self._scale_anim.setDuration(200)
        self._scale_anim.setEndValue(1.05)
        self._scale_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._scale_anim.stop()
        self._scale_anim.setDuration(200)
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background with scale
        rect = self.rect()
        painter.translate(rect.center())
        painter.scale(self._hover_scale, self._hover_scale)
        painter.translate(-rect.center())
        
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 12, 12)
        
        # Draw ripple
        if self._animation.state() == QPropertyAnimation.State.Running:
            painter.setBrush(QColor(255, 255, 255, 80))
            painter.drawEllipse(self._ripple_pos, self._ripple_radius, self._ripple_radius)
        
        # Draw text
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Poppins")
        font.setPixelSize(16) # 1rem (16px) specified
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

class CalibrationSummaryDialog(QDialog):
    # Return codes
    ACTION_START = 1
    ACTION_RECALIBRATE_STEREO = 2
    ACTION_RECALIBRATE_DEPTH = 4
    ACTION_RECALIBRATE_ALL = 3
    ACTION_EXIT = 0

    def __init__(self, summary_data):
        super().__init__()
        self.summary = summary_data
        self.result_action = self.ACTION_EXIT
        
        self.setWindowTitle("Resumen de Calibración")
        self.setFixedSize(900, 820) # Further increased height for comfort
        
        # Colors
        self.ORANGE = "#FB8C00"
        self.BLUE = "#1E90FF"
        self.DARK = "#193264"
        self.CYAN_BG = "#E0F7FA"
        
        # Try to load fonts
        self._load_fonts()
        
        self._build_ui()
        self._start_entrance_animations()

    def _load_fonts(self):
        # We assume the system might have them, or we use fallbacks
        self.font_title = QFont("Righteous")
        self.font_title.setFamilies(["Righteous", "Impact", "Arial Black", "sans-serif"])
        self.font_title.setPixelSize(35) # 35.2px specified
        self.font_title.setBold(True)
        
        self.font_body = QFont("Poppins")
        self.font_body.setPixelSize(14) # 14.4px specified
        
        self.font_data = QFont("Poppins", weight=QFont.Weight.Bold)
        self.font_data.setPixelSize(18) # 17.6px specified

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background color
        painter.fillRect(self.rect(), QColor(self.CYAN_BG))
        
        # Decorative circles
        time_offset = 0 # Could add a timer for actual animation if needed
        
        # Top-right orange glow
        grad1 = QRadialGradient(QPointF(self.width(), 0), 400)
        grad1.setColorAt(0, QColor(251, 140, 0, 40))
        grad1.setColorAt(0.7, QColor(251, 140, 0, 0))
        painter.setBrush(grad1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(self.width()-300, -200, 600, 600)
        
        # Bottom-left blue glow
        grad2 = QRadialGradient(QPointF(0, self.height()), 300)
        grad2.setColorAt(0, QColor(30, 144, 255, 30))
        grad2.setColorAt(0.7, QColor(30, 144, 255, 0))
        painter.setBrush(grad2)
        painter.drawEllipse(-150, self.height()-150, 400, 400)

    def _build_ui(self):
        # Base layout for the dialog
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main scroll area for overflow protection
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        dialog_layout.addWidget(scroll)
        
        # Content container
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(25, 20, 25, 20) # Optimized vertical margins
        self.container_layout.setSpacing(10) # Balanced spacing between phases
        scroll.setWidget(self.container)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(4) # Tighter header
        
        title = QLabel("CALIBRACIÓN COMPLETA")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setMinimumHeight(45) # Lower height
        title.setStyleSheet(f"""
            QLabel {{
                color: {self.ORANGE};
                font-family: 'Righteous', 'Impact', 'Arial Black';
                font-size: 40px; /* Slight reduction for space */
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin: 0;
            }}
        """)
        
        # Exact shadow from HTML: 3px 3px 0px rgba(30, 144, 255, 0.2)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(0)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(30, 144, 255, 51))
        title.setGraphicsEffect(shadow)
        
        info_badges = QHBoxLayout()
        info_badges.setSpacing(20)
        info_badges.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        fecha_badge = self._create_info_badge(f"Fecha: {self.summary.get('fecha', 'N/A')}")
        version_badge = self._create_info_badge(f"Versión: {self.summary.get('version', '2.0')}")
        info_badges.addWidget(fecha_badge)
        info_badges.addWidget(version_badge)
        
        header_layout.addWidget(title)
        header_layout.addLayout(info_badges)
        self.container_layout.addWidget(header)
        
        # Phase sections tracking
        self.phase_sections = []
        
        # Phase 1: Individual
        p1 = self._create_phase_section(1, "Parametrización Intrínseca")
        err_l = self.summary.get('error_left', 0.0)
        err_r = self.summary.get('error_right', 0.0)
        
        # Row Left with distortion status
        self._add_data_row_with_status_badge(p1, "RMS de Reproyección Intrínseca (RMSL)", f"{err_l:.6f}", "px", "CORREGIDA")
        # Lens coefficients Izq
        k_left = self.summary.get('dist_coeffs_left', [0, 0])
        self._add_data_row(p1, "  └ Coef. Radiales Izquierda (k1, k2)", f"{k_left[0]:.4f}, {k_left[1]:.4f}", "")
        
        # Row Right with distortion status
        self._add_data_row_with_status_badge(p1, "RMS de Reproyección Intrínseca (RMSR)", f"{err_r:.6f}", "px", "CORREGIDA")
        # Lens coefficients Der
        k_right = self.summary.get('dist_coeffs_right', [0, 0])
        self._add_data_row(p1, "  └ Coef. Radiales Derecha (k1, k2)", f"{k_right[0]:.4f}, {k_right[1]:.4f}", "")
        self.container_layout.addWidget(p1)
        self.phase_sections.append(p1)
        
        # Phase 2: Stereo
        p2 = self._create_phase_section(2, "Geometría Estereoscópica")
        baseline = self.summary.get('baseline_cm', 0.0)
        rms_stereo = self.summary.get('error_stereo', 0.0)
        self._add_data_row(p2, "Longitud de Línea Base Óptica (b)", f"{baseline:.2f}", "cm")
        self._add_status_row(p2, "RMS de Reproyección Estéreo (RMSstereo)", f"{rms_stereo:.6f}")
        self.container_layout.addWidget(p2)
        self.phase_sections.append(p2)
        
        # Phase 3: Depth
        p3 = self._create_phase_section(3, "Optimización de Profundidad")
        kb_dist = self.summary.get('keyboard_distance_cm', 0.0)
        m = self.summary.get('depth_m', 1.0)
        c = self.summary.get('depth_c', 0.0)
        r2 = self.summary.get('depth_r2', 1.0)
        mae = self.summary.get('depth_mae', 0.0)
        
        self._add_data_row(p3, "Distancia Nominal al Plano Focal (Zref)", f"{kb_dist:.2f}", "cm")
        self._add_data_row(p3, "Sesgo Sistemático de Profundidad (c)", f"{c:.4f}", "cm", precision=4)
        
        self.container_layout.addWidget(p3)
        self.phase_sections.append(p3)
        
        # Phase 4: Plane
        p4 = self._create_phase_section(4, "Estimación de Plano de Referencia")
        
        coeffs = self.summary.get('plane_coeffs', [])
        avg_depth = self.summary.get('avg_key_depth', 0.0)
        std_depth = self.summary.get('std_key_depth', 0.0)
        
        if coeffs and len(coeffs) == 4:
            nx, ny, nz, d = coeffs
            # Plane Model with actual values
            sign_y = "+" if ny >= 0 else "-"
            sign_z = "+" if nz >= 0 else "-"
            sign_d = "+" if d >= 0 else "-"
            eq_str = f"{nx:.3f}x {sign_y} {abs(ny):.3f}y {sign_z} {abs(nz):.3f}z {sign_d} {abs(d):.1f} = 0"
            
            self._add_data_row(p4, "Ecuación del Plano de Referencia", eq_str, "")
            self._add_data_row(p4, "  └ Vector Normal (nx, ny, nz)", f"{nx:.3f}, {ny:.3f}, {nz:.3f}", "")
            self._add_data_row(p4, "Resolución Topográfica Vertical (ΔZkeys)", f"±{std_depth:.3f}", "cm")
        elif avg_depth > 0:
            self._add_data_row(p4, "Distancia Media Planar", f"{avg_depth:.2f}", "cm")
            self._add_data_row(p4, "Estado", "Modelo Parcial", "")
        else:
            self._add_data_row(p4, "Estado", "Pendiente", "")
        
        self.container_layout.addWidget(p4)
        self.phase_sections.append(p4)
        
        self.container_layout.addStretch()
        
        # Buttons
        btn_group = QHBoxLayout()
        btn_group.setSpacing(15) 
        btn_group.setContentsMargins(0, 10, 0, 0) # Optimized margin at top of buttons
        
        btn_recal = RippleButton("Re-Calibrar", self.ORANGE)
        btn_recal.setMinimumHeight(40) # Slightly shorter
        btn_recal.clicked.connect(lambda: self._finish(self.ACTION_RECALIBRATE_ALL))
        
        btn_back = RippleButton("Volver", self.BLUE)
        btn_back.setMinimumHeight(40) # Slightly shorter
        btn_back.clicked.connect(lambda: self._finish(self.ACTION_EXIT))
        
        btn_group.addWidget(btn_recal)
        btn_group.addWidget(btn_back)
        self.container_layout.addLayout(btn_group)

    def _create_info_badge(self, text):
        badge = QLabel(text)
        badge.setStyleSheet(f"""
            QLabel {{
                background: rgba(135, 206, 235, 0.2);
                color: {self.DARK};
                padding: 6px 16px;
                border-radius: 15px;
                border: 1px solid rgba(30, 144, 255, 0.3);
                font-family: 'Poppins';
                font-weight: 500;
                font-size: 14px; /* 14.4px specified */
            }}
        """)
        return badge

    def _create_phase_section(self, num, title_text):
        section = QFrame()
        section.setObjectName(f"phaseSection{num}")
        section.setStyleSheet(f"""
            QFrame#phaseSection{num} {{
                background: rgba(255, 255, 255, 0.85);
                border-radius: 16px;
                border-left: 6px solid {self.ORANGE};
            }}
            QFrame#phaseSection{num}:hover {{
                border: 1px solid rgba(251, 140, 0, 0.3);
                border-left: 6px solid {self.ORANGE};
            }}
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 10, 20, 10) # Optimized internal padding
        layout.setSpacing(5) # Balanced internal spacing
        
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setContentsMargins(0, 0, 0, 2) # Minimal space below title
        
        num_circle = QLabel(str(num))
        num_circle.setFixedSize(32, 32)
        num_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_circle.setStyleSheet(f"""
            QLabel {{
                background: {self.ORANGE};
                color: white;
                border-radius: 16px;
                font-weight: bold;
                font-family: 'Poppins';
                font-size: 16px; /* 16px specified */
            }}
        """)
        
        title = QLabel(title_text)
        title.setStyleSheet(f"""
            QLabel {{
                color: {self.ORANGE};
                font-family: 'Righteous', 'Impact', 'Arial Black';
                font-size: 20px;
                min-height: 25px;
            }}
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_layout.addWidget(num_circle)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        return section

    def _add_data_row(self, section, label_text, value_text, unit_text, precision=2):
        row = QWidget()
        row.setMinimumHeight(25) # Ultra-reduced height
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0) # No margin
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {self.DARK}; font-weight: 600; font-family: 'Poppins'; font-size: 13px;") # Tighter font size
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        value_container = QWidget()
        value_layout = QHBoxLayout(value_container)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(4)
        
        format_str = "{:.6f}" if "px" in unit_text else f"{{:.{precision}f}}"
        val_label = AnimatedLabel(parent=self)
        val_label.setStyleSheet(f"""
            QLabel {{
                color: {self.BLUE};
                font-family: 'Poppins';
                font-size: 18px; /* 17.6px specified */
                font-weight: bold;
            }}
        """)
        val_label.animate_to(value_text, fmt=format_str)
        val_label.setMinimumHeight(24) # Adjusted for compact rows
        val_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        unit = QLabel(unit_text)
        unit.setStyleSheet(f"color: {self.ORANGE}; font-weight: 600; font-family: 'Poppins'; font-size: 14px;") # 14.4px specified
        unit.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        value_layout.addWidget(val_label)
        value_layout.addWidget(unit)
        
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(value_container)
        
        # Add a subtle separator except for the first child (which is the title layout)
        if section.layout().count() > 1:
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background: rgba(0, 0, 0, 0.06); max-height: 1px; border: none;")
            section.layout().addWidget(line)
            
        section.layout().addWidget(row)

    def _add_status_row(self, section, label_text, value_text):
        row = QWidget()
        row.setMinimumHeight(25)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {self.DARK}; font-weight: 600; font-family: 'Poppins'; font-size: 13px;")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        val_label = AnimatedLabel(parent=self)
        val_label.setStyleSheet(f"""
            QLabel {{
                color: {self.BLUE};
                font-family: 'Poppins';
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        val_label.animate_to(value_text, fmt="{:.4f}")
        val_label.setMinimumHeight(20)
        val_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        # Status Badge
        try:
            val = float(value_text)
            status_text = "EXCELENTE" if val < 0.3 else "BUENA" if val < 0.5 else "REGULAR" if val < 1.0 else "MALA"
        except:
            status_text = "REGULAR"
            
        badge = self._create_status_badge(status_text)
        
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(val_label)
        row_layout.addSpacing(10)
        row_layout.addWidget(badge)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: rgba(0, 0, 0, 0.06); max-height: 1px; border: none;")
        section.layout().addWidget(line)
        section.layout().addWidget(row)

    def _add_data_row_with_status_badge(self, section, label_text, value_text, unit_text, badge_text):
        """Helper to add a data row with a trailing status badge (like corrected distortion)"""
        row = QWidget()
        row.setMinimumHeight(25)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {self.DARK}; font-weight: 600; font-family: 'Poppins'; font-size: 13px;")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        value_container = QWidget()
        v_layout = QHBoxLayout(value_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(4)
        
        val_label = AnimatedLabel(parent=self)
        val_label.setStyleSheet(f"color: {self.BLUE}; font-family: 'Poppins'; font-size: 16px; font-weight: bold;")
        val_label.animate_to(value_text, fmt="{:.6f}")
        
        unit = QLabel(unit_text)
        unit.setStyleSheet(f"color: {self.ORANGE}; font-weight: 600; font-family: 'Poppins'; font-size: 14px;")
        
        v_layout.addWidget(val_label)
        v_layout.addWidget(unit)
        
        badge = self._create_status_badge(badge_text)
        
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(value_container)
        row_layout.addSpacing(10)
        row_layout.addWidget(badge)
        
        if section.layout().count() > 1:
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background: rgba(0, 0, 0, 0.06); max-height: 1px; border: none;")
            section.layout().addWidget(line)
            
        section.layout().addWidget(row)

    def _create_status_badge(self, text):
        badge = QLabel(text)
        badge.setStyleSheet(f"""
            QLabel {{
                background: {self.ORANGE};
                color: white;
                padding: 2px 10px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Poppins';
            }}
        """)
        return badge

    def _start_entrance_animations(self):
        # We removed the Opacity animation as it was causing some widgets to disappear 
        # on certain systems. Keeping the interface static and stable for now.
        pass

    def _finish(self, action):
        self.result_action = action
        self.accept()

def show_calibration_summary(summary_data):
    """Muestra el diálogo de resumen y retorna la acción seleccionada"""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    dialog = CalibrationSummaryDialog(summary_data)
    dialog.exec()
    
    return dialog.result_action

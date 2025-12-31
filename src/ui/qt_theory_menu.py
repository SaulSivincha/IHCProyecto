import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QWidget, QFrame,
    QSpacerItem, QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QBrush, QLinearGradient, QPainter, QPen, QPainterPath
from src.theory.progress_manager import ProgressManager

class RoadmapContainer(QWidget):
    """Contenedor personalizado que dibuja las líneas de conexión"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = [] # Lista de (widget, widget_next)

    def set_connections(self, widgets_in_order):
        self.points = []
        for i in range(len(widgets_in_order) - 1):
            self.points.append((widgets_in_order[i], widgets_in_order[i+1]))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(255, 255, 255, 150))
        pen.setWidth(4)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        for w1, w2 in self.points:
            if w1.isVisible() and w2.isVisible():
                # Calcular centros relativos a este contenedor
                p1 = w1.mapTo(self, QPoint(w1.width()//2, w1.height()//2))
                p2 = w2.mapTo(self, QPoint(w2.width()//2, w2.height()//2))
                
                path = QPainterPath()
                # Pasar coordenadas float para evitar TypeError con QPoint
                path.moveTo(p1.x(), p1.y())
                
                # Curva bézier suave entre puntos
                # Usamos coordenadas directas
                c1x = p1.x() + 50
                c1y = p1.y()
                c2x = p2.x() - 50
                c2y = p2.y()
                
                # Ajustar control points si están en diferentes filas (zigzag vertical)
                if abs(p1.y() - p2.y()) > 50:
                    c1x = p1.x() + 20
                    c2x = p2.x() - 20

                path.cubicTo(c1x, c1y, c2x, c2y, p2.x(), p2.y())
                painter.drawPath(path)


class TheoryMenuDialog(QDialog):
    def __init__(self, lessons):
        super().__init__()
        self.lessons = lessons
        self.selected_lesson_id: Optional[str] = None
        self.progress = ProgressManager()
        
        self.setWindowTitle("Mi Aventura Musical")
        self.setMinimumSize(1000, 600)
        
        # Fondo estilo cielo infantil
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #87CEEB, stop:1 #E0F7FA);
            }
        """)
        
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- HEADER ---
        header = QHBoxLayout()
        title = QLabel("MI RUTA MUSICAL")
        title.setStyleSheet("""
            font-family: 'Comic Sans MS', 'Verdana'; 
            font-size: 42px; 
            font-weight: bold; 
            color: #FFFFFF; 
            background-color: transparent;
            margin-bottom: 10px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(title)
        main_layout.addLayout(header)
        
        # --- SCROLL AREA HORIZONTAL ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        # Usar nuestro contenedor personalizado
        container = RoadmapContainer()
        container.setStyleSheet("background: transparent;")
        
        # Layout GRID para organizar mejor el ZigZag
        # Fila 0: Top
        # Fila 1: Bottom
        grid_layout = QGridLayout(container)
        grid_layout.setContentsMargins(50, 50, 50, 50)
        grid_layout.setSpacing(40) # Espacio entre elementos

        ordered_widgets = []

        # Generar niveles
        for i, (lesson_id, lesson) in enumerate(self.lessons):
            is_unlocked = self.progress.is_unlocked(lesson_id, i)
            
            # --- WIDGET DE LECCIÓN (Botón + Texto) ---
            lesson_widget = QWidget()
            v_box = QVBoxLayout(lesson_widget)
            v_box.setContentsMargins(0,0,0,0)
            v_box.setSpacing(5)
            
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(120, 120) # Tamaño ligeramente menor para que quepa mejor
            
            # Estilo base
            base_style = """
                QPushButton {
                    border-radius: 60px;
                    border: 5px solid #FFFFFF;
                    font-family: 'Comic Sans MS', 'Arial';
                    font-size: 45px;
                    font-weight: bold;
                    color: white;
                }
                QPushButton:hover {
                    border: 7px solid #FFFFFF;
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %COLOR_LIGHT%, stop:1 %COLOR_MAIN%);
                    margin: -3px; 
                }
            """
            
            if is_unlocked:
                colors = [
                    ("#FF7043", "#F4511E"), # Naranja
                    ("#66BB6A", "#43A047"), # Verde
                    ("#42A5F5", "#1E88E5"), # Azul
                    ("#FFCA28", "#FFB300"), # Amarillo
                    ("#AB47BC", "#8E24AA"), # Violeta
                    ("#EC407A", "#D81B60")  # Rosa
                ]
                bg_light, bg_main = colors[i % len(colors)]
                
                style = base_style.replace("%COLOR_MAIN%", bg_main).replace("%COLOR_LIGHT%", bg_light)
                btn.setStyleSheet(style + f"QPushButton {{ background-color: {bg_main}; }}")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, lid=lesson_id: self._select(lid))
                
            else:
                # Bloqueado
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #B0BEC5;
                        color: #ECEFF1;
                        border: 5px solid #CFD8DC;
                        border-radius: 60px;
                        font-family: 'Comic Sans MS';
                        font-size: 30px;
                        font-weight: bold;
                    }
                """)
                btn.setText("") 
                btn.setEnabled(False)
            
            v_box.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
            
            lbl_name = QLabel(lesson.name)
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_name.setWordWrap(True)
            lbl_name.setStyleSheet("""
                color: #37474F; 
                font-family: 'Comic Sans MS';
                font-weight: bold;
                font-size: 13px;
                background-color: rgba(255,255,255,0.9);
                border-radius: 8px;
                padding: 4px;
            """)
            lbl_name.setFixedWidth(130)
            v_box.addWidget(lbl_name, 0, Qt.AlignmentFlag.AlignCenter)
            
            # POSICIONAMIENTO EN GRID (ZigZag)
            # Columna = i
            # Fila = 0 si es par, 1 si es impar
            row = 1 if i % 2 != 0 else 0
            
            grid_layout.addWidget(lesson_widget, row, i)
            ordered_widgets.append(btn) # Guardamos el BOTÓN para calcular líneas al centro

        # Establecer conexiones para dibujar líneas
        # Nota: llamamos esto con un delay o al mostrar, pero QPaintEvent lo manejará
        container.set_connections(ordered_widgets)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # --- FOOTER ---
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        exit_btn = QPushButton("VOLVER A CASA")
        exit_btn.setFixedSize(200, 50)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FB8C00;
                color: white;
                font-family: 'Comic Sans MS';
                font-size: 16px;
                font-weight: bold;
                border-radius: 25px;
                border: 3px solid #FFF3E0;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        exit_btn.clicked.connect(self.reject)
        footer_layout.addWidget(exit_btn)
        
        footer_layout.addStretch()
        main_layout.addLayout(footer_layout)

    def _select(self, lesson_id):
        self.selected_lesson_id = lesson_id
        self.accept()

def show_theory_menu(lessons) -> Optional[str]:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    dlg = TheoryMenuDialog(lessons)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selected_lesson_id
    return None
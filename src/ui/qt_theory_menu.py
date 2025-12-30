import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt
from src.theory.progress_manager import ProgressManager

class TheoryMenuDialog(QDialog):
    def __init__(self, lessons):
        super().__init__()
        self.lessons = lessons
        self.selected_lesson_id: Optional[str] = None
        self.progress = ProgressManager()
        
        self.setWindowTitle("Ruta de Aprendizaje Musical")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #1a1a2e;") # Fondo oscuro
        
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Título llamativo para niños
        title = QLabel("¡MI RUTA MUSICAL!")
        title.setStyleSheet("""
            font-size: 40px; 
            font-weight: bold; 
            color: #FFD700; 
            margin: 20px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Área de desplazamiento para la ruta
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        container = QWidget()
        path_layout = QVBoxLayout(container)
        path_layout.setContentsMargins(50, 20, 50, 20)
        path_layout.setSpacing(30)

        # Generar botones en zigzag
        for i, (lesson_id, lesson) in enumerate(self.lessons):
            is_unlocked = self.progress.is_unlocked(lesson_id, i)
            
            # Contenedor para el zigzag
            row = QHBoxLayout()
            pos = i % 4
            
            # Lógica de posición: Derecha, Centro, Izquierda, Centro
            if pos == 0: row.addStretch(2)
            elif pos == 1 or pos == 3: row.addStretch(1)
            
            # Botón circular
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(120, 120)
            
            if is_unlocked:
                # Colores vivos (Verde para pares, Azul para impares)
                color = "#58CC02" if i % 2 == 0 else "#1CB0F6"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        border-bottom: 8px solid rgba(0,0,0,0.2);
                        border-radius: 60px;
                        font-size: 35px;
                        font-weight: bold;
                        color: white;
                    }}
                    QPushButton:hover {{ background-color: #78D932; transform: scale(1.1); }}
                """)
                btn.clicked.connect(lambda checked, lid=lesson_id: self._select(lid))
            else:
                # Color gris bloqueado
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3c3c5a;
                        border-bottom: 8px solid #2a2a40;
                        border-radius: 60px;
                        color: #666680;
                        font-size: 35px;
                    }
                """)
                btn.setEnabled(False)

            row.addWidget(btn)
            
            if pos == 2: row.addStretch(2)
            elif pos == 1 or pos == 3: row.addStretch(1)
            
            path_layout.addLayout(row)
            
            # Etiqueta con el nombre de la lección
            label = QLabel(lesson.name.upper())
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
            path_layout.addWidget(label)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Botón para salir
        exit_btn = QPushButton("VOLVER AL PIANO")
        exit_btn.setStyleSheet("""
            background-color: #FF4B4B; 
            color: white; 
            padding: 15px; 
            border-radius: 10px; 
            font-weight: bold;
        """)
        exit_btn.clicked.connect(self.reject)
        main_layout.addWidget(exit_btn)

    def _select(self, lesson_id):
        self.selected_lesson_id = lesson_id
        self.accept()

# ESTA FUNCIÓN ES LA QUE LLAMA MAIN.PY
def show_theory_menu(lessons) -> Optional[str]:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    dlg = TheoryMenuDialog(lessons)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selected_lesson_id
    return None
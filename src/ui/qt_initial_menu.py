import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QSpacerItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class InitialMenuDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.choice: int | None = None  # 1, 2, 3 o None (salir)

        self.setWindowTitle("Configuración Inicial")
        self.setMinimumSize(800, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a0f0f;
            }
            QLabel#titleLabel {
                color: #ffcc00;
                font-size: 32px;
                font-weight: bold;
            }
            QLabel#hintLabel {
                color: #00ff66;
                font-size: 18px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 12px 18px;
                font-size: 20px;
                text-align: left;
                color: white;
                border: 2px solid #444444;
            }
            QPushButton#btn1 {
                background-color: #00c853;
                border-color: #00e676;
            }
            QPushButton#btn2 {
                background-color: #2962ff;
                border-color: #448aff;
            }
            QPushButton#btn3 {
                background-color: #5e35b1;
                border-color: #7e57c2;
            }
            QPushButton:hover {
                border-color: #ffffff;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Título
        title = QLabel("CONFIGURACIÓN INICIAL")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(
            20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        ))

        # Botón 1
        btn1 = QPushButton("  1  -  USAR CALIBRACIÓN GUARDADA")
        btn1.setObjectName("btn1")
        btn1.clicked.connect(lambda: self._select(1))
        layout.addWidget(btn1)

        # Botón 2
        btn2 = QPushButton("  2  -  NUEVA CALIBRACIÓN")
        btn2.setObjectName("btn2")
        btn2.clicked.connect(lambda: self._select(2))
        layout.addWidget(btn2)

        # Botón 3
        btn3 = QPushButton("  3  -  SALTAR (usar por defecto)")
        btn3.setObjectName("btn3")
        btn3.clicked.connect(lambda: self._select(3))
        layout.addWidget(btn3)

        layout.addSpacerItem(QSpacerItem(
            20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        ))

        hint = QLabel("Puedes hacer clic en un botón\n"
                      "o presionar 1, 2, 3 en el teclado.")
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.setLayout(layout)

    def _select(self, value: int):
        self.choice = value
        self.accept()

    # Opcional: seguir aceptando 1, 2, 3 por teclado
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_1:
            self._select(1)
        elif event.key() == Qt.Key.Key_2:
            self._select(2)
        elif event.key() == Qt.Key.Key_3:
            self._select(3)
        elif event.key() in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            # Respetamos el comportamiento anterior de "q" = salir
            self.choice = None
            self.reject()
        else:
            super().keyPressEvent(event)


def show_initial_menu() -> int | None:
    """
    Muestra el diálogo y devuelve:
        1 -> usar calibración guardada
        2 -> nueva calibración
        3 -> saltar (usar por defecto)
        None -> salir
    """
    app = QApplication.instance()
    owns_app = False

    if app is None:
        app = QApplication(sys.argv)
        owns_app = True

    dlg = InitialMenuDialog()
    dlg.exec()

    choice = dlg.choice  # puede ser 1,2,3 o None

    if owns_app:
        app.quit()

    return choice
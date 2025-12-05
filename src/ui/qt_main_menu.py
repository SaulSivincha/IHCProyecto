import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QSpacerItem, QSizePolicy, QWidget, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter
from pathlib import Path


class MainMenuDialog(QDialog):
    """
    Menú principal con submenús integrados para Teoría y Configuración.
    """

    def __init__(self):
        super().__init__()

        # Cargar el fondo
        img_path = Path(__file__).parent / "imagenes" / "fondoPiano.png"
        self.bg_pixmap = QPixmap(str(img_path))

        self.choice: Optional[str] = None

        self.setWindowTitle("Piano Virtual")
        self.setMinimumSize(900, 500)

        self.setStyleSheet("""
            QLabel#titleMain {
                color: #ffffff;
                font-size: 52px;
                font-weight: bold;
            }
            QLabel#titleSub {
                color: #ffffff;
                font-size: 52px;
            }
            QLabel#subtitle {
                color: #ffcc00;
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                text-align: left;
            }
            QPushButton:hover {
                color: #ffe082;
            }
            QPushButton:pressed {
                color: #fff59d;
            }
        """)

        self._build_ui()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

    def _build_ui(self):
        root = QHBoxLayout()
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(40)

        # --- Columna izquierda: título ---
        left = QVBoxLayout()
        left.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        lbl1 = QLabel("PIANO")
        lbl1.setObjectName("titleMain")
        lbl1.setFont(QFont("Arial", 48, QFont.Weight.Bold))

        lbl2 = QLabel("VIRTUAL")
        lbl2.setObjectName("titleSub")
        lbl2.setFont(QFont("Arial", 48, QFont.Weight.Bold))

        left.addWidget(lbl1)
        left.addWidget(lbl2)
        left.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        root.addLayout(left, 1)

        # --- Columna derecha: Stacked Widget ---
        self.right_stack = QStackedWidget()
        
        # === PAGINA 1: MENÚ PRINCIPAL ===
        self.page_main = QWidget()
        self.layout_main = QVBoxLayout(self.page_main)
        self.layout_main.setSpacing(10)
        self.layout_main.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self._btn_rhythm = QPushButton("▶  JUEGO DE RITMO")
        self._btn_rhythm.clicked.connect(lambda: self._select("rhythm"))
        self.layout_main.addWidget(self._btn_rhythm)

        self._btn_free = QPushButton("   MODO LIBRE")
        self._btn_free.clicked.connect(lambda: self._select("free"))
        self.layout_main.addWidget(self._btn_free)

        self._btn_theory = QPushButton("   APRENDER TEORÍA")
        self._btn_theory.clicked.connect(self._show_theory_menu)
        self.layout_main.addWidget(self._btn_theory)

        self._btn_config = QPushButton("   CONFIGURACIÓN")
        self._btn_config.clicked.connect(self._show_config_menu)
        self.layout_main.addWidget(self._btn_config)

        self._btn_exit = QPushButton("   SALIR")
        self._btn_exit.clicked.connect(lambda: self._select("exit"))
        self.layout_main.addWidget(self._btn_exit)

        self.layout_main.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # === PAGINA 2: SUBMENÚ TEORÍA ===
        self.page_theory = QWidget()
        self.layout_theory = QVBoxLayout(self.page_theory)
        self.layout_theory.setSpacing(10)
        self.layout_theory.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        lbl_theory = QLabel("LECCIONES:")
        lbl_theory.setObjectName("subtitle")
        self.layout_theory.addWidget(lbl_theory)

        self._btn_t1 = QPushButton("▶  1 - ACORDES BÁSICOS")
        self._btn_t1.clicked.connect(lambda: self._select("theory_chords"))
        self.layout_theory.addWidget(self._btn_t1)

        self._btn_t2 = QPushButton("   2 - INTERVALOS")
        self._btn_t2.clicked.connect(lambda: self._select("theory_intervals"))
        self.layout_theory.addWidget(self._btn_t2)

        self._btn_t3 = QPushButton("   3 - RITMO Y TEMPO")
        self._btn_t3.clicked.connect(lambda: self._select("theory_rhythm"))
        self.layout_theory.addWidget(self._btn_t3)

        self._btn_t4 = QPushButton("   4 - ESCALAS")
        self._btn_t4.clicked.connect(lambda: self._select("theory_scales"))
        self.layout_theory.addWidget(self._btn_t4)
        
        self.layout_theory.addSpacing(20)
        self._btn_theory_back = QPushButton("   VOLVER AL MENÚ")
        self._btn_theory_back.clicked.connect(self._show_main_menu)
        self.layout_theory.addWidget(self._btn_theory_back)

        self.layout_theory.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # === PAGINA 3: SUBMENÚ CONFIGURACIÓN ===
        self.page_config = QWidget()
        self.layout_config = QVBoxLayout(self.page_config)
        self.layout_config.setSpacing(10)
        self.layout_config.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        lbl_config = QLabel("CONFIGURACIÓN:")
        lbl_config.setObjectName("subtitle")
        self.layout_config.addWidget(lbl_config)

        self._btn_c1 = QPushButton("▶  1 - USAR CALIBRACIÓN")
        self._btn_c1.clicked.connect(lambda: self._select("config_load"))
        self.layout_config.addWidget(self._btn_c1)

        self._btn_c2 = QPushButton("   2 - NUEVA CALIBRACIÓN")
        self._btn_c2.clicked.connect(lambda: self._select("config_new"))
        self.layout_config.addWidget(self._btn_c2)

        self._btn_c3 = QPushButton("   3 - SALTAR (DEFAULT)")
        self._btn_c3.clicked.connect(lambda: self._select("config_skip"))
        self.layout_config.addWidget(self._btn_c3)
        
        self.layout_config.addSpacing(20)
        self._btn_config_back = QPushButton("   VOLVER AL MENÚ")
        self._btn_config_back.clicked.connect(self._show_main_menu)
        self.layout_config.addWidget(self._btn_config_back)

        self.layout_config.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Añadir páginas al stack
        self.right_stack.addWidget(self.page_main)
        self.right_stack.addWidget(self.page_theory)
        self.right_stack.addWidget(self.page_config)

        # Layout derecho contenedor
        right_container = QVBoxLayout()
        right_container.addWidget(self.right_stack)
        
        self.hint = QLabel("Usa ↑ / ↓ y ENTER, o haz clic con el mouse")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setStyleSheet("color: #ffffff; font-size: 14px;")
        right_container.addWidget(self.hint)

        root.addLayout(right_container, 1)
        self.setLayout(root)

        # Listas de botones
        self._buttons_main = [self._btn_rhythm, self._btn_free,
                              self._btn_theory, self._btn_config, self._btn_exit]
        
        self._buttons_theory = [self._btn_t1, self._btn_t2, 
                                self._btn_t3, self._btn_t4, self._btn_theory_back]

        self._buttons_config = [self._btn_c1, self._btn_c2, 
                                self._btn_c3, self._btn_config_back]

        self._current_index = 0
        self._menu_state = "main" # main, theory, config
        self._update_focus()

    def _show_theory_menu(self):
        self._menu_state = "theory"
        self.right_stack.setCurrentWidget(self.page_theory)
        self._current_index = 0
        self._update_focus()

    def _show_config_menu(self):
        self._menu_state = "config"
        self.right_stack.setCurrentWidget(self.page_config)
        self._current_index = 0
        self._update_focus()

    def _show_main_menu(self):
        if self._menu_state == "theory":
            prev_idx = 2
        elif self._menu_state == "config":
            prev_idx = 3
        else:
            prev_idx = 0
            
        self._menu_state = "main"
        self.right_stack.setCurrentWidget(self.page_main)
        self._current_index = prev_idx
        self._update_focus()

    def _update_focus(self):
        if self._menu_state == "theory":
            current_list = self._buttons_theory
        elif self._menu_state == "config":
            current_list = self._buttons_config
        else:
            current_list = self._buttons_main

        for i, btn in enumerate(current_list):
            text_clean = btn.text().replace("▶", "").strip()
            if i == self._current_index:
                btn.setText("▶  " + text_clean)
                btn.setFocus()
            else:
                btn.setText("   " + text_clean)

    def keyPressEvent(self, event):
        if self._menu_state == "theory":
            current_list = self._buttons_theory
        elif self._menu_state == "config":
            current_list = self._buttons_config
        else:
            current_list = self._buttons_main

        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self._current_index = (self._current_index - 1) % len(current_list)
            self._update_focus()
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self._current_index = (self._current_index + 1) % len(current_list)
            self._update_focus()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            current_list[self._current_index].click()
        elif event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Backspace):
            if self._menu_state == "main":
                self._select("exit")
            else:
                self._show_main_menu()
        else:
            super().keyPressEvent(event)

    def _select(self, value: str):
        self.choice = value
        self.accept()


def show_main_menu() -> Optional[str]:
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv)
        owns_app = True
    dlg = MainMenuDialog()
    dlg.exec()
    choice = dlg.choice
    if owns_app:
        app.quit()
    return choice
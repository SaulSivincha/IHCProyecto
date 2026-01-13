import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QSpacerItem, QSizePolicy, QWidget, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient
from pathlib import Path
from src.config.theme import Theme


class MainMenuDialog(QDialog):
    """
    Menú principal con submenús integrados para Teoría y Configuración.
    """

    def __init__(self):
        super().__init__()

        # Cargar el fondo
        self.img_path = Path(__file__).parent / "imagenes" / "fondoPiano.png"
        self.bg_pixmap = QPixmap()
        if self.img_path.exists():
            self.bg_pixmap = QPixmap(str(self.img_path))

        self.choice: Optional[str] = None

        self.setWindowTitle("Piano Virtual")
        self.setMinimumSize(900, 500)

        # Aplicar tema GLOBAL (Estilo Aventura / Kids)
        # Usamos Theme.BG_MAIN como base si no hay imagen
        # Y definimos estilos para botones y textos
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.to_hex(Theme.BG_MAIN)};
            }}
            QLabel#titleMain {{
                color: #FFFFFF; /* Título siempre blanco para contraste con fondo/imagen */
                font-size: 52px;
                font-weight: bold;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QLabel#titleSub {{
                color: #FFFFFF;
                font-size: 52px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QLabel#subtitle {{
                color: {Theme.to_hex(Theme.TEXT_HIGHLIGHT)};
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
                font-family: 'Comic Sans MS', 'Arial';
            }}
            QPushButton {{
                background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                font-size: 22px;
                font-weight: bold;
                border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                border-radius: 12px;
                padding: 10px 20px;
                text-align: left;
                font-family: 'Comic Sans MS', 'Arial';
                margin: 4px;
            }}
            QPushButton:hover {{
                background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
            }}
            QPushButton:pressed {{
                background-color: {Theme.to_hex(Theme.SUCCESS)};
            }}
        """)

        self._build_ui()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 1. Dibujar Fondo (Gradiente del Tema)
        # Si Theme define gradiente, lo usamos como base
        grad_start = QColor(Theme.to_hex(Theme.BG_GRADIENT_START))
        grad_end = QColor(Theme.to_hex(Theme.BG_GRADIENT_END))
        
        # Rellenar con Gradiente vertical
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, grad_start)
        gradient.setColorAt(1, grad_end)
        painter.fillRect(self.rect(), gradient)
        
        # 2. Dibujar Imagen (si existe) encima
        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            # Dibujar con opacidad opcional si se quiere mezclar
            painter.setOpacity(0.3) # Mezclar imagen con el color bonito del tema
            painter.drawPixmap(x, y, scaled)
            painter.setOpacity(1.0)
            
        else:
            # Si no hay imagen, el gradiente ya se dibujó
            pass

    def _build_ui(self):
        root = QHBoxLayout()
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(40)

        # --- Columna izquierda: título ---
        left = QVBoxLayout()
        left.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        lbl1 = QLabel("PIANO")
        lbl1.setObjectName("titleMain")
        
        lbl2 = QLabel("VIRTUAL")
        lbl2.setObjectName("titleSub")
        
        left.addWidget(lbl1)
        left.addWidget(lbl2)
        left.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        root.addLayout(left, 1)

        # --- Columna derecha: Stacked Widget ---
        self.right_stack = QStackedWidget()
        self.right_stack.setStyleSheet("background-color: transparent;") 
        
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
        self._btn_theory.clicked.connect(lambda: self._select("theory"))
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

        self._btn_t1 = QPushButton("▶  1 - RITMO Y TEMPO")
        self._btn_t1.clicked.connect(lambda: self._select("theory_01_rhythm"))
        self.layout_theory.addWidget(self._btn_t1)

        self._btn_t2 = QPushButton("   2 - INTERVALOS")
        self._btn_t2.clicked.connect(lambda: self._select("theory_02_intervals"))
        self.layout_theory.addWidget(self._btn_t2)

        self._btn_t3 = QPushButton("   3 - ESCALAS")
        self._btn_t3.clicked.connect(lambda: self._select("theory_03_scales"))
        self.layout_theory.addWidget(self._btn_t3)

        self._btn_t4 = QPushButton("   4 - ACORDES BÁSICOS")
        self._btn_t4.clicked.connect(lambda: self._select("theory_04_chords"))
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

        self._btn_c1 = QPushButton("▶  1 - CALIBRACIÓN")
        self._btn_c1.clicked.connect(lambda: self._select("config_calibration"))
        self.layout_config.addWidget(self._btn_c1)
        
        self._btn_c2 = QPushButton("   2 - ALGORITMOS")
        self._btn_c2.clicked.connect(lambda: self._select("config_advanced"))
        self.layout_config.addWidget(self._btn_c2)
        
        self._btn_c3 = QPushButton("   3 - CÁMARAS")
        self._btn_c3.clicked.connect(lambda: self._select("config_cameras"))
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
        self.hint.setStyleSheet(f"color: {Theme.to_hex(Theme.TEXT_ON_DARK)}; font-size: 14px; font-weight: bold;")
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
                # Highlight explícito
                btn.setStyleSheet(f"""
                    background-color: {Theme.to_hex(Theme.SELECTION_BG)};
                    color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                    border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                    border-radius: 12px;
                    padding: 10px 20px;
                    text-align: left;
                    font-size: 22px;
                    font-weight: bold;
                    font-family: 'Comic Sans MS', 'Arial';
                }}
                QPushButton:hover {{
                    background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                }}""")
            else:
                btn.setText("   " + text_clean)
                # Estilo normal - AHORA SOLIDO AZUL
                btn.setStyleSheet(f"""
                    background-color: {Theme.to_hex(Theme.BTN_PRIMARY_BG)};
                    color: {Theme.to_hex(Theme.BTN_PRIMARY_TEXT)};
                    border: 2px solid {Theme.to_hex(Theme.BORDER_DEFAULT)};
                    border-radius: 12px;
                    padding: 10px 20px;
                    text-align: left;
                    font-size: 22px;
                    font-weight: bold;
                    font-family: 'Comic Sans MS', 'Arial';
                }}
                QPushButton:hover {{
                    background-color: {Theme.to_hex(Theme.ORANGE_VIVID)};
                }}""")

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
        
    # Necesario para importar QLinearGradient si no lo importe arriba
    from PyQt6.QtGui import QLinearGradient


def show_main_menu() -> Optional[str]:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(False)
    
    dlg = MainMenuDialog()
    dlg.exec()
    choice = dlg.choice
    return choice
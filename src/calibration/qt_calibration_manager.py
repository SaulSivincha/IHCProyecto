#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Calibración con PyQt6
Versión adaptada que usa interfaz PyQt6 en lugar de OpenCV directo
"""

import cv2
import numpy as np
import json
import sys
import time
from PyQt6.QtWidgets import QApplication, QInputDialog
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from pathlib import Path

from .calibration_config import CalibrationConfig
from .camera_calibrator import CameraCalibrator
from .stereo_calibrator import StereoCalibrator
from .depth_calibrator import DepthCalibrator
from .qt_calibration_window import CalibrationWindow
from .qt_config_dialog import CalibrationConfigDialog
from ..config.theme import Theme  # Import global theme

# Importar recursos persistentes para reutilizar cámaras
try:
    from src.core.persistent_resources import get_resources
    PERSISTENT_RESOURCES_AVAILABLE = True
except ImportError:
    PERSISTENT_RESOURCES_AVAILABLE = False

# Importaciones de visión (ajustar rutas según estructura)
try:
    from ..vision.hand_detector import HandDetector
    from ..vision.depth_estimator import load_depth_estimator
    from ..vision.stereo_config import StereoConfig
except ImportError:
    # Fallback por si la estructura de directorios es diferente
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from vision.hand_detector import HandDetector
    from vision.depth_estimator import load_depth_estimator
    from vision.stereo_config import StereoConfig

# Import VirtualKeyboard for Phase 4C visualization
try:
    from ..piano.virtual_keyboard import VirtualKeyboard
except ImportError:
    from piano.virtual_keyboard import VirtualKeyboard


class QtCalibrationManager(QObject):
    """
    Gestor de calibración que usa PyQt6 para la interfaz
    OpenCV solo se usa para captura y procesamiento
    """
    
    finished = pyqtSignal(bool)  # Señal cuando termina (éxito/fallo)
    
    def __init__(self, cam_left_id, cam_right_id, resolution=(1280, 720)):
        super().__init__()
        
        self.cam_left_id = cam_left_id
        self.cam_right_id = cam_right_id
        self.resolution = resolution
        
        # Parámetros del tablero (fijo: 8x8 = 7x7 esquinas)
        self.board_cols = 7
        self.board_rows = 7
        self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM
        
        # Calibradores
        self.calibrator_left = None
        self.calibrator_right = None
        self.stereo_calibrator = None
        self.depth_calibrator = None
        
        # Herramientas de visión para Fase 3
        self.hand_detector = None
        self.hand_detector_right = None # Nuevo detector para cámara derecha
        self.depth_estimator = None
        
        # Ventana PyQt6
        self.window = CalibrationWindow(width=resolution[0], height=resolution[1])
        
        # Cámaras
        self.cap_left = None
        self.cap_right = None

        
        # Estado
        self.current_phase = "intro"
        self.current_camera = None
        self.photo_count = 0
        self.total_photos = CalibrationConfig.get_total_photos()
        self.pair_count = 0
        self.detection_frames = 0
        self.last_capture_time = 0
        
        # Variables para Fase 3 (Depth)
        self.last_depth_value = None
        self.last_hand_detected = False
        self.keyboard_samples_collected = 0
        
        # Variables para Fase 2 (Stereo)
        self.last_detected_stereo = False
        self.last_corners_left = None
        self.last_corners_right = None
        self.last_frame_left = None
        self.last_frame_right = None
        
        # Variables para Fase 1 (Single camera)
        self.last_detected = False
        self.last_corners = None
        self.last_frame = None
        
        # Variables para Rectificación de cámaras
        self.guide_line_y = 0.45  # Posición de la línea guía (0.0 = arriba, 1.0 = abajo)
        
        # Timer para actualizar frames
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        
        # Resultados
        self.calibration_data = {}
        
        # Conectar señales
        self.window.capture_requested.connect(self._on_capture)
        self.window.cancel_requested.connect(self._on_cancel)
        self.window.frame_clicked.connect(self._on_frame_clicked)  # Para compatibilidad
        # Nuevas señales para drag (Fase 4 mejorada)
        self.window.frame_drag_started.connect(self._on_drag_started)
        self.window.frame_drag_moved.connect(self._on_drag_moved)
        self.window.frame_drag_ended.connect(self._on_drag_ended)
        
        self.window.continue_requested.connect(self._on_phase_continue)
        self.window.retry_requested.connect(self._on_retry)
        self.window.arrow_key_pressed.connect(self._on_arrow_key)
        
        # Datos para definición de mesa (rectángulo por drag)
        self.table_corners = []  # [TL, TR, BR, BL]
        self.drag_start_point = None  # Punto inicial del drag
        self.drag_current_point = None  # Punto actual durante drag
        self.is_dragging = False
        
        # Asegurar directorios
        CalibrationConfig.ensure_directories()
    
    def _get_or_create_camera(self, camera_name):
        """
        Crea una instancia de VideoThread para la cámara especificada.
        
        Args:
            camera_name: 'left' o 'right'
            
        Returns:
            VideoThread: Instancia con thread corriendo
        """
        from ..vision.video_thread import VideoThread
        
        camera_id = self.cam_left_id if camera_name == "left" else self.cam_right_id
        print(f"  [CAM] Creando VideoThread para camara {camera_name} (ID: {camera_id})...")
        
        # Crear VideoThread (maneja threading automáticamente)
        video_thread = VideoThread(
            video_source=camera_id,
            video_width=self.resolution[0],
            video_height=self.resolution[1],
            video_frame_rate=30,
            buffer_all=False  # Solo último frame
        )
        
        # Verificar que se abrió correctamente
        if not video_thread.is_available():
            print(f"  [ERROR] Error al abrir camara {camera_id}")
            return None
        
        # Iniciar thread de captura
        video_thread.start()
        print(f"  [OK] VideoThread iniciado para camara {camera_name}")
        
        return video_thread
    
    def run_calibration(self, start_phase=None):
        """
        Inicia el proceso de calibración
        
        Args:
            start_phase: Ignorado, se usa el diálogo para determinar la fase
        """
        print("[DEBUG] run_calibration() iniciado")
        
        # Verificar qué fases están completas para habilitar opciones
        file_exists = CalibrationConfig.CALIBRATION_FILE.exists()
        has_phase1 = False
        has_phase2 = False
        if file_exists:
            try:
                with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                    prev_data = json.load(f)
                # Verifica que existan datos de Fase 1
                has_left = 'left_camera' in prev_data and 'camera_matrix' in prev_data['left_camera']
                has_right = 'right_camera' in prev_data and 'camera_matrix' in prev_data['right_camera']
                has_phase1 = has_left and has_right
                # Verifica que existan datos de Fase 2 (el campo es 'stereo', no 'stereo_config')
                has_phase2 = 'stereo' in prev_data and prev_data['stereo'] is not None
            except Exception as e:
                print(f"[DEBUG] Error leyendo calibración previa: {e}")
        print(f"[DEBUG] Archivo existe: {file_exists}, has_phase1: {has_phase1}, has_phase2: {has_phase2}")
        
        # Procesar eventos pendientes antes de mostrar diálogo
        QApplication.processEvents()
        
        # ========== CONFIGURACIÓN DE TABLERO ==========
        # SIEMPRE pedir configuración al usuario para permitir recalibración
        # Verificar si Fase 3 ya está completa para habilitar Fase 4
        has_phase3 = self._check_phase3_complete()
        
        dialog = CalibrationConfigDialog(
            default_rows=self.board_rows,
            default_cols=self.board_cols,
            default_size_mm=self.square_size_mm,
            enable_phase2=has_phase1,
            enable_phase3=has_phase2,
            enable_phase4=has_phase3
        )
        
        print("[DEBUG] Diálogo de configuración creado, mostrando...")
        
        # Asegurar que el diálogo tenga foco y esté visible
        dialog.raise_()
        dialog.activateWindow()
        dialog.setFocus()
        
        # Procesar eventos para que el diálogo se muestre
        QApplication.processEvents()
        
        result = dialog.exec()
        print(f"[DEBUG] Resultado del diálogo de configuración: {result}")
        
        print(f"[DEBUG] dialog.exec() retornó: {result} (tipo: {type(result)})")
        
        if result:
            new_rows, new_cols, new_size_mm, selected_phase = dialog.get_values()
            print(f"[DEBUG] Valores del diálogo:")
            print(f"  - new_rows: {new_rows} (tipo: {type(new_rows)})")
            print(f"  - new_cols: {new_cols} (tipo: {type(new_cols)})")
            print(f"  - new_size_mm: {new_size_mm} (tipo: {type(new_size_mm)})")
            print(f"  - selected_phase: {selected_phase} (tipo: {type(selected_phase)})")
            print(f"[OK] Configuracion: {new_cols}x{new_rows}, {new_size_mm}mm - Iniciando en Fase {selected_phase}")

            # Cargar configuración previa si existe
            prev_config = None
            if CalibrationConfig.CALIBRATION_FILE.exists():
                try:
                    with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                        prev_data = json.load(f)
                        prev_config = prev_data.get('board_config', {})
                except Exception as e:
                    print(f"[DEBUG] No se pudo leer calibración previa: {e}")

            # Si el usuario cambió filas, columnas o tamaño de casilla, forzar recalibración completa
            # SOLO verificar si se selecciona Fase 1 (recalibración desde cero)
            if prev_config and selected_phase == 1:
                prev_rows = prev_config.get('rows')
                prev_cols = prev_config.get('cols')
                prev_size = prev_config.get('square_size_mm')
                
                # Verificar si algún valor previo es None o si hay diferencias
                config_changed = False
                if prev_rows is None or prev_cols is None or prev_size is None:
                    # Si falta algún valor, considerar que cambió
                    config_changed = True
                else:
                    # Comparar valores
                    try:
                        config_changed = (prev_rows != new_rows) or (prev_cols != new_cols) or (abs(float(prev_size) - float(new_size_mm)) > 1e-3)
                    except (TypeError, ValueError):
                        # Si hay error en la conversión, considerar que cambió
                        config_changed = True
                
                if config_changed:
                    print("[DEBUG] El usuario cambió el tamaño del tablero. Borrando calibración previa...")
                    try:
                        CalibrationConfig.CALIBRATION_FILE.unlink()
                        print("[DEBUG] Archivo de calibración eliminado.")
                    except Exception as e:
                        print(f"[DEBUG] No se pudo borrar calibración previa: {e}")
                    # Resetear flags
                    has_phase1 = False
                    has_phase2 = False
            elif selected_phase in [2, 3] and prev_config:
                # Para fase 2 o 3, usar la configuración guardada (no verificar cambios)
                self.board_rows = prev_config.get('rows', new_rows)
                self.board_cols = prev_config.get('cols', new_cols)
                self.square_size_mm = prev_config.get('square_size_mm', new_size_mm)
                print(f"[DEBUG] Usando configuración guardada: {self.board_cols}x{self.board_rows}, {self.square_size_mm}mm")

            self.board_rows = new_rows
            self.board_cols = new_cols
            self.square_size_mm = new_size_mm
        else:
            print("Cancelado por usuario en diálogo de configuración")
            # Si ya existe calibración previa, continuar con ella
            if CalibrationConfig.calibration_exists():
                print("[INFO] Usando calibración existente (cancelado por usuario)")
                self.finished.emit(True)
            else:
                self.finished.emit(False)
            return

        # Mostrar ventana
        self.window.show()

        # Verificar que selected_phase tiene un valor válido
        if selected_phase is None:
            print("[DEBUG] WARNING: selected_phase es None, usando fase 1 por defecto")
            selected_phase = 1

        # Iniciar según la fase seleccionada en el diálogo
        print(f"[DEBUG] Iniciando fase: {selected_phase}")
        if selected_phase == 0:
            print("\n[OK] Iniciando rectificación de cámaras...")
            self._start_rectify_intro()
        elif selected_phase == 3:
            print("\n[OK] Iniciando directamente en Fase 3...")
            print("  Cargando Fase 1...")
            phase1_ok = self._load_phase1_calibration()
            print(f"  Fase 1 cargada: {phase1_ok}")
            if phase1_ok:
                print("  Cargando Fase 2...")
                phase2_ok = self._load_phase2_calibration()
                print(f"  Fase 2 cargada: {phase2_ok}")
                if phase2_ok:
                    print("  Iniciando Fase 3...")
                    self._start_phase3()
                else:
                    print("[ERROR] Error al cargar Fase 2, volviendo a Fase 1")
                    self._start_intro()
            else:
                print("[ERROR] Error al cargar Fase 1, volviendo a Fase 1")
                self._start_intro()
        elif selected_phase == 2:
            print("\n[OK] Iniciando directamente en Fase 2...")
            
            # Primero, limpiar solo la parte estéreo del archivo (mantener Fase 1)
            if CalibrationConfig.CALIBRATION_FILE.exists():
                try:
                    with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                        calib_data = json.load(f)
                    # Solo borrar la sección stereo, mantener Fase 1
                    calib_data['stereo'] = None
                    with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
                        json.dump(calib_data, f, indent=4)
                    print("[DEBUG] Sección estéreo limpiada, Fase 1 mantenida")
                except Exception as e:
                    print(f"[DEBUG] Error limpiando stereo: {e}")
            
            phase1_ok = self._load_phase1_calibration()
            if phase1_ok:
                # Verificar que los calibradores están correctamente inicializados
                if self.calibrator_left and self.calibrator_left.is_calibrated and \
                   self.calibrator_right and self.calibrator_right.is_calibrated:
                    self._load_board_config()
                    print("[OK] Calibracion previa de Fase 1 valida. Iniciando Fase 2...")
                    # Reiniciar timer y estado por seguridad
                    if self.timer.isActive():
                        self.timer.stop()
                    self.current_phase = None
                    self._start_phase2()
                else:
                    print("[ERROR] Calibracion previa de Fase 1 incompleta o invalida. Volviendo a Fase 1.")
                    self.window.set_status("No se encontró calibración previa válida de Fase 1. Debes completarla antes de Fase 2.", "#FF0000")
                    self._start_intro()
            else:
                print("[ERROR] Error al cargar datos previos, volviendo a Fase 1")
                self.window.set_status("Error al cargar calibración previa. Debes completar Fase 1.", "#FF0000")
                self._start_intro()
        elif selected_phase == 4:
            print("\n[OK] Iniciando directamente en Fase 4 (Definicion de Mesa AR)...")
            # Solo cargar lo mínimo (estereo no es necesario para tabla, pero phase1 sí para las cámaras)
            phase1_ok = self._load_phase1_calibration()
            if phase1_ok:
                self._load_board_config()
                self._start_table_definition()
            else:
                print("[ERROR] Error al cargar Fase 1, volviendo a Fase 1")
                self._start_intro()
        else:
            # Fase 1 (Default)
            self._start_intro()
    
    def _start_intro(self):
        """Muestra la pantalla de introducción inicial (rectificación de cámaras)"""
        self._start_rectify_intro()

    def _start_rectify_intro(self):
        """Muestra la introducción para rectificación de cámaras"""
        self.current_phase = "rectify_intro"
        
        # Ocultar barra de progreso en rectificación
        self.window.show_progress(False)
        
        instructions = [
            "<b>OBJETIVO:</b> Que ambas cámaras estén niveladas igual",
            "",
            "<b>1.</b> Usa <b style='color: #FFFF00;'>↑ ↓ flechas</b> para mover la línea verde",
            "<b>2.</b> Ajusta cada cámara para que un borde recto (mesa, tablero)",
            "       quede <b style='color: #00FF00;'>PARALELO</b> a la línea verde",
            "",
            "<i>No importa el tamaño del objeto, solo que esté paralelo</i>"
        ]
        
        self.window.show_intro_screen(
            "ALINEACIÓN DE CÁMARAS",
            instructions
        )
        
        black_frame = np.zeros((self.resolution[1]//2, self.resolution[0]//2, 3), dtype=np.uint8)
        self.window.update_frames(black_frame, black_frame)

    def _start_rectify_preview(self):
        """Inicia vista previa con líneas guía para alinear cámaras"""
        self.current_phase = "rectify_preview"
        self.window.set_phase(self.current_phase, "ALINEACIÓN DE CÁMARAS")
        self.window.set_status("Haz que un borde recto quede PARALELO a la línea verde en ambas cámaras", "#00FF00")
        self.window.show_progress(False)
        instructions = [
            "<b style='color: #FFFF00;'>↑ ↓ FLECHAS:</b> Mueve la línea verde arriba/abajo",
            "",
            "<b style='color: #00FF00;'>AJUSTA CADA CÁMARA:</b>",
            "   El borde de la mesa o tablero debe quedar <b>PARALELO</b> a la línea",
            "   (ver ejemplos BIEN / MAL en pantalla)",
            "",
            "<span style='color: #00FF00;'>✔ LISTO:</span> Cuando esté paralelo en AMBAS → <b>CONTINUAR</b>"
        ]
        self.window.show_intro_screen("ALINEACIÓN DE CÁMARAS", instructions)
        self.window.show_continue_button(True)
        self.window.show_retry_button(False)

        # Obtener cámaras
        self.cap_left = self._get_or_create_camera("left")
        self.cap_right = self._get_or_create_camera("right")

        if not self.cap_left or not self.cap_left.is_available() or \
           not self.cap_right or not self.cap_right.is_available():
            print("[ERROR] Error al abrir camaras para rectificación")
            self._finish_calibration(False)
            return

        self.timer.start(33)

    def _stop_rectify_preview(self):
        """Detiene la vista previa de rectificación"""
        if self.timer.isActive():
            self.timer.stop()
        self.cap_left = None
        self.cap_right = None

    def _on_arrow_key(self, direction):
        """Maneja las teclas de flecha para ajustar la altura de la línea guía"""
        if self.current_phase != "rectify_preview":
            return
        
        # Ajuste de 2% por cada pulsación
        step = 0.02
        
        if direction == 'up':
            self.guide_line_y = max(0.1, self.guide_line_y - step)
        elif direction == 'down':
            self.guide_line_y = min(0.9, self.guide_line_y + step)
        
        # Actualizar estado para feedback visual
        height_pct = int(self.guide_line_y * 100)
        self.window.set_status(f"Altura de línea: {height_pct}% (usa ↑↓ para ajustar)", "#FFFF00")

    def _start_phase1_intro(self):
        """Muestra la pantalla de introducción para Fase 1"""
        self.current_phase = "phase1_intro"
        self.window.show_progress(True)
        
        instructions = [
            f"Usaremos un tablero de ajedrez de <b>{self.board_cols+1}x{self.board_rows+1}</b>",
            f"Se detectarán <b>{self.board_cols}x{self.board_rows} esquinas internas</b>",
            f"Tamaño de cuadrado configurado: <b>{self.square_size_mm} mm</b>",
            "El proceso tiene 2 fases: calibración individual y calibración estéreo",
            "Prepara tu tablero y buena iluminación"
        ]
        
        self.window.show_intro_screen(
            "CALIBRACIÓN ESTEREOSCÓPICA - FASE 1",
            instructions
        )
        
        black_frame = np.zeros((self.resolution[1]//2, self.resolution[0]//2, 3), dtype=np.uint8)
        self.window.update_frames(black_frame, black_frame)
    
    def _on_phase_continue(self):
        """Maneja el botón de continuar entre fases"""
        # Ocultar botón de reintentar al continuar
        self.window.show_retry_button(False)
        
        if self.current_phase == "rectify_intro":
            self._start_rectify_preview()
        
        elif self.current_phase == "rectify_preview":
            self._stop_rectify_preview()
            self._start_phase1_intro()
        
        elif self.current_phase == "phase1_intro":
            self._start_camera_calibration("left")
            
        elif self.current_phase == "left_complete":
            # Camara izquierda completada - pasar a camara derecha
            self._start_camera_calibration("right")
            
        elif self.current_phase == "phase1_complete":
            self._start_phase2()
            
        elif self.current_phase == "phase2_complete":
            self._start_phase3()
            
        elif self.current_phase == "phase3_complete":
            # IR A NUEVA FASE: Definición de Mesa
            self._start_table_definition()
            
        elif self.current_phase == "table_definition":
            # --- CORRECCIÓN: VALIDACIÓN PARA EVITAR INDEX ERROR ---
            if not self.table_corners or len(self.table_corners) != 4:
                self.window.set_status("⚠️ ERROR: Debes dibujar el área del teclado primero", "#FF0000")
                return
            # ------------------------------------------------------
            self._save_table_definition() # Guardar coordenadas
            self.current_phase = "table_definition_complete"
            self._start_corner_depth_calibration() # Pasar a tocar esquinas
            
        elif self.current_phase == "table_definition_complete":
            # Fase 4B se inicia automáticamente, pero por si acaso
            self._start_corner_depth_calibration()
            
        elif self.current_phase == "corner_depth_calibration":
            # El usuario confirmó las instrucciones (Intro)
            # Ocultamos el botón para que no confunda, la detección ya corre en background
            self.window.show_continue_button(False)
            self.window.set_status("👆 Buscando dedo en la esquina...", "#00FF00")
        
        elif self.current_phase == "phase4b_complete":
            # Fase 4B completada - IR A FASE 4C (Nivelación de teclas)
            self._start_key_depth_calibration()
            
        elif self.current_phase == "key_depth_calibration":
             # Usuario termino de barrer las teclas
             self._finish_key_calibration()

        # Lógica de reintento (si el usuario presionó Continuar en lugar de Reintentar en pantalla de error)
        elif self.current_phase in ["capture_left", "capture_left_intro"]:
            if self.calibrator_left and self.calibrator_left.is_calibrated:
                self._start_camera_calibration("right")
            
        elif self.current_phase in ["capture_right", "capture_right_intro"]:
            if self.calibrator_right and self.calibrator_right.is_calibrated:
                self._start_phase2()
            
        elif self.current_phase == "stereo_intro":
            # Después de las instrucciones de stereo, iniciar captura
            self._on_stereo_continue()
        
        elif self.current_phase == "depth_intro":
            # Después de las instrucciones de depth, iniciar captura
            self._start_depth_capture()
    
    def _on_retry(self):
        """
        Maneja el botón de reintentar.
        Reinicia la fase actual manteniendo los parámetros de configuración.
        """
        print(f"[RETRY] Reintentando fase: {self.current_phase}")
        
        # Detener timer si está activo
        if self.timer.isActive():
            self.timer.stop()
        
        # Ocultar botón de reintentar mientras se procesa
        self.window.show_retry_button(False)
        
        # Determinar qué fase reiniciar basándose en el estado actual
        if self.current_phase in ["capture_left", "left_complete"]:
            # Reiniciar calibración de cámara izquierda
            print("  [RETRY] Reiniciando calibracion camara IZQUIERDA")
            self._reset_camera_calibration("left")
            self._start_camera_calibration("left")
            
        elif self.current_phase in ["capture_right", "right_complete"]:
            # Reiniciar calibración de cámara derecha
            print("  [RETRY] Reiniciando calibracion camara DERECHA")
            self._reset_camera_calibration("right")
            self._start_camera_calibration("right")
            
        elif self.current_phase in ["stereo_capture", "stereo_intro", "phase2_complete"]:
            # Reiniciar calibración estéreo
            print("  [RETRY] Reiniciando calibracion ESTEREO")
            self._reset_stereo_calibration()
            self._start_phase2()
            
        elif self.current_phase in ["depth_capture", "depth_intro", "phase3_complete"]:
            # Reiniciar calibración de profundidad
            print("  [RETRY] Reiniciando calibracion de PROFUNDIDAD")
            self._reset_depth_calibration()
            self._start_phase3()
    
    def _reset_camera_calibration(self, camera_name):
        """Resetea los datos de calibración de una cámara"""
        if camera_name == "left":
            if self.calibrator_left:
                self.calibrator_left.reset()
        elif camera_name == "right":
            if self.calibrator_right:
                self.calibrator_right.reset()
        
        self.photo_count = 0
        self.detection_frames = 0
    
    def _reset_stereo_calibration(self):
        """Resetea los datos de calibración estéreo"""
        if self.stereo_calibrator:
            self.stereo_calibrator = None
        self.pair_count = 0
        self.detection_frames = 0
    
    def _reset_depth_calibration(self):
        """Resetea los datos de calibración de profundidad"""
        if self.depth_calibrator:
            self.depth_calibrator = None
        if hasattr(self, 'keyboard_samples_collected'):
            self.keyboard_samples_collected = 0
        self.detection_frames = 0
    
    def _start_camera_calibration(self, camera_name):
        """
        Inicia la calibración de una cámara individual
        
        Args:
            camera_name: 'left' o 'right'
        """
        self.current_camera = camera_name
        self.photo_count = 0
        
        # Determinar ID de cámara
        camera_id = self.cam_left_id if camera_name == "left" else self.cam_right_id
        display_name = "IZQUIERDA" if camera_name == "left" else "DERECHA"
        
        # Crear calibrador
        if camera_name == "left":
            self.calibrator_left = CameraCalibrator(
                camera_id=camera_id,
                camera_name=camera_name,
                board_size=(self.board_cols, self.board_rows),
                square_size_mm=self.square_size_mm
            )
            self.current_calibrator = self.calibrator_left
        else:
            self.calibrator_right = CameraCalibrator(
                camera_id=camera_id,
                camera_name=camera_name,
                board_size=(self.board_cols, self.board_rows),
                square_size_mm=self.square_size_mm
            )
            self.current_calibrator = self.calibrator_right
        
        # Mostrar estado de carga
        self.window.set_status(f"Iniciando cámara {display_name}...", "#FFA500")
        QApplication.processEvents()
        
        # Obtener cámara (reutiliza persistente si está disponible)
        cap = self._get_or_create_camera(camera_name)
        if cap is None or not cap.is_available():
            print(f"[ERROR] No se pudo abrir la camara {camera_id}")
            self._finish_calibration(False)
            return
        
        
        if camera_name == "left":
            self.cap_left = cap
        else:
            self.cap_right = cap
        
        # Actualizar UI
        self.current_phase = f"capture_{camera_name}"
        self.window.set_phase(self.current_phase, f"FASE 1 - CÁMARA {display_name}")
        self.window.update_progress(0, self.total_photos)
        
        # Mostrar primera instrucción
        cat_title, specific_instr, objective = CalibrationConfig.get_instruction_for_photo(0)
        self.window.show_capture_instructions(
            cat_title, specific_instr, objective, 0, self.total_photos
        )
        
        # Mostrar botón de reintentar
        self.window.show_retry_button(True
        )
        
        # Iniciar actualización de frames
        self.timer.start(33)  # ~30 FPS
    
    def _update_frame(self):
        """Actualiza los frames de las cámaras (llamado por timer)"""
        if self.current_phase == "rectify_preview":
            self._update_rectify_preview_frame()
        elif self.current_phase.startswith("capture_"):
            self._update_single_camera_frame()
        elif self.current_phase == "stereo_capture":
            self._update_stereo_frame()
        elif self.current_phase == "depth_capture":
            self._update_depth_frame()
        elif self.current_phase == "table_definition":
            self._update_table_definition_frame()
        elif self.current_phase == "corner_depth_calibration":
            self._update_corner_depth_frame()
        elif self.current_phase == "key_depth_calibration":
            self._update_key_depth_frame()
    
    def _update_single_camera_frame(self):
        """Actualiza frame para calibración de cámara individual"""
        camera_name = self.current_camera
        cap = self.cap_left if camera_name == "left" else self.cap_right
        
        if cap is None or not cap.is_available():
            return
        
        finished, frame = cap.next(black=True, wait=0.033)
        if frame is None:
            return
        
        # IMPORTANTE: Aplicar transformaciones antes de detectar tablero
        # Esto asegura que la calibración se haga en el espacio transformado correcto
        from ..vision.stereo_config import StereoConfig
        frame = StereoConfig.apply_camera_transforms(frame)

        # Detectar tablero en cada frame para seguimiento fluido
        # OPTIMIZACIÓN: No refinar esquinas en preview (solo al capturar)
        detected, corners, frame_overlay = self.current_calibrator.detect_chessboard(frame, refine_corners=False)
        
        # Guardar para captura
        self.last_detected = detected
        self.last_corners = corners
        self.last_frame = frame
        
        # Actualizar estado
        if detected:
            self.window.set_status("[OK] Tablero detectado - Presiona CAPTURAR", "#00FF00")
            self.window.enable_capture(True)
        else:
            self.window.set_status("Buscando tablero...", "#FFA500")
            self.window.enable_capture(False)
        
        # Mostrar frame (aplicar espejo para visualización intuitiva)
        frame_display = StereoConfig.apply_display_transform(frame_overlay)
        if camera_name == "left":
            self.window.update_frames(frame_left=frame_display)
        else:
            self.window.update_frames(frame_right=frame_display)

    def _update_rectify_preview_frame(self):
        """Actualiza frames para rectificación de cámaras"""
        if not self.cap_left or not self.cap_right:
            return

        finished_left, frame_left = self.cap_left.next(black=True, wait=0.033)
        finished_right, frame_right = self.cap_right.next(black=True, wait=0.033)

        if frame_left is None or frame_right is None:
            return

        from ..vision.stereo_config import StereoConfig

        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)

        # Aplicar display transform PRIMERO (rotación 180)
        frame_left_display = StereoConfig.apply_display_transform(frame_left)
        frame_right_display = StereoConfig.apply_display_transform(frame_right)

        # Dibujar guías DESPUÉS de la transformación para que el texto quede derecho
        frame_left_display = self._draw_rectify_guides(frame_left_display, side="left")
        frame_right_display = self._draw_rectify_guides(frame_right_display, side="right")

        self.window.update_frames(frame_left=frame_left_display, frame_right=frame_right_display)

    def _draw_rectify_guides(self, frame, side="left"):
        """Dibuja líneas guía para alinear cámaras - SIMPLIFICADO"""
        if frame is None:
            return frame
        h, w = frame.shape[:2]
        
        # === LÍNEA PRINCIPAL (altura configurable con flechas) ===
        line_y = int(h * self.guide_line_y)
        
        # Línea gruesa verde
        cv2.line(frame, (0, line_y), (w, line_y), (0, 255, 0), 4)
        
        # Líneas paralelas de referencia (ayudan a ver si está paralelo)
        cv2.line(frame, (0, line_y - 25), (w, line_y - 25), (0, 180, 0), 1)
        cv2.line(frame, (0, line_y + 25), (w, line_y + 25), (0, 180, 0), 1)
        
        # === EJEMPLO CORRECTO (esquina superior derecha) ===
        ex_x = w - 140
        ex_y = 70
        
        # Fondo
        cv2.rectangle(frame, (ex_x - 5, ex_y - 20), (w - 10, ex_y + 50), (0, 50, 0), -1)
        cv2.rectangle(frame, (ex_x - 5, ex_y - 20), (w - 10, ex_y + 50), (0, 255, 0), 1)
        
        cv2.putText(frame, "BIEN", (ex_x + 40, ex_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        
        # Mini línea verde
        cv2.line(frame, (ex_x + 5, ex_y + 20), (w - 20, ex_y + 20), (0, 255, 0), 2)
        
        # Objeto PARALELO a la línea (horizontal)
        cv2.rectangle(frame, (ex_x + 20, ex_y + 16), (ex_x + 90, ex_y + 24), (255, 0, 255), -1)
        cv2.putText(frame, "paralelo", (ex_x + 15, ex_y + 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
        
        # === EJEMPLO INCORRECTO (esquina superior izquierda) ===
        bad_x = 10
        bad_y = 70
        
        # Fondo
        cv2.rectangle(frame, (bad_x, bad_y - 20), (bad_x + 130, bad_y + 50), (50, 0, 0), -1)
        cv2.rectangle(frame, (bad_x, bad_y - 20), (bad_x + 130, bad_y + 50), (0, 0, 255), 1)
        
        cv2.putText(frame, "MAL", (bad_x + 45, bad_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        
        # Mini línea verde
        cv2.line(frame, (bad_x + 5, bad_y + 20), (bad_x + 120, bad_y + 20), (0, 255, 0), 2)
        
        # Objeto INCLINADO (no paralelo)
        pts = np.array([
            [bad_x + 25, bad_y + 12],
            [bad_x + 95, bad_y + 24],
            [bad_x + 93, bad_y + 32],
            [bad_x + 23, bad_y + 20]
        ], np.int32)
        cv2.fillPoly(frame, [pts], (255, 0, 255))
        cv2.putText(frame, "inclinado", (bad_x + 30, bad_y + 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
        
        # === ETIQUETA DE CÁMARA ===
        cam_label = "CAM IZQUIERDA" if side == "left" else "CAM DERECHA"
        label_color = (0, 165, 255) if side == "left" else (255, 165, 0)
        cv2.putText(frame, cam_label, (w//2 - 100, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, label_color, 2, cv2.LINE_AA)
        
        # === INDICADOR DE ALTURA ===
        height_pct = int(self.guide_line_y * 100)
        cv2.putText(frame, f"[Flechas] Altura: {height_pct}%", (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2, cv2.LINE_AA)
        
        # === INSTRUCCIÓN SIMPLE ===
        cv2.putText(frame, "Borde de tablero/mesa PARALELO a esta linea", (w//2 - 230, line_y - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "(como el ejemplo BIEN)", (w//2 - 120, line_y + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        
        return frame

    def _draw_alignment_targets(self, frame, side="left"):
        """Método mantenido por compatibilidad - ya no se usa"""
        return frame
    
    def _on_capture(self):
        """Maneja el evento de captura"""
        if self.current_phase.startswith("capture_"):
            self._capture_single_photo()
        elif self.current_phase == "stereo_capture":
            self._capture_stereo_pair()
        elif self.current_phase == "depth_capture":
            self._capture_depth_measurement()
    
    def _capture_single_photo(self):
        """Captura una foto para calibración individual"""
        if not self.last_detected:
            return
        
        # IMPORTANTE: Refinar esquinas con precisión subpíxel antes de guardar
        _, corners_refined, _ = self.current_calibrator.detect_chessboard(
            self.last_frame, 
            refine_corners=True
        )
        
        # Capturar imagen con esquinas refinadas
        self.current_calibrator.capture_image(self.last_frame, corners_refined)
        self.photo_count += 1
        
        print(f"[OK] Foto {self.photo_count}/{self.total_photos} capturada")
        
        # Actualizar progreso
        self.window.update_progress(self.photo_count, self.total_photos)
        
        # Actualizar instrucciones para la siguiente foto
        if self.photo_count < self.total_photos:
            cat_title, specific_instr, objective = CalibrationConfig.get_instruction_for_photo(self.photo_count)
            self.window.show_capture_instructions(
                cat_title, specific_instr, objective, self.photo_count, self.total_photos
            )
        else:
            # Captura completa, procesar calibración
            self._process_single_camera_calibration()
    
    def _process_single_camera_calibration(self):
        """Procesa la calibración de la cámara actual"""
        self.timer.stop()
        
        
        # Limpiar referencias
        if self.current_camera == "left":
            self.cap_left = None
        else:
            self.cap_right = None
        
        # Ejecutar calibración
        print(f"\n{'='*70}")
        print(f"PROCESANDO CALIBRACIÓN - CÁMARA {self.current_camera.upper()}")
        print(f"{'='*70}")
        
        result = self.current_calibrator.calibrate()
        
        if result is None:
            print("[ERROR] La calibracion fallo")
            self._finish_calibration(False)
            return
        
        # Mostrar resumen
        camera_display = "IZQUIERDA" if self.current_camera == "left" else "DERECHA"
        
        # Definir color según la calidad del error (Verde < 0.5, Amarillo < 1.0, Rojo > 1.0)
        error_val = result['reprojection_error']
        color_error = "#00FF00" if error_val < 0.5 else "#FFFF00" if error_val < 1.0 else "#FF0000"
        
        summary_html = f"<h3 style='color: #00FF00;'>CÁMARA {camera_display} FINALIZADA</h3>"
        summary_html += "<table style='width: 100%; color: #FFFFFF; font-size: 14px;'>"
        
        # Dato de la cámara actual
        summary_html += f"<tr><td><b>Fotos:</b></td><td>{self.photo_count}</td></tr>"
        summary_html += f"<tr><td><b>RMS Actual:</b></td><td style='color:{color_error};'><b>{error_val:.4f} px</b></td></tr>"
        
        # TRUCO: Si estamos en la DERECHA, mostrar también el error de la IZQUIERDA anterior
        if self.current_camera == "right" and self.calibrator_left and self.calibrator_left.is_calibrated:
            prev_err = self.calibrator_left.reprojection_error
            c_prev = "#00FF00" if prev_err < 0.5 else "#FFFF00" if prev_err < 1.0 else "#FF0000"
            summary_html += "<tr><td colspan='2'><hr></td></tr>" # Separador
            summary_html += f"<tr><td>RMS Izquierda:</td><td style='color:{c_prev};'>{prev_err:.4f} px</td></tr>"
            summary_html += f"<tr><td>RMS Derecha:</td><td style='color:{color_error};'>{error_val:.4f} px</td></tr>"
            
        summary_html += "</table>"
        
        if error_val > 1.0:
            summary_html += "<p style='color: #FF0000; margin-top: 10px;'>⚠ Error alto. Se recomienda <b>Reintentar</b>.</p>"
        else:
            summary_html += "<p style='color: #00FF00; margin-top: 20px;'><b>✔ Calibración Correcta</b><br>Presiona CONTINUAR</p>"
        
        self.window.set_instructions(summary_html)
        self.window.set_status("[OK] Calibracion completada", "#00FF00")
        self.window.show_continue_button(True)
        self.window.show_retry_button(True)  # Permitir reintentar si el resultado no es satisfactorio
        
        # Actualizar fase
        if self.current_camera == "left":
            self.current_phase = "left_complete"
        else:
            self.current_phase = "phase1_complete"
            # Guardar Fase 1
            self._save_phase1_only()
    
    def _start_phase2(self):
        """Inicia la Fase 2: calibración estéreo"""
        # Reiniciar timer si está activo
        if self.timer.isActive():
            self.timer.stop()
        self.current_phase = "stereo_intro"
        instructions = [
            "Ahora calibraremos el <b>par estéreo</b>",
            "Coloca el tablero visible en <b>AMBAS cámaras</b> simultáneamente",
            "Necesitamos capturar <b>10 pares</b> de imágenes",
            "Varía la posición y orientación del tablero entre capturas",
            "Asegúrate de que el tablero esté completamente visible en ambas vistas"
        ]
        self.window.show_intro_screen(
            "FASE 2 - CALIBRACIÓN ESTÉREO",
            instructions
        )
        self.current_phase = "stereo_intro"
    
    def _on_stereo_continue(self):
        """Inicia la captura estéreo después de la introducción"""
        # Crear calibrador estéreo
        self.stereo_calibrator = StereoCalibrator(self.calibrator_left, self.calibrator_right)
        
        # Mostrar estado
        self.window.set_status("Iniciando cámaras estéreo...", "#FFA500")
        QApplication.processEvents()
        
        # Obtener ambas cámaras (reutiliza persistentes si están disponibles)
        self.cap_left = self._get_or_create_camera("left")
        self.cap_right = self._get_or_create_camera("right")
        
        if not self.cap_left or not self.cap_left.is_available() or \
           not self.cap_right or not self.cap_right.is_available():
            print("[ERROR] Error al abrir las camaras")
            self._finish_calibration(False)
            return
        
        
        # Actualizar UI
        self.current_phase = "stereo_capture"
        self.window.set_phase(self.current_phase, "FASE 2 - CALIBRACIÓN ESTÉREO")
        self.pair_count = 0
        self.window.show_stereo_instructions(0, 20)
        
        # Mostrar botón de reintentar
        self.window.show_retry_button(True)
        
        # Iniciar timer
        self.timer.start(33)
    
    def _update_stereo_frame(self):
        """Actualiza frames para calibración estéreo"""
        if not self.cap_left or not self.cap_right:
            return
        
        finished_left, frame_left = self.cap_left.next(black=True, wait=0.033)
        finished_right, frame_right = self.cap_right.next(black=True, wait=0.033)
        
        if frame_left is None or frame_right is None:
            return
        
        # IMPORTANTE: Aplicar las mismas transformaciones que en runtime
        # Esto asegura que la calibración se haga en el espacio transformado correcto
        from ..vision.stereo_config import StereoConfig
        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)

        # Detectar tablero en ambas cámaras (sin refinar para preview)
        detected_both, corners_left, corners_right, display_left, display_right = \
            self.stereo_calibrator.detect_chessboard_pair(frame_left, frame_right, refine_corners=False)
        
        # Guardar para captura
        self.last_detected_stereo = detected_both
        self.last_corners_left = corners_left
        self.last_corners_right = corners_right
        self.last_frame_left = frame_left
        self.last_frame_right = frame_right
        
        # Contar frames de detección consecutivos
        if detected_both:
            self.detection_frames += 1
        else:
            self.detection_frames = 0
        
        # Actualizar estado
        current_time = time.time()
        can_capture = (current_time - self.last_capture_time) > 1.0
        
        if detected_both and self.detection_frames >= 5 and can_capture:
            self.window.set_status("[OK] Tablero detectado en AMBAS - Presiona CAPTURAR", "#00FF00")
            self.window.enable_capture(True)
        elif detected_both:
            self.window.set_status(f"Estabilizando... {self.detection_frames}/5", "#00C8FF")
            self.window.enable_capture(False)
        else:
            self.window.set_status("Buscando tablero en ambas cámaras...", "#FFA500")
            self.window.enable_capture(False)
        
        # Mostrar frames (con espejo)
        self.window.update_frames(
            StereoConfig.apply_display_transform(display_left), 
            StereoConfig.apply_display_transform(display_right)
        )
    
    def _capture_stereo_pair(self):
        """Captura un par estéreo"""
        if not self.last_detected_stereo or self.detection_frames < 5:
            return
        
        # IMPORTANTE: Refinar esquinas con precisión antes de guardar
        _, corners_left_refined, corners_right_refined, _, _ = \
            self.stereo_calibrator.detect_chessboard_pair(
                self.last_frame_left, 
                self.last_frame_right, 
                refine_corners=True
            )
        
        # Capturar par con esquinas refinadas
        self.stereo_calibrator.capture_stereo_pair(
            self.last_frame_left, self.last_frame_right,
            corners_left_refined, corners_right_refined
        )
        self.pair_count += 1
        
        print(f"[OK] Par {self.pair_count} capturado")
        
        # Actualizar progreso
        self.window.show_stereo_instructions(self.pair_count, 20)
        
        # Resetear detección
        self.detection_frames = 0
        self.last_capture_time = time.time()
        
        # Si tenemos suficientes pares, finalizar automáticamente
        if self.pair_count >= 20:
            self._on_stereo_complete()
    
    def _on_stereo_complete(self):
        """Procesa la calibración estéreo"""
        self.timer.stop()
        
        
        # Limpiar referencias
        self.cap_left = None
        self.cap_right = None
        
        # Ejecutar calibración estéreo
        print("\n⏳ Procesando calibración estéreo...")
        stereo_result = self.stereo_calibrator.calibrate_stereo_pair()
        
        if stereo_result is None:
            print("[ERROR] Error en calibracion estereo")
            self._finish_calibration(False)
            return
        
        # Calcular rectificación
        print("⏳ Calculando parámetros de rectificación...")
        self.stereo_calibrator.compute_rectification()
        
        # Recopilar datos finales
        self._compile_calibration_data()
        
        # Guardar
        self._save_calibration()
        
        # Mostrar resumen
        summary_data = {
            'board_config': f"{self.board_cols}x{self.board_rows} ({self.square_size_mm} mm)",
            'left_error': self.calibrator_left.reprojection_error,
            'right_error': self.calibrator_right.reprojection_error,
            'stereo_error': self.stereo_calibrator.stereo_error,
            'baseline': np.linalg.norm(self.stereo_calibrator.T) * 100
        }
        
        self.window.show_summary_screen(summary_data)
        self.window.show_retry_button(True)  # Permitir reintentar si el resultado no es satisfactorio
        self.current_phase = "phase2_complete"

    def _start_phase3(self):
        """Inicia la Fase 3: calibración de profundidad"""
        self.current_phase = "depth_intro"
        
        # Pedir la distancia real al usuario
        self._ask_real_distance()
    
    def _ask_real_distance(self):
        """Muestra un diálogo para que el usuario ingrese la distancia real"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton, QFrame
        from PyQt6.QtCore import Qt
        
        dialog = QDialog(self.window)
        dialog.setWindowTitle("Calibración de Profundidad")
        dialog.setModal(True)
        dialog.setFixedSize(520, 450)
        
        # Usar colores correctos del Theme (Adventure Mode)
        bg_sky = Theme.to_hex(Theme.BG_MAIN)  # Azul celeste - fondo principal
        bg_white = Theme.to_hex(Theme.BG_PANEL)  # Blanco - para paneles/inputs
        text_dark = Theme.to_hex(Theme.TEXT_PRIMARY)  # Azul oscuro - texto
        header_orange = Theme.to_hex(Theme.BG_HEADER)  # Naranja - header
        border_orange = Theme.to_hex(Theme.BORDER_FOCUS)  # Naranja - bordes
        accent_blue = Theme.to_hex(Theme.BTN_PRIMARY_BG)  # Azul vivido - botones
        success_green = Theme.to_hex(Theme.SUCCESS)  # Verde - success
        error_red = Theme.to_hex(Theme.ERROR)  # Rojo - cancelar
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_sky};
                border: none;
                border-radius: 12px;
            }}
            
            QLabel {{
                color: {text_dark};
                font-size: 13px;
                background: transparent;
            }}
            
            QLabel#title {{
                color: {header_orange};
                background: transparent;
                font-size: 22px;
                font-weight: bold;
                padding: 5px;
            }}
            
            QLabel#subtitle {{
                color: {text_dark};
                font-size: 13px;
                padding: 12px 20px;
                background-color: rgba(255, 255, 255, 0.6);
                border-radius: 8px;
            }}
            
            QLabel#stepLabel {{
                color: {text_dark};
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }}
            
            QLabel#info {{
                color: {text_dark};
                font-size: 12px;
                background-color: rgba(255, 255, 255, 0.8);
                padding: 12px;
                border-radius: 8px;
                border-left: 4px solid {success_green};
            }}
            
            QDoubleSpinBox {{
                background-color: {bg_white};
                color: {text_dark};
                border: 2px solid {border_orange};
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 22px;
                font-weight: bold;
                min-width: 150px;
            }}
            
            QDoubleSpinBox:focus {{
                border: 3px solid {accent_blue};
            }}
            
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 20px;
                border-radius: 3px;
            }}
            
            QPushButton {{
                background-color: {border_orange};
                color: white;
                font-size: 15px;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                padding: 12px 32px;
                min-width: 120px;
            }}
            
            QPushButton:hover {{
                background-color: {header_orange};
            }}
            
            QPushButton:pressed {{
                background-color: #CC5500;
            }}
            
            QPushButton#skipBtn {{
                background-color: {accent_blue};
                color: white;
                border: none;
            }}
            
            QPushButton#skipBtn:hover {{
                background-color: #1468B8;
            }}
            
            QFrame#separator {{
                background-color: rgba(25, 50, 100, 0.2);
                max-height: 1px;
                margin: 8px 30px;
            }}
        """)
        
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Título
        title = QLabel("Calibración de Profundidad")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(2)
        
        # Subtítulo
        subtitle = QLabel(
            "Ingresa las mediciones de distancia para calibrar\n"
            "el sistema de detección de profundidad."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(5)
        
        # Separador
        separator1 = QFrame()
        separator1.setObjectName("separator")
        separator1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator1)
        
        layout.addSpacing(12)
        
        # Input 1: Altura MANO
        input_layout1 = QHBoxLayout()
        input_layout1.addStretch()
        
        label1 = QLabel("Altura calibración (mano):")
        label1.setObjectName("stepLabel")
        input_layout1.addWidget(label1)
        
        input_layout1.addSpacing(12)
        
        self.spin_calib_height = QDoubleSpinBox()
        self.spin_calib_height.setRange(10, 200)
        self.spin_calib_height.setValue(20)
        self.spin_calib_height.setSuffix(" cm")
        self.spin_calib_height.setDecimals(1)
        self.spin_calib_height.setSingleStep(1)
        input_layout1.addWidget(self.spin_calib_height)
        
        input_layout1.addStretch()
        layout.addLayout(input_layout1)
        
        layout.addSpacing(12)
        
        # Input 2: Altura MESA
        input_layout2 = QHBoxLayout()
        input_layout2.addStretch()
        
        label2 = QLabel("Altura real (mesa/teclado):")
        label2.setObjectName("stepLabel")
        input_layout2.addWidget(label2)
        
        
        input_layout2.addSpacing(12)
        
        self.spin_table_height = QDoubleSpinBox()
        self.spin_table_height.setRange(10, 200)
        self.spin_table_height.setValue(41)
        self.spin_table_height.setSuffix(" cm")
        self.spin_table_height.setDecimals(1)
        self.spin_table_height.setSingleStep(1)
        input_layout2.addWidget(self.spin_table_height)
        
        input_layout2.addStretch()
        layout.addLayout(input_layout2)
        
        # Guardar referencia al diálogo
        self._distance_dialog = dialog
        
        layout.addSpacing(15)
        
        # Separador
        separator2 = QFrame()
        separator2.setObjectName("separator")
        separator2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator2)
        
        # Info
        info = QLabel(
            "<b>Sugerencia:</b> Calibra con la mano cerca (~20cm) para mejor precisión. "
            "Luego indica la altura de la mesa donde tocarás."
        )
        info.setObjectName("info")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        skip_btn = QPushButton("Omitir")
        skip_btn.setObjectName("skipBtn")
        skip_btn.clicked.connect(lambda: self._on_distance_entered(dialog, skip=True))
        buttons_layout.addWidget(skip_btn)
        
        buttons_layout.addSpacing(15)
        
        confirm_btn = QPushButton("Continuar")
        confirm_btn.clicked.connect(lambda: self._on_distance_entered(dialog, skip=False))

        buttons_layout.addWidget(confirm_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        dialog.exec()
    
    def _on_distance_entered(self, dialog, skip=False):
        """Procesa la distancia ingresada y continúa con la Fase 3"""
        if skip:
            self.calib_start_height = 20.0
            self.real_table_height = 41.0
            print("[Fase 3] Omitiendo, usando valores por defecto (20cm, 41cm)")
        else:
            # Leer los DOS valores
            self.calib_start_height = self.spin_calib_height.value()
            self.real_table_height = self.spin_table_height.value()
            
            print(f"")
            print(f"========================================")
            print(f"[Fase 3] Configuración:")
            print(f"  - Iniciar medición mano en: {self.calib_start_height} cm")
            print(f"  - Altura real de la mesa:   {self.real_table_height} cm")
            print(f"========================================")
            print(f"")
        
        dialog.accept()
        
        # CAMBIO: Solo 1 paso (la altura que definiste)
        self.depth_step = 0
        self.depth_targets = [
            self.calib_start_height  # Solo un objetivo
        ]
        
        # Guardar base_height por compatibilidad con otros métodos
        self.base_height = self.calib_start_height
        
        # Instrucciones simplificadas
        instructions = [
            f"Configuración: Medir desde <b>{self.calib_start_height} cm</b>",
            f"Mesa definida a: <b>{self.real_table_height} cm</b>",
            "",
            "<b>🎯 CALIBRACIÓN RÁPIDA (1 PUNTO):</b>",
            f"   1. Pon tu mano a <b>{self.depth_targets[0]:.0f} cm</b> y captura.",
            "",
            "El sistema calculará el ajuste automáticamente."
        ]
        
        self.window.show_intro_screen("FASE 3 - CALIBRACIÓN SIMPLE", instructions)
    
    def _start_depth_capture(self):
        """Inicia la captura de profundidad con flujo de 3 pasos"""
        try:
            # Inicializar componentes de visión
            if self.hand_detector is None:
                self.window.set_status("Cargando detector de manos...", "#FFA500")
                QApplication.processEvents()
                self.hand_detector = HandDetector(maxHands=2)
            
            # --- Corrección: Detector para cámara derecha ---
            if self.hand_detector_right is None:
                self.hand_detector_right = HandDetector(maxHands=2)
                # ------------------------------------------------
            
            # --- CAMBIO CRÍTICO: SIEMPRE RECARGAR DE CERO ---
            self.window.set_status("Reseteando estimador de profundidad...", "#FFA500")
            QApplication.processEvents()
            
            # Forzamos la carga de un estimador NUEVO
            self.depth_estimator = load_depth_estimator(str(CalibrationConfig.CALIBRATION_FILE))
            
            # TRUCO DE SEGURIDAD: Forzar la pendiente a 1.0 en memoria antes de calibrar
            # Esto evita que una mala calibración anterior contamine la nueva.
            self.depth_estimator.depth_slope = 1.0
            self.depth_estimator.depth_intercept = 0.0
            self.depth_estimator.DEPTH_CORRECTION_FACTOR = 1.0
            print("[INFO] Estimador reseteado en memoria a Slope=1.0 para calibración limpia.")
            # -----------------------------------------------
            
            # Inicializar calibrador de profundidad
            self.depth_calibrator = DepthCalibrator(self.depth_estimator)
            
            # --- AGREGAR ESTAS LÍNEAS PARA LIMPIAR BASURA VIEJA ---
            print("[INFO] Limpiando historial de mediciones anteriores...")
            self.depth_calibrator.measurements = []  # ¡ESTO ES LA CLAVE!
            self.depth_calibrator.slope = 1.0
            self.depth_calibrator.intercept = 0.0
            # ------------------------------------------------------
            
            # Configurar número de pasos (ahora es 1 medición)
            self.keyboard_samples_needed = 1
            self.keyboard_samples_collected = 0
            
            # Asegurar que tenemos depth_step y depth_targets
            if not hasattr(self, 'depth_step'):
                self.depth_step = 0
            if not hasattr(self, 'depth_targets') or not self.depth_targets:
                base = getattr(self, 'base_height', 20.0)
                self.depth_targets = [base]  # Solo 1 target
                print(f"[DEBUG] depth_targets CREADO con fallback base={base}")
            else:
                print(f"[DEBUG] depth_targets YA EXISTEN: {self.depth_targets}")
            
            print(f"[DEBUG] base_height = {getattr(self, 'base_height', 'NO EXISTE')}")
            print(f"[DEBUG] depth_targets = {self.depth_targets}")

            # Mostrar estado
            self.window.set_status("Iniciando cámaras...", "#FFA500")
            QApplication.processEvents()
            
            # Obtener cámaras si están cerradas (reutiliza persistentes)
            if self.cap_left is None:
                self.cap_left = self._get_or_create_camera("left")
                
            if self.cap_right is None:
                self.cap_right = self._get_or_create_camera("right")
                
            if not self.cap_left or not self.cap_left.is_available() or \
               not self.cap_right or not self.cap_right.is_available():
                print("[ERROR] Error al abrir las camaras para profundidad")
                self._finish_calibration(False)
                return
                
            # Actualizar UI con instrucciones del paso actual
            self.current_phase = "depth_capture"
            self.window.set_phase(self.current_phase, "FASE 3 - CALIBRACIÓN DE PROFUNDIDAD")
            self._prompt_next_depth_step()
            
            self.window.show_continue_button(False)
            self.window.enable_capture(True)
            
            # Mostrar botón de reintentar
            self.window.show_retry_button(True)
            
            # Iniciar timer
            if not self.timer.isActive():
                self.timer.start(33)
                
        except Exception as e:
            print(f"[ERROR] Error critico al iniciar Fase 3: {e}")
            import traceback
            traceback.print_exc()
            self.window.set_status(f"Error: {str(e)}", "#FF0000")
            self._finish_calibration(False)
    
    def _prompt_next_depth_step(self):
        """Guía al usuario paso a paso en la calibración de profundidad"""
        if self.depth_step < len(self.depth_targets):
            target = self.depth_targets[self.depth_step]
            step_num = self.depth_step + 1
            total_steps = len(self.depth_targets)
            
            # Mensaje del paso actual
            step_msg = f"Coloca tu mano a <b>{target:.1f} cm</b>"
            
            self.window.set_instructions(
                f"<b>🎯 PASO {step_num}/{total_steps}</b><br><br>"
                f"{step_msg}<br><br>"
                f"<span style='color: #00FF00;'>Presiona ESPACIO o CAPTURAR cuando esté listo</span>"
            )
            self.window.set_status(f"Paso {step_num}/{total_steps}: Pon tu mano a {target:.1f} cm", "#00BFFF")

    def _update_depth_frame(self):
        """Actualiza frame para calibración de profundidad"""
        if not self.cap_left or not self.cap_right:
            return
            
        finished_left, frame_left = self.cap_left.next(black=True, wait=0.033)
        finished_right, frame_right = self.cap_right.next(black=True, wait=0.033)
        
        if frame_left is None or frame_right is None:
            return
        
        # Importar configuración estéreo
        from ..vision.stereo_config import StereoConfig

        # 1. Transformación RAW (para geometría correcta y detección)
        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)

        # 2. Detección en RAW (coordenadas reales)
        # Usamos hand_detector tanto para izq como der? No, self.hand_detector es el principal?
        # Revisando código abajo: usa self.hand_detector para AMBAS? (Líneas 1110 y 1116 usan self.hand_detector)
        # Esto parece un BUG original si usa el mismo detector para ambas imágenes secuencialmente
        # Pero asumiremos que es intencional o que es una instancia compartida.
        # CORRECCIÓN: Debería usar detectores separados si existen, pero depth_calibrator usa landmarks.
        
        found_left = self.hand_detector.findHands(frame_left)
        landmarks_left = None
        if found_left and self.hand_detector.results.multi_hand_landmarks:
            landmarks_left = self.hand_detector.results.multi_hand_landmarks[0]
            
        # Detección derecha con nuevo detector independiente
        if self.hand_detector_right is None: self.hand_detector_right = HandDetector(maxHands=1)
        
        found_right = self.hand_detector_right.findHands(frame_right)
        landmarks_right = None
        if found_right and self.hand_detector_right.results.multi_hand_landmarks:
            landmarks_right = self.hand_detector_right.results.multi_hand_landmarks[0]

        # 3. Preparar Display (Espejo para visualización)
        display_left = StereoConfig.apply_display_transform(frame_left)
        display_right = StereoConfig.apply_display_transform(frame_right)
        
        # 4. Dibujar en Display (con rotate_180=True)
        if landmarks_right:
            self.hand_detector_right.drawHands(display_right, rotate_180=True)
            
        if landmarks_left:
            self.hand_detector.drawHands(display_left, rotate_180=True)
            
        # Actualizar variables para cálculo (ya son independientes)
        # landmarks_left = landmarks_left
            
        # Calcular profundidad si hay manos en ambas
        self.last_depth_value = None
        
        if landmarks_left and landmarks_right:
            try:
                # 1. Obtener coordenadas del dedo índice (Landmark 8) de los resultados de MediaPipe
                # Estas coordenadas vienen en rango 0.0 a 1.0
                h_raw, w_raw = frame_left.shape[:2]
                pt_L_raw = (landmarks_left.landmark[8].x * w_raw, landmarks_left.landmark[8].y * h_raw)
                pt_R_raw = (landmarks_right.landmark[8].x * w_raw, landmarks_right.landmark[8].y * h_raw)

                # 2. RECTIFICAR PRIMERO (Cada sensor con su propia matriz)
                # IMPORTANTE: Usamos is_left según la ID física de la cámara
                rect_L = self.depth_estimator.rectify_point(pt_L_raw, is_left=True)
                rect_R = self.depth_estimator.rectify_point(pt_R_raw, is_left=False)

                # 3. APLICAR SWAP (Si las cámaras están físicamente invertidas)
                if StereoConfig.CAMERAS_SWAPPED:
                    pt_for_tri_L = rect_R
                    pt_for_tri_R = rect_L
                else:
                    pt_for_tri_L = rect_L
                    pt_for_tri_R = rect_R

                # 4. TRIANGULAR con método simple (más robusto para calibración)
                p3d = self.depth_estimator.triangulate_point(pt_for_tri_L, pt_for_tri_R, method='simple')

                if p3d and 10 < p3d[2] < 150:
                    depth = p3d[2]
                    self.last_depth_value = depth
                    self.window.set_status(
                        f"[OK] Mano detectada - Distancia: {depth:.1f} cm - !PRESIONA ESPACIO!", 
                        "#00FF00"
                    )
                    self.window.enable_capture(True)
                else:
                    self.window.set_status("Calculando profundidad...", "#FFA500")
                    self.window.enable_capture(False)

            except Exception as e:
                print(f"[Fase 3] Error en cálculo: {e}")
                self.window.set_status("Error en triangulación", "#FF0000")
        else:
            status_msg = "Muestra tu mano en "
            if not landmarks_left:
                status_msg += "CÁMARA IZQUIERDA "
            if not landmarks_right:
                status_msg += "CÁMARA DERECHA"
            self.window.set_status(status_msg, "#FFA500")
            self.window.enable_capture(False)
            
        # Guardar landmarks para captura
        self.last_landmarks_left = landmarks_left
        self.last_landmarks_right = landmarks_right
        
        # Mostrar frames
        self.window.update_frames(display_left, display_right)

    def _capture_depth_measurement(self):
        """Captura una medición de profundidad para el paso actual"""
        if self.last_depth_value is None:
            return
        
        # Obtener la distancia real objetivo del paso actual
        if self.depth_step < len(self.depth_targets):
            real_val = self.depth_targets[self.depth_step]
            measured_val = self.last_depth_value
            
            # Agregar medición al calibrador: (Real, Medido)
            self.depth_calibrator.add_measurement(real_val, measured_val)
            print(f"[OK] Captura {self.depth_step + 1}: Real={real_val:.1f} cm, Medido={measured_val:.1f} cm")
            
            # Avanzar al siguiente paso
            self.depth_step += 1
            self.keyboard_samples_collected += 1
            
            # Verificar si tenemos todas las mediciones
            if self.depth_step >= len(self.depth_targets):
                # Finalizar calibración
                self._finish_phase3()
            else:
                # Mostrar instrucciones para el siguiente paso
                self._prompt_next_depth_step()
                self.window.set_status(f"[OK] Paso {self.depth_step} completado - Continúa con el siguiente", "#00FF00")

    def _finish_phase3(self):
        """Finaliza la Fase 3 con regresión lineal"""
        self.timer.stop()
        
        # IMPORTANTE: Usar la altura real de la mesa (Input 2) como referencia del teclado
        # aunque la calibración haya empezado en otra altura (Input 1)
        if hasattr(self, 'real_table_height') and self.real_table_height:
            self.depth_calibrator.keyboard_distance = self.real_table_height
            print(f"[Fase 3] Guardando altura de mesa: {self.real_table_height} cm")
        else:
            # Fallback si por alguna razón no existe la variable
            self.depth_calibrator.keyboard_distance = 41.0
            print("[Fase 3] Usando altura de mesa por defecto: 41.0 cm")
        
        # Calcular regresión lineal y guardar
        result = self.depth_calibrator.calculate_and_save()
        
        if result is None:
            print("Error en calibracion de profundidad - no hay suficientes mediciones")
            self._finish_calibration(False)
            return
        
        slope, intercept = result
        print(f"")
        print(f"========================================")
        print(f"[OK] CALIBRACIÓN DE PROFUNDIDAD COMPLETADA")
        print(f"     Fórmula: Real = {slope:.4f} * Medido + {intercept:.4f}")
        print(f"========================================")
        print(f"")
            
        # Recopilar datos para el resumen
        summary_data = {
            'board_config': f"{self.board_cols}x{self.board_rows} ({self.square_size_mm}mm)",
            'left_error': self.calibrator_left.reprojection_error if self.calibrator_left else 'N/A',
            'right_error': self.calibrator_right.reprojection_error if self.calibrator_right else 'N/A',
            'keyboard_distance': self.depth_calibrator.keyboard_distance,
            'correction_factor': slope,  # Para retrocompatibilidad en UI
            'depth_slope': slope,
            'depth_intercept': intercept
        }
        
        # Agregar datos de mediciones
        if self.depth_calibrator.measurements:
            summary_data['num_measurements'] = len(self.depth_calibrator.measurements)
            summary_data['regression_formula'] = f"Real = {slope:.3f} × Medido + {intercept:.2f}"
        
        # Agregar datos estéreo si existen
        if self.stereo_calibrator:
            if hasattr(self.stereo_calibrator, 'stereo_error') and self.stereo_calibrator.stereo_error is not None:
                summary_data['stereo_error'] = self.stereo_calibrator.stereo_error
            
            if self.stereo_calibrator.T is not None:
                # T está en mm, convertir a cm
                baseline_mm = np.linalg.norm(self.stereo_calibrator.T)
                summary_data['baseline_cm'] = baseline_mm / 10.0
        
        # Agregar datos de Fase 4 (Mesa AR) si existen
        # Intenta obtener de los atributos guardados o de la configuración persistente
        if hasattr(self, 'table_corners') and self.table_corners:
             summary_data['table_corners'] = self.table_corners
        elif self.calibration_data.get('table_corners'):
             summary_data['table_corners'] = self.calibration_data.get('table_corners')
             
        table_def = self.calibration_data.get('table_definition', {})
        if table_def and 'corner_depths' in table_def:
            summary_data['corner_depths'] = table_def['corner_depths']
        if table_def and 'plane_equation' in table_def:
            summary_data['plane_equation'] = table_def['plane_equation']
        
        # Mostrar pantalla de resumen
        self.window.show_summary_screen(summary_data)
        self.window.show_retry_button(True)  # Permitir reintentar si el resultado no es satisfactorio
        self.window.show_continue_button(True)  # Permitir continuar a Fase 4
        self.current_phase = "phase3_complete"
    
    def _on_cancel(self):
        """Maneja la cancelación"""
        print("\n[CANCEL] Calibracion cancelada por el usuario")
        self._cleanup()
        self.finished.emit(False)
        self.window.close()
    
    def _finish_calibration(self, success):
        """Finaliza el proceso de calibración"""
        self._cleanup()
        self.window.close()
        self.finished.emit(success)
        
        if success:
            print("\n🎉 ¡Calibración completa exitosa!")
        else:
            print("\n❌ La calibración no se completó.")
    
    def _cleanup(self):
        """Limpia recursos (cámaras, timers, etc.)"""
        if self.timer.isActive():
            self.timer.stop()
        
        # Limpiar referencias (pero no cerrar si son persistentes)
        self.cap_left = None
        self.cap_right = None
    
    # Métodos auxiliares (verificación, carga, guardado)
    
    def _check_phase1_complete(self):
        """Verifica si la Fase 1 está completa"""
        if not CalibrationConfig.CALIBRATION_FILE.exists():
            return False
        
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            has_left = 'left_camera' in data and 'camera_matrix' in data['left_camera']
            has_right = 'right_camera' in data and 'camera_matrix' in data['right_camera']
            
            return has_left and has_right
        except:
            return False
    
    def _check_phase2_complete(self):
        """Verifica si la Fase 2 está completa"""
        if not CalibrationConfig.CALIBRATION_FILE.exists():
            return False
        
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            has_stereo = 'stereo' in data and data['stereo'] is not None
            if has_stereo:
                return 'rotation_matrix' in data['stereo'] and 'translation_vector' in data['stereo']
            
            return False
        except:
            return False
    
    def _check_phase3_complete(self):
        """Verifica si la Fase 3 (Profundidad) está completa"""
        if not CalibrationConfig.CALIBRATION_FILE.exists():
            return False
        
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Verificar si existe depth_correction con keyboard_distance_cm (guardado por Fase 3)
            if 'depth_correction' in data and data['depth_correction'] is not None:
                return 'keyboard_distance_cm' in data['depth_correction']
            
            return False
        except:
            return False
    
    def _load_phase1_calibration(self):
        """Carga calibraciones de Fase 1"""
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            board_config = data['board_config']
            board_size = (board_config['cols'], board_config['rows'])
            square_size = board_config['square_size_mm']
            
            # Calibrador izquierdo
            self.calibrator_left = CameraCalibrator(
                camera_id=self.cam_left_id,
                camera_name='left',
                board_size=board_size,
                square_size_mm=square_size
            )
            self.calibrator_left.camera_matrix = np.array(data['left_camera']['camera_matrix'])
            self.calibrator_left.distortion_coeffs = np.array(data['left_camera']['distortion_coeffs'])
            self.calibrator_left.reprojection_error = data['left_camera']['reprojection_error']
            self.calibrator_left.image_size = (data['left_camera']['image_width'], data['left_camera']['image_height'])
            self.calibrator_left.obj_points = [None] * data['left_camera']['num_images']
            self.calibrator_left.is_calibrated = True
            
            # Calibrador derecho
            self.calibrator_right = CameraCalibrator(
                camera_id=self.cam_right_id,
                camera_name='right',
                board_size=board_size,
                square_size_mm=square_size
            )
            self.calibrator_right.camera_matrix = np.array(data['right_camera']['camera_matrix'])
            self.calibrator_right.distortion_coeffs = np.array(data['right_camera']['distortion_coeffs'])
            self.calibrator_right.reprojection_error = data['right_camera']['reprojection_error']
            self.calibrator_right.image_size = (data['right_camera']['image_width'], data['right_camera']['image_height'])
            self.calibrator_right.obj_points = [None] * data['right_camera']['num_images']
            self.calibrator_right.is_calibrated = True
            
            return True
        except Exception as e:
            print(f"[ERROR] Error al cargar Fase 1: {e}")
            return False

    def _load_phase2_calibration(self):
        """Carga calibración estéreo de Fase 2"""
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            if 'stereo' not in data or data['stereo'] is None:
                return False
                
            # Crear calibrador estéreo si no existe
            if self.stereo_calibrator is None:
                self.stereo_calibrator = StereoCalibrator(self.calibrator_left, self.calibrator_right)
            
            # Cargar matrices
            stereo = data['stereo']
            self.stereo_calibrator.R = np.array(stereo['rotation_matrix'])
            self.stereo_calibrator.T = np.array(stereo['translation_vector'])
            self.stereo_calibrator.E = np.array(stereo['essential_matrix'])
            self.stereo_calibrator.F = np.array(stereo['fundamental_matrix'])
            
            # Cargar error si existe
            if 'rms_error' in stereo:
                self.stereo_calibrator.stereo_error = stereo['rms_error']
            
            # Calcular rectificación para tener mapas listos
            self.stereo_calibrator.compute_rectification()
            
            return True
        except Exception as e:
            print(f"[ERROR] Error al cargar Fase 2: {e}")
            return False
    
    def _load_board_config(self):
        """Carga configuración del tablero"""
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            board_config = data['board_config']
            self.board_cols = board_config['cols']
            self.board_rows = board_config['rows']
            self.square_size_mm = board_config['square_size_mm']
        except:
            self.board_cols = 7
            self.board_rows = 7
            self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM
    
    # ==================== FASE 4: DEFINICIÓN DE MESA (AR) ====================
    
    def _start_table_definition(self):
        """Inicia la fase de definición de esquinas de la mesa"""
        self.current_phase = "table_definition"
        self.table_corners = []
        self.drag_start_point = None
        self.drag_current_point = None
        self.is_dragging = False
        
        instructions = [
            "<b>CONFIGURACIÓN DE PROYECCIÓN AR</b>",
            "",
            "📐 <b>ARRASTRA para definir el área del teclado:</b>",
            "",
            "1. Haz <b>CLIC</b> en una esquina del área deseada",
            "2. <b>MANTÉN PRESIONADO</b> y arrastra hasta la esquina opuesta",
            "3. <b>SUELTA</b> para confirmar el rectángulo",
            "",
            "💡 El rectángulo aparecerá en <span style='color:#00FF00'>VERDE</span> mientras arrastras"
        ]
        
        self.window.show_intro_screen(
            "DEFINICIÓN DE SUPERFICIE",
            instructions
        )
        
        # --- CORRECCIÓN ---
        # Forzar que el botón de continuar esté OCULTO hasta que se dibuje el rectángulo
        self.window.show_continue_button(False) 
        # ------------------
        
        # Iniciar video
        if not self.cap_left:
             self.cap_left = self._get_or_create_camera("left")
        
        self.timer.start(33)
        self.window.set_status("🖱️ Arrastra en la CÁMARA IZQUIERDA para definir el área", "#00C8FF")

    def _update_table_definition_frame(self):
        """Muestra el video y dibuja el rectángulo (durante drag o finalizado)"""
        if not self.cap_left:
            self.cap_left = self._get_or_create_camera("left")
            
        frame_left = None
        if self.cap_left:
            _, frame_left = self.cap_left.next(wait=0.033)
            
        if frame_left is None:
            return

        from ..vision.stereo_config import StereoConfig
        h, w = frame_left.shape[:2]

        # 1. Usar TRANSFORMACIÓN DE DISPLAY (Rotada 180) para que se vea bien
        display = StereoConfig.apply_display_transform(frame_left.copy())
        h_disp, w_disp = display.shape[:2]
        
        # 2. Dibujar rectángulo
        # CASO A: Estamos arrastrando (Coordenadas de mouse son Display/Rotadas)
        if self.is_dragging and self.drag_start_point and self.drag_current_point:
            # Escalar coordenadas de mouse (label) a frame
            lbl_w = self.window.camera_left_label.width()
            lbl_h = self.window.camera_left_label.height()
            
            x1 = int(self.drag_start_point[0] * (w_disp / lbl_w))
            y1 = int(self.drag_start_point[1] * (h_disp / lbl_h))
            x2 = int(self.drag_current_point[0] * (w_disp / lbl_w))
            y2 = int(self.drag_current_point[1] * (h_disp / lbl_h))
            
            # Visual UX: Overlay transparente
            overlay = display.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
            cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
            
            # Borde sólido y esquinas
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Dibujar esquinas resaltadas
            for corner in [(x1,y1), (x2,y1), (x2,y2), (x1,y2)]:
                cv2.circle(display, corner, 4, (255, 255, 255), -1)
                
            # Texto flotante
            cv2.putText(display, f"{abs(x2-x1)}x{abs(y2-y1)}", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        # CASO B: Ya tenemos esquinas guardadas (Están en RAW, convertir a Display)
        elif self.table_corners:
            for i, pt in enumerate(self.table_corners):
                # Convertir RAW -> DISPLAY para dibujar en el lugar correcto
                disp_pt = StereoConfig.transform_point_for_display(pt, w, h)
                cv2.circle(display, disp_pt, 8, (0, 255, 0), -1)
                cv2.putText(display, str(i+1), (disp_pt[0]+10, disp_pt[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

        self.window.update_frames(frame_left=display)

    def _on_drag_started(self, camera_name, x, y):
        """Maneja el inicio del arrastre"""
        if self.current_phase != "table_definition":
            return
        if camera_name != "left":
            return
            
        self.is_dragging = True
        self.drag_start_point = (x, y)
        self.drag_current_point = (x, y)
        self.table_corners = []  # Limpiar esquinas previas
        self.window.set_status("🎯 Arrastrando... suelta para confirmar", "#FFFF00")
        print(f"[Drag] Iniciado en ({x}, {y})")
    
    def _on_drag_moved(self, camera_name, x, y):
        """Maneja el movimiento durante el arrastre"""
        if self.current_phase != "table_definition":
            return
        if camera_name != "left":
            return
        if not self.is_dragging:
            return
            
        self.drag_current_point = (x, y)
    
    def _on_drag_ended(self, camera_name, x, y):
        """Maneja el fin del arrastre - crea el rectángulo"""
        if self.current_phase != "table_definition": return
        if camera_name != "left": return
        if not self.is_dragging: return
        
        self.is_dragging = False
        self.drag_current_point = (x, y)
        
        # Obtener dimensiones
        lbl_w = self.window.camera_left_label.width()
        lbl_h = self.window.camera_left_label.height()
        
        # Resolución real
        frame_w, frame_h = self.resolution
        if self.cap_left:
            cw = self.cap_left.video_width
            ch = self.cap_left.video_height
            if cw > 0 and ch > 0:
                frame_w, frame_h = int(cw), int(ch)
        
        # 1. Obtener coordenadas en espacio DISPLAY (Rotado)
        x1_disp = int(self.drag_start_point[0] * (frame_w / lbl_w))
        y1_disp = int(self.drag_start_point[1] * (frame_h / lbl_h))
        x2_disp = int(self.drag_current_point[0] * (frame_w / lbl_w))
        y2_disp = int(self.drag_current_point[1] * (frame_h / lbl_h))
        
        # Ordenar coordenadas (min/max)
        left = min(x1_disp, x2_disp)
        right = max(x1_disp, x2_disp)
        top = min(y1_disp, y2_disp)
        bottom = max(y1_disp, y2_disp)
        
        # Definir las 4 esquinas en orden: TL, TR, BR, BL (en espacio Display)
        corners_display = [
            (left, top),      # TL
            (right, top),     # TR
            (right, bottom),  # BR
            (left, bottom)    # BL
        ]
        
        # 2. CONVERTIR A RAW (Invertir rotación) para guardar
        from ..vision.stereo_config import StereoConfig
        self.table_corners = []
        
        for pt in corners_display:
            # transform_point_for_display es simétrica para rotación 180
            # (Raw -> Display es igual que Display -> Raw)
            raw_pt = StereoConfig.transform_point_for_display(pt, frame_w, frame_h)
            self.table_corners.append(raw_pt)
            
        print(f"[Drag] Rectángulo definido (RAW): {self.table_corners}")
        
        # CAMBIO: Mostrar botón en lugar de usar Timer automático
        self.window.set_status("✅ Área definida. Presiona CONTINUAR para calibrar profundidad.", "#00FF00")
        self.window.show_continue_button(True)

    def _on_frame_clicked(self, camera_name, x, y):
        """Maneja el clic en el video (ya no usado en Fase 4, pero mantenido para compatibilidad)"""
        # En Fase 4 usamos drag, no clics individuales
        if self.current_phase == "table_definition":
            return  # Ignorar clics simples en fase 4
            
        if camera_name != "left":
            print("Por favor, marca en la cámara izquierda.")
            return


    def _finish_table_definition(self):
        """Finaliza la Fase 4A e inicia OBLIGATORIAMENTE la Fase 4B (Toque)"""
        if not self.table_corners or len(self.table_corners) < 4:
            self.window.set_status("⚠️ Error: Dibuja el rectángulo primero", "#FF0000")
            return

        print("\n[PLANO 3D] Zona definida. Iniciando Fase 4B (Toque manual)...")
        
        # Opcional: Intentar cálculo automático como respaldo
        try:
            # Puedes dejar aquí tu lógica de _find_corners_in_right_camera 
            # pero NO llames a _save_table_definition todavía.
            pass
        except:
            pass

        # Cambiamos el estado y saltamos a la calibración de profundidad por toque
        self.current_phase = "table_definition_complete"
        self._start_corner_depth_calibration()

    def _save_table_definition(self):
        """
        Guarda la definición de mesa en calibration.json.
        NUEVO: También triangula las esquinas para calcular el plano 3D.
        """
        # Obtener resolución real usada para la definición
        frame_w, frame_h = 1280, 720 # Valor por defecto seguro si todo falla
        if self.cap_left:
            cw = self.cap_left.video_width
            ch = self.cap_left.video_height
            if cw > 0 and ch > 0:
                frame_w, frame_h = int(cw), int(ch)
        
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Guardar definición básica 2D
            table_def = {
                'corners': self.table_corners,
                'camera': 'left',
                'resolution': [frame_w, frame_h]
            }
            
            # NUEVO: Calcular plano 3D usando las matrices de calibración (Fase 1 y 2)
            plane_coeffs = self._calculate_table_plane_3d() # <-- ¡DESCOMENTAR!
            # plane_coeffs = None
            
            if plane_coeffs is not None:
                table_def['plane_3d'] = {
                    'coefficients': list(plane_coeffs),
                    'description': 'Plano ax + by + cz + d = 0'
                }
                print(f"[AR] Plano 3D calculado: a={plane_coeffs[0]:.4f}, b={plane_coeffs[1]:.4f}, c={plane_coeffs[2]:.4f}, d={plane_coeffs[3]:.2f}")
            else:
                print("[AR] No se pudo calcular plano 3D - usando método de distancia fija")
            
            data['table_definition'] = table_def
            
            # IMPORTANTE: Preservar el flag cameras_swapped si ya existe
            if 'cameras_swapped' not in data:
                # Si no existe, intentar leerlo del archivo actual
                try:
                    with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f2:
                        existing_data = json.load(f2)
                        if 'cameras_swapped' in existing_data:
                            data['cameras_swapped'] = existing_data['cameras_swapped']
                            print(f"[INFO] Preservando cameras_swapped={existing_data['cameras_swapped']}")
                except:
                    pass
            
            with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"[AR] Definición de mesa guardada: {self.table_corners} (Res: {frame_w}x{frame_h})")
            
        except Exception as e:
            print(f"Error guardando mesa: {e}")
            import traceback
            traceback.print_exc()
            self.board_rows = 7
            self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM

    def _calculate_table_plane_3d(self):
        """
        Calcula el plano 3D de la mesa usando triangulación estéreo.
        
        Método:
        1. Captura frames de ambas cámaras
        2. Usa template matching para encontrar las esquinas en cámara derecha
        3. Triangula las 4 esquinas
        4. Calcula el plano que las contiene
        
        Returns:
            tuple: (a, b, c, d) coeficientes del plano, o None si falla
        """
        print("\n[PLANO 3D] Calculando plano de la mesa...")
        
        # Verificar que tenemos ambas cámaras
        if not self.cap_right:
            self.cap_right = self._get_or_create_camera("right")
        
        if not self.cap_left or not self.cap_right:
            print("  [ERROR] Cámaras no disponibles")
            return None
        
        # Capturar frames de ambas cámaras
        _, frame_left = self.cap_left.next(wait=0.1)
        _, frame_right = self.cap_right.next(wait=0.1)
        
        if frame_left is None or frame_right is None:
            print("  [ERROR] No se pudieron capturar frames")
            return None
        
        # Aplicar transformaciones de cámara (igual que en runtime)
        frame_left = StereoConfig.apply_camera_transforms(frame_left)
        frame_right = StereoConfig.apply_camera_transforms(frame_right)
        
        # Encontrar esquinas correspondientes en cámara derecha
        corners_right = self._find_corners_in_right_camera(frame_left, frame_right)
        
        if corners_right is None or len(corners_right) != 4:
            print("  [ERROR] No se encontraron correspondencias en cámara derecha")
            return None
        
        print(f"  [OK] Esquinas encontradas en cámara derecha: {corners_right}")
        
        # Cargar depth estimator para triangular
        try:
            depth_estimator = load_depth_estimator(str(CalibrationConfig.CALIBRATION_FILE))
        except Exception as e:
            print(f"  [ERROR] No se pudo cargar depth_estimator: {e}")
            return None
        
        # [BLOQUE CORREGIDO]
        # 1. Rectificar esquinas detectadas usando sus matrices originales
        rect_corners_L = [depth_estimator.rectify_point(p, is_left=True) for p in self.table_corners]
        rect_corners_R = [depth_estimator.rectify_point(p, is_left=False) for p in corners_right]
        
        # 2. Intercambiar para triangulación si es necesario
        if StereoConfig.CAMERAS_SWAPPED:
            pts_tri_L = rect_corners_R
            pts_tri_R = rect_corners_L
        else:
            pts_tri_L = rect_corners_L
            pts_tri_R = rect_corners_R
            
        # 3. Triangular (Ya están rectificados, pasamos directamente a simple)
        corners_3d = []
        for i in range(4):
            p3d = depth_estimator.triangulate_point_simple(pts_tri_L[i], pts_tri_R[i])
            if p3d is not None: corners_3d.append(p3d)
        
        if corners_3d is None:
            print("  [ERROR] Triangulación fallida")
            return None
        
        # Calcular plano
        plane_coeffs = depth_estimator.compute_table_plane(corners_3d)
        
        return plane_coeffs
    
    # ==================== FASE 4B: CALIBRACIÓN DE PROFUNDIDAD DE ESQUINAS ====================
    
    def _start_corner_depth_calibration(self):
        """Inicia la fase de calibración de profundidad en las 4 esquinas"""
        self.current_phase = "corner_depth_calibration"
        self.corner_depth_samples = {0: [], 1: [], 2: [], 3: []}  # Muestras por esquina
        self.current_corner_index = 0
        self.samples_per_corner = 30  # Número de muestras por esquina
        
        # Inicializar hand detector si no existe
        if self.hand_detector is None:
            self.hand_detector = HandDetector(
                mode=False,
                maxHands=1,
                detectionCon=0.7,
                trackCon=0.5
            )
        
        # --- CORRECCIÓN: FORZAR RECARGA DE CALIBRACIÓN NUEVA ---
        print("[INFO] Recargando calibración actualizada (Fase 3)...")
        try:
            # Siempre recargar para obtener la corrección guardada hace un momento
            self.depth_estimator = load_depth_estimator(str(CalibrationConfig.CALIBRATION_FILE))
            print(f"[INFO] Estimador recargado. Pendiente actual: {self.depth_estimator.depth_slope:.4f}")
            print(f"[INFO] Intercept actual: {self.depth_estimator.depth_intercept:.4f}")
        except Exception as e:
            print(f"[ERROR] No se pudo cargar depth_estimator: {e}")
            self.window.set_status(f"⚠️ Error cargando calibración: {e}", "#FF0000")
            # self._finish_calibration_without_4b() # NO SALTAR la fase si hay error
            return
        # -------------------------------------------------------
        
        # Asegurar cámara derecha activa
        if not self.cap_right or not self.cap_right.is_available():
            self.cap_right = self._get_or_create_camera("right")
        
        self._show_corner_instructions()
        self.timer.start(33)
    
    def _show_corner_instructions(self):
        """Muestra instrucciones para la esquina actual"""
        corner_names = ["Superior-Izquierda", "Superior-Derecha", "Inferior-Derecha", "Inferior-Izquierda"]
        corner_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
        
        self.window.show_intro_screen(
            f"FASE 4B: Calibración de Esquina {self.current_corner_index + 1}/4",
            [
                f"<b>📍 Esquina: {corner_names[self.current_corner_index]}</b>",
                "",
                f"<span style='color:{corner_colors[self.current_corner_index]}'>●</span> Un círculo marca la esquina en el video",
                "",
                "👆 <b>Toca la esquina con tu dedo índice</b>",
                "",
                "📊 Mantén el dedo quieto mientras se recogen muestras",
                "",
                f"Muestras: 0 / {self.samples_per_corner}",
                "",
                "El sistema medirá automáticamente la profundidad."
            ]
        )
        
        self.window.set_status(f"👆 Toca la esquina {corner_names[self.current_corner_index]} con tu dedo", "#00C8FF")
    
    def _update_corner_depth_frame(self):
        """Actualiza el frame durante la calibración de esquinas"""
        if not self.cap_left or not self.cap_right:
            return
            
        try:
            # 1. Obtener frames CRUDOS
            _, frame_left_raw = self.cap_left.next(wait=0.033)
            _, frame_right_raw = self.cap_right.next(wait=0.033)
            
            if frame_left_raw is None or frame_right_raw is None:
                return

            from ..vision.stereo_config import StereoConfig
            h, w = frame_left_raw.shape[:2]

            # 2. Generar frames DISPLAY (Rotados 180) para visualización y DETECCIÓN
            # MediaPipe funciona mucho mejor con manos "derechas" (dedos hacia arriba)
            display_left = StereoConfig.apply_display_transform(frame_left_raw.copy())
            display_right = StereoConfig.apply_display_transform(frame_right_raw.copy())
            
            # Visual UX: Dibujar camino recorrido (Líneas entre esquinas)
            if self.current_corner_index > 0:
                for i in range(self.current_corner_index):
                    # Obtener puntos consecutivos
                    p1_raw = self.table_corners[i]
                    p2_raw = self.table_corners[i+1] # Siempre existe porque corners tiene 4 ptos
                    
                    # Transformar a display
                    p1_disp = StereoConfig.transform_point_for_display(p1_raw, w, h)
                    p2_disp = StereoConfig.transform_point_for_display(p2_raw, w, h)
                    
                    # Dibujar línea
                    if i == self.current_corner_index - 1:
                         # Último tramo hacia el objetivo actual: Amarillo/Pulsante
                         cv2.line(display_left, p1_disp, p2_disp, (0, 255, 255), 2)
                    else:
                         # Tramos completados: Verde
                         cv2.line(display_left, p1_disp, p2_disp, (0, 255, 0), 2)

            # 3. Dibujar objetivo (Círculo amarillo PULSANTE y PROGRESO)
            # Convertir coordenada de la esquina (RAW) a DISPLAY
            corner_raw = self.table_corners[self.current_corner_index]
            corner_disp = StereoConfig.transform_point_for_display(corner_raw, w, h)
            
            # Calcular pulso
            pulse = abs(np.sin(time.time() * 5))
            radius = int(12 + (pulse * 3))
            
            # Color base (Amarillo)
            color_target = (0, 255, 255) 
            
            # Dibujar anillo de progreso
            count = len(self.corner_depth_samples[self.current_corner_index])
            total = self.samples_per_corner
            
            # Anillo de fondo (Gris)
            cv2.circle(display_left, corner_disp, 22, (100, 100, 100), 3)
            
            # Anillo de progreso (Verde)
            if total > 0:
                angle = int((count / total) * 360)
                # Dibujar arco
                cv2.ellipse(display_left, corner_disp, (22, 22), -90, 0, angle, (0, 255, 0), 3)
            
            # Dibujar target pulsante
            cv2.circle(display_left, corner_disp, radius, color_target, 2)
            cv2.circle(display_left, corner_disp, 3, color_target, -1)
            
            # 4. Detectar mano en DISPLAY (para dibujar feedback visual)
            self.hand_detector.findHands(display_left)
            # Usamos drawHands y acceso directo en lugar de findPosition
            self.hand_detector.drawHands(display_left)
            
            pt_left_display = None
            lm_display = None
            if self.hand_detector.results.multi_hand_landmarks:
                 lm_display = self.hand_detector.results.multi_hand_landmarks[0]
                 
            if lm_display:
                # Obtener índice (8)
                idx = lm_display.landmark[8]
                h_disp, w_disp = display_left.shape[:2]
                pt_left_display = (int(idx.x * w_disp), int(idx.y * h_disp))
                
                # Dibujar punta
                cv2.circle(display_left, pt_left_display, 8, (0, 0, 255), -1)
                
                # Calcular distancia visual al objetivo
                distance_to_corner = np.hypot(pt_left_display[0] - corner_disp[0], pt_left_display[1] - corner_disp[1])
            else:
                distance_to_corner = 999

            # 5. Detectar mano en CÁMARA DERECHA (Display)
            # Usar display frame también para asegurar consistencia
            if not hasattr(self, 'hand_detector_right') or self.hand_detector_right is None:
                from ..vision.hand_detector import HandDetector
                self.hand_detector_right = HandDetector(maxHands=1, detectionCon=0.5)
                
            self.hand_detector_right.findHands(display_right)
            pt_right_display = None
            if self.hand_detector_right.results.multi_hand_landmarks:
                 lm_right_display = self.hand_detector_right.results.multi_hand_landmarks[0]
                 idx_R = lm_right_display.landmark[8]
                 h_disp, w_disp = display_right.shape[:2]
                 pt_right_display = (int(idx_R.x * w_disp), int(idx_R.y * h_disp))

            # 6. Lógica de Medición (Transformar DISPLAY -> RAW)
            if pt_left_display and pt_right_display and distance_to_corner < 60:
                # A. Invertir rotación para volver al espacio del sensor (Raw)
                pt_L_raw = StereoConfig.transform_point_for_display(pt_left_display, w, h)
                pt_R_raw = StereoConfig.transform_point_for_display(pt_right_display, w, h)
                
                # B. RECTIFICAR PRIMERO (Cada sensor con su propia matriz K/D)
                # Sensor Left (ID 1) usa is_left=True, Sensor Right (ID 2) usa is_left=False
                rect_L_clean = self.depth_estimator.rectify_point(pt_L_raw, is_left=True)
                rect_R_clean = self.depth_estimator.rectify_point(pt_R_raw, is_left=False)
                
                # C. AHORA SWAP para la triangulación
                # Si están cruzadas, la cámara derecha (ID 2) es la "izquierda" matemática
                if StereoConfig.CAMERAS_SWAPPED:
                    pt_for_tri_L = rect_R_clean # ID 2 rectificado
                    pt_for_tri_R = rect_L_clean # ID 1 rectificado
                else:
                    pt_for_tri_L = rect_L_clean
                    pt_for_tri_R = rect_R_clean
                    
                # D. TRIANGULAR
                # Ahora usamos triangulate_point_simple que espera puntos YA rectificados
                depth_pt = self.depth_estimator.triangulate_point_simple(pt_for_tri_L, pt_for_tri_R)
                
                if depth_pt:
                     self.corner_depth_samples[self.current_corner_index].append(depth_pt[2]) # Guarda SOLO Z (Profundidad)
                     self.window.set_status(f"Capturando muestra {count}/{total}...", "#00FF00")
            
            # Avanzar si completamos muestras
            if len(self.corner_depth_samples[self.current_corner_index]) >= self.samples_per_corner:
                self.current_corner_index += 1
                if self.current_corner_index >= 4:
                     self._finish_corner_depth_calibration()
                else:
                     self._show_corner_instructions()

            self.window.update_frames(frame_left=display_left, frame_right=display_right)

        except Exception as e:
            print(f"[ERROR UI Loop] {e}")
            # NO detener timer, solo loguear error para evitar freeze
            pass

    
    def _advance_to_next_corner(self):
        """Avanza a la siguiente esquina o finaliza"""
        self.current_corner_index += 1
        
        if self.current_corner_index >= 4:
            # Todas las esquinas calibradas
            self._finish_corner_depth_calibration()
        else:
            # Mostrar instrucciones para la siguiente esquina
            self._show_corner_instructions()
    
    def _finish_corner_depth_calibration(self):
        """Finaliza la Fase 4B: Calcula el PLANO MATEMÁTICO 3D"""
        self.timer.stop()
        
        corner_depths = []
        corners_3d = []
        
        print("\n[AR] Calculando geometría de la mesa...")
        
        for i in range(4):
            samples = self.corner_depth_samples[i]
            if samples:
                # 1. Obtener profundidad promedio medida
                avg_depth = float(np.median(samples))
                corner_depths.append(round(avg_depth, 1))
                
                # 2. Recuperar la coordenada 2D de esa esquina (de Fase 4)
                pixel_x, pixel_y = self.table_corners[i]
                
                # 3. Convertir a punto 3D real (X, Y, Z)
                point_3d = self.depth_estimator.pixel_to_point_3d(pixel_x, pixel_y, avg_depth)
                
                if point_3d:
                    corners_3d.append(point_3d)
                    print(f"  📍 Esquina {i}: 2D({pixel_x}, {pixel_y}) + Z({avg_depth:.1f}) -> 3D{point_3d}")
            else:
                # Fallback
                fallback = self.depth_estimator.keyboard_distance_cm or 41.0
                corner_depths.append(fallback)
        
        # 4. Calcular el Plano Matemático (ax + by + cz + d = 0)
        plane_coeffs = None
        if len(corners_3d) >= 3:
            plane_coeffs = self.depth_estimator.compute_table_plane(corners_3d)
        
        # 5. Guardar todo en el JSON
        self._save_ar_calibration(corner_depths, plane_coeffs)
        
        # Mostrar resumen
        msg = ["✅ Mesa 3D calibrada exitosamente", ""]
        if plane_coeffs:
            a, b, c, d = plane_coeffs
            msg.append(f"📐 Plano detectado: {a:.2f}x + {b:.2f}y + {c:.2f}z + {d:.1f} = 0")
            msg.append("🎹 El piano se ajustará a la inclinación de tu mesa.")
        else:
            msg.append("⚠️ No se pudo calcular el plano (usando modo plano simple).")
            
        self.window.show_intro_screen("¡CALIBRACIÓN AR COMPLETA!", msg)
        self.window.set_status("✅ Calibración AR lista", "#00FF00")
        self.window.show_continue_button(True)
        self.current_phase = "phase4b_complete"
    
    def _save_ar_calibration(self, corner_depths, plane_coeffs):
        """Guarda los datos avanzados de AR en el JSON"""
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            if 'table_definition' not in data:
                data['table_definition'] = {}
                
            # Guardar profundidades simples
            data['table_definition']['corner_depths'] = corner_depths
            
            # Guardar el plano matemático
            if plane_coeffs:
                data['table_definition']['plane_3d'] = {
                    'coefficients': list(plane_coeffs),
                    'description': "Plano ax + by + cz + d = 0 generado por toque"
                }
            
            # Preservar flags importantes
            # Cargar de nuevo para evitar modificar el 'data' actual si 'cameras_swapped' no existe
            # y luego intentar leerlo de un archivo que podría no tenerlo.
            # Mejor: cargar el original y luego mergear.
            original_data = {}
            try:
                with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f_orig:
                    original_data = json.load(f_orig)
            except FileNotFoundError:
                pass # File might not exist yet
            except json.JSONDecodeError:
                pass # File might be empty or malformed
            
            if 'cameras_swapped' in original_data:
                 data['cameras_swapped'] = original_data['cameras_swapped']
                 
            with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            print("[OK] Datos AR guardados en calibration.json")
            
        except Exception as e:
            print(f"[ERROR] Al guardar AR: {e}")
    
    def _save_corner_depths(self, corner_depths):
        """Guarda las profundidades de esquinas en calibration.json"""
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            if 'table_definition' not in data:
                data['table_definition'] = {}
            
            data['table_definition']['corner_depths'] = corner_depths
            
            # IMPORTANTE: Preservar el flag cameras_swapped si ya existe
            if 'cameras_swapped' not in data:
                try:
                    with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f2:
                        existing_data = json.load(f2)
                        if 'cameras_swapped' in existing_data:
                            data['cameras_swapped'] = existing_data['cameras_swapped']
                            print(f"[INFO] Preservando cameras_swapped={existing_data['cameras_swapped']}")
                except:
                    pass
            
            with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"[4B] Corner depths guardados: {corner_depths}")
            
        except Exception as e:
            print(f"[4B] Error guardando corner_depths: {e}")
    
    def _finish_calibration_without_4b(self):
        """Finaliza calibración sin Fase 4B (fallback)"""
        self.timer.stop()
        self.window.show_intro_screen(
            "¡CALIBRACIÓN FINALIZADA!",
            [
                "✅ Has completado las fases principales.",
                "",
                "⚠️ La Fase 4B no pudo completarse.",
                "   Se usará distancia fija para la detección.",
                "",
                "🎹 Tu piano virtual está listo.",
                "",
                "Presiona <b>Continuar</b> para comenzar a tocar."
            ]
        )
        self.window.show_continue_button(True)
        self.current_phase = "complete"
    
    def _find_corners_in_right_camera(self, frame_left, frame_right):
        """
        Encuentra las esquinas del rectángulo en la cámara derecha.
        Usa template matching con búsqueda amplia en AMBAS direcciones.
        
        Args:
            frame_left: Frame de cámara izquierda
            frame_right: Frame de cámara derecha
            
        Returns:
            list: 4 puntos (x, y) en cámara derecha, o None si falla
        """
        corners_right = []
        
        # Parámetros de búsqueda MÁS AMPLIOS
        template_size = 100  # píxeles - template más grande
        search_range = 250   # Rango de búsqueda horizontal AMPLIO
        
        gray_left = cv2.cvtColor(frame_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(frame_right, cv2.COLOR_BGR2GRAY)
        
        # Aplicar ecualización de histograma para mejorar contraste
        gray_left = cv2.equalizeHist(gray_left)
        gray_right = cv2.equalizeHist(gray_right)
        
        h, w = gray_left.shape
        
        print(f"  [DEBUG] Buscando correspondencias (template={template_size}px, range={search_range}px)")
        
        for i, corner in enumerate(self.table_corners):
            x_l, y_l = corner
            
            # Extraer template de la cámara izquierda
            half = template_size // 2
            x1 = max(0, x_l - half)
            y1 = max(0, y_l - half)
            x2 = min(w, x_l + half)
            y2 = min(h, y_l + half)
            
            template = gray_left[y1:y2, x1:x2]
            
            if template.size == 0 or template.shape[0] < 20 or template.shape[1] < 20:
                print(f"  [WARN] Template muy pequeño o vacío para esquina {i}")
                return None
            
            # BÚSQUEDA AMPLIA: Buscar en AMBAS direcciones horizontalmente
            # Esto funciona independientemente de si las cámaras están swapped
            search_x1 = max(0, x_l - search_range - half)
            search_x2 = min(w, x_l + search_range + half)
            search_y1 = max(0, y_l - half - 50)  # Margen vertical aumentado
            search_y2 = min(h, y_l + half + 50)
            
            search_region = gray_right[search_y1:search_y2, search_x1:search_x2]
            
            if search_region.shape[0] < template.shape[0] or search_region.shape[1] < template.shape[1]:
                print(f"  [WARN] Región de búsqueda muy pequeña para esquina {i}")
                # Intentar con toda la imagen
                search_region = gray_right
                search_x1, search_y1 = 0, 0
            
            # Template matching con múltiples métodos
            best_val = -1
            best_loc = None
            
            for method in [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]:
                result = cv2.matchTemplate(search_region, template, method)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_val:
                    best_val = max_val
                    best_loc = max_loc
            
            if best_val < 0.3:  # Umbral de confianza muy bajo
                print(f"  [WARN] Muy baja confianza ({best_val:.2f}) para esquina {i} - intentando ORB")
                # Fallback: usar ORB features
                orb_result = self._find_corner_with_orb(gray_left, gray_right, (x_l, y_l), template_size)
                if orb_result:
                    x_r, y_r = orb_result
                    disparity = x_l - x_r
                    print(f"  Esquina {i} (ORB): L=({x_l},{y_l}) -> R=({x_r},{y_r}), disp={disparity}")
                    corners_right.append((x_r, y_r))
                    continue
                else:
                    print(f"  [ERROR] No se pudo encontrar esquina {i}")
                    return None
            
            # Convertir ubicación local a global
            x_r = search_x1 + best_loc[0] + half
            y_r = search_y1 + best_loc[1] + half
            
            # Validar que está dentro de la imagen
            x_r = max(0, min(w-1, x_r))
            y_r = max(0, min(h-1, y_r))
            
            disparity = x_l - x_r
            print(f"  Esquina {i}: L=({x_l},{y_l}) -> R=({x_r},{y_r}), disp={disparity}, conf={best_val:.2f}")
            
            corners_right.append((x_r, y_r))
        
        return corners_right
    
    def _find_corner_with_orb(self, gray_left, gray_right, corner_left, region_size):
        """
        Usa ORB features para encontrar correspondencia de una esquina.
        
        Args:
            gray_left: Imagen izquierda en escala de grises
            gray_right: Imagen derecha en escala de grises
            corner_left: (x, y) de la esquina en imagen izquierda
            region_size: Tamaño de la región a analizar
            
        Returns:
            tuple: (x, y) en imagen derecha, o None si falla
        """
        x_l, y_l = corner_left
        half = region_size // 2
        h, w = gray_left.shape
        
        # Extraer regiones
        x1 = max(0, x_l - half)
        y1 = max(0, y_l - half)
        x2 = min(w, x_l + half)
        y2 = min(h, y_l + half)
        
        region_left = gray_left[y1:y2, x1:x2]
        
        # Región más amplia en la derecha
        search_x1 = max(0, x_l - 300)
        search_x2 = min(w, x_l + 300)
        region_right = gray_right[y1:y2, search_x1:search_x2]
        
        if region_left.size == 0 or region_right.size == 0:
            return None
        
        # Crear detector ORB
        orb = cv2.ORB_create(nfeatures=500)
        
        # Detectar keypoints y descriptores
        kp1, des1 = orb.detectAndCompute(region_left, None)
        kp2, des2 = orb.detectAndCompute(region_right, None)
        
        if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
            return None
        
        # Matching
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        
        if len(matches) < 3:
            return None
        
        # Ordenar por distancia
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Usar los mejores matches para estimar el desplazamiento
        dx_list = []
        for m in matches[:10]:
            pt1 = kp1[m.queryIdx].pt
            pt2 = kp2[m.trainIdx].pt
            dx = pt2[0] - pt1[0]  # Diferencia en X
            dx_list.append(dx)
        
        if len(dx_list) == 0:
            return None
        
        # Mediana del desplazamiento (más robusto a outliers)
        median_dx = np.median(dx_list)
        
        # Calcular posición en imagen derecha
        # El centro del template en imagen izquierda está en (half, half) de la región
        # En la región derecha, está desplazado por median_dx
        x_r = search_x1 + half + int(median_dx)
        y_r = y_l  # Asumimos misma Y (línea epipolar)
        
        return (x_r, y_r)
    
    def _save_phase1_only(self):
        """Guarda solo Fase 1"""
        self.calibration_data = {
            'version': '2.0',
            'board_config': {
                'cols': self.board_cols,
                'rows': self.board_rows,
                'square_size_mm': self.square_size_mm
            },
            'left_camera': self.calibrator_left.get_calibration_data(),
            'right_camera': self.calibrator_right.get_calibration_data(),
            'stereo': None,
            'camera_ids': {
                'left': self.cam_left_id,
                'right': self.cam_right_id
            },
            # Guardar los IDs originales de calibración
            'calibration_camera_ids': {
                'left': self.cam_left_id,
                'right': self.cam_right_id
            },
            'resolution': {
                'width': self.resolution[0],
                'height': self.resolution[1]
            },
            # Campo para indicar si las cámaras deben intercambiarse
            'swap_cameras': False  # Por defecto no intercambiar
        }
        
        with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n[OK] Fase 1 guardada")
    
    def _compile_calibration_data(self):
        """Recopila todos los datos de calibración"""
        stereo_data = self.stereo_calibrator.get_calibration_data()
        left_camera_data = self.calibrator_left.get_calibration_data()
        right_camera_data = self.calibrator_right.get_calibration_data()
        
        # Agregar transformaciones al mundo
        if stereo_data and 'rotation_matrix' in stereo_data:
            left_camera_data['world_rotation'] = [[1.0, 0.0, 0.0],
                                                   [0.0, 1.0, 0.0],
                                                   [0.0, 0.0, 1.0]]
            left_camera_data['world_translation'] = [[0.0], [0.0], [0.0]]
            
            right_camera_data['world_rotation'] = stereo_data['rotation_matrix']
            right_camera_data['world_translation'] = stereo_data['translation_vector']
        
        self.calibration_data = {
            'version': '2.0',
            'board_config': {
                'cols': self.board_cols,
                'rows': self.board_rows,
                'square_size_mm': self.square_size_mm
            },
            'left_camera': left_camera_data,
            'right_camera': right_camera_data,
            'stereo': stereo_data,
            'camera_ids': {
                'left': self.cam_left_id,
                'right': self.cam_right_id
            },
            # Guardar los IDs originales de calibración para detectar inversiones futuras
            'calibration_camera_ids': {
                'left': self.cam_left_id,
                'right': self.cam_right_id
            },
            'resolution': {
                'width': self.resolution[0],
                'height': self.resolution[1]
            }
        }
    
    def _save_calibration(self):
        """Guarda calibración completa"""
        output_file = CalibrationConfig.CALIBRATION_FILE
        
        # IMPORTANTE: Preservar el flag cameras_swapped y swap_cameras si ya existe
        cameras_swapped_value = None
        swap_cameras_value = None
        try:
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    existing_data = json.load(f)
                    if 'cameras_swapped' in existing_data:
                        cameras_swapped_value = existing_data['cameras_swapped']
                        print(f"[INFO] Preservando cameras_swapped={cameras_swapped_value}")
                    if 'swap_cameras' in existing_data:
                        swap_cameras_value = existing_data['swap_cameras']
                        print(f"[INFO] Preservando swap_cameras={swap_cameras_value}")
        except Exception as e:
            print(f"[WARN] No se pudo leer flags del archivo existente: {e}")
        
        # Agregar los flags preservados al nuevo archivo
        if cameras_swapped_value is not None:
            self.calibration_data['cameras_swapped'] = cameras_swapped_value
        if swap_cameras_value is not None:
            self.calibration_data['swap_cameras'] = swap_cameras_value
        elif 'swap_cameras' not in self.calibration_data:
            # Si no existe, agregar con valor por defecto
            self.calibration_data['swap_cameras'] = False
        
        with open(output_file, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n[OK] Calibracion guardada en: {output_file}")

    # ==================== FASE 4C: NIVELACIÓN DE TECLAS ====================
    def _start_key_depth_calibration(self):
        """FASE 4C: Calibración tecla por tecla con Perspectiva Correcta"""
        self.current_phase = "key_depth_calibration"
        
        instructions = [
            "<b>🎹 FASE FINAL: NIVELACIÓN DE TECLAS</b>",
            "El sistema necesita aprender la altura exacta de cada tecla.",
            "",
            "1. Pasa tu dedo presionando <b>FIRMEMENTE</b> tecla por tecla.",
            "2. Asegúrate de tocar también las <b>TECLAS NEGRAS</b>.",
            "3. Las teclas se pondrán <span style='color:#00FF00'>VERDES</span> al quedar calibradas.",
            "4. Pulsa <b>Continuar</b> cuando hayas barrido todo el piano."
        ]
        
        self.window.show_intro_screen("NIVELACIÓN DE TECLAS", instructions)
        self.window.show_continue_button(True)
        
        self.temp_key_readings = {} 
        
        # --- CORRECCIÓN DE PERSPECTIVA ---
        if hasattr(self, 'table_corners') and len(self.table_corners) == 4:
            # 1. Obtener dimensiones
            h, w = 720, 1280 
            if self.cap_left:
                w, h = int(self.cap_left.video_width), int(self.cap_left.video_height)
            
            # 2. Transformar esquinas a espacio de pantalla (Display)
            corners_display = [
                StereoConfig.transform_point_for_display(pt, w, h) 
                for pt in self.table_corners
            ]
            
            # 3. Inicializar teclado
            n_white_keys = 14  # Default: 2 octavas
            if hasattr(self, 'keyboard_mapper') and self.keyboard_mapper:
                n_white_keys = getattr(self.keyboard_mapper, 'kb_white_n_keys', 14)
            
            self.viz_keyboard = VirtualKeyboard(w, h, n_white_keys)
            
            # 4. CALCULAR MATRIZ DE PERSPECTIVA (La clave para que las negras funcionen)
            # Definimos el rectángulo lógico plano
            src_pts = np.float32([
                [self.viz_keyboard.kb_x0, self.viz_keyboard.kb_y0],
                [self.viz_keyboard.kb_x1, self.viz_keyboard.kb_y0],
                [self.viz_keyboard.kb_x1, self.viz_keyboard.kb_y1],
                [self.viz_keyboard.kb_x0, self.viz_keyboard.kb_y1]
            ])
            dst_pts = np.float32(corners_display)
            
            # Calcular matriz
            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            
            # Inyectar matriz en el teclado para que 'find_key' funcione con perspectiva
            self.viz_keyboard.M_inv = np.linalg.inv(matrix)
            self.viz_keyboard.ar_mode_active = True
            
            # 5. PRE-CALCULAR POLÍGONOS VISUALES (Para dibujar correctamente)
            self.viz_keyboard.screen_key_polygons = []
            logical_geoms = self.viz_keyboard.generate_logical_key_geometries()
            
            for key_geom in logical_geoms:
                pts_src = key_geom['pts']
                # Proyectar puntos lógicos a pantalla usando la matriz
                pts_dst = cv2.perspectiveTransform(pts_src, matrix)[0]
                
                self.viz_keyboard.screen_key_polygons.append({
                    'id': key_geom['id'],
                    'black': key_geom['black'],
                    'contour': pts_dst.astype(np.int32)
                })
            
            print(f"[Phase 4C] Piano con perspectiva: {len(self.viz_keyboard.screen_key_polygons)} teclas")
        else:
            print("[ERROR] No hay esquinas definidas")
            self.viz_keyboard = None
        
        # Reiniciar cámaras y timer
        if not self.cap_left: self.cap_left = self._get_or_create_camera("left")
        if not self.cap_right: self.cap_right = self._get_or_create_camera("right")
        
        if self.timer.isActive(): self.timer.stop()
        self.timer.start(30)

    def _update_key_depth_frame(self):
        """Loop de calibración con visualización AR precisa"""
        if self.current_phase != "key_depth_calibration": return
        if not self.cap_left or not self.cap_right: return

        _, frame_l = self.cap_left.next(wait=0.001)
        _, frame_r = self.cap_right.next(wait=0.001)
        if frame_l is None: return

        # Transformaciones
        display_l = StereoConfig.apply_display_transform(frame_l.copy())
        display_r = StereoConfig.apply_display_transform(frame_r.copy()) if frame_r is not None else None
        overlay = display_l.copy()

        # Detección de manos
        self.hand_detector.findHands(display_l)
        if self.hand_detector_right is None:
            from ..vision.hand_detector import HandDetector
            self.hand_detector_right = HandDetector(maxHands=1)
        if display_r is not None:
            self.hand_detector_right.findHands(display_r)
        
        # Lógica de calibración
        current_key_id = -1
        h, w = display_l.shape[:2]
        
        # Necesitamos manos en ambas cámaras para triangular Z
        l_res = self.hand_detector.results.multi_hand_landmarks
        r_res = self.hand_detector_right.results.multi_hand_landmarks if display_r is not None else None
        
        if l_res and r_res:
            try:
                # Dedo índice (8)
                idx_l = l_res[0].landmark[8]
                idx_r = r_res[0].landmark[8]
                
                # Coordenadas pantalla
                xl, yl = int(idx_l.x * w), int(idx_l.y * h)
                xr, yr = int(idx_r.x * w), int(idx_r.y * h)
                
                # 1. TRIANGULAR Z (Profundidad)
                # Volver a RAW para cálculo preciso
                raw_l = StereoConfig.transform_point_for_display((xl, yl), w, h)
                raw_r = StereoConfig.transform_point_for_display((xr, yr), w, h)
                
                rect_l = self.depth_estimator.rectify_point(raw_l, is_left=True)
                rect_r = self.depth_estimator.rectify_point(raw_r, is_left=False)
                
                if StereoConfig.CAMERAS_SWAPPED:
                    p3d = self.depth_estimator.triangulate_point_simple(rect_r, rect_l)
                else:
                    p3d = self.depth_estimator.triangulate_point_simple(rect_l, rect_r)
                
                z_cm = p3d[2] if p3d else 0
                
                # --- DEBUG: Mostrar coordenadas al lado del dedo ---
                coords_text = f"X:{xl} Y:{yl} Z:{z_cm:.2f}cm"
                # Sombra negra (para leer mejor)
                cv2.putText(display_l, coords_text, (xl + 16, yl - 14), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
                # Texto amarillo
                cv2.putText(display_l, coords_text, (xl + 15, yl - 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                # ---------------------------------------------------
                
                # 2. DETECTAR TECLA (Usando la matriz de perspectiva corregida)
                if self.viz_keyboard:
                    # find_key usa internamente M_inv que definimos en _start
                    current_key_id = self.viz_keyboard.find_key(xl, yl)
                    
                    if current_key_id is not None and current_key_id >= 0:
                        if current_key_id not in self.temp_key_readings:
                            self.temp_key_readings[current_key_id] = []
                        
                        # Guardar lectura (filtro simple)
                        if -10 < z_cm < 50:
                            self.temp_key_readings[current_key_id].append(z_cm)
                        
                        # Feedback: Círculo en el dedo
                        cv2.circle(display_l, (xl, yl), 8, (0, 255, 255), -1)

            except Exception as e:
                pass

        # DIBUJAR PIANO AR (Usando los polígonos pre-calculados)
        if self.viz_keyboard and hasattr(self.viz_keyboard, 'screen_key_polygons'):
            for poly in self.viz_keyboard.screen_key_polygons:
                kid = poly['id']
                pts = poly['contour']
                
                # Color logic
                if kid in self.temp_key_readings and len(self.temp_key_readings[kid]) > 5:
                    color = (0, 255, 0)  # Verde (Listo)
                elif kid == current_key_id:
                    color = (0, 165, 255)  # Naranja (Tocando)
                else:
                    color = (0, 0, 0) if poly['black'] else (255, 255, 255)  # Negro/Blanco
                
                cv2.fillPoly(overlay, [pts], color)
                cv2.polylines(display_l, [pts], True, (100, 100, 100), 1)

            # Aplicar transparencia
            cv2.addWeighted(overlay, 0.5, display_l, 0.5, 0, display_l)
            
            # Info
            total_keys = len(self.viz_keyboard.screen_key_polygons)
            calibrated = len([k for k, v in self.temp_key_readings.items() if len(v) > 5])
            cv2.rectangle(display_l, (20, 20), (350, 70), (0, 0, 0), -1)
            cv2.putText(display_l, f"Calibradas: {calibrated}/{total_keys}", (30, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            self.window.set_status(f"Progreso: {calibrated} teclas listas.", "#FFFF00")

        self.window.update_frames(frame_left=display_l)

    def _finish_key_calibration(self):
        """Finaliza la calibración de teclas y guarda los datos"""
        print("Procesando calibración de teclas...")
        final_floors = {}
        
        # Promediar lecturas
        for key_id, readings in self.temp_key_readings.items():
            if len(readings) > 3:  # Mínimo de muestras
                sorted_r = sorted(readings)
                n_samples = max(1, int(len(sorted_r) * 0.2))
                deepest = sorted_r[-n_samples:] 
                avg_floor = sum(deepest) / len(deepest)
                
                final_floors[int(key_id)] = avg_floor
        
        # Guardar en config GLOBAL (clase)
        from .calibration_config import CalibrationConfig
        CalibrationConfig.key_floors = final_floors
        CalibrationConfig.save_key_floors()
        
        print(f"¡Nivelación guardada! {len(final_floors)} teclas calibradas.")
        
        # Finalizar todo
        self._finish_calibration(True)


def run_qt_calibration(cam_left_id=1, cam_right_id=2):
    """
    Función para ejecutar calibración con PyQt6
    
    Args:
        cam_left_id: ID de cámara izquierda
        cam_right_id: ID de cámara derecha
    
    Returns:
        bool: True si fue exitosa
    """
    from PyQt6.QtCore import QEventLoop
    
    # Reutilizar QApplication existente si ya hay una
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    print("[DEBUG] Creando QtCalibrationManager...")
    
    manager = QtCalibrationManager(
        cam_left_id=cam_left_id,
        cam_right_id=cam_right_id,
        resolution=(1280, 720)
    )
    
    # Variable para capturar resultado
    result = [False]
    finished_flag = [False]
    
    def on_finished(success):
        print(f"[DEBUG] Calibración terminada con resultado: {success}")
        result[0] = success
        finished_flag[0] = True
    
    manager.finished.connect(on_finished)
    
    print("[DEBUG] Ejecutando run_calibration()...")
    
    # Iniciar calibración
    manager.run_calibration()
    
    # Si ya terminó (usuario canceló el diálogo de configuración), retornar
    if finished_flag[0]:
        print("[DEBUG] Calibración terminó inmediatamente (diálogo cancelado)")
        return result[0]
    
    print("[DEBUG] Entrando en event loop local...")
    
    # Usar un event loop local que no afecte la app principal
    loop = QEventLoop()
    
    def exit_loop(success):
        loop.quit()
    
    manager.finished.connect(exit_loop)
    loop.exec()
    
    # IMPORTANTE: Procesar eventos pendientes para asegurar que la ventana se cierre visualmente
    # antes de retornar al bloqueante main.py
    print("[DEBUG] Event loop terminado, procesando eventos de cierre...")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()
    
    print(f"[DEBUG] Retornando resultado: {result[0]}")
    
    return result[0]


if __name__ == '__main__':
    print("\n" + "="*70)
    print("CALIBRACIÓN ESTEREOSCÓPICA CON PYQT6")
    print("="*70)
    
    success = run_qt_calibration(cam_left_id=1, cam_right_id=2)
    
    if success:
        print("\n ¡Calibración completa exitosa!")
    else:
        print("\nLa calibración no se completó.")

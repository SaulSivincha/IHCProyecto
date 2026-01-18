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
        print(f"  📷 Creando VideoThread para cámara {camera_name} (ID: {camera_id})...")
        
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
            print(f"  ✗ Error al abrir cámara {camera_id}")
            return None
        
        # Iniciar thread de captura
        video_thread.start()
        print(f"  ✓ VideoThread iniciado para cámara {camera_name}")
        
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
            print(f"✓ Configuración: {new_cols}x{new_rows}, {new_size_mm}mm - Iniciando en Fase {selected_phase}")

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
        if selected_phase == 3:
            print("\n✓ Iniciando directamente en Fase 3...")
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
                    print("✗ Error al cargar Fase 2, volviendo a Fase 1")
                    self._start_intro()
            else:
                print("✗ Error al cargar Fase 1, volviendo a Fase 1")
                self._start_intro()
        elif selected_phase == 2:
            print("\n✓ Iniciando directamente en Fase 2...")
            
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
                    print("✓ Calibración previa de Fase 1 válida. Iniciando Fase 2...")
                    # Reiniciar timer y estado por seguridad
                    if self.timer.isActive():
                        self.timer.stop()
                    self.current_phase = None
                    self._start_phase2()
                else:
                    print("✗ Calibración previa de Fase 1 incompleta o inválida. Volviendo a Fase 1.")
                    self.window.set_status("No se encontró calibración previa válida de Fase 1. Debes completarla antes de Fase 2.", "#FF0000")
                    self._start_intro()
            else:
                print("✗ Error al cargar datos previos, volviendo a Fase 1")
                self.window.set_status("Error al cargar calibración previa. Debes completar Fase 1.", "#FF0000")
                self._start_intro()
        elif selected_phase == 4:
            print("\n✓ Iniciando directamente en Fase 4 (Definición de Mesa AR)...")
            # Solo cargar lo mínimo (estereo no es necesario para tabla, pero phase1 sí para las cámaras)
            phase1_ok = self._load_phase1_calibration()
            if phase1_ok:
                self._load_board_config()
                self._start_table_definition()
            else:
                print("✗ Error al cargar Fase 1, volviendo a Fase 1")
                self._start_intro()
        else:
            # Fase 1 (Default)
            self._start_intro()
    
    def _start_intro(self):
        """Muestra la pantalla de introducción"""
        self.current_phase = "intro"
        
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
        
        # Crear frames negros para visualización
        black_frame = np.zeros((self.resolution[1]//2, self.resolution[0]//2, 3), dtype=np.uint8)
        self.window.update_frames(black_frame, black_frame)
    
    def _on_phase_continue(self):
        """Maneja el botón de continuar entre fases"""
        # Ocultar botón de reintentar al continuar
        self.window.show_retry_button(False)
        
        if self.current_phase == "intro":
            self._start_camera_calibration("left")
            
        elif self.current_phase == "phase1_complete":
            self._start_phase2()
            
        elif self.current_phase == "phase2_complete":
            self._start_phase3()
            
        elif self.current_phase == "phase3_complete":
            # IR A NUEVA FASE: Definición de Mesa
            self._start_table_definition()
            
        elif self.current_phase == "table_definition_complete":
            self._finish_calibration(True)

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
        print(f"🔄 Reintentando fase: {self.current_phase}")
        
        # Detener timer si está activo
        if self.timer.isActive():
            self.timer.stop()
        
        # Ocultar botón de reintentar mientras se procesa
        self.window.show_retry_button(False)
        
        # Determinar qué fase reiniciar basándose en el estado actual
        if self.current_phase in ["capture_left", "left_complete"]:
            # Reiniciar calibración de cámara izquierda
            print("  → Reiniciando calibración cámara IZQUIERDA")
            self._reset_camera_calibration("left")
            self._start_camera_calibration("left")
            
        elif self.current_phase in ["capture_right", "right_complete"]:
            # Reiniciar calibración de cámara derecha
            print("  → Reiniciando calibración cámara DERECHA")
            self._reset_camera_calibration("right")
            self._start_camera_calibration("right")
            
        elif self.current_phase in ["stereo_capture", "stereo_intro", "phase2_complete"]:
            # Reiniciar calibración estéreo
            print("  → Reiniciando calibración ESTÉREO")
            self._reset_stereo_calibration()
            self._start_phase2()
            
        elif self.current_phase in ["depth_capture", "depth_intro", "phase3_complete"]:
            # Reiniciar calibración de profundidad
            print("  → Reiniciando calibración de PROFUNDIDAD")
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
            print(f"✗ No se pudo abrir la cámara {camera_id}")
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
        if self.current_phase.startswith("capture_"):
            self._update_single_camera_frame()
        elif self.current_phase == "stereo_capture":
            self._update_stereo_frame()
        elif self.current_phase == "depth_capture":
            self._update_depth_frame()
        elif self.current_phase == "table_definition":
            self._update_table_definition_frame()
    
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

        # Detectar tablero
        detected, corners, frame_overlay = self.current_calibrator.detect_chessboard(frame)
        
        # Guardar para captura
        self.last_detected = detected
        self.last_corners = corners
        self.last_frame = frame
        
        # Actualizar estado
        if detected:
            self.window.set_status("✓ Tablero detectado - Presiona CAPTURAR", "#00FF00")
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
        
        # Capturar imagen
        self.current_calibrator.capture_image(self.last_frame, self.last_corners)
        self.photo_count += 1
        
        print(f"✓ Foto {self.photo_count}/{self.total_photos} capturada")
        
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
            print("✗ La calibración falló")
            self._finish_calibration(False)
            return
        
        # Mostrar resumen
        camera_display = "IZQUIERDA" if self.current_camera == "left" else "DERECHA"
        summary_html = f"<h3 style='color: #00FF00;'>CÁMARA {camera_display} CALIBRADA</h3>"
        summary_html += "<table style='width: 100%; color: #FFFFFF;'>"
        summary_html += f"<tr><td><b>Configuración:</b></td><td>{self.board_cols}x{self.board_rows} esquinas ({self.square_size_mm} mm)</td></tr>"
        summary_html += f"<tr><td><b>Imágenes capturadas:</b></td><td>{self.photo_count}</td></tr>"
        summary_html += f"<tr><td><b>Error de reproyección:</b></td><td>{result['reprojection_error']:.6f} px</td></tr>"
        summary_html += "</table>"
        summary_html += "<p style='color: #00FF00; margin-top: 20px;'><b>Presiona CONTINUAR o ENTER</b></p>"
        
        self.window.set_instructions(summary_html)
        self.window.set_status("✓ Calibración completada", "#00FF00")
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
            print("✗ Error al abrir las cámaras")
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

        # Detectar tablero en ambas cámaras
        detected_both, corners_left, corners_right, display_left, display_right = \
            self.stereo_calibrator.detect_chessboard_pair(frame_left, frame_right)
        
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
            self.window.set_status("✓ Tablero detectado en AMBAS - Presiona CAPTURAR", "#00FF00")
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
        
        # Capturar par
        self.stereo_calibrator.capture_stereo_pair(
            self.last_frame_left, self.last_frame_right,
            self.last_corners_left, self.last_corners_right
        )
        self.pair_count += 1
        
        print(f"✓ Par {self.pair_count} capturado")
        
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
            print("✗ Error en calibración estéreo")
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
        dialog.setWindowTitle("Distancia Real del Teclado")
        dialog.setModal(True)
        dialog.setFixedSize(450, 320)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            QLabel#title {
                color: #00C8FF;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#info {
                color: #888888;
                font-size: 11px;
            }
            QDoubleSpinBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 2px solid #00C8FF;
                border-radius: 4px;
                padding: 8px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #00C8FF;
                color: #000000;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #33D6FF;
            }
            QPushButton#skipBtn {
                background-color: #555555;
                color: #ffffff;
            }
            QPushButton#skipBtn:hover {
                background-color: #666666;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Título
        title = QLabel("Medicion de Distancia Real")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instrucciones
        instructions = QLabel(
            "Mide con una regla o cinta metrica la distancia\n"
            "desde las CAMARAS hasta el TECLADO/MESA.\n\n"
            "Esto permite calcular el error de medicion\n"
            "y corregir la profundidad automaticamente."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        layout.addSpacing(8)
        
        # Input de distancia
        input_layout = QHBoxLayout()
        input_layout.addStretch()
        
        input_label = QLabel("Distancia real:")
        input_layout.addWidget(input_label)
        
        self.distance_spinbox = QDoubleSpinBox()
        self.distance_spinbox.setRange(10, 200)
        self.distance_spinbox.setValue(35)  # Valor por defecto más realista
        self.distance_spinbox.setSuffix(" cm")
        self.distance_spinbox.setDecimals(1)
        self.distance_spinbox.setSingleStep(1)
        self.distance_spinbox.setFixedWidth(140)
        input_layout.addWidget(self.distance_spinbox)
        
        # Guardar referencia al diálogo para poder acceder al spinbox después
        self._distance_dialog = dialog
        
        input_layout.addStretch()
        layout.addLayout(input_layout)
        
        # Info adicional
        info = QLabel("Tip: Mide desde el lente de la camara hasta la superficie donde tocaras")
        info.setObjectName("info")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addSpacing(12)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        skip_btn = QPushButton("Omitir")
        skip_btn.setObjectName("skipBtn")
        skip_btn.clicked.connect(lambda: self._on_distance_entered(dialog, skip=True))
        buttons_layout.addWidget(skip_btn)
        
        buttons_layout.addSpacing(12)
        
        confirm_btn = QPushButton("Continuar")
        confirm_btn.clicked.connect(lambda: self._on_distance_entered(dialog, skip=False))
        buttons_layout.addWidget(confirm_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        dialog.exec()
    
    def _on_distance_entered(self, dialog, skip=False):
        """Procesa la distancia ingresada y continúa con la Fase 3"""
        # IMPORTANTE: Leer el valor ANTES de cerrar el diálogo
        if skip:
            self.real_distance_cm = None
            print("[Fase 3] Omitiendo medicion de distancia real")
        else:
            # Leer valor del spinbox antes de cerrar
            self.real_distance_cm = self.distance_spinbox.value()
            print(f"")
            print(f"========================================")
            print(f"[Fase 3] DISTANCIA REAL INGRESADA: {self.real_distance_cm} cm")
            print(f"========================================")
            print(f"")
        
        # Ahora sí cerrar el diálogo
        dialog.accept()
        
        # Mostrar instrucciones de la Fase 3
        if self.real_distance_cm:
            instructions = [
                f"Distancia real configurada: <b>{self.real_distance_cm} cm</b>",
                "Ahora pon tu <b>mano</b> en el lugar donde tocaras las teclas",
                "Manten la mano <b>apoyada</b> sobre el teclado/mesa",
                "El sistema medira y calculara el <b>factor de correccion</b>",
                "Capturaremos <b>5 muestras</b> para mayor precision"
            ]
        else:
            instructions = [
                "Pon tu <b>mano</b> en el lugar donde tocaras las teclas",
                "Manten la mano <b>apoyada</b> sobre el teclado/mesa",
                "El sistema medira la distancia automaticamente",
                "Capturaremos <b>5 muestras</b> para mayor precision"
            ]
        
        self.window.show_intro_screen(
            "FASE 3 - CALIBRACION DE DISTANCIA",
            instructions
        )
    
    def _start_depth_capture(self):
        """Inicia la captura de profundidad simplificada"""
        try:
            # Inicializar componentes de visión
            if self.hand_detector is None:
                self.window.set_status("Cargando detector de manos...", "#FFA500")
                QApplication.processEvents()
                self.hand_detector = HandDetector(maxHands=2)
            
            if self.depth_estimator is None:
                self.window.set_status("Cargando estimador de profundidad...", "#FFA500")
                QApplication.processEvents()
                # Cargar estimador base (sin calibración fina aún)
                self.depth_estimator = load_depth_estimator()
            
            # Inicializar calibrador de profundidad
            self.depth_calibrator = DepthCalibrator(self.depth_estimator)
            
            # Pasar la distancia real si fue ingresada
            print(f"[DEBUG] hasattr real_distance_cm: {hasattr(self, 'real_distance_cm')}")
            print(f"[DEBUG] real_distance_cm value: {getattr(self, 'real_distance_cm', 'NO EXISTE')}")
            
            if hasattr(self, 'real_distance_cm') and self.real_distance_cm is not None:
                self.depth_calibrator.set_real_distance(self.real_distance_cm)
            else:
                print("[DEBUG] NO se paso distancia real al calibrador!")
            
            # Configurar número de muestras (simplificado)
            self.keyboard_samples_needed = 5
            self.keyboard_samples_collected = 0

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
                print("✗ Error al abrir las cámaras para profundidad")
                self._finish_calibration(False)
                return
                
            # Actualizar UI
            self.current_phase = "depth_capture"
            self.window.set_phase(self.current_phase, "FASE 3 - DISTANCIA DEL TECLADO")
            self.window.set_status("Pon tu mano sobre el teclado y presiona ESPACIO o CAPTURAR", "#00BFFF")
            self.window.set_instructions(
                f"<b>Muestra {self.keyboard_samples_collected + 1} de {self.keyboard_samples_needed}</b><br>"
                "Mantén la mano apoyada en el plano del teclado<br>"
                "<span style='color: #FFD700;'>Nota: El valor mostrado puede parecer incorrecto, es normal</span>"
            )
            self.window.show_continue_button(False)  # Mostrar botón de captura, no continuar
            self.window.enable_capture(True)  # Habilitar captura desde el inicio
            
            # Mostrar botón de reintentar
            self.window.show_retry_button(True)
            
            # Iniciar timer
            if not self.timer.isActive():
                self.timer.start(33)
                
        except Exception as e:
            print(f"✗ Error crítico al iniciar Fase 3: {e}")
            import traceback
            traceback.print_exc()
            self.window.set_status(f"Error: {str(e)}", "#FF0000")
            self._finish_calibration(False)

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
            
        # IMPORTANTE: Si usamos el mismo detector, debemos guardar landmarks_left antes de detectar right
        # O si hay un detector derecho... Revisemos init.
        # Asumiendo self.hand_detector se usa para Left. Para Right usamos... el mismo?
        # El código original (línea 1116) usa self.hand_detector.findHands(display_right) SOBREESCRIBIENDO results.
        # ESTO ES UN BUG POTENCIAL si calculate_depth necesita both results?
        # No, depth_calibrator.calculate_depth recibe (landmarks_left, landmarks_right).
        # Así que debemos guardar los objetos landmarks antes de la segunda detección.
        
        # Guardar landmarks izq
        import copy
        processed_landmarks_left = copy.deepcopy(landmarks_left) if landmarks_left else None

        found_right = self.hand_detector.findHands(frame_right)
        landmarks_right = None
        if found_right and self.hand_detector.results.multi_hand_landmarks:
            landmarks_right = self.hand_detector.results.multi_hand_landmarks[0]

        # 3. Preparar Display (Espejo para visualización)
        display_left = StereoConfig.apply_display_transform(frame_left)
        display_right = StereoConfig.apply_display_transform(frame_right)
        
        # 4. Dibujar en Display (con rotate_180=True)
        # Mejor solución: Dibujar Right primero (que está activo en results)
        if landmarks_right:
            self.hand_detector.drawHands(display_right, rotate_180=True)
            
        # Para Left, tendríamos que re-inyectar los resultados... o re-detectar en display?
        # Re-detectar es lento. 
        # Intentemos "mockear" los resultados para dibujar
        if processed_landmarks_left:
            # Restaurar landmarks izq temporalmente
            class MockResults:
                def __init__(self, lm): self.multi_hand_landmarks = [lm]
            
            original_results = self.hand_detector.results
            self.hand_detector.results = MockResults(processed_landmarks_left)
            self.hand_detector.drawHands(display_left, rotate_180=True)
            self.hand_detector.results = original_results # Restaurar (que tiene Right)
            
        # Actualizar variables para cálculo (usamos las copias/referencias directas)
        landmarks_left = processed_landmarks_left
            
        # Calcular profundidad si hay manos en ambas
        self.last_depth_value = None
        
        if landmarks_left and landmarks_right:
            depth = self.depth_calibrator.calculate_depth(landmarks_left, landmarks_right)
            
            if depth is not None and depth > 0:
                self.last_depth_value = depth
                self.window.set_status(
                    f"✓ Mano detectada - Distancia: {depth:.1f} cm - ¡PRESIONA ESPACIO o CAPTURAR!", 
                    "#00FF00"
                )
                self.window.enable_capture(True)
            elif depth is not None:
                # Profundidad negativa o cero - problema de triangulación
                self.last_depth_value = abs(depth) if depth != 0 else 50  # Valor temporal
                self.window.set_status(
                    f"⚠ Distancia estimada: {abs(depth):.1f} cm - Puedes capturar", 
                    "#FFA500"
                )
                self.window.enable_capture(True)
            else:
                self.window.set_status("Calculando profundidad...", "#FFA500")
                self.window.enable_capture(False)
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
        """Captura una muestra de la distancia del teclado"""
        if self.last_depth_value is None:
            return
            
        # Agregar muestra de distancia del teclado
        self.depth_calibrator.add_keyboard_distance_sample(self.last_depth_value)
        self.keyboard_samples_collected += 1
        
        # Actualizar UI
        if self.keyboard_samples_collected < self.keyboard_samples_needed:
            self.window.set_instructions(
                f"<b>Muestra {self.keyboard_samples_collected + 1} de {self.keyboard_samples_needed}</b><br>"
                f"Última medición: {self.last_depth_value:.1f} cm<br>"
                "Mantén la mano apoyada y presiona CAPTURAR"
            )
            self.window.set_status(f"✓ Muestra {self.keyboard_samples_collected} capturada", "#00FF00")
        else:
            # Finalizar
            self._finish_phase3()

    def _finish_phase3(self):
        """Finaliza la Fase 3"""
        self.timer.stop()
        
        # Calcular distancia del teclado (y factor de corrección si hay distancia real)
        keyboard_distance = self.depth_calibrator.calculate_keyboard_distance()
        
        if keyboard_distance is None:
            print("Error en calibracion de distancia")
            self._finish_calibration(False)
            return
        
        # Guardar la distancia del teclado y factor de corrección
        self.depth_calibrator.save_keyboard_distance_only()
            
        # Recopilar datos para el resumen
        summary_data = {
            'board_config': f"{self.board_cols}x{self.board_rows} ({self.square_size_mm}mm)",
            'left_error': self.calibrator_left.reprojection_error if self.calibrator_left else 'N/A',
            'right_error': self.calibrator_right.reprojection_error if self.calibrator_right else 'N/A',
            'keyboard_distance': keyboard_distance,
            'correction_factor': self.depth_calibrator.correction_factor
        }
        
        # Agregar datos de corrección si hay distancia real
        if self.depth_calibrator.real_distance_cm is not None:
            measured = float(np.median(self.depth_calibrator.keyboard_distance_samples))
            error_cm = abs(measured - self.depth_calibrator.real_distance_cm)
            error_percent = (error_cm / self.depth_calibrator.real_distance_cm) * 100
            
            summary_data['real_distance_cm'] = self.depth_calibrator.real_distance_cm
            summary_data['measured_distance_cm'] = measured
            summary_data['depth_error_cm'] = error_cm
            summary_data['depth_error_percent'] = error_percent
        
        # Agregar datos estéreo si existen
        if self.stereo_calibrator:
            if hasattr(self.stereo_calibrator, 'stereo_error') and self.stereo_calibrator.stereo_error is not None:
                summary_data['stereo_error'] = self.stereo_calibrator.stereo_error
            
            if self.stereo_calibrator.T is not None:
                # T está en mm, convertir a cm
                baseline_mm = np.linalg.norm(self.stereo_calibrator.T)
                summary_data['baseline'] = baseline_mm / 10.0
        
        # Mostrar pantalla de resumen
        self.window.show_summary_screen(summary_data)
        self.window.show_retry_button(True)  # Permitir reintentar si el resultado no es satisfactorio
        self.current_phase = "phase3_complete"
    
    def _on_cancel(self):
        """Maneja la cancelación"""
        print("\n✗ Calibración cancelada por el usuario")
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
            print(f"✗ Error al cargar Fase 1: {e}")
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
            print(f"✗ Error al cargar Fase 2: {e}")
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
            
        # Dibujar sobre el frame
        display = frame_left.copy()
        
        # Aplicar transformaciones para display
        display = StereoConfig.apply_display_transform(StereoConfig.apply_camera_transforms(display))

        # Obtener dimensiones del label y frame para conversión de coordenadas
        lbl_w = self.window.camera_left_label.width()
        lbl_h = self.window.camera_left_label.height()
        frame_h, frame_w = display.shape[:2]
        
        # Si estamos arrastrando, dibujar rectángulo en tiempo real
        if self.is_dragging and self.drag_start_point and self.drag_current_point:
            # Convertir coordenadas de label a frame
            x1 = int(self.drag_start_point[0] * (frame_w / lbl_w))
            y1 = int(self.drag_start_point[1] * (frame_h / lbl_h))
            x2 = int(self.drag_current_point[0] * (frame_w / lbl_w))
            y2 = int(self.drag_current_point[1] * (frame_h / lbl_h))
            
            # Dibujar rectángulo semitransparente
            overlay = display.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
            cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
            
            # Dibujar borde del rectángulo
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            # Dibujar esquinas con círculos
            for pt in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
                cv2.circle(display, pt, 8, (0, 255, 0), -1)
                cv2.circle(display, pt, 8, (255, 255, 255), 2)
            
            # Mostrar dimensiones
            width_px = abs(x2 - x1)
            height_px = abs(y2 - y1)
            text = f"{width_px}x{height_px}px"
            cv2.putText(display, text, (min(x1, x2) + 5, min(y1, y2) - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Si ya hay esquinas definidas (después de soltar), dibujar el rectángulo final
        elif len(self.table_corners) == 4:
            pts = [self.table_corners[i] for i in range(4)]
            
            # Dibujar rectángulo relleno semitransparente
            overlay = display.copy()
            pts_array = np.array(pts, np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(overlay, [pts_array], (0, 255, 0))
            cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
            
            # Dibujar bordes
            cv2.polylines(display, [pts_array], True, (0, 255, 0), 3)
            
            # Dibujar esquinas numeradas
            for i, pt in enumerate(pts):
                cv2.circle(display, pt, 8, (0, 255, 0), -1)
                cv2.circle(display, pt, 8, (255, 255, 255), 2)
                cv2.putText(display, str(i+1), (pt[0]+12, pt[1]-8), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
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
        if self.current_phase != "table_definition":
            return
        if camera_name != "left":
            return
        if not self.is_dragging:
            return
            
        self.is_dragging = False
        self.drag_current_point = (x, y)
        
        # Obtener dimensiones para conversión
        lbl_w = self.window.camera_left_label.width()
        lbl_h = self.window.camera_left_label.height()
        
        # Obtener resolución real del frame
        frame_w, frame_h = self.resolution
        if self.cap_left:
            cw = self.cap_left.video_width
            ch = self.cap_left.video_height
            if cw > 0 and ch > 0:
                frame_w, frame_h = int(cw), int(ch)
        
        # Convertir coordenadas de label a frame
        x1 = int(self.drag_start_point[0] * (frame_w / lbl_w))
        y1 = int(self.drag_start_point[1] * (frame_h / lbl_h))
        x2 = int(x * (frame_w / lbl_w))
        y2 = int(y * (frame_h / lbl_h))
        
        # Asegurar que tenemos un rectángulo válido (mínimo 50x50 píxeles)
        if abs(x2 - x1) < 50 or abs(y2 - y1) < 50:
            self.window.set_status("⚠️ Área muy pequeña. Intenta de nuevo arrastrando más.", "#FF6600")
            self.drag_start_point = None
            self.drag_current_point = None
            return
        
        # Crear las 4 esquinas del rectángulo en orden: TL, TR, BR, BL
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        
        self.table_corners = [
            (min_x, min_y),  # Top-Left
            (max_x, min_y),  # Top-Right
            (max_x, max_y),  # Bottom-Right
            (min_x, max_y)   # Bottom-Left
        ]
        
        print(f"[Drag] Finalizado: ({x1},{y1}) -> ({x2},{y2})")
        print(f"[Drag] Rectángulo: {self.table_corners}")
        
        # Guardar y finalizar
        self.window.set_status("✅ ¡Área definida! Guardando...", "#00FF00")
        self.current_phase = "table_definition_complete"
        self._save_table_definition()
        
        # Mostrar mensaje final
        QTimer.singleShot(1000, lambda: self.window.show_intro_screen(
            "¡CALIBRACIÓN FINALIZADA!",
            [
                "✅ Has completado todas las fases.",
                "",
                f"📐 Área definida: {max_x - min_x} x {max_y - min_y} píxeles",
                "",
                "🎹 Tu piano virtual está listo.",
                "",
                "Presiona <b>Continuar</b> para comenzar a tocar."
            ]
        ))
        
    def _on_frame_clicked(self, camera_name, x, y):
        """Maneja el clic en el video (ya no usado en Fase 4, pero mantenido para compatibilidad)"""
        # En Fase 4 usamos drag, no clics individuales
        if self.current_phase == "table_definition":
            return  # Ignorar clics simples en fase 4
            
        if camera_name != "left":
            print("Por favor, marca en la cámara izquierda.")
            return

    def _save_table_definition(self):
        """Guarda la definición de mesa en calibration.json"""
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
            
            data['table_definition'] = {
                'corners': self.table_corners,
                'camera': 'left',
                'resolution': [frame_w, frame_h]
            }
            
            with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"[AR] Definición de mesa guardada: {self.table_corners} (Res: {frame_w}x{frame_h})")
            
        except Exception as e:
            print(f"Error guardando mesa: {e}")
            self.board_rows = 7
            self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM
    
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
            'resolution': {
                'width': self.resolution[0],
                'height': self.resolution[1]
            }
        }
        
        with open(CalibrationConfig.CALIBRATION_FILE, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n✓ Fase 1 guardada")
    
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
            'resolution': {
                'width': self.resolution[0],
                'height': self.resolution[1]
            }
        }
    
    def _save_calibration(self):
        """Guarda calibración completa"""
        output_file = CalibrationConfig.CALIBRATION_FILE
        
        with open(output_file, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n✓ Calibración guardada en: {output_file}")


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
        print("\n🎉 ¡Calibración completa exitosa!")
    else:
        print("\n❌ La calibración no se completó.")

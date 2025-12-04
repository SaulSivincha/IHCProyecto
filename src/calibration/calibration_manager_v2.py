#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor Principal de Calibración - Versión 2 con Fase Estéreo
Orquesta el proceso completo en dos fases
"""

import cv2
import numpy as np
import json
from pathlib import Path
from .calibration_config import CalibrationConfig
from .camera_calibrator import CameraCalibrator
from .stereo_calibrator import StereoCalibrator
from .calibration_ui import CalibrationUI


class CalibrationManager:
    """
    Gestor principal del proceso de calibración estereoscópica
    Fase 1: Calibración individual de cada cámara (25 fotos cada una)
    Fase 2: Calibración estéreo (8-15 pares simultáneos)
    """
    
    def __init__(self, cam_left_id, cam_right_id, resolution=(1280, 720)):
        """
        Args:
            cam_left_id: ID de la cámara izquierda
            cam_right_id: ID de la cámara derecha
            resolution: Tupla (width, height) de resolución
        """
        self.cam_left_id = cam_left_id
        self.cam_right_id = cam_right_id
        self.resolution = resolution
        
        # Parámetros del tablero (fijo: 8x8 = 7x7 esquinas)
        self.board_cols = 7  # 8x8 cuadrados = 7x7 esquinas internas
        self.board_rows = 7
        self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM
        
        # UI
        self.ui = CalibrationUI(width=resolution[0], height=resolution[1])
        
        # Calibradores
        self.calibrator_left = None
        self.calibrator_right = None
        self.stereo_calibrator = None
        
        # Resultados
        self.calibration_data = {}
        
        # Asegurar que existen los directorios
        CalibrationConfig.ensure_directories()
    
    def run_full_calibration(self):
        """
        Ejecuta el proceso completo de calibración
        Inteligente: salta fases ya completadas
        
        Returns:
            bool: True si la calibración fue exitosa
        """
        # Verificar qué fases están completas
        has_phase1 = self._check_phase1_complete()
        has_phase2 = self._check_phase2_complete()
        
        print("\n" + "="*70)
        print("PROCESO DE CALIBRACION ESTEREOSCOPICA")
        print("="*70)
        
        # Determinar desde dónde empezar
        if has_phase1 and has_phase2:
            print("\n✓ Ambas fases ya completadas")
            print("  Fase 1: Calibración individual - COMPLETA")
            print("  Fase 2: Calibración estéreo - COMPLETA")
            print("="*70)
            return True
        elif has_phase1:
            print("\n✓ Fase 1 ya completada, saltando a Fase 2...")
            print("  Cargando calibraciones individuales existentes...")
            if not self._load_phase1_calibration():
                print("✗ Error al cargar Fase 1, recalibrando desde cero...")
                has_phase1 = False
            else:
                print("✓ Calibraciones individuales cargadas")
        
        if not has_phase1:
            print("\nFASE 1: Calibración individual de cámaras (25 fotos cada una)")
            print("FASE 2: Calibración estéreo (8-15 pares simultáneos)")
        else:
            print("\nFASE 2: Calibración estéreo (8-15 pares simultáneos)")
        
        print("="*70 + "\n")
        
        # Paso 1: Configurar tablero (solo si no hay Fase 1)
        if not has_phase1:
            if not self._configure_chessboard():
                print("✗ Configuración cancelada")
                return False
        else:
            # Cargar configuración del tablero desde JSON
            self._load_board_config()
        
        # Paso 2 y 3: Calibrar cámaras individuales (solo si no hay Fase 1)
        if not has_phase1:
            # Calibrar cámara izquierda (Fase 1.1)
            print("\n[FASE 1.1] Calibrando cámara IZQUIERDA...")
            self.calibrator_left = CameraCalibrator(
                camera_id=self.cam_left_id,
                camera_name='left',
                board_size=(self.board_cols, self.board_rows),
                square_size_mm=self.square_size_mm
            )
            
            if not self._calibrate_single_camera(self.calibrator_left, "IZQUIERDA"):
                print("✗ Calibración de cámara izquierda fallida")
                return False
            
            # Calibrar cámara derecha (Fase 1.2)
            print("\n[FASE 1.2] Calibrando cámara DERECHA...")
            self.calibrator_right = CameraCalibrator(
                camera_id=self.cam_right_id,
                camera_name='right',
                board_size=(self.board_cols, self.board_rows),
                square_size_mm=self.square_size_mm
            )
            
            if not self._calibrate_single_camera(self.calibrator_right, "DERECHA"):
                print("✗ Calibración de cámara derecha fallida")
                return False
            
            # Guardar Fase 1 inmediatamente
            self._save_phase1_only()
        
        # Paso 4: Calibración estéreo (Fase 2)
        print("\n[FASE 2] Calibrando PAR ESTÉREO...")
        if not self._calibrate_stereo_pair():
            print("✗ Calibración estéreo fallida")
            return False
        
        print("\n[DEBUG] ✓ _calibrate_stereo_pair() completado exitosamente")
        
        # Paso 5: Recopilar datos finales
        print("[DEBUG] → Recopilando datos finales...")
        self._compile_calibration_data()
        print("[DEBUG] ✓ Datos recopilados")
        
        # Paso 6: Guardar resultados
        print("[DEBUG] → Guardando calibración...")
        self._save_calibration()
        print("[DEBUG] ✓ Calibración guardada")
        
        print("\n" + "="*70)
        print("✓ CALIBRACION COMPLETADA EXITOSAMENTE")
        print("="*70)
        print(f"📊 Errores de reproyección:")
        print(f"  Cámara izquierda:  {self.calibrator_left.reprojection_error:.6f} px")
        print(f"  Cámara derecha:    {self.calibrator_right.reprojection_error:.6f} px")
        print(f"  Par estéreo:       {self.stereo_calibrator.stereo_error:.6f}")
        print(f"📏 Baseline:           {np.linalg.norm(self.stereo_calibrator.T)*100:.2f} cm")
        print(f"\n💾 Datos guardados en: {CalibrationConfig.CALIBRATION_FILE}")
        print(f"📁 Imágenes guardadas en: {CalibrationConfig.CALIBRATION_IMAGES_DIR}")
        print("="*70 + "\n")
        
        return True
    
    def _check_phase1_complete(self):
        """
        Verifica si la Fase 1 (calibración individual) está completa
        
        Returns:
            bool: True si ambas cámaras están calibradas
        """
        if not CalibrationConfig.CALIBRATION_FILE.exists():
            return False
        
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Verificar que existan calibraciones individuales
            has_left = 'left_camera' in data and 'camera_matrix' in data['left_camera']
            has_right = 'right_camera' in data and 'camera_matrix' in data['right_camera']
            
            return has_left and has_right
        except:
            return False
    
    def _check_phase2_complete(self):
        """
        Verifica si la Fase 2 (calibración estéreo) está completa
        
        Returns:
            bool: True si la calibración estéreo está completa
        """
        if not CalibrationConfig.CALIBRATION_FILE.exists():
            return False
        
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Verificar que exista calibración estéreo
            has_stereo = 'stereo' in data and data['stereo'] is not None
            if has_stereo:
                has_r = 'rotation_matrix' in data['stereo']
                has_t = 'translation_vector' in data['stereo']
                return has_r and has_t
            
            return False
        except:
            return False
    
    def _load_phase1_calibration(self):
        """
        Carga las calibraciones individuales desde el archivo JSON
        
        Returns:
            bool: True si se cargó exitosamente
        """
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Recrear calibradores con datos existentes
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
            # Crear obj_points dummy para que len() funcione
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
            # Crear obj_points dummy para que len() funcione
            self.calibrator_right.obj_points = [None] * data['right_camera']['num_images']
            self.calibrator_right.is_calibrated = True
            
            print(f"  ✓ Cámara izquierda: error {self.calibrator_left.reprojection_error:.4f} px")
            print(f"  ✓ Cámara derecha: error {self.calibrator_right.reprojection_error:.4f} px")
            
            return True
            
        except Exception as e:
            print(f"✗ Error al cargar Fase 1: {e}")
            return False
    
    def _load_board_config(self):
        """
        Carga la configuración del tablero desde el archivo JSON
        """
        try:
            with open(CalibrationConfig.CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            board_config = data['board_config']
            self.board_cols = board_config['cols']
            self.board_rows = board_config['rows']
            self.square_size_mm = board_config['square_size_mm']
            
            print(f"  ✓ Tablero: {self.board_rows+1}x{self.board_cols+1} ({self.square_size_mm} mm)")
        except:
            # Si falla, usar valores por defecto
            self.board_cols = 7
            self.board_rows = 7
            self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM
    
    def _save_phase1_only(self):
        """
        Guarda solo la Fase 1 (calibración individual) en JSON
        Útil para guardar progreso antes de Fase 2
        """
        self.calibration_data = {
            'version': '2.0',
            'board_config': {
                'cols': self.board_cols,
                'rows': self.board_rows,
                'square_size_mm': self.square_size_mm
            },
            'left_camera': self.calibrator_left.get_calibration_data(),
            'right_camera': self.calibrator_right.get_calibration_data(),
            'stereo': None,  # Aún no completada
            'camera_ids': {
                'left': self.cam_left_id,
                'right': self.cam_right_id
            },
            'resolution': {
                'width': self.resolution[0],
                'height': self.resolution[1]
            }
        }
        
        output_file = CalibrationConfig.CALIBRATION_FILE
        with open(output_file, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n✓ Fase 1 guardada. Continuando con Fase 2...")
    
    def _configure_chessboard(self):
        """
        Solicita al usuario solo el tamaño del cuadrado
        (Tablero 8x8 fijo: 7x7 esquinas internas)
        
        Returns:
            bool: True si se configuró exitosamente
        """
        window_name = "Configuracion del Tablero"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.resolution[0], self.resolution[1])
        
        # Frame negro para la UI
        base_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        
        # Solicitar tamaño del cuadrado
        input_value = str(int(self.square_size_mm))
        error_msg = ""
        
        while True:
            frame = base_frame.copy()
            
            # Panel informativo
            info_y = 100
            cv2.putText(frame, "TABLERO DE AJEDREZ ESTANDAR (8x8)", 
                       (self.resolution[0]//2 - 300, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 200, 255), 3)
            
            cv2.putText(frame, "El sistema detectara 7x7 esquinas internas", 
                       (self.resolution[0]//2 - 250, info_y + 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            
            # Dibujar representación visual del tablero
            board_x = self.resolution[0]//2 - 120
            board_y = info_y + 100
            square_size = 30
            for i in range(8):
                for j in range(8):
                    color = (200, 200, 200) if (i + j) % 2 == 0 else (50, 50, 50)
                    cv2.rectangle(frame, 
                                (board_x + j*square_size, board_y + i*square_size),
                                (board_x + (j+1)*square_size, board_y + (i+1)*square_size),
                                color, -1)
            
            # Dibujar esquinas internas
            for i in range(1, 8):
                for j in range(1, 8):
                    cv2.circle(frame, 
                             (board_x + j*square_size, board_y + i*square_size),
                             4, (0, 255, 0), -1)
            
            cv2.putText(frame, "49 esquinas detectadas", 
                       (board_x + 20, board_y + 8*square_size + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Solicitar tamaño
            frame = self.ui.draw_input_screen(
                frame,
                f"Tamano de cada cuadrado (milimetros):",
                input_value,
                error_msg
            )
            
            # Agregar instrucción de medición
            cv2.putText(frame, "Mide un cuadrado de tu tablero con una regla", 
                       (self.resolution[0]//2 - 250, self.resolution[1] - 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 1)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13:  # ENTER
                try:
                    size = float(input_value)
                    if 10.0 <= size <= 100.0:
                        self.square_size_mm = size
                        break
                    else:
                        error_msg = "Valor debe estar entre 10 y 100 mm"
                except ValueError:
                    error_msg = "Ingresa un numero valido"
            elif key == 27:  # ESC
                cv2.destroyWindow(window_name)
                return False
            elif key == 8 and len(input_value) > 0:  # BACKSPACE
                input_value = input_value[:-1]
                error_msg = ""
            elif 48 <= key <= 57 or key == 46:  # Números 0-9 y punto decimal
                if key == 46 and '.' in input_value:
                    continue
                input_value += chr(key)
                error_msg = ""
        
        cv2.destroyWindow(window_name)
        
        print(f"\n✓ Configuración del tablero:")
        print(f"  Tipo: Ajedrez estándar (8x8 cuadrados)")
        print(f"  Esquinas internas: 7 x 7")
        print(f"  Tamaño cuadrado: {self.square_size_mm} mm")
        
        return True
    
    def _calibrate_single_camera(self, calibrator, camera_name):
        """
        Ejecuta la calibración de una cámara individual (Fase 1)
        
        Args:
            calibrator: Instancia de CameraCalibrator
            camera_name: Nombre descriptivo de la cámara
            
        Returns:
            bool: True si la calibración fue exitosa
        """
        window_name = f"Calibracion - Camara {camera_name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.resolution[0], self.resolution[1])
        
        # Abrir cámara
        cap = cv2.VideoCapture(calibrator.camera_id)
        if not cap.isOpened():
            print(f"✗ No se pudo abrir la cámara {calibrator.camera_id}")
            cv2.destroyWindow(window_name)
            return False
        
        # Configurar resolución
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        
        total_photos = CalibrationConfig.get_total_photos()
        photo_count = 0
        
        print(f"\n{'='*70}")
        print(f"CAPTURANDO IMÁGENES - CÁMARA {camera_name}")
        print(f"{'='*70}")
        print(f"Total de fotos requeridas: {total_photos}")
        print(f"Mínimo recomendado: {CalibrationConfig.MIN_IMAGES}")
        print("\nControles:")
        print("  ESPACIO - Capturar imagen (cuando el tablero esté detectado)")
        print("  ESC     - Cancelar")
        print("  Q       - Finalizar captura anticipada (mín. 15 fotos)")
        print(f"{'='*70}\n")
        
        while photo_count < total_photos:
            ret, frame = cap.read()
            if not ret:
                print("✗ Error al leer frame")
                break
            
            # Detectar tablero
            detected, corners, frame_overlay = calibrator.detect_chessboard(frame)
            
            # Dibujar UI con instrucciones contextuales
            frame_display = self.ui.draw_capture_screen(
                frame_overlay,
                camera_name,
                photo_count,
                total_photos,
                detected,
                ""
            )
            
            cv2.imshow(window_name, frame_display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' ') and detected:
                calibrator.capture_image(frame, corners)
                photo_count += 1
                print(f"✓ Foto {photo_count}/{total_photos} capturada")
                cv2.waitKey(200)
                
            elif key == ord('q') or key == ord('Q'):
                if photo_count >= CalibrationConfig.MIN_IMAGES:
                    print(f"\n⚠ Finalizando captura anticipada con {photo_count} fotos")
                    break
                else:
                    print(f"\n⚠ Se necesitan al menos {CalibrationConfig.MIN_IMAGES} fotos")
                    print(f"   Capturadas: {photo_count}. Continúa...")
                    
            elif key == 27:  # ESC
                print("\n✗ Captura cancelada por el usuario")
                cap.release()
                cv2.destroyWindow(window_name)
                return False
        
        cap.release()
        
        # Ejecutar calibración
        print(f"\n{'='*70}")
        print(f"PROCESANDO CALIBRACIÓN - CÁMARA {camera_name}")
        print(f"{'='*70}")
        
        result = calibrator.calibrate()
        
        if result is None:
            print("✗ La calibración falló")
            cv2.destroyWindow(window_name)
            return False
        
        # Mostrar resumen
        base_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        summary_frame = self.ui.draw_summary_screen(
            base_frame,
            camera_name,
            photo_count,
            result['reprojection_error']
        )
        
        cv2.imshow(window_name, summary_frame)
        cv2.waitKey(0)
        cv2.destroyWindow(window_name)
        
        return True
    
    def _calibrate_stereo_pair(self):
        """
        Calibración del par estéreo (Fase 2)
        Captura 8-15 pares de imágenes simultáneas
        
        Returns:
            bool: True si la calibración fue exitosa
        """
        MIN_PAIRS = 8
        MAX_PAIRS = 15
        
        # Crear calibrador estéreo
        self.stereo_calibrator = StereoCalibrator(self.calibrator_left, self.calibrator_right)
        
        # Abrir ambas cámaras
        cap_left = cv2.VideoCapture(self.cam_left_id)
        cap_right = cv2.VideoCapture(self.cam_right_id)
        
        if not cap_left.isOpened() or not cap_right.isOpened():
            print("✗ Error al abrir las cámaras")
            cap_left.release()
            cap_right.release()
            return False
        
        # Configurar resolución
        for cap in [cap_left, cap_right]:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        print(f"\n{'='*70}")
        print(f"CAPTURA DE PARES ESTÉREO")
        print(f"{'='*70}")
        print(f"Se necesitan entre {MIN_PAIRS} y {MAX_PAIRS} capturas simultáneas")
        print(f"\n📋 INSTRUCCIONES:")
        print(f"  1. Coloca el tablero 8x8 frente a AMBAS cámaras")
        print(f"  2. Asegúrate de que el tablero sea visible en AMBAS vistas")
        print(f"  3. Varía la posición y ángulo del tablero entre capturas")
        print(f"  4. Presiona ESPACIO cuando el tablero esté detectado en ambas")
        print(f"  5. Presiona ESC cuando hayas capturado suficientes pares")
        print(f"{'='*70}\n")
        
        last_capture_time = 0
        detection_frames = 0
        STABILITY_FRAMES = 5
        
        window_name = "Calibracion Estereo"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.resolution[0] * 2, self.resolution[1])
        
        while True:
            ret_left, frame_left = cap_left.read()
            ret_right, frame_right = cap_right.read()
            
            if not ret_left or not ret_right:
                print("✗ Error al leer frames")
                break
            
            # Detectar tablero en ambas cámaras
            detected_both, corners_left, corners_right, display_left, display_right = \
                self.stereo_calibrator.detect_chessboard_pair(frame_left, frame_right)
            
            # Contar frames de detección consecutivos
            if detected_both:
                detection_frames += 1
            else:
                detection_frames = 0
            
            # Estado de captura
            pairs_count = self.stereo_calibrator.get_pair_count()
            progress = min(100, int((pairs_count / MIN_PAIRS) * 100))
            
            # Dibujar UI en ambos frames
            current_time = cv2.getTickCount() / cv2.getTickFrequency()
            can_capture = (current_time - last_capture_time) > 1.0
            
            for frame, label in [(display_left, "Izquierda"), (display_right, "Derecha")]:
                # Título
                cv2.putText(frame, f"FASE 2: CALIBRACION ESTEREO - {label}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Contador de pares
                color = (0, 255, 0) if pairs_count >= MIN_PAIRS else (0, 165, 255)
                cv2.putText(frame, f"Pares: {pairs_count}/{MIN_PAIRS}",
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                # Barra de progreso
                bar_width = frame.shape[1] - 20
                cv2.rectangle(frame, (10, 90), (10 + bar_width, 110), (60, 60, 60), -1)
                cv2.rectangle(frame, (10, 90), (10 + int(bar_width * progress / 100), 110), color, -1)
                
                # Estado de detección
                if detected_both:
                    if detection_frames >= STABILITY_FRAMES:
                        status = "LISTO PARA CAPTURAR" if can_capture else "Espere..."
                        status_color = (0, 255, 0) if can_capture else (0, 165, 255)
                    else:
                        status = f"Estabilizando... {detection_frames}/{STABILITY_FRAMES}"
                        status_color = (0, 255, 255)
                else:
                    status = "Buscando tablero en ambas camaras..."
                    status_color = (0, 0, 255)
                
                cv2.putText(frame, status, (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                
                # Instrucciones
                if pairs_count >= MIN_PAIRS:
                    cv2.putText(frame, "ESC = Finalizar | ESPACIO = Mas capturas",
                               (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv2.putText(frame, "ESPACIO = Capturar par | ESC = Cancelar",
                               (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Mostrar frames lado a lado
            combined = np.hstack([display_left, display_right])
            cv2.imshow(window_name, combined)
            
            # Manejar teclas
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                if pairs_count >= MIN_PAIRS:
                    print(f"\n✓ Captura finalizada con {pairs_count} pares")
                    break
                else:
                    print(f"\n✗ Cancelado. Se necesitan al menos {MIN_PAIRS} pares")
                    cap_left.release()
                    cap_right.release()
                    cv2.destroyWindow(window_name)
                    return False
            
            elif key == ord(' '):  # ESPACIO
                if detected_both and detection_frames >= STABILITY_FRAMES and can_capture:
                    if pairs_count < MAX_PAIRS:
                        self.stereo_calibrator.capture_stereo_pair(
                            frame_left, frame_right, corners_left, corners_right
                        )
                        print(f"✓ Par {pairs_count + 1} capturado")
                        last_capture_time = current_time
                        detection_frames = 0
                    else:
                        print(f"⚠️  Máximo de {MAX_PAIRS} pares alcanzado")
        
        cap_left.release()
        cap_right.release()
        cv2.destroyWindow(window_name)
        
        # Ejecutar calibración estéreo
        print("\n⏳ Procesando calibración estéreo...")
        stereo_result = self.stereo_calibrator.calibrate_stereo_pair()
        
        if stereo_result is None:
            print("✗ Error en calibración estéreo")
            return False
        
        # Calcular rectificación
        print("⏳ Calculando parámetros de rectificación...")
        rect_result = self.stereo_calibrator.compute_rectification()
        
        if rect_result is None:
            print("⚠️  Advertencia: No se pudo calcular rectificación")
        
        # Mostrar estadísticas finales de Fase 2
        print("[DEBUG] → Mostrando estadísticas de Fase 2...")
        self._show_phase2_statistics(stereo_result, pairs_count)
        print("[DEBUG] ✓ Usuario cerró ventana de estadísticas")
        
        return True
    
    def _show_phase2_statistics(self, stereo_result, pairs_count):
        """Muestra estadísticas finales de la Fase 2 con interfaz visual"""
        window_name = "FASE 2 - Estadisticas Finales"
        cv2.namedWindow(window_name)
        cv2.moveWindow(window_name, self.resolution[0]//4, self.resolution[1]//4)
        
        # Extraer datos
        baseline_cm = stereo_result['baseline_cm']
        rms_error = stereo_result['rms_error']
        
        # Imprimir en consola
        print("\n" + "="*70)
        print("📊 ESTADÍSTICAS DE CALIBRACIÓN ESTÉREO (FASE 2)")
        print("="*70)
        print(f"✓ Pares capturados:     {pairs_count}")
        print(f"✓ Baseline:             {baseline_cm:.2f} cm")
        print(f"✓ Error RMS:            {rms_error:.6f}")
        print(f"✓ Cámara izquierda:     {self.calibrator_left.reprojection_error:.6f} px")
        print(f"✓ Cámara derecha:       {self.calibrator_right.reprojection_error:.6f} px")
        print("="*70)
        
        # Crear frame para mostrar estadísticas
        stats_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        
        while True:
            frame = stats_frame.copy()
            
            # Título principal
            cv2.putText(frame, "FASE 2 COMPLETADA", 
                       (self.resolution[0]//2 - 250, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            
            cv2.putText(frame, "Calibracion Estereo Exitosa", 
                       (self.resolution[0]//2 - 220, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # Línea separadora
            cv2.line(frame, (50, 130), (self.resolution[0]-50, 130), (100, 100, 100), 2)
            
            # Estadísticas principales
            y_pos = 180
            line_height = 50
            
            stats = [
                ("Pares Capturados:", f"{pairs_count}", (0, 255, 255)),
                ("Baseline:", f"{baseline_cm:.2f} cm", (255, 200, 0)),
                ("Error RMS Estereo:", f"{rms_error:.6f}", (255, 150, 0)),
                ("", "", None),  # Espacio
                ("Error Camara Izquierda:", f"{self.calibrator_left.reprojection_error:.6f} px", (100, 255, 100)),
                ("Error Camara Derecha:", f"{self.calibrator_right.reprojection_error:.6f} px", (100, 255, 100)),
            ]
            
            for label, value, color in stats:
                if color is None:  # Espacio en blanco
                    y_pos += line_height // 2
                    continue
                
                cv2.putText(frame, label, 
                           (80, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                
                cv2.putText(frame, value, 
                           (self.resolution[0]//2 + 50, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                y_pos += line_height
            
            # Indicador de calidad
            y_quality = y_pos + 30
            cv2.line(frame, (50, y_quality), (self.resolution[0]-50, y_quality), (100, 100, 100), 2)
            
            y_quality += 50
            quality_label = "Calidad de Calibracion:"
            if rms_error < 0.3:
                quality_text = "EXCELENTE"
                quality_color = (0, 255, 0)
            elif rms_error < 0.6:
                quality_text = "BUENA"
                quality_color = (0, 255, 255)
            elif rms_error < 1.0:
                quality_text = "ACEPTABLE"
                quality_color = (0, 200, 255)
            else:
                quality_text = "MEJORABLE"
                quality_color = (0, 165, 255)
            
            cv2.putText(frame, quality_label, 
                       (80, y_quality),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
            
            cv2.putText(frame, quality_text, 
                       (self.resolution[0]//2 + 50, y_quality),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, quality_color, 3)
            
            # Instrucciones finales
            y_instructions = self.resolution[1] - 80
            cv2.rectangle(frame, (40, y_instructions - 20), 
                         (self.resolution[0] - 40, y_instructions + 60), 
                         (50, 50, 50), -1)
            cv2.rectangle(frame, (40, y_instructions - 20), 
                         (self.resolution[0] - 40, y_instructions + 60), 
                         (0, 255, 0), 2)
            
            cv2.putText(frame, "Presiona [ENTER] para continuar", 
                       (self.resolution[0]//2 - 250, y_instructions + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            cv2.imshow(window_name, frame)
            
            # Esperar indefinidamente hasta que se presione una tecla
            key = cv2.waitKey(0) & 0xFF
            if key == 13:  # ENTER
                print("[DEBUG] Usuario presionó ENTER en estadísticas")
                break
            elif key == 27:  # ESC
                print("[DEBUG] Usuario presionó ESC en estadísticas")
                break
            else:
                # Cualquier otra tecla también cierra
                print(f"[DEBUG] Usuario presionó tecla {key} en estadísticas")
                break
        
        cv2.destroyWindow(window_name)
        print("[DEBUG] Ventana de estadísticas cerrada")
        print("\n✓ Continuando...\n")
    
    def _compile_calibration_data(self):
        """
        Recopila todos los datos de calibración en un diccionario
        
        ACTUALIZADO: Incluye transformaciones al mundo en cada cámara
        para uso correcto en triangulación DLT
        """
        print("[DEBUG] _compile_calibration_data() iniciado")
        print(f"[DEBUG] stereo_calibrator existe: {self.stereo_calibrator is not None}")
        
        stereo_data = None
        if self.stereo_calibrator:
            print(f"[DEBUG] stereo_calibrator.R es None: {self.stereo_calibrator.R is None}")
            print(f"[DEBUG] stereo_calibrator.T es None: {self.stereo_calibrator.T is None}")
            print(f"[DEBUG] stereo_calibrator.stereo_error: {self.stereo_calibrator.stereo_error}")
            
            stereo_data = self.stereo_calibrator.get_calibration_data()
            print(f"[DEBUG] stereo_data es None: {stereo_data is None}")
            if stereo_data:
                print(f"[DEBUG] stereo_data tiene {len(stereo_data)} campos")
                print(f"[DEBUG] stereo_data keys: {list(stereo_data.keys())}")
        
        # Obtener datos de cámaras individuales
        left_camera_data = self.calibrator_left.get_calibration_data()
        right_camera_data = self.calibrator_right.get_calibration_data()
        
        # NUEVO: Agregar transformaciones al mundo para DLT correcto
        # Convención: Cámara izquierda = origen del mundo
        if stereo_data and 'rotation_matrix' in stereo_data:
            # Cámara izquierda como origen (R=I, T=0)
            left_camera_data['world_rotation'] = [[1.0, 0.0, 0.0],
                                                   [0.0, 1.0, 0.0],
                                                   [0.0, 0.0, 1.0]]
            left_camera_data['world_translation'] = [[0.0], [0.0], [0.0]]
            
            # Cámara derecha con transformación estéreo
            right_camera_data['world_rotation'] = stereo_data['rotation_matrix']
            right_camera_data['world_translation'] = stereo_data['translation_vector']
            
            print("[DEBUG] Transformaciones al mundo agregadas a cámaras individuales")
        
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
        
        # Verificación final
        print(f"[DEBUG] calibration_data['stereo'] es None: {self.calibration_data['stereo'] is None}")
        if left_camera_data and 'world_rotation' in left_camera_data:
            print("[DEBUG] ✓ world_rotation agregado a left_camera")
        if right_camera_data and 'world_rotation' in right_camera_data:
            print("[DEBUG] ✓ world_rotation agregado a right_camera")
    
    def _save_calibration(self):
        """Guarda los datos de calibración en formato JSON"""
        output_file = CalibrationConfig.CALIBRATION_FILE
        
        # Debug: verificar contenido antes de guardar
        print(f"[DEBUG] _save_calibration() - Verificando datos...")
        print(f"[DEBUG] stereo en calibration_data: {'stereo' in self.calibration_data}")
        if 'stereo' in self.calibration_data:
            print(f"[DEBUG] stereo es None: {self.calibration_data['stereo'] is None}")
            if self.calibration_data['stereo']:
                print(f"[DEBUG] stereo keys: {list(self.calibration_data['stereo'].keys())}")
        
        with open(output_file, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n✓ Datos de calibración guardados en: {output_file}")
        
        # Verificar que se guardó correctamente
        try:
            with open(output_file, 'r') as f:
                saved_data = json.load(f)
            print(f"[DEBUG] Verificación post-guardado:")
            print(f"[DEBUG] stereo guardado: {'stereo' in saved_data}")
            if 'stereo' in saved_data:
                print(f"[DEBUG] stereo es None: {saved_data['stereo'] is None}")
        except Exception as e:
            print(f"[DEBUG] Error verificando archivo guardado: {e}")
    
    @staticmethod
    def load_calibration():
        """
        Carga datos de calibración desde archivo
        
        Returns:
            dict: Datos de calibración o None si no existe
        """
        calib_file = CalibrationConfig.CALIBRATION_FILE
        
        if not calib_file.exists():
            print(f"⚠ No se encontró archivo de calibración: {calib_file}")
            return None
        
        try:
            with open(calib_file, 'r') as f:
                data = json.load(f)
            
            print(f"✓ Calibración cargada desde: {calib_file}")
            return data
        
        except Exception as e:
            print(f"✗ Error al cargar calibración: {e}")
            return None


def main():
    """Función principal para ejecutar calibración standalone"""
    print("\n" + "="*70)
    print("HERRAMIENTA DE CALIBRACIÓN ESTEREOSCÓPICA PROFESIONAL v2.0")
    print("="*70)
    print("\n📋 PROCESO DE CALIBRACIÓN:")
    print("  FASE 1: Calibración individual")
    print("    - Cámara izquierda: 25 fotos variadas")
    print("    - Cámara derecha: 25 fotos variadas")
    print("  FASE 2: Calibración estéreo")
    print("    - 8-15 pares simultáneos de ambas cámaras")
    print("\n✓ REQUISITOS:")
    print("  1. Tablero de ajedrez 8x8 impreso")
    print("  2. Medida exacta del tamaño de cada cuadrado")
    print("  3. Dos cámaras USB conectadas")
    print("  4. Buena iluminación uniforme")
    print("\n⚠ IMPORTANTE:")
    print("  - Mantén el tablero COMPLETO dentro del encuadre")
    print("  - Evita reflejos o sombras intensas")
    print("  - En Fase 1: mantén la cámara FIJA, solo mueve el tablero")
    print("  - En Fase 2: el tablero debe ser visible en AMBAS cámaras")
    print("="*70)
    
    input("\nPresiona ENTER para comenzar...")
    
    # IDs de cámaras
    cam_left_id = 1
    cam_right_id = 2
    
    # Crear gestor
    manager = CalibrationManager(
        cam_left_id=cam_left_id,
        cam_right_id=cam_right_id,
        resolution=(1280, 720)
    )
    
    # Ejecutar calibración
    success = manager.run_full_calibration()
    
    if success:
        print("\n🎉 ¡Calibración completa exitosa!")
        print("\nPuedes usar estos datos en tu aplicación de visión estéreo.")
    else:
        print("\n❌ La calibración no se completó.")
        print("Revisa los errores anteriores e intenta nuevamente.")


if __name__ == '__main__':
    main()

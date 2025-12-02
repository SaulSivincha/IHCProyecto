#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor Principal de Calibración
Orquesta todo el proceso de calibración en dos fases
"""

import cv2
import numpy as np
import json
from pathlib import Path
from .calibration_config import CalibrationConfig
from .camera_calibrator import CameraCalibrator
from .calibration_ui import CalibrationUI


class CalibrationManager:
    """
    Gestor principal del proceso de calibración estereoscópica
    Fase 1: Calibración individual de cada cámara
    Fase 2: Calibración estéreo (para implementar después)
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
        
        # Parámetros del tablero (se solicitarán al usuario)
        self.board_cols = CalibrationConfig.DEFAULT_CHESSBOARD_COLS
        self.board_rows = CalibrationConfig.DEFAULT_CHESSBOARD_ROWS
        self.square_size_mm = CalibrationConfig.DEFAULT_SQUARE_SIZE_MM
        
        # UI
        self.ui = CalibrationUI(width=resolution[0], height=resolution[1])
        
        # Calibradores
        self.calibrator_left = None
        self.calibrator_right = None
        
        # Resultados
        self.calibration_data = {}
        
        # Asegurar que existen los directorios
        CalibrationConfig.ensure_directories()
    
    def run_full_calibration(self):
        """
        Ejecuta el proceso completo de calibración
        
        Returns:
            bool: True si la calibración fue exitosa
        """
        print("\n" + "="*70)
        print("PROCESO DE CALIBRACION ESTEREOSCOPICA")
        print("="*70)
        print("\nFASE 1: Calibración individual de cámaras")
        print("FASE 2: Calibración estéreo (próximamente)")
        print("="*70 + "\n")
        
        # Paso 1: Solicitar parámetros del tablero
        if not self._configure_chessboard():
            print("✗ Configuración cancelada")
            return False
        
        # Paso 2: Calibrar cámara izquierda
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
        
        # Paso 3: Calibrar cámara derecha
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
        
        # Paso 4: Recopilar datos finales
        self._compile_calibration_data()
        
        # Paso 5: Guardar resultados
        self._save_calibration()
        
        print("\n" + "="*70)
        print("✓ CALIBRACION COMPLETADA EXITOSAMENTE")
        print("="*70)
        print(f"Datos guardados en: {CalibrationConfig.CALIBRATION_FILE}")
        print(f"Imágenes guardadas en: {CalibrationConfig.CALIBRATION_IMAGES_DIR}")
        print("="*70 + "\n")
        
        return True
    
    def _configure_chessboard(self):
        """
        Solicita al usuario los parámetros del tablero de calibración
        
        Returns:
            bool: True si se configuró exitosamente
        """
        window_name = "Configuracion del Tablero"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.resolution[0], self.resolution[1])
        
        # Frame negro para la UI
        base_frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        
        # ========== SOLICITAR NÚMERO DE COLUMNAS ==========
        input_value = str(self.board_cols)
        error_msg = ""
        
        while True:
            frame = base_frame.copy()
            frame = self.ui.draw_input_screen(
                frame,
                f"Columnas internas del tablero (esquinas):",
                input_value,
                error_msg
            )
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13:  # ENTER
                try:
                    cols = int(input_value)
                    if 4 <= cols <= 15:
                        self.board_cols = cols
                        break
                    else:
                        error_msg = "Valor debe estar entre 4 y 15"
                except ValueError:
                    error_msg = "Ingresa un numero valido"
            elif key == 27:  # ESC
                cv2.destroyWindow(window_name)
                return False
            elif key == 8 and len(input_value) > 0:  # BACKSPACE
                input_value = input_value[:-1]
                error_msg = ""
            elif 48 <= key <= 57:  # Números 0-9
                input_value += chr(key)
                error_msg = ""
        
        # ========== SOLICITAR NÚMERO DE FILAS ==========
        input_value = str(self.board_rows)
        error_msg = ""
        
        while True:
            frame = base_frame.copy()
            frame = self.ui.draw_input_screen(
                frame,
                f"Filas internas del tablero (esquinas):",
                input_value,
                error_msg
            )
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13:  # ENTER
                try:
                    rows = int(input_value)
                    if 4 <= rows <= 15:
                        self.board_rows = rows
                        break
                    else:
                        error_msg = "Valor debe estar entre 4 y 15"
                except ValueError:
                    error_msg = "Ingresa un numero valido"
            elif key == 27:  # ESC
                cv2.destroyWindow(window_name)
                return False
            elif key == 8 and len(input_value) > 0:  # BACKSPACE
                input_value = input_value[:-1]
                error_msg = ""
            elif 48 <= key <= 57:  # Números 0-9
                input_value += chr(key)
                error_msg = ""
        
        # ========== SOLICITAR TAMAÑO DEL CUADRADO ==========
        input_value = str(self.square_size_mm)
        error_msg = ""
        
        while True:
            frame = base_frame.copy()
            frame = self.ui.draw_input_screen(
                frame,
                f"Tamano del cuadrado (milimetros):",
                input_value,
                error_msg
            )
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13:  # ENTER
                try:
                    size = float(input_value)
                    if 5.0 <= size <= 100.0:
                        self.square_size_mm = size
                        break
                    else:
                        error_msg = "Valor debe estar entre 5 y 100 mm"
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
        print(f"  Columnas: {self.board_cols}")
        print(f"  Filas: {self.board_rows}")
        print(f"  Tamaño cuadrado: {self.square_size_mm} mm")
        
        return True
    
    def _calibrate_single_camera(self, calibrator, camera_name):
        """
        Ejecuta la calibración de una cámara individual
        
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
        
        # Deshabilitar autofocus si es posible
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
                ""  # La instrucción se genera internamente
            )
            
            cv2.imshow(window_name, frame_display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' ') and detected:
                # Capturar imagen
                calibrator.capture_image(frame, corners)
                photo_count += 1
                print(f"✓ Foto {photo_count}/{total_photos} capturada")
                
                # Pequeña pausa para evitar capturas duplicadas
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
    
    def _compile_calibration_data(self):
        """Recopila todos los datos de calibración en un diccionario"""
        self.calibration_data = {
            'version': '1.0',
            'board_config': {
                'cols': self.board_cols,
                'rows': self.board_rows,
                'square_size_mm': self.square_size_mm
            },
            'left_camera': self.calibrator_left.get_calibration_data(),
            'right_camera': self.calibrator_right.get_calibration_data(),
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
        """Guarda los datos de calibración en formato JSON"""
        output_file = CalibrationConfig.CALIBRATION_FILE
        
        with open(output_file, 'w') as f:
            json.dump(self.calibration_data, f, indent=4)
        
        print(f"\n✓ Datos de calibración guardados en: {output_file}")
    
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
    print("HERRAMIENTA DE CALIBRACIÓN ESTEREOSCÓPICA PROFESIONAL")
    print("="*70)
    print("\n📋 REQUISITOS:")
    print("  1. Tablero de ajedrez impreso")
    print("  2. Medida exacta del tamaño de cada cuadrado")
    print("  3. Dos cámaras USB conectadas")
    print("  4. Buena iluminación uniforme")
    print("\n⚠ IMPORTANTE:")
    print("  - Mantén el tablero COMPLETO dentro del encuadre")
    print("  - Evita reflejos o sombras intensas")
    print("  - Mantén la cámara FIJA, solo mueve el tablero")
    print("  - Captura 25 fotos siguiendo las instrucciones en pantalla")
    print("="*70)
    
    input("\nPresiona ENTER para comenzar...")
    
    # IDs de cámaras (pueden configurarse)
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
        print("\n🎉 ¡Calibración completada exitosamente!")
        print("\nPuedes usar estos datos en tu aplicación.")
    else:
        print("\n❌ La calibración no se completó.")
        print("Revisa los errores anteriores e intenta nuevamente.")


if __name__ == '__main__':
    main()

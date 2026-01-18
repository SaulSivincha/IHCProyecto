#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Recursos Persistentes
Mantiene cámaras, detectores y sintetizador entre cambios de modo
para evitar la reinicialización lenta.
"""

import time
import os
import fluidsynth
from typing import Optional, Tuple

from src.vision import video_thread
from src.vision.hand_detector import HandDetector
from src.vision import load_depth_estimator
from src.vision.stereo_config import StereoConfig
from src.config.app_config import AppConfig


class PersistentResources:
    """
    Singleton que mantiene recursos costosos de inicializar.
    Solo se inicializan una vez y se reutilizan entre modos.
    """
    
    _instance: Optional['PersistentResources'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Estado
        self._cameras_ready = False
        self._detectors_ready = False
        self._synth_ready = False
        self._depth_ready = False
        
        # Recursos
        self.cam_left: Optional[video_thread.VideoThread] = None
        self.cam_right: Optional[video_thread.VideoThread] = None
        self.left_detector: Optional[HandDetector] = None
        self.right_detector: Optional[HandDetector] = None
        self.synth: Optional[fluidsynth.Synth] = None
        self.sfid: Optional[int] = None
        self.depth_estimator = None
        self.use_stereo_calibration = False
        
        # Configuración
        self.config: Optional[StereoConfig] = None
        
    def initialize_all(self, config: StereoConfig) -> bool:
        """
        Inicializa todos los recursos de una vez.
        Retorna True si todo se inicializó correctamente.
        """
        self.config = config
        
        print("\n" + "="*60)
        print("[INFO] INICIALIZANDO RECURSOS (solo una vez)...")
        print("="*60)
        
        start_time = time.time()
        
        # 1. Cámaras
        if not self._cameras_ready:
            self._init_cameras()
        
        # 2. Detectores de manos
        if not self._detectors_ready:
            self._init_detectors()
        
        # 3. Sintetizador
        if not self._synth_ready:
            self._init_synth()
        
        # 4. Estimador de profundidad
        if not self._depth_ready:
            self._init_depth_estimator()
        
        elapsed = time.time() - start_time
        print("="*60)
        print(f"[EXITO] RECURSOS LISTOS en {elapsed:.2f} segundos")
        print("="*60 + "\n")
        
        return self._cameras_ready and self._synth_ready
    

    def _init_cameras(self):
        """Inicializa las cámaras"""
        left_id = self.config.LEFT_CAMERA_SOURCE
        right_id = self.config.RIGHT_CAMERA_SOURCE
        print(f"  Iniciando camaras (LEFT={left_id}, RIGHT={right_id})...")
        print("  NOTA: Iniciando secuencialmente para garantizar carga dual...")
        
        try:
            # 1. Iniciar Cámara Izquierda
            print(f"  > Iniciando Izquierda ({left_id})...")
            self.cam_left = video_thread.VideoThread(
                video_source=left_id,
                video_width=self.config.PIXEL_WIDTH,
                video_height=self.config.PIXEL_HEIGHT,
                video_frame_rate=self.config.FRAME_RATE,
                buffer_all=False,
                try_to_reconnect=False
            )
            self.cam_left.start()
            
            # ESPERA CRÍTICA
            time.sleep(1.0)
            
            # 2. Iniciar Cámara Derecha
            print(f"  > Iniciando Derecha ({right_id})...")
            self.cam_right = video_thread.VideoThread(
                video_source=right_id,
                video_width=self.config.PIXEL_WIDTH,
                video_height=self.config.PIXEL_HEIGHT,
                video_frame_rate=self.config.FRAME_RATE,
                buffer_all=False,
                try_to_reconnect=False
            )
            self.cam_right.start()
            
            # Esperar para estabilizar
            time.sleep(0.5)
            
            left_ok = self.cam_left.is_available()
            right_ok = self.cam_right.is_available()
            
            if left_ok and right_ok:
                self._cameras_ready = True
                print("  OK Camaras listas")
            else:
                # Mostrar cuál falló
                if not left_ok:
                    print(f"  ADVERTENCIA: Camara izquierda ({left_id}) no disponible")
                if not right_ok:
                    print(f"  ADVERTENCIA: Camara derecha ({right_id}) no disponible")
                # Permitir continuar si al menos una funciona
                if left_ok or right_ok:
                    self._cameras_ready = True
                    print("  OK Continuando con camaras parciales")
                else:
                    print("  ERROR: Ninguna camara disponible")
                    print("         Ve a Configuracion > Camaras para seleccionar las correctas")
                
        except Exception as e:
            print(f"  ERROR iniciando camaras: {e}")
    
    def _init_detectors(self):
        """Inicializa los detectores de manos"""
        print("  [INFO] Iniciando detectores de manos...")
        
        try:
            self.left_detector = HandDetector(
                staticImageMode=False,
                detectionCon=self.config.HAND_DETECTION_CONFIDENCE,
                trackCon=self.config.HAND_TRACKING_CONFIDENCE
            )
            
            self.right_detector = HandDetector(
                staticImageMode=False,
                detectionCon=self.config.HAND_DETECTION_CONFIDENCE,
                trackCon=self.config.HAND_TRACKING_CONFIDENCE
            )
            
            self._detectors_ready = True
            print("  [EXITO] Detectores listos")
            
        except Exception as e:
            print(f"  [ERROR] Error iniciando detectores: {e}")
    
    def _init_synth(self):
        """Inicializa el sintetizador y carga el SoundFont"""
        print("  [INFO] Iniciando sintetizador...")
        
        try:
            # Intentar varios drivers de audio en orden de preferencia para Windows
            drivers = ['dsound', 'wasapi', 'portaudio', 'winmm']
            started = False
            self.synth = fluidsynth.Synth()
            
            error_msgs = []
            for driver in drivers:
                try:
                    print(f"  [INTENTO] Iniciando driver de audio: {driver}...")
                    self.synth.start(driver=driver)
                    # Si no lanza excepción, asumimos éxito inicial
                    started = True
                    print(f"  [EXITO] Driver {driver} iniciado.")
                    break
                except Exception as e:
                    error_msgs.append(f"{driver}: {e}")
                    # Reiniciar objeto synth por si quedo en mal estado
                    self.synth.delete()
                    self.synth = fluidsynth.Synth()
            
            if not started:
                print(f"  [FALLO] No se pudo iniciar audio. Errores: {'; '.join(error_msgs)}")
                # Continuar sin audio, pero marcar flag
                self._synth_ready = False
                return

            # Buscar SoundFont
            soundfont_paths = [
                r"C:\CodingWindows\IHCProyecto\utils\fluid\fluid\FluidR3_GM.sf2",
                r"C:\CodingWindows\IHCProyecto\utils\fluid\FluidR3_GM.sf2",
                AppConfig.get_soundfont_path()
            ]
            
            for sf_path in soundfont_paths:
                if sf_path and os.path.exists(sf_path):
                    try:
                        self.sfid = self.synth.sfload(sf_path)
                        self.synth.program_select(0, self.sfid, 0, 0)
                        self._synth_ready = True
                        print(f"  [EXITO] SoundFont cargado: {os.path.basename(sf_path)}")
                        break
                    except Exception as e:
                        print(f"  [ALERTA] Error cargando SF2 {sf_path}: {e}")
            
            if not self._synth_ready:
                print("  [ERROR] No se encontro SoundFont valido")
                
        except Exception as e:
            print(f"  [ERROR] Error general iniciando sintetizador: {e}")
    
    def _init_depth_estimator(self):
        """Inicializa el estimador de profundidad si hay calibración"""
        print("  [INFO] Cargando calibracion estereo...")
        
        try:
            from src.calibration.calibration_config import CalibrationConfig
            
            if CalibrationConfig.calibration_exists():
                self.depth_estimator = load_depth_estimator(CalibrationConfig.CALIBRATION_FILE)
                
                # IMPORTANTE: Establecer resolución de runtime
                # La calibración se hizo a una resolución (ej: 1280x720)
                # pero runtime puede usar otra (ej: 640x480)
                runtime_w = self.config.PIXEL_WIDTH
                runtime_h = self.config.PIXEL_HEIGHT
                self.depth_estimator.set_runtime_resolution(runtime_w, runtime_h)
                
                self.use_stereo_calibration = True
                self._depth_ready = True
                print(f"  [EXITO] Calibracion cargada (baseline: {self.depth_estimator.baseline_cm:.2f} cm)")
            else:
                print("  [ALERTA] No hay calibracion estereo")
                self._depth_ready = True  # No es error, simplemente no hay
                
        except Exception as e:
            print(f"  [ALERTA] Calibracion no disponible: {e}")
            self._depth_ready = True
    
    def stop_cameras(self):
        """Detiene las cámaras y libera recursos"""
        print("  [INFO] Deteniendo cámaras...")
        try:
            if self.cam_left:
                self.cam_left.stop()
                self.cam_left = None
        except Exception as e:
            print(f"Error deteniendo camara izquierda: {e}")
        
        try:
            if self.cam_right:
                self.cam_right.stop()
                self.cam_right = None
        except Exception as e:
            print(f"Error deteniendo camara derecha: {e}")
        
        self._cameras_ready = False
        print("  [INFO] Cámaras detenidas")

    def reload_depth_estimator(self):
        """Recarga el estimador de profundidad (después de recalibrar)"""
        print("  [INFO] Recargando configuración estéreo y profundidad...")
        
        # 1. Recargar configuración estática (StereoConfig)
        if self.config:
            # StereoConfig es una clase con métodos estáticos/clase
            StereoConfig.load_calibration()
            
        # 2. Reiniciar estimador
        self._depth_ready = False
        self._init_depth_estimator()
    
    def restart_cameras(self, config: StereoConfig):
        """Reinicia las cámaras con nueva configuración"""
        print("  Deteniendo camaras actuales...")
        
        # Detener cámaras actuales
        try:
            if self.cam_left:
                self.cam_left.stop()
                self.cam_left = None
        except:
            pass
        
        try:
            if self.cam_right:
                self.cam_right.stop()
                self.cam_right = None
        except:
            pass
        
        self._cameras_ready = False
        self.config = config
        
        # Esperar un momento para que se liberen los recursos
        time.sleep(0.5)
        
        # Reiniciar con nueva configuración
        self._init_cameras()
        
        # Reiniciar también los detectores para limpiar estado
        if self._cameras_ready:
            self.cam_left.start()
            self.cam_right.start()
            time.sleep(0.3)
    
    def get_cameras(self) -> Tuple:
        """Retorna las cámaras"""
        return self.cam_left, self.cam_right
    
    def get_detectors(self) -> Tuple:
        """Retorna los detectores de manos"""
        return self.left_detector, self.right_detector
    
    def get_synth(self):
        """Retorna el sintetizador"""
        return self.synth
    
    def is_ready(self) -> bool:
        """Verifica si todos los recursos esenciales están listos"""
        return self._cameras_ready and self._synth_ready
    
    def cleanup(self):
        """Libera todos los recursos"""
        print("\n[INFO] Limpiando recursos...")
        
        try:
            if self.synth:
                self.synth.delete()
                self.synth = None
        except:
            pass
        
        try:
            if self.cam_left:
                self.cam_left.stop()
                self.cam_left = None
        except:
            pass
        
        try:
            if self.cam_right:
                self.cam_right.stop()
                self.cam_right = None
        except:
            pass
        
        self._cameras_ready = False
        self._detectors_ready = False
        self._synth_ready = False
        self._depth_ready = False
        
        print("[EXITO] Recursos liberados")


# Función de acceso global
_resources: Optional[PersistentResources] = None


def get_resources() -> PersistentResources:
    """Obtiene la instancia global de recursos"""
    global _resources
    if _resources is None:
        _resources = PersistentResources()
    return _resources


def initialize_resources(config: StereoConfig) -> bool:
    """Inicializa los recursos si no están listos"""
    resources = get_resources()
    if not resources.is_ready():
        return resources.initialize_all(config)
    return True


def cleanup_resources():
    """Limpia todos los recursos"""
    global _resources
    if _resources:
        _resources.cleanup()
        _resources = None


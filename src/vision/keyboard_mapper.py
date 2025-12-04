#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyboardMap Modular - Sistema de detección refactorizado
Usa arquitectura modular con algoritmos independientes

@author: mherrera
@updated: 2025 - Modular Architecture
"""
import time
import numpy as np
from collections import deque
from src.config.app_config import AppConfig

# Sistema modular de algoritmos
from src.vision.algorithms.algorithm_manager import AlgorithmManager
from src.vision.algorithms.algo_antirebote import AntireboteAlgorithm
from src.vision.algorithms.algo_histeresis import HisteresisAlgorithm
from src.vision.algorithms.algo_suavizado import SuavizadoAlgorithm
from src.vision.algorithms.algo_multinota import MultinotaAlgorithm
from src.vision.algorithms.algo_filtro_espacial import FiltroEspacialAlgorithm
from src.vision.algorithms.algo_zona_salida import ZonaSalidaAlgorithm
from src.vision.algorithms.algorithms_config import ALGORITHMS_CONFIG, EXECUTION_ORDER


class KeyboardMapModular:
    """
    Mapeador de teclado modular con algoritmos independientes.
    
    Ventajas:
    - Algoritmos separados en archivos individuales
    - Fácil agregar/eliminar algoritmos
    - Configuración centralizada
    - Activar/desactivar sin tocar código
    """
    
    def __init__(self, depth_threshold=None, config_preset='default'):
        """
        Inicializa el mapeador con sistema modular.
        
        Args:
            depth_threshold: Profundidad máxima (cm) para detectar contacto
            config_preset: Preset de configuración ('default', 'sensitive', 'stable', 'minimal')
        """
        self.prev_map = np.empty(0, dtype=bool)
        self.depth_threshold = depth_threshold if depth_threshold is not None else AppConfig.DEPTH_THRESHOLD
        self.finger_depths = {}
        
        # Sistema de velocidad (legacy, para compatibilidad)
        self.finger_depth_history = {}
        self.velocity_threshold = AppConfig.VELOCITY_THRESHOLD
        self.velocity_enabled = AppConfig.VELOCITY_ENABLED
        self.velocity_history_size = AppConfig.VELOCITY_HISTORY_SIZE
        
        # NUEVO: Sistema modular de algoritmos
        self.algorithm_manager = AlgorithmManager()
        self._initialize_algorithms()
        
    def _initialize_algorithms(self):
        """Inicializa y registra todos los algoritmos según configuración."""
        
        # Crear instancias de algoritmos
        algorithms = {
            'Antirebote': AntireboteAlgorithm(),
            'Histéresis': HisteresisAlgorithm(),
            'Suavizado': SuavizadoAlgorithm(),
            'Multi-nota': MultinotaAlgorithm(),
            'Filtro Espacial': FiltroEspacialAlgorithm(),
            'Zona Salida': ZonaSalidaAlgorithm()
        }
        
        # Registrar algoritmos en orden de ejecución
        for algo_name in EXECUTION_ORDER:
            if algo_name in algorithms:
                algorithm = algorithms[algo_name]
                
                # Aplicar configuración desde algorithms_config.py
                if algo_name in ALGORITHMS_CONFIG:
                    config = ALGORITHMS_CONFIG[algo_name]
                    
                    # Activar/desactivar
                    if config['enabled']:
                        algorithm.enable()
                    else:
                        algorithm.disable()
                    
                    # Configurar parámetros
                    if config['params']:
                        algorithm.configure(**config['params'])
                
                # Registrar en el manager
                self.algorithm_manager.register_algorithm(algorithm)
    
    def set_depth_threshold(self, threshold):
        """Actualiza el umbral de profundidad."""
        self.depth_threshold = threshold
    
    def get_kayboard_map(self, virtual_keyboard, fingertips_pos, 
                        finger_depths=None, keyboard_n_key=13):
        """
        Genera el mapa de teclado usando el sistema modular de algoritmos.
        
        Args:
            virtual_keyboard: Instancia de VirtualKeyboard
            fingertips_pos: Lista de posiciones de dedos [(hand_id, tip_id, x, y), ...]
            finger_depths: Dict con profundidades {(hand_id, tip_id): depth_cm}
            keyboard_n_key: Número de teclas
            
        Returns:
            tuple: (on_map, off_map) - Arrays booleanos de teclas presionadas/liberadas
        """
        curr_map = np.full(keyboard_n_key, False, dtype=bool)
        on_map = np.full(keyboard_n_key, False, dtype=bool)
        off_map = np.full(keyboard_n_key, False, dtype=bool)
        
        # Inicializar prev_map si es primera vez
        if len(self.prev_map) == 0:
            self.prev_map = np.full(keyboard_n_key, False, dtype=bool)
        
        if finger_depths is None:
            finger_depths = {}
        
        # FASE 1: Recolectar detecciones brutas
        raw_detections = []
        current_time = time.time()
        
        for fingertip_pos in fingertips_pos:
            hand_id = fingertip_pos[0]
            tip_id = fingertip_pos[1]
            x_pos = fingertip_pos[2]
            y_pos = fingertip_pos[3]
            
            finger_id = (hand_id, tip_id)
            
            # Verificar intersección con teclado
            if virtual_keyboard.intersect((x_pos, y_pos)):
                key = virtual_keyboard.find_key(x_pos, y_pos)
                
                if 0 <= key < keyboard_n_key:
                    # Obtener profundidad
                    if finger_id in finger_depths:
                        depth = finger_depths[finger_id]
                        
                        # Actualizar historial de profundidad
                        if finger_id not in self.finger_depth_history:
                            self.finger_depth_history[finger_id] = deque(maxlen=self.velocity_history_size)
                        self.finger_depth_history[finger_id].append(depth)
                        
                        # Calcular velocidad
                        velocity = 0.0
                        if len(self.finger_depth_history[finger_id]) >= 2:
                            history = list(self.finger_depth_history[finger_id])
                            velocity = history[-2] - history[-1]
                        
                        # Verificar condición básica de activación
                        should_activate = False
                        
                        if self.velocity_enabled and len(self.finger_depth_history[finger_id]) >= 2:
                            # Modo velocidad
                            if depth <= self.depth_threshold and velocity >= self.velocity_threshold:
                                should_activate = True
                        else:
                            # Modo clásico
                            if depth <= self.depth_threshold:
                                should_activate = True
                        
                        if should_activate:
                            raw_detections.append((finger_id, key, depth, velocity, x_pos, y_pos))
                    else:
                        # Fallback sin profundidad
                        raw_detections.append((finger_id, key, 0.0, 0.0, x_pos, y_pos))
        
        # FASE 2: Procesar detecciones a través de algoritmos modulares
        context = {
            'timestamp': current_time,
            'virtual_keyboard': virtual_keyboard,
            'keyboard_n_key': keyboard_n_key
        }
        
        # Aplicar cadena de algoritmos
        filtered_detections = self.algorithm_manager.process_detections(raw_detections, context)
        
        # FASE 3: Aplicar detecciones filtradas al mapa
        for detection in filtered_detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            curr_map[key] = True
            self.finger_depths[finger_id] = depth
        
        # FASE 4: Calcular cambios (on/off)
        on_map = np.logical_and(curr_map, np.logical_not(self.prev_map))
        off_map = np.logical_and(self.prev_map, np.logical_not(curr_map))
        
        # Actualizar prev_map
        self.prev_map = curr_map.copy()
        
        return on_map, off_map
    
    # ==================== MÉTODOS DE CONTROL ====================
    
    def enable_algorithm(self, name):
        """Activa un algoritmo específico."""
        self.algorithm_manager.enable_algorithm(name)
    
    def disable_algorithm(self, name):
        """Desactiva un algoritmo específico."""
        self.algorithm_manager.disable_algorithm(name)
    
    def configure_algorithm(self, name, **params):
        """Configura parámetros de un algoritmo."""
        self.algorithm_manager.configure_algorithm(name, **params)
    
    def reset_algorithms(self):
        """Reinicia el estado de todos los algoritmos."""
        self.algorithm_manager.reset_all()
    
    def get_algorithm_stats(self):
        """Obtiene estadísticas de todos los algoritmos."""
        return self.algorithm_manager.get_all_stats()
    
    def get_algorithm_configs(self):
        """Obtiene configuración de todos los algoritmos."""
        return self.algorithm_manager.get_all_configs()
    
    def print_algorithm_status(self):
        """Imprime el estado actual de todos los algoritmos."""
        self.algorithm_manager.print_status()
    
    def get_current_chord(self):
        """
        Obtiene el acorde actual detectado por el algoritmo Multi-nota.
        
        Returns:
            set: Conjunto de teclas en el acorde actual
        """
        multinota = self.algorithm_manager.get_algorithm('Multi-nota')
        if multinota and multinota.is_enabled():
            return multinota.get_current_chord()
        return set()


# Alias para compatibilidad con código existente
KeyboardMap = KeyboardMapModular

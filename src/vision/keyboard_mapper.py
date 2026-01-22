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
from src.vision.stereo_config import StereoConfig

# Sistema modular de algoritmos - solo importar lo necesario
from src.vision.algorithms.algorithm_manager import AlgorithmManager

# Physics engine for velocity and triggering
from src.vision.piano_physics import VelocityCalculator, TriggerSystem


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
        self.depth_threshold = depth_threshold if depth_threshold is not None else StereoConfig.DEPTH_THRESHOLD
        self.finger_depths = {}
        
        # Sistema de velocidad (legacy, para compatibilidad)
        self.finger_depth_history = {}
        self.velocity_threshold = StereoConfig.VELOCITY_THRESHOLD
        self.velocity_enabled = StereoConfig.VELOCITY_ENABLED
        self.velocity_history_size = StereoConfig.VELOCITY_HISTORY_SIZE
        
        # SISTEMA DE ESTADO POR DEDO:
        # Trackea si cada dedo está 'pressing' o 'released'
        # Un dedo en 'pressing' NO puede activar nuevas teclas hasta que suba
        self.finger_state = {}  # {finger_id: 'pressing' | 'released'}
        self.finger_last_depth = {}  # {finger_id: last_depth} - para trackear globalmente
        self.release_height = 5.0  # cm - debe subir a 5cm para liberar (mayor que threshold de 4cm)
        
        # Debugeo
        self._debug_frame_count = 0
        
        # NUEVO: Sistema modular de algoritmos - USAR SINGLETON GLOBAL
        from src.vision.algorithms import get_algorithm_manager
        self.algorithm_manager = get_algorithm_manager()
        
        # PHYSICS ENGINE: Velocity and Triggering
        self.physics_velocity = VelocityCalculator()
        self.physics_trigger = TriggerSystem()
        self.active_velocities = {}  # {key_id: midi_velocity}
        
        # Configuración de suavizado de profundidad (dinámico desde algorithms_config)
        self._update_smoothing_config()
        
    def _update_smoothing_config(self):
        """Actualiza parámetros de suavizado desde algorithms_config."""
        from src.vision.algorithms.algorithms_config import ALGORITHMS_CONFIG
        
        smoothing_config = ALGORITHMS_CONFIG.get('Suavizado de Profundidad', {})
        self.smoothing_enabled = smoothing_config.get('enabled', True)
        params = smoothing_config.get('params', {})
        self.smoothing_window = params.get('smoothing_window', 3)
        self.outlier_threshold = params.get('outlier_threshold', 15.0)
        
    def _initialize_algorithms(self):
        """Inicializa y registra todos los algoritmos según configuración."""
        
        # NOTA: Este método ya no es necesario porque el manager global
        # ya está inicializado por get_algorithm_manager()
        # Se mantiene para compatibilidad pero no hace nada
        pass
    
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
        
        # FASE 1: Recolectar detecciones brutas (TODAS las intersecciones)
        raw_detections = []
        current_time = time.time()
        
        for fingertip_pos in fingertips_pos:
            hand_id = fingertip_pos[0]
            tip_id = fingertip_pos[1]
            x_pos = fingertip_pos[2]
            y_pos = fingertip_pos[3]
            
            finger_id = (hand_id, tip_id)
            
            # OPTIMIZACIÓN: Verificar profundidad PRIMERO (operación más barata)
            # Si la mano está muy lejos (flotando), evitamos cálculos espaciales costosos
            if finger_id not in finger_depths:
                # [FIX] Sin datos de profundidad: SALTAR FRAME
                # ANTES: Usábamos depth=99.0, pero esto contaminaba el historial
                # de velocidad causando spikes masivos (vel=98cm/frame).
                # AHORA: Simplemente no procesamos este dedo este frame.
                # El historial se mantiene limpio y velocity se calcula
                # solo con datos válidos.
                continue
            else:
                depth = finger_depths[finger_id]
                
                # ESTRATEGIA DE VALIDACIÓN ESTRICTA (Sin Clamping)
                # Evitar "falsos positivos" cuando la mano está muy cerca de la cámara
                # 
                # Rango Físico Razonable para profundidad RELATIVA (depth = abs - mesa):
                # -5.0 cm: Presionando fuerte (dedo "atravesando" el plano virtual)
                # +25.0 cm: Mano levantada en el aire sobre la mesa
                
                if depth < -5.0 or depth > 25.0:
                    # Caso: Profundidad fuera de rango físico posible.
                    # - < -5.0: Error de calibración o mano muy cerca de cámara
                    # - > +25.0: Mano muy lejos del teclado (ignorar)
                    
                    if self._debug_frame_count % 30 == 0:
                        # print(f"[RECHAZADO] Dedo {finger_id} Depth={depth:.1f}cm (Fuera de rango -5 a +25)")
                        pass
                        
                    # Acción: DESCARTAR.
                    continue
            
            # AHORA verificar intersección con teclado (solo si está cerca)
            if virtual_keyboard.intersect((x_pos, y_pos)):
                key = virtual_keyboard.find_key(x_pos, y_pos)
                
                # Verificar que key no sea None y esté en rango válido
                if key is not None and 0 <= key < keyboard_n_key:
                    # Actualizar historial de profundidad
                    if finger_id not in self.finger_depth_history:
                        self.finger_depth_history[finger_id] = deque(maxlen=self.velocity_history_size)
                    self.finger_depth_history[finger_id].append(depth)
                    
                    # NUEVO: Suavizar profundidad para reducir ruido de tracking
                    depth_smoothed = depth
                    
                    if self.smoothing_enabled and len(self.finger_depth_history[finger_id]) >= self.smoothing_window:
                        history = list(self.finger_depth_history[finger_id])
                        # Filtrar outliers extremos antes de promediar
                        recent_values = history[-self.smoothing_window:]
                        median_val = sorted(recent_values)[len(recent_values)//2]
                        filtered = [v for v in recent_values if abs(v - median_val) < self.outlier_threshold]
                        if len(filtered) > 0:
                            depth_smoothed = sum(filtered) / len(filtered)
                    
                    # Calcular velocidad usando profundidad suavizada
                    velocity = 0.0
                    if len(self.finger_depth_history[finger_id]) >= 2:
                        history = list(self.finger_depth_history[finger_id])
                        velocity = history[-2] - history[-1]
                    
                    # AGREGAR a raw_detections
                    raw_detections.append((finger_id, key, depth_smoothed, velocity, x_pos, y_pos))
        
        # DEBUG INICIAL: Mostrar cuántas intersecciones se detectaron
        if not hasattr(self, '_debug_frame_count'):
            self._debug_frame_count = 0
        self._debug_frame_count += 1
        
        # FASE 1.5: Aplicar filtro de profundidad SOLO si hay algoritmos activos
        has_active_algorithms = any(algo.is_enabled() for algo in self.algorithm_manager.algorithms)
        
        if has_active_algorithms:
            filtered_by_depth = []
            activation_threshold = self.depth_threshold  # 0.5cm
            
            # DEBUG CRÍTICO: Ver TODOS los valores de depth que llegan
            if self._debug_frame_count % 20 == 0 and len(raw_detections) > 0:
                print(f"\n[DEBUG RAW] {len(raw_detections)} detecciones:")
                for det in raw_detections[:3]:
                    fid, key, depth, vel, x, y = det
                    state = self.finger_state.get(fid, 'released')
                    print(f"  Dedo {fid}: key={key}, depth={depth:.2f}cm, vel={vel:.2f}, state={state}")
            
            # PRIMERO: Actualizar estado de TODOS los dedos detectados
            detected_fingers = set()
            for detection in raw_detections:
                finger_id = detection[0]
                depth = detection[2]
                detected_fingers.add(finger_id)
                
                # Actualizar last_depth
                self.finger_last_depth[finger_id] = depth
                
                # Si el dedo subió lo suficiente, liberarlo
                if depth > self.release_height:
                    if finger_id in self.finger_state and self.finger_state[finger_id] == 'pressing':
                        self.finger_state[finger_id] = 'released'
                        print(f"[RELEASE] Dedo {finger_id} liberado (depth={depth:.1f}cm > {self.release_height})")
            
            # Limpiar dedos que desaparecieron
            fingers_to_clean = [fid for fid in self.finger_state if fid not in detected_fingers]
            for fid in fingers_to_clean:
                del self.finger_state[fid]
                if fid in self.finger_last_depth:
                    del self.finger_last_depth[fid]
            
            # AHORA: Filtrar detecciones usando PHYSICS ENGINE
            for detection in raw_detections:
                finger_id, key, depth, velocity, x_pos, y_pos = detection
                
                # A. Calcular Velocidad Real usando Physics Engine
                midi_vel = self.physics_velocity.calculate_velocity(finger_id, depth, current_time)
                
                # B. Calcular Z Relativo (Profundidad respecto a la mesa)
                # depth ya es relativo (depth_absolute - keyboard_distance)
                # Para physics: z_relative = depth - threshold
                # Si depth < threshold (ej. 0.5), z_relative es negativo = presión
                z_relative_physics = depth - self.depth_threshold
                
                # C. Evaluar Disparo usando Trigger System
                action = self.physics_trigger.evaluate_trigger(key, z_relative_physics)
                
                if action == 'NOTE_ON':
                    self.finger_state[finger_id] = 'pressing'
                    self.active_velocities[key] = midi_vel  # GUARDAR VELOCIDAD
                    filtered_by_depth.append(detection)
                    print(f"[NOTE_ON] Tecla {key} (depth={depth:.2f}cm, vel={midi_vel})")
                    
                elif action == 'NOTE_OFF':
                    self.finger_state[finger_id] = 'released'
                    # Limpiar velocidad almacenada
                    if key in self.active_velocities:
                        del self.active_velocities[key]
                    # No añadimos a filtered, dejar que se apague natural
                    
                elif action == 'HOLD':
                    if self.finger_state.get(finger_id) == 'pressing':
                        filtered_by_depth.append(detection)
            
            # DEBUG: Mostrar resultado del filtro
            raw_detections = filtered_by_depth
        
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
        # Si es suavizado de profundidad, actualizar también nuestra config local
        if name == 'Suavizado de Profundidad':
            # Actualizar en algorithms_config
            self.algorithm_manager.configure_algorithm(name, **params)
            # Recargar nuestra configuración local
            self._update_smoothing_config()
            print(f"✓ Suavizado actualizado: enabled={self.smoothing_enabled}, window={self.smoothing_window}, threshold={self.outlier_threshold}cm")
        else:
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

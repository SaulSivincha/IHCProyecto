#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyboardMap Modular - Sistema de detección refactorizado
"""
import time
import numpy as np
from collections import deque
from src.config.app_config import AppConfig
from src.vision.stereo_config import StereoConfig

# Sistema modular de algoritmos
from src.vision.algorithms.algorithm_manager import AlgorithmManager

# IMPORTACIÓN CORREGIDA: Importamos las clases individuales, no 'PianoPhysics'
from src.vision.piano_physics import VelocityCalculator, TriggerSystem

class KeyboardMapModular:
    
    def __init__(self, depth_threshold=None, config_preset='default'):
        self.prev_map = np.empty(0, dtype=bool)
        self.depth_threshold = depth_threshold if depth_threshold is not None else StereoConfig.DEPTH_THRESHOLD
        self.finger_depths = {}
        
        # Historial para algoritmos legacy
        self.finger_depth_history = {}
        self.velocity_threshold = StereoConfig.VELOCITY_THRESHOLD
        self.velocity_enabled = StereoConfig.VELOCITY_ENABLED
        self.velocity_history_size = StereoConfig.VELOCITY_HISTORY_SIZE
        
        # ESTADO DEL DEDO
        self.finger_state = {}
        self.finger_last_depth = {}
        
        # CORRECCIÓN CRÍTICA: Altura de liberación bajada a 0.8 cm
        # Esto permite tocar rápido sin tener que levantar tanto la mano.
        self.release_height = 0.8
        
        # Debug
        self._debug_frame_count = 0
        
        # Sistema de algoritmos
        from src.vision.algorithms import get_algorithm_manager
        self.algorithm_manager = get_algorithm_manager()
        
        # MOTORES DE FÍSICA
        self.physics_velocity = VelocityCalculator()
        self.physics_trigger = TriggerSystem()
        self.active_velocities = {}
        
        self._update_smoothing_config()
        
    def _update_smoothing_config(self):
        from src.vision.algorithms.algorithms_config import ALGORITHMS_CONFIG
        smoothing_config = ALGORITHMS_CONFIG.get('Suavizado de Profundidad', {})
        self.smoothing_enabled = smoothing_config.get('enabled', True)
        params = smoothing_config.get('params', {})
        self.smoothing_window = params.get('smoothing_window', 3)
        self.outlier_threshold = params.get('outlier_threshold', 15.0)
        
    def get_kayboard_map(self, virtual_keyboard, fingertips_pos, 
                        finger_depths=None, keyboard_n_key=13):
        
        curr_map = np.full(keyboard_n_key, False, dtype=bool)
        on_map = np.full(keyboard_n_key, False, dtype=bool)
        off_map = np.full(keyboard_n_key, False, dtype=bool)
        
        if len(self.prev_map) == 0:
            self.prev_map = np.full(keyboard_n_key, False, dtype=bool)
        
        if finger_depths is None: finger_depths = {}
        
        # FASE 1: Recolección
        raw_detections = []
        current_time = time.time()
        
        for fingertip_pos in fingertips_pos:
            hand_id, tip_id, x_pos, y_pos = fingertip_pos
            finger_id = (hand_id, tip_id)
            
            if finger_id not in finger_depths: continue
            
            depth = finger_depths[finger_id]
            
            # Filtro básico de rango físico (-5 a +25 cm)
            if depth < -5.0 or depth > 25.0: continue
            
            if virtual_keyboard.intersect((x_pos, y_pos)):
                key = virtual_keyboard.find_key(x_pos, y_pos)
                
                if key is not None and 0 <= key < keyboard_n_key:
                    # Historial para suavizado
                    if finger_id not in self.finger_depth_history:
                        self.finger_depth_history[finger_id] = deque(maxlen=self.velocity_history_size)
                    self.finger_depth_history[finger_id].append(depth)
                    
                    depth_smoothed = depth
                    if self.smoothing_enabled and len(self.finger_depth_history[finger_id]) >= self.smoothing_window:
                        history = list(self.finger_depth_history[finger_id])
                        depth_smoothed = sum(history[-self.smoothing_window:]) / self.smoothing_window
                    
                    # Velocidad simple para compatibilidad
                    velocity = 0.0
                    if len(self.finger_depth_history[finger_id]) >= 2:
                        velocity = self.finger_depth_history[finger_id][-2] - self.finger_depth_history[finger_id][-1]
                    
                    raw_detections.append((finger_id, key, depth_smoothed, velocity, x_pos, y_pos))
        
        self._debug_frame_count += 1
        
        # FASE 1.5: Filtrado por Física
        filtered_by_depth = []
        
        # Gestión de dedos detectados para limpieza
        detected_fingers = set()
        for detection in raw_detections:
            finger_id = detection[0]
            depth = detection[2]
            detected_fingers.add(finger_id)
            self.finger_last_depth[finger_id] = depth
            
            # Liberación de seguridad por altura
            if depth > self.release_height:
                if finger_id in self.finger_state and self.finger_state[finger_id] == 'pressing':
                    self.finger_state[finger_id] = 'released'
        
        fingers_to_clean = [fid for fid in self.finger_state if fid not in detected_fingers]
        for fid in fingers_to_clean:
            del self.finger_state[fid]
            if fid in self.finger_last_depth: del self.finger_last_depth[fid]
            
        # LÓGICA DE DISPARO PRINCIPAL
        for detection in raw_detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            
            # A. Calcular Velocidad Real (Módulo Physics)
            midi_vel = self.physics_velocity.calculate_velocity(finger_id, depth, current_time)
            
            # B. Usar profundidad directa (ya es relativa al plano)
            z_relative_physics = depth
            
            # C. Evaluar Disparo (Sticky Trigger)
            action = self.physics_trigger.evaluate_trigger(key, z_relative_physics)
            
            if action == 'NOTE_ON':
                self.finger_state[finger_id] = 'pressing'
                self.active_velocities[key] = midi_vel
                filtered_by_depth.append(detection)
                print(f"[NOTE_ON] Tecla {key} | Profundidad: {depth:.2f}cm")
                
            elif action == 'NOTE_OFF':
                self.finger_state[finger_id] = 'released'
                if key in self.active_velocities: del self.active_velocities[key]
                
            elif action == 'HOLD':
                # Si está en HOLD, mantenemos la tecla presionada
                if self.finger_state.get(finger_id) == 'pressing':
                    filtered_by_depth.append(detection)
        
        # FASE 2: Algoritmos Modulares (Acordes, etc.)
        context = {
            'timestamp': current_time,
            'virtual_keyboard': virtual_keyboard,
            'keyboard_n_key': keyboard_n_key
        }
        filtered_detections = self.algorithm_manager.process_detections(filtered_by_depth, context)
        
        # FASE 3: Generar mapa
        for detection in filtered_detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            curr_map[key] = True
            self.finger_depths[finger_id] = depth
        
        on_map = np.logical_and(curr_map, np.logical_not(self.prev_map))
        off_map = np.logical_and(self.prev_map, np.logical_not(curr_map))
        self.prev_map = curr_map.copy()
        
        return on_map, off_map

    # Métodos delegados al manager (compatibilidad)
    def enable_algorithm(self, name): self.algorithm_manager.enable_algorithm(name)
    def disable_algorithm(self, name): self.algorithm_manager.disable_algorithm(name)
    def configure_algorithm(self, name, **params):
        if name == 'Suavizado de Profundidad':
            self.algorithm_manager.configure_algorithm(name, **params)
            self._update_smoothing_config()
        else:
            self.algorithm_manager.configure_algorithm(name, **params)
    def reset_algorithms(self): self.algorithm_manager.reset_all()
    def get_algorithm_stats(self): return self.algorithm_manager.get_all_stats()
    def get_current_chord(self):
        alg = self.algorithm_manager.get_algorithm('Multi-nota')
        return alg.get_current_chord() if alg and alg.is_enabled() else set()

# Alias
KeyboardMap = KeyboardMapModular

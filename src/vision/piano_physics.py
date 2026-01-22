#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piano Physics Engine - Velocity, Triggering, and Filtering
Provides professional piano-like behavior with velocity sensitivity and bounce prevention

@author: Piano Physics System
@created: 2026-01-21
"""

import time
import numpy as np
from collections import deque


class VelocityCalculator:
    """
    Calculates MIDI velocity from finger movement speed.
    Tracks position history to compute downward velocity in cm/s.
    """
    
    def __init__(self):
        self.last_positions = {}  # {finger_id: [(z, timestamp), ...]}
        self.history_size = 5
    
    def calculate_velocity(self, finger_id, z_current, timestamp):
        """
        Calcula velocidad de impacto (cm/s) y la convierte a MIDI (0-127)
        
        Args:
            finger_id: Unique identifier for the finger
            z_current: Current Z position in cm
            timestamp: Current timestamp in seconds
            
        Returns:
            int: MIDI velocity (20-127)
        """
        if finger_id not in self.last_positions:
            self.last_positions[finger_id] = []
        
        history = self.last_positions[finger_id]
        history.append((z_current, timestamp))
        
        # Keep only recent history
        if len(history) > self.history_size:
            history.pop(0)
        
        # Need at least 3 points for reliable velocity
        if len(history) < 3:
            return 64  # Velocidad media por defecto
        
        z_start, t_start = history[0]
        z_end, t_end = history[-1]
        
        delta_z = z_start - z_end  # Positivo si baja hacia la mesa
        delta_t = t_end - t_start
        
        if delta_t < 0.001:
            return 64
        
        # Velocidad en cm/s
        velocity_cm_s = delta_z / delta_t
        
        # Solo nos importa la velocidad de bajada (positiva hacia la mesa)
        if velocity_cm_s < 0:
            velocity_cm_s = 0
        
        # Mapeo: 10 cm/s = suave (20), 150 cm/s = fuerte (127)
        midi_velocity = int(np.clip((velocity_cm_s / 150.0) * 127, 20, 127))
        return midi_velocity


class TriggerSystem:
    """
    Hysteresis-based note triggering system.
    Prevents bounce by using separate press and release thresholds.
    """
    
    # Umbrales ajustados (Z relativo: negativo = cruzó la mesa)
    TRIGGER_PRESS = -0.2      # Cruzar 2mm la mesa activa la nota
    TRIGGER_RELEASE = +0.5    # Subir 5mm libera la nota (histéresis)
    
    def __init__(self):
        self.key_states = {}  # {key_id: 'idle'/'pressed'}
    
    def evaluate_trigger(self, key_id, z_relative):
        """
        Evalúa si una tecla debe activarse, mantenerse o liberarse.
        
        Args:
            key_id: Key identifier (0-12 for 13 keys)
            z_relative: Z position relative to keyboard surface (negative = below surface)
            
        Returns:
            str: 'NOTE_ON', 'NOTE_OFF', or 'HOLD'
        """
        current_state = self.key_states.get(key_id, 'idle')
        
        if current_state == 'idle':
            # Si cruza el umbral de presión
            if z_relative < self.TRIGGER_PRESS:
                self.key_states[key_id] = 'pressed'
                return 'NOTE_ON'
        
        elif current_state == 'pressed':
            # Si sube por encima del umbral de liberación
            if z_relative > self.TRIGGER_RELEASE:
                self.key_states[key_id] = 'idle'
                return 'NOTE_OFF'
        
        return 'HOLD'


class TemporalFilter:
    """
    Smooths finger positions over time to reduce tracking jitter.
    Uses a simple moving average filter.
    """
    
    def __init__(self):
        self.finger_tracks = {}
        self.smooth_window = 5
    
    def smooth_position(self, finger_id, x, y, z):
        """
        Aplica suavizado temporal a una posición 3D.
        
        Args:
            finger_id: Unique identifier for the finger
            x, y, z: Current 3D position
            
        Returns:
            tuple: (x_smooth, y_smooth, z_smooth) smoothed coordinates
        """
        if finger_id not in self.finger_tracks:
            self.finger_tracks[finger_id] = deque(maxlen=self.smooth_window)
        
        track = self.finger_tracks[finger_id]
        track.append((x, y, z))
        
        # Media simple para estabilidad
        avg = np.mean(track, axis=0)
        return avg[0], avg[1], avg[2]

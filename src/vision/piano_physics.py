#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piano Physics Engine - CON AUTO-NIVELACIÓN (Corrección Final)
"""
import numpy as np
import json
from pathlib import Path

class VelocityCalculator:
    def __init__(self):
        self.last_depths = {}
        self.last_times = {}

    def calculate_velocity(self, finger_id, z_current, timestamp):
        # Cálculo de velocidad real
        prev_z = self.last_depths.get(finger_id, z_current)
        prev_t = self.last_times.get(finger_id, timestamp)
        
        dt = timestamp - prev_t
        dz = z_current - prev_z # Positivo si baja (hacia la mesa)
        
        self.last_depths[finger_id] = z_current
        self.last_times[finger_id] = timestamp
        
        # Si dt es muy pequeño o cero, devolvemos un valor seguro
        velocity = dz / dt if dt > 0 else 0
        
        # Convertir cm/s a MIDI (0-127)
        # Ajuste de sensibilidad: (vel * 5) + 70
        return int(np.clip(velocity * 5.0 + 70, 50, 127))

class TriggerSystem:
    def __init__(self, calibration_config=None):
        self.key_states = {} 
        self.key_floors = {} 
        
        # PISO ALTO INICIAL (10.0 cm):
        # Esto es crucial. Iniciamos creyendo que el piso está alto (en el aire).
        # Cuando el sistema detecte tu dedo en -2.0, bajará el piso automáticamente.
        self.DEFAULT_FLOOR = 10.0 

        # Cargar configuración si existe, pero la auto-nivelación mandará
        if calibration_config and hasattr(calibration_config, 'key_floors'):
            self.key_floors = calibration_config.key_floors.copy()
        
        # Parámetros de histeresis
        self.PRESS_MARGIN = 0.5    # Distancia para activar (cm)
        self.RELEASE_MARGIN = 1.5  # Distancia para soltar (cm)

    def evaluate_trigger(self, key_id, z_current):
        # 1. Obtener el piso actual
        floor = self.key_floors.get(key_id, self.DEFAULT_FLOOR)
        
        # =================================================================
        # LA CORRECCIÓN DE AUTO-NIVELACIÓN
        # =================================================================
        # --- FILTRO DE CORDURA IHC ---
        # Solo bajamos el piso si la lectura es lógica (entre -15 y el piso actual)
        # Esto evita que un ruido de -83.0 destruya la calibración
        if -15.0 < z_current < floor:
            floor = z_current
            self.key_floors[key_id] = floor
            # print(f"[FISICA] Piso validado Tecla {key_id}: {floor:.2f} cm") # Descomentar para debug
            # Descomenta la siguiente línea si quieres ver en consola cuando aprende
            # print(f"[AUTO] Tecla {key_id} piso ajustado a {floor:.2f}")
        # =================================================================

        # 2. Calcular distancia relativa
        dist = z_current - floor
        
        state = self.key_states.get(key_id, 'idle')
        action = 'HOLD'

        # 3. Máquina de estados
        if state == 'idle':
            # Si bajamos más allá del margen (distancia negativa o cercana a 0)
            if dist <= self.PRESS_MARGIN:
                self.key_states[key_id] = 'pressed'
                action = 'NOTE_ON'
                
        elif state == 'pressed':
            # Para soltar, hay que subir claramente por encima del piso
            if dist > self.RELEASE_MARGIN:
                self.key_states[key_id] = 'idle'
                action = 'NOTE_OFF'

        return action
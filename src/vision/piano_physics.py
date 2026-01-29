#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piano Physics Engine
Maneja la lógica de disparo de teclas y velocidad.
Soporta calibración manual (key_floors) con fallback a JSON.
"""

import numpy as np
import json
import os
from pathlib import Path

class VelocityCalculator:
    def __init__(self):
        pass
    def calculate_velocity(self, finger_id, z_current, timestamp):
        return 110 

class TriggerSystem:
    def __init__(self, calibration_config=None):
        self.key_states = {} 
        self.key_floors = {} 
        
        # 1. Intentar cargar de objeto config directo
        if calibration_config and hasattr(calibration_config, 'key_floors'):
            print("[PHYSICS] Usando config en memoria.")
            self.key_floors = calibration_config.key_floors
        
        # 2. FALLBACK: Si no hay config, leer directo del JSON (Seguridad total)
        if not self.key_floors:
            self._load_from_json_fallback()

        # TOLERANCIA DEL DEDO (El "colchón")
        self.PRESS_MARGIN = 0.5   
        self.RELEASE_MARGIN = 1.5 
        self.DEFAULT_FLOOR = 2.0 

    def _load_from_json_fallback(self):
        """Carga de emergencia directa del archivo"""
        try:
            # Ruta relativa al archivo calibration.json
            base_dir = Path(__file__).parent.parent.parent
            json_path = base_dir / "camcalibration" / "calibration.json"
            
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    if "key_floors" in data:
                        raw = data["key_floors"]
                        # Convertir keys string "0" a int 0
                        self.key_floors = {int(k): float(v) for k, v in raw.items()}
                        print(f"[PHYSICS] FALLBACK: Cargados {len(self.key_floors)} pisos desde JSON.")
        except Exception as e:
            print(f"[PHYSICS] Error en carga fallback: {e}")

    def evaluate_trigger(self, key_id, z_current):
        # Obtener piso calibrado para ESTA tecla
        floor = self.key_floors.get(key_id, self.DEFAULT_FLOOR)
        dist = z_current - floor
        
        state = self.key_states.get(key_id, 'idle')
        action = 'HOLD'

        if state == 'idle':
            if dist <= self.PRESS_MARGIN:
                self.key_states[key_id] = 'pressed'
                action = 'NOTE_ON'
        elif state == 'pressed':
            if dist > self.RELEASE_MARGIN:
                self.key_states[key_id] = 'idle'
                action = 'NOTE_OFF'

        return action

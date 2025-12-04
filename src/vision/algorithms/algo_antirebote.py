#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO 1: Anti-rebote (Debouncing)
Previene activaciones múltiples rápidas de la misma tecla
"""

import time
from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class AntireboteAlgorithm(BaseAlgorithm):
    """
    Implementa debouncing para evitar rebotes en la detección.
    
    Parámetros configurables:
    - debounce_time: Tiempo mínimo (s) entre activaciones de la misma tecla
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Antirebote", enabled=enabled)
        
        # Parámetros configurables
        self.debounce_time = 0.05  # 50ms
        
        # Estado interno
        self.last_press_time = {}  # {key_id: timestamp}
        self.last_release_time = {}  # {key_id: timestamp}
        
        # Estadísticas
        self.stats = {
            'total_checks': 0,
            'blocked_presses': 0,
            'allowed_presses': 0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Filtra detecciones que ocurren muy rápido después de una anterior.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: {'timestamp': float, ...}
            
        Returns:
            Lista filtrada de detecciones
        """
        if not self.enabled:
            return detections
        
        current_time = context.get('timestamp', time.time())
        filtered = []
        
        for detection in detections:
            finger_id, key, depth, velocity, x, y = detection
            
            self.stats['total_checks'] += 1
            
            # Verificar si pasó suficiente tiempo desde última presión
            if key in self.last_press_time:
                time_since_press = current_time - self.last_press_time[key]
                
                if time_since_press < self.debounce_time:
                    # Bloquear: muy rápido
                    self.stats['blocked_presses'] += 1
                    continue
            
            # Permitir detección
            self.last_press_time[key] = current_time
            filtered.append(detection)
            self.stats['allowed_presses'] += 1
        
        return filtered
    
    def configure(self, **params):
        """
        Configura parámetros del algoritmo.
        
        Args:
            debounce_time: float (segundos)
        """
        if 'debounce_time' in params:
            self.debounce_time = float(params['debounce_time'])
    
    def reset(self):
        """Limpia el historial de tiempos."""
        self.last_press_time.clear()
        self.last_release_time.clear()
        self.stats['total_checks'] = 0
        self.stats['blocked_presses'] = 0
        self.stats['allowed_presses'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'debounce_time': self.debounce_time
        }

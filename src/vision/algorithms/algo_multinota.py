#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO 4: Multi-nota (Acordes)
Detecta cuando múltiples teclas se presionan simultáneamente
"""

import time
from typing import Any, Dict, List, Tuple, Set
from .base_algorithm import BaseAlgorithm


class MultinotaAlgorithm(BaseAlgorithm):
    """
    Implementa detección de acordes (múltiples notas simultáneas).
    
    Parámetros configurables:
    - simultaneous_window: Ventana temporal (s) para considerar notas simultáneas
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Multi-nota", enabled=enabled)
        
        # Parámetros configurables
        self.simultaneous_window = 0.05  # 50ms
        
        # Estado interno
        self.press_timestamps = {}  # {key_id: timestamp}
        self.last_chord_keys = set()  # Últimas teclas en acorde
        
        # Estadísticas
        self.stats = {
            'total_chords': 0,
            'total_single_notes': 0,
            'max_chord_size': 0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Agrupa detecciones temporalmente cercanas como acordes.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: {'timestamp': float, ...}
            
        Returns:
            Lista de detecciones (sin modificar, solo registra acordes)
        """
        if not self.enabled:
            return detections
        
        current_time = context.get('timestamp', time.time())
        
        # Registrar timestamps de nuevas presiones
        current_keys = set()
        for detection in detections:
            _, key, _, _, _, _ = detection
            self.press_timestamps[key] = current_time
            current_keys.add(key)
        
        # Limpiar timestamps antiguos
        keys_to_remove = []
        for key, timestamp in self.press_timestamps.items():
            if current_time - timestamp > self.simultaneous_window * 2:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.press_timestamps[key]
        
        # Detectar si hay acorde activo
        simultaneous_keys = set()
        for key, timestamp in self.press_timestamps.items():
            if current_time - timestamp <= self.simultaneous_window:
                simultaneous_keys.add(key)
        
        # Actualizar estadísticas
        if len(simultaneous_keys) >= 2:
            if simultaneous_keys != self.last_chord_keys:
                self.stats['total_chords'] += 1
                self.stats['max_chord_size'] = max(
                    self.stats['max_chord_size'],
                    len(simultaneous_keys)
                )
            self.last_chord_keys = simultaneous_keys
        elif len(simultaneous_keys) == 1:
            if simultaneous_keys != self.last_chord_keys:
                self.stats['total_single_notes'] += 1
            self.last_chord_keys = simultaneous_keys
        else:
            self.last_chord_keys = set()
        
        return detections
    
    def configure(self, **params):
        """
        Configura ventana temporal para acordes.
        
        Args:
            simultaneous_window: float (segundos)
        """
        if 'simultaneous_window' in params:
            self.simultaneous_window = float(params['simultaneous_window'])
    
    def reset(self):
        """Limpia historial de acordes."""
        self.press_timestamps.clear()
        self.last_chord_keys.clear()
        self.stats['total_chords'] = 0
        self.stats['total_single_notes'] = 0
        self.stats['max_chord_size'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'simultaneous_window': self.simultaneous_window
        }
    
    def get_current_chord(self) -> Set[int]:
        """Retorna las teclas del acorde actual."""
        return self.last_chord_keys.copy()

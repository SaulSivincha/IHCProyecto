#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO 2: Histéresis
Usa umbrales diferentes para presionar y soltar teclas
"""

from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class HisteresisAlgorithm(BaseAlgorithm):
    """
    Implementa histéresis con umbrales distintos para presionar/soltar.
    
    Parámetros configurables:
    - press_threshold: Profundidad (cm) para activar tecla
    - release_threshold: Profundidad (cm) para liberar tecla
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Histéresis", enabled=enabled)
        
        # Parámetros configurables
        self.press_threshold = 3.0  # cm (más bajo)
        self.release_threshold = 4.0  # cm (más alto)
        
        # Estado interno
        self.key_pressed_state = {}  # {key_id: bool}
        
        # Estadísticas
        self.stats = {
            'total_checks': 0,
            'press_applied': 0,
            'release_applied': 0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Aplica umbrales diferentes según el estado actual de la tecla.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: Contexto adicional
            
        Returns:
            Lista filtrada con histéresis aplicada
        """
        if not self.enabled:
            return detections
        
        filtered = []
        
        for detection in detections:
            finger_id, key, depth, velocity, x, y = detection
            
            self.stats['total_checks'] += 1
            
            is_pressed = self.key_pressed_state.get(key, False)
            
            if is_pressed:
                # Tecla ya presionada: usar umbral de liberación
                if depth <= self.release_threshold:
                    # Mantener presionada
                    filtered.append(detection)
                else:
                    # Liberar
                    self.key_pressed_state[key] = False
                    self.stats['release_applied'] += 1
            else:
                # Tecla no presionada: usar umbral de presión
                if depth <= self.press_threshold:
                    # Activar
                    self.key_pressed_state[key] = True
                    filtered.append(detection)
                    self.stats['press_applied'] += 1
        
        return filtered
    
    def configure(self, **params):
        """
        Configura umbrales de histéresis.
        
        Args:
            press_threshold: float (cm)
            release_threshold: float (cm)
        """
        if 'press_threshold' in params:
            self.press_threshold = float(params['press_threshold'])
        if 'release_threshold' in params:
            self.release_threshold = float(params['release_threshold'])
    
    def reset(self):
        """Limpia el estado de teclas."""
        self.key_pressed_state.clear()
        self.stats['total_checks'] = 0
        self.stats['press_applied'] = 0
        self.stats['release_applied'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'press_threshold': self.press_threshold,
            'release_threshold': self.release_threshold
        }

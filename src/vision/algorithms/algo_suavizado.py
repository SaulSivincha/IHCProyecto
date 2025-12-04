#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO 3: Suavizado de velocidad
Calcula velocidad promediando múltiples mediciones
"""

from collections import deque, defaultdict
from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class SuavizadoAlgorithm(BaseAlgorithm):
    """
    Implementa suavizado de velocidad mediante promedio móvil.
    
    Parámetros configurables:
    - smoothing_window: Número de mediciones para promediar
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Suavizado", enabled=enabled)
        
        # Parámetros configurables
        self.smoothing_window = 7  # Número de frames
        
        # Estado interno
        self.finger_depth_history = defaultdict(lambda: deque(maxlen=self.smoothing_window))
        
        # Estadísticas
        self.stats = {
            'total_smoothed': 0,
            'avg_smoothing_effect': 0.0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Suaviza la velocidad de cada dedo usando historial.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: Contexto adicional
            
        Returns:
            Lista con velocidades suavizadas
        """
        if not self.enabled:
            return detections
        
        smoothed = []
        
        for detection in detections:
            finger_id, key, depth, velocity, x, y = detection
            
            # Agregar profundidad al historial
            self.finger_depth_history[finger_id].append(depth)
            
            # Calcular velocidad suavizada
            history = list(self.finger_depth_history[finger_id])
            
            if len(history) >= 2:
                # Velocidad promedio de las últimas N mediciones
                velocities = [history[i] - history[i+1] for i in range(len(history) - 1)]
                smoothed_velocity = sum(velocities) / len(velocities)
                
                # Registrar efecto de suavizado
                original_mag = abs(velocity)
                smoothed_mag = abs(smoothed_velocity)
                if original_mag > 0:
                    effect = abs(smoothed_mag - original_mag) / original_mag
                    self.stats['avg_smoothing_effect'] = (
                        (self.stats['avg_smoothing_effect'] * self.stats['total_smoothed'] + effect) /
                        (self.stats['total_smoothed'] + 1)
                    )
                
                self.stats['total_smoothed'] += 1
                
                # Usar velocidad suavizada
                smoothed.append((finger_id, key, depth, smoothed_velocity, x, y))
            else:
                # No hay suficiente historial
                smoothed.append(detection)
        
        return smoothed
    
    def configure(self, **params):
        """
        Configura tamaño de ventana de suavizado.
        
        Args:
            smoothing_window: int (número de frames)
        """
        if 'smoothing_window' in params:
            new_window = int(params['smoothing_window'])
            self.smoothing_window = new_window
            # Recrear deques con nuevo tamaño
            for finger_id in self.finger_depth_history:
                old_data = list(self.finger_depth_history[finger_id])
                self.finger_depth_history[finger_id] = deque(old_data[-new_window:], maxlen=new_window)
    
    def reset(self):
        """Limpia historial de profundidades."""
        self.finger_depth_history.clear()
        self.stats['total_smoothed'] = 0
        self.stats['avg_smoothing_effect'] = 0.0
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'smoothing_window': self.smoothing_window
        }

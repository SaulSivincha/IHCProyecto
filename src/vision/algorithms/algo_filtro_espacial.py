#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO 5: Filtrado espacial
Previene que dedos cercanos activen múltiples teclas adyacentes
"""

import math
from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class FiltroEspacialAlgorithm(BaseAlgorithm):
    """
    Implementa filtrado espacial para evitar activaciones múltiples de dedos cercanos.
    
    Parámetros configurables:
    - min_finger_distance: Distancia mínima (px) entre dedos
    - adjacent_keys_threshold: Distancia máxima (teclas) para considerarlas adyacentes
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Filtro Espacial", enabled=enabled)
        
        # Parámetros configurables
        self.min_finger_distance = 35  # píxeles
        self.adjacent_keys_threshold = 2  # teclas
        
        # Estado interno
        self.finger_positions = {}  # {finger_id: (x, y, key, depth)}
        
        # Estadísticas
        self.stats = {
            'total_conflicts': 0,
            'resolved_by_depth': 0,
            'resolved_by_distance': 0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Filtra detecciones donde dedos cercanos activan teclas adyacentes.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: Contexto adicional
            
        Returns:
            Lista filtrada sin conflictos espaciales
        """
        if not self.enabled:
            return detections
        
        # Actualizar posiciones
        for detection in detections:
            finger_id, key, depth, velocity, x, y = detection
            self.finger_positions[finger_id] = (x, y, key, depth)
        
        # Detectar conflictos (dedos cercanos en teclas adyacentes)
        conflicts = []
        fingers = list(self.finger_positions.keys())
        
        for i in range(len(fingers)):
            for j in range(i + 1, len(fingers)):
                finger1 = fingers[i]
                finger2 = fingers[j]
                
                x1, y1, key1, depth1 = self.finger_positions[finger1]
                x2, y2, key2, depth2 = self.finger_positions[finger2]
                
                # Calcular distancia euclidiana
                distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                
                # Calcular distancia entre teclas
                key_distance = abs(key2 - key1)
                
                # Verificar si hay conflicto
                if (distance < self.min_finger_distance and 
                    key_distance <= self.adjacent_keys_threshold):
                    conflicts.append((finger1, finger2, distance, depth1, depth2))
                    self.stats['total_conflicts'] += 1
        
        # Resolver conflictos: mantener el dedo con mayor profundidad (más cerca)
        fingers_to_remove = set()
        
        for finger1, finger2, distance, depth1, depth2 in conflicts:
            if depth1 < depth2:
                # finger1 está más cerca (menor profundidad)
                fingers_to_remove.add(finger2)
            else:
                # finger2 está más cerca
                fingers_to_remove.add(finger1)
            
            self.stats['resolved_by_depth'] += 1
        
        # Filtrar detecciones
        filtered = [
            detection for detection in detections
            if detection[0] not in fingers_to_remove
        ]
        
        return filtered
    
    def configure(self, **params):
        """
        Configura parámetros de filtrado espacial.
        
        Args:
            min_finger_distance: int (píxeles)
            adjacent_keys_threshold: int (número de teclas)
        """
        if 'min_finger_distance' in params:
            self.min_finger_distance = int(params['min_finger_distance'])
        if 'adjacent_keys_threshold' in params:
            self.adjacent_keys_threshold = int(params['adjacent_keys_threshold'])
    
    def reset(self):
        """Limpia posiciones de dedos."""
        self.finger_positions.clear()
        self.stats['total_conflicts'] = 0
        self.stats['resolved_by_depth'] = 0
        self.stats['resolved_by_distance'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'min_finger_distance': self.min_finger_distance,
            'adjacent_keys_threshold': self.adjacent_keys_threshold
        }

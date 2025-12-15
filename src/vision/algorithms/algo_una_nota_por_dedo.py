#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO: Una Nota Por Dedo (ONPD)
Garantiza que cada dedo solo pueda activar UNA tecla a la vez.
Soluciona el problema de dedos que activan múltiples teclas simultáneamente.
"""

import time
from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class UnaNotaPorDedoAlgorithm(BaseAlgorithm):
    """
    Asegura que cada dedo físico solo active una tecla.
    
    Problema que resuelve:
    - Un dedo puede estar "sobre" varias teclas por imprecisión en la detección
    - Sin este filtro, un dedo podría activar 2-3 teclas adyacentes
    
    Solución:
    - Para cada dedo, solo mantiene la tecla con mayor profundidad (más presionada)
    - Opcionalmente puede usar "tecla más cercana al centro del dedo"
    
    Parámetros:
    - selection_mode: 'depth' (mayor profundidad) o 'center' (más cercana al centro)
    - min_depth_advantage: Ventaja mínima de profundidad para cambiar de tecla (cm)
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Una Nota Por Dedo", enabled=enabled)
        
        # Parámetros configurables
        self.selection_mode = 'depth'  # 'depth' o 'center'
        self.min_depth_advantage = 0.3  # cm de ventaja mínima para cambiar
        self.sticky_time = 0.1  # Tiempo (s) que una tecla permanece "pegajosa"
        
        # Estado interno
        self.finger_to_key = {}  # {finger_id: (key, timestamp, depth)}
        
        # Estadísticas
        self.stats = {
            'total_filtered': 0,
            'single_activations': 0,
            'multi_activations_blocked': 0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Filtra detecciones para que cada dedo solo tenga una tecla.
        
        Para cada dedo con múltiples detecciones:
        1. Si mode='depth': mantiene la tecla con mayor profundidad
        2. Si mode='center': mantiene la tecla más cercana al centro del dedo
        """
        if not self.enabled or not detections:
            return detections
        
        current_time = context.get('timestamp', time.time())
        
        # Agrupar detecciones por dedo
        finger_detections = {}  # {finger_id: [detections]}
        
        for detection in detections:
            finger_id = detection[0]  # (hand_id, tip_id)
            
            if finger_id not in finger_detections:
                finger_detections[finger_id] = []
            finger_detections[finger_id].append(detection)
        
        # Filtrar: un dedo = una tecla
        filtered = []
        
        for finger_id, finger_dets in finger_detections.items():
            if len(finger_dets) == 1:
                # Solo una detección, mantenerla
                filtered.append(finger_dets[0])
                self.stats['single_activations'] += 1
            else:
                # Múltiples detecciones para el mismo dedo
                best = self._select_best_detection(finger_id, finger_dets, current_time)
                filtered.append(best)
                self.stats['multi_activations_blocked'] += len(finger_dets) - 1
                self.stats['total_filtered'] += len(finger_dets) - 1
        
        return filtered
    
    def _select_best_detection(self, finger_id, detections: List[Tuple], current_time: float) -> Tuple:
        """
        Selecciona la mejor detección para un dedo con múltiples candidatas.
        """
        if self.selection_mode == 'depth':
            # Ordenar por profundidad (mayor = más presionado)
            sorted_dets = sorted(detections, key=lambda d: d[2], reverse=True)
            best = sorted_dets[0]
            
            # Verificar si hay una tecla "pegajosa" (sticky) anterior
            if finger_id in self.finger_to_key:
                prev_key, prev_time, prev_depth = self.finger_to_key[finger_id]
                
                # Si la tecla anterior aún está en las detecciones y dentro del tiempo sticky
                if current_time - prev_time < self.sticky_time:
                    for det in detections:
                        if det[1] == prev_key:
                            # La tecla anterior sigue siendo válida
                            # Solo cambiar si la nueva tiene ventaja significativa
                            if best[2] - det[2] < self.min_depth_advantage:
                                best = det
                            break
            
            # Actualizar estado
            self.finger_to_key[finger_id] = (best[1], current_time, best[2])
            
        else:  # 'center' mode
            # Usar la primera detección (la que está más centrada en el dedo)
            # En la práctica, las detecciones ya vienen ordenadas por cercanía
            best = detections[0]
            self.finger_to_key[finger_id] = (best[1], current_time, best[2])
        
        return best
    
    def configure(self, **params):
        """Configura los parámetros del algoritmo."""
        if 'selection_mode' in params:
            mode = params['selection_mode']
            if mode in ['depth', 'center']:
                self.selection_mode = mode
        
        if 'min_depth_advantage' in params:
            self.min_depth_advantage = float(params['min_depth_advantage'])
        
        if 'sticky_time' in params:
            self.sticky_time = float(params['sticky_time'])
    
    def reset(self):
        """Reinicia el estado interno."""
        self.finger_to_key = {}
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual."""
        return {
            'selection_mode': self.selection_mode,
            'min_depth_advantage': self.min_depth_advantage,
            'sticky_time': self.sticky_time
        }
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del algoritmo."""
        base_stats = super().get_stats()
        return {**base_stats, **self.stats}

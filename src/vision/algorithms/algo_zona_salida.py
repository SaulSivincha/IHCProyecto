#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO 8: Zona de salida
Previene titubeo cuando el dedo sale del borde inferior del teclado
"""

import time
from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class ZonaSalidaAlgorithm(BaseAlgorithm):
    """
    Implementa zona de salida para detectar cuando un dedo está saliendo del teclado.
    
    Parámetros configurables:
    - exit_zone_margin: Margen (px) desde el borde inferior
    - exit_grace_time: Tiempo de gracia (s) para confirmar salida
    """
    
    def __init__(self, enabled: bool = False):
        super().__init__(name="Zona Salida", enabled=enabled)
        
        # Parámetros configurables
        self.exit_zone_margin = 30  # píxeles desde el borde
        self.exit_grace_time = 0.3  # segundos
        
        # Estado interno
        self.finger_last_valid = {}  # {finger_id: (key, timestamp, y_pos)}
        self.finger_in_exit_zone = {}  # {finger_id: timestamp_entered}
        
        # Estadísticas
        self.stats = {
            'total_exit_checks': 0,
            'exits_blocked': 0,
            'exits_allowed': 0
        }
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Filtra activaciones cuando el dedo está saliendo del teclado.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: {'timestamp': float, 'virtual_keyboard': VirtualKeyboard, ...}
            
        Returns:
            Lista filtrada sin activaciones de salida
        """
        if not self.enabled:
            return detections
        
        current_time = context.get('timestamp', time.time())
        virtual_keyboard = context.get('virtual_keyboard')
        
        if virtual_keyboard is None:
            # No hay teclado, no podemos calcular zona de salida
            return detections
        
        filtered = []
        
        for detection in detections:
            finger_id, key, depth, velocity, x, y = detection
            
            self.stats['total_exit_checks'] += 1
            
            # Calcular límites del teclado
            keyboard_bottom = virtual_keyboard.kb_y1
            exit_zone_start = keyboard_bottom - self.exit_zone_margin
            
            # Verificar si está en zona de salida
            in_exit_zone = y >= exit_zone_start
            
            if not in_exit_zone:
                # Fuera de zona de salida: permitir
                self.finger_last_valid[finger_id] = (key, current_time, y)
                if finger_id in self.finger_in_exit_zone:
                    del self.finger_in_exit_zone[finger_id]
                filtered.append(detection)
                self.stats['exits_allowed'] += 1
                continue
            
            # Está en zona de salida
            if finger_id not in self.finger_in_exit_zone:
                # Primera vez en zona de salida
                self.finger_in_exit_zone[finger_id] = current_time
            
            time_in_exit_zone = current_time - self.finger_in_exit_zone[finger_id]
            
            # Calcular dirección de movimiento
            if finger_id in self.finger_last_valid:
                last_key, last_time, last_y = self.finger_last_valid[finger_id]
                
                dt = current_time - last_time
                if dt > 0:
                    # Calcular velocidad Y (positivo = hacia abajo/saliendo)
                    y_velocity = (y - last_y) / dt
                    
                    # Si se mueve hacia abajo (saliendo) y pasó el tiempo de gracia
                    if y_velocity > 10 and time_in_exit_zone > self.exit_grace_time:
                        # Bloquear: está saliendo del teclado
                        self.stats['exits_blocked'] += 1
                        continue
            
            # Dentro del tiempo de gracia o moviéndose hacia arriba
            self.finger_last_valid[finger_id] = (key, current_time, y)
            filtered.append(detection)
            self.stats['exits_allowed'] += 1
        
        return filtered
    
    def configure(self, **params):
        """
        Configura parámetros de zona de salida.
        
        Args:
            exit_zone_margin: int (píxeles)
            exit_grace_time: float (segundos)
        """
        if 'exit_zone_margin' in params:
            self.exit_zone_margin = int(params['exit_zone_margin'])
        if 'exit_grace_time' in params:
            self.exit_grace_time = float(params['exit_grace_time'])
    
    def reset(self):
        """Limpia historial de zona de salida."""
        self.finger_last_valid.clear()
        self.finger_in_exit_zone.clear()
        self.stats['total_exit_checks'] = 0
        self.stats['exits_blocked'] = 0
        self.stats['exits_allowed'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'exit_zone_margin': self.exit_zone_margin,
            'exit_grace_time': self.exit_grace_time
        }

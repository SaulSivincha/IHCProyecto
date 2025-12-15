#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO: Una Nota Por Acción
Evita que un dedo active múltiples notas durante un solo movimiento de tocar.
Solo permite una nueva activación después de que el dedo se aleje suficientemente.
"""

from typing import Any, Dict, List, Tuple, Set
from .base_algorithm import BaseAlgorithm


class UnaNotaPorAccionAlgorithm(BaseAlgorithm):
    """
    Evita activaciones múltiples durante un solo gesto de tocar.
    
    Problema que resuelve:
    - Al levantar el dedo después de tocar "Sol", pasa por "La" y "Si"
      y las activa incorrectamente.
    
    Solución:
    - Rastrea qué dedos ya activaron una nota
    - Solo permite nueva activación cuando el dedo se ALEJA del teclado
      (depth sube por encima de un umbral de "reset")
    - Esto crea un ciclo: TOCAR → ALEJAR → TOCAR
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Una Nota Por Acción", enabled=enabled)
        
        # Parámetros configurables
        self.profundidad_activacion = -10.0  # Depth para activar (tocando)
        self.profundidad_reset = -5.0       # Depth para resetear (alejado)
        
        # Estado: dedos que ya activaron una nota en este ciclo
        self.dedos_activos: Set[Tuple] = set()  # {finger_id, ...}
        
        # Estadísticas
        self.stats = {
            'total_verificaciones': 0,
            'activaciones_permitidas': 0,
            'activaciones_bloqueadas': 0,
            'resets_aplicados': 0
        }
        
        # Debug
        self._debug_count = 0
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Filtra detecciones permitiendo solo una activación por ciclo tocar-alejar.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: Contexto adicional
            
        Returns:
            Lista filtrada
        """
        if not self.enabled or not detections:
            return detections
        
        filtered = []
        self._debug_count += 1
        
        # Primero, verificar qué dedos se alejaron (reset)
        dedos_en_detecciones = {det[0] for det in detections}
        
        for finger_id in list(self.dedos_activos):
            # Si el dedo NO está en las detecciones actuales, resetear
            if finger_id not in dedos_en_detecciones:
                self.dedos_activos.discard(finger_id)
                self.stats['resets_aplicados'] += 1
                if self._debug_count % 30 == 0:
                    print(f"[UNA NOTA/ACCIÓN] Reset dedo {finger_id} (ya no detectado)")
        
        # Procesar detecciones
        for detection in detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            
            self.stats['total_verificaciones'] += 1
            
            # Verificar si el dedo se alejó lo suficiente para resetear
            if depth > self.profundidad_reset:
                # Dedo LEJOS del teclado → resetear
                if finger_id in self.dedos_activos:
                    self.dedos_activos.discard(finger_id)
                    self.stats['resets_aplicados'] += 1
                    if self._debug_count % 30 == 0:
                        print(f"[UNA NOTA/ACCIÓN] Reset dedo {finger_id} (depth={depth:.1f} > {self.profundidad_reset})")
                # No agregar a filtered (dedo lejos)
                continue
            
            # Dedo CERCA del teclado
            if depth <= self.profundidad_activacion:
                # Verificar si ya activó una nota
                if finger_id in self.dedos_activos:
                    # YA activó → BLOQUEAR
                    self.stats['activaciones_bloqueadas'] += 1
                    if self._debug_count % 30 == 0:
                        print(f"[UNA NOTA/ACCIÓN] BLOQUEADO dedo {finger_id} tecla {key} (ya activó en este ciclo)")
                else:
                    # PRIMERA activación → PERMITIR
                    filtered.append(detection)
                    self.dedos_activos.add(finger_id)
                    self.stats['activaciones_permitidas'] += 1
                    if self._debug_count % 30 == 0:
                        print(f"[UNA NOTA/ACCIÓN] PERMITIDO dedo {finger_id} tecla {key} (primera activación)")
        
        return filtered
    
    def configure(self, **params):
        """
        Configura parámetros del algoritmo.
        
        Args:
            profundidad_activacion: float - Depth para activar nota
            profundidad_reset: float - Depth para resetear ciclo
        """
        if 'profundidad_activacion' in params:
            self.profundidad_activacion = float(params['profundidad_activacion'])
        if 'profundidad_reset' in params:
            self.profundidad_reset = float(params['profundidad_reset'])
    
    def reset(self):
        """Reinicia estado."""
        self.dedos_activos.clear()
        self.stats['total_verificaciones'] = 0
        self.stats['activaciones_permitidas'] = 0
        self.stats['activaciones_bloqueadas'] = 0
        self.stats['resets_aplicados'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna configuración actual."""
        return {
            'profundidad_activacion': self.profundidad_activacion,
            'profundidad_reset': self.profundidad_reset
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del algoritmo."""
        base_stats = super().get_stats()
        return {
            **base_stats,
            **self.stats,
            'dedos_activos_count': len(self.dedos_activos)
        }

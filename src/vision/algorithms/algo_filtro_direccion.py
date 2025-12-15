#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO: Filtro de Dirección
Bloquea activaciones cuando el dedo está SUBIENDO (alejándose del teclado).
Solo permite activaciones cuando está BAJANDO (acercándose).
"""

from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class FiltroDireccionAlgorithm(BaseAlgorithm):
    """
    Filtra detecciones basándose en la dirección de movimiento del dedo.
    
    Problema que resuelve:
    - Al levantar el dedo después de tocar una nota, pasa por otras teclas
      y las activa incorrectamente.
    
    Solución:
    - Solo permite activaciones cuando velocity > 0 (dedo bajando hacia teclado)
    - Bloquea activaciones cuando velocity <= 0 (dedo subiendo o quieto)
    
    Sistema invertido:
    - Dedo BAJA: depth va de -5 → -15 → -20 (más negativo), velocity > 0
    - Dedo SUBE: depth va de -20 → -15 → -5 (menos negativo), velocity < 0
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Filtro Dirección", enabled=enabled)
        
        # Parámetros configurables
        self.umbral_velocidad = 0.5  # cm/frame mínimo (bajando)
        
        # Estadísticas
        self.stats = {
            'total_verificaciones': 0,
            'permitidas_bajando': 0,
            'bloqueadas_subiendo': 0,
            'bloqueadas_quieto': 0
        }
        
        # Debug
        self._debug_count = 0
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Filtra detecciones permitiendo solo las que tienen velocity positiva.
        
        Args:
            detections: [(finger_id, key, depth, velocity, x, y), ...]
            context: Contexto adicional
            
        Returns:
            Lista filtrada con solo detecciones de dedos bajando
        """
        if not self.enabled or not detections:
            return detections
        
        filtered = []
        self._debug_count += 1
        
        for detection in detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            
            self.stats['total_verificaciones'] += 1
            
            # DEBUG: Mostrar velocity cada 30 frames (primeras 2 detecciones)
            if self._debug_count % 30 == 0 and len(filtered) < 2:
                print(f"[FILTRO DIR] Dedo {finger_id}, Tecla {key}, Depth={depth:.1f}, Vel={velocity:.2f}")
            
            # Verificar dirección de movimiento
            # velocity > 0 = dedo BAJANDO hacia teclado (depth más negativo)
            # velocity <= 0 = dedo SUBIENDO o QUIETO
            
            if velocity >= self.umbral_velocidad:
                # Dedo bajando → PERMITIR activación
                filtered.append(detection)
                self.stats['permitidas_bajando'] += 1
                if self._debug_count % 30 == 0 and len(filtered) <= 2:
                    print(f"  → PERMITIDO (bajando, vel={velocity:.2f})")
            elif velocity < 0:
                # Dedo subiendo → BLOQUEAR
                self.stats['bloqueadas_subiendo'] += 1
                if self._debug_count % 30 == 0:
                    print(f"  → BLOQUEADO (subiendo, vel={velocity:.2f})")
            else:
                # Dedo quieto → BLOQUEAR
                self.stats['bloqueadas_quieto'] += 1
                if self._debug_count % 30 == 0:
                    print(f"  → BLOQUEADO (quieto, vel={velocity:.2f})")
        
        return filtered
    
    def configure(self, **params):
        """
        Configura parámetros del algoritmo.
        
        Args:
            umbral_velocidad: float (cm/frame) - Velocidad mínima hacia abajo
        """
        if 'umbral_velocidad' in params:
            self.umbral_velocidad = float(params['umbral_velocidad'])
    
    def reset(self):
        """Reinicia estadísticas."""
        self.stats['total_verificaciones'] = 0
        self.stats['permitidas_bajando'] = 0
        self.stats['bloqueadas_subiendo'] = 0
        self.stats['bloqueadas_quieto'] = 0
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna configuración actual."""
        return {
            'umbral_velocidad': self.umbral_velocidad
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del algoritmo."""
        base_stats = super().get_stats()
        return {**base_stats, **self.stats}

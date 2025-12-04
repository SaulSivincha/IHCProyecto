#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clase base abstracta para algoritmos de detección
Define la interfaz común que todos los algoritmos deben implementar
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseAlgorithm(ABC):
    """
    Clase base para todos los algoritmos de detección.
    
    Cada algoritmo debe:
    1. Heredar de esta clase
    2. Implementar los métodos abstractos
    3. Definir sus parámetros de configuración
    4. Mantener su propio estado interno
    """
    
    def __init__(self, name: str, enabled: bool = False):
        """
        Args:
            name: Nombre identificador del algoritmo
            enabled: Estado inicial (activado/desactivado)
        """
        self.name = name
        self.enabled = enabled
        self.stats = {}
        
    @abstractmethod
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        """
        Procesa las detecciones aplicando la lógica del algoritmo.
        
        Args:
            detections: Lista de detecciones [(finger_id, key, depth, velocity, x, y), ...]
            context: Diccionario con contexto adicional (virtual_keyboard, timestamp, etc.)
            
        Returns:
            Lista de detecciones filtradas/modificadas
        """
        pass
    
    @abstractmethod
    def configure(self, **params):
        """
        Configura los parámetros del algoritmo.
        
        Args:
            **params: Parámetros específicos del algoritmo
        """
        pass
    
    @abstractmethod
    def reset(self):
        """
        Reinicia el estado interno del algoritmo.
        """
        pass
    
    def enable(self):
        """Activa el algoritmo."""
        self.enabled = True
        
    def disable(self):
        """Desactiva el algoritmo."""
        self.enabled = False
        
    def is_enabled(self) -> bool:
        """Retorna si el algoritmo está activado."""
        return self.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del algoritmo.
        
        Returns:
            Diccionario con métricas y estadísticas
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            **self.stats
        }
    
    def get_config(self) -> Dict[str, Any]:
        """
        Retorna la configuración actual del algoritmo.
        
        Returns:
            Diccionario con parámetros configurables
        """
        return {}
    
    def __repr__(self):
        status = "✓" if self.enabled else "✗"
        return f"{status} {self.name}"

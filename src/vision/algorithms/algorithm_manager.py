#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de algoritmos de detección
Orquesta la ejecución de múltiples algoritmos en secuencia
"""

import time
from typing import Any, Dict, List, Tuple
from .base_algorithm import BaseAlgorithm


class AlgorithmManager:
    """
    Gestor centralizado para todos los algoritmos de detección.
    
    Responsabilidades:
    - Cargar y configurar algoritmos
    - Ejecutar algoritmos en orden
    - Recopilar estadísticas
    - Activar/desactivar algoritmos dinámicamente
    """
    
    def __init__(self):
        self.algorithms: List[BaseAlgorithm] = []
        self.execution_order: List[str] = []
        
    def register_algorithm(self, algorithm: BaseAlgorithm):
        """
        Registra un nuevo algoritmo en el gestor.
        
        Args:
            algorithm: Instancia de BaseAlgorithm
        """
        self.algorithms.append(algorithm)
        self.execution_order.append(algorithm.name)
        
    def process_detections(self, 
                          detections: List[Tuple], 
                          context: Dict[str, Any]) -> List[Tuple]:
        """
        Procesa detecciones a través de todos los algoritmos activos.
        
        Args:
            detections: Lista inicial de detecciones
            context: Contexto compartido entre algoritmos
            
        Returns:
            Lista final de detecciones procesadas
        """
        # Asegurar timestamp en contexto
        if 'timestamp' not in context:
            context['timestamp'] = time.time()
        
        # Aplicar cada algoritmo en secuencia
        current_detections = detections
        
        for algorithm in self.algorithms:
            if algorithm.is_enabled():
                current_detections = algorithm.process(current_detections, context)
        
        return current_detections
    
    def get_algorithm(self, name: str) -> BaseAlgorithm:
        """
        Obtiene un algoritmo por nombre.
        
        Args:
            name: Nombre del algoritmo
            
        Returns:
            Instancia del algoritmo o None si no existe
        """
        for algorithm in self.algorithms:
            if algorithm.name == name:
                return algorithm
        return None
    
    def enable_algorithm(self, name: str):
        """Activa un algoritmo por nombre."""
        algorithm = self.get_algorithm(name)
        if algorithm:
            algorithm.enable()
    
    def disable_algorithm(self, name: str):
        """Desactiva un algoritmo por nombre."""
        algorithm = self.get_algorithm(name)
        if algorithm:
            algorithm.disable()
    
    def configure_algorithm(self, name: str, **params):
        """
        Configura un algoritmo específico.
        
        Args:
            name: Nombre del algoritmo
            **params: Parámetros de configuración
        """
        algorithm = self.get_algorithm(name)
        if algorithm:
            algorithm.configure(**params)
    
    def reset_all(self):
        """Reinicia el estado de todos los algoritmos."""
        for algorithm in self.algorithms:
            algorithm.reset()
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Recopila estadísticas de todos los algoritmos.
        
        Returns:
            Diccionario {nombre_algoritmo: estadísticas}
        """
        stats = {}
        for algorithm in self.algorithms:
            stats[algorithm.name] = algorithm.get_stats()
        return stats
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Recopila configuración de todos los algoritmos.
        
        Returns:
            Diccionario {nombre_algoritmo: configuración}
        """
        configs = {}
        for algorithm in self.algorithms:
            configs[algorithm.name] = {
                'enabled': algorithm.is_enabled(),
                'params': algorithm.get_config()
            }
        return configs
    
    def print_status(self):
        """Imprime el estado de todos los algoritmos."""
        print("\n" + "="*60)
        print("ESTADO DE ALGORITMOS")
        print("="*60)
        for i, algorithm in enumerate(self.algorithms, 1):
            status = "✓ ACTIVO" if algorithm.is_enabled() else "✗ INACTIVO"
            print(f"{i}. {algorithm.name:20s} [{status}]")
            config = algorithm.get_config()
            if config:
                for key, value in config.items():
                    print(f"   - {key}: {value}")
        print("="*60 + "\n")
    
    def __repr__(self):
        active = sum(1 for algo in self.algorithms if algo.is_enabled())
        total = len(self.algorithms)
        return f"AlgorithmManager({active}/{total} activos)"

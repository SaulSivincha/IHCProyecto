"""
Módulo de algoritmos de detección para piano virtual
Arquitectura modular y escalable - Sistema limpio
"""

from .base_algorithm import BaseAlgorithm
from .algorithm_manager import AlgorithmManager
from .algorithms_config import (
    ALGORITHMS_CONFIG, 
    PRESETS, 
    apply_preset, 
    get_active_algorithms
)

# === SINGLETON GLOBAL DEL ALGORITHM MANAGER ===
_global_algorithm_manager = None


def get_algorithm_manager() -> AlgorithmManager:
    """
    Obtiene la instancia global del AlgorithmManager (singleton).
    Inicializa los algoritmos si es la primera vez.
    
    Returns:
        AlgorithmManager: Instancia global configurada
    """
    global _global_algorithm_manager
    
    if _global_algorithm_manager is None:
        _global_algorithm_manager = AlgorithmManager()
        _initialize_algorithms(_global_algorithm_manager)
    
    return _global_algorithm_manager


def _initialize_algorithms(manager: AlgorithmManager):
    """
    Inicializa todos los algoritmos y los registra en el manager.
    Por ahora está vacío - se llenará conforme se agreguen algoritmos.
    """
    # TODO: Importar y registrar algoritmos aquí
    # Ejemplo:
    # from .algo_mi_algoritmo import MiAlgoritmo
    # algo = MiAlgoritmo(enabled=ALGORITHMS_CONFIG['Mi Algoritmo']['enabled'])
    # algo.configure(**ALGORITHMS_CONFIG['Mi Algoritmo']['params'])
    # manager.register_algorithm(algo)
    
    pass  # Sin algoritmos por ahora


def sync_algorithms_from_config():
    """
    Sincroniza el estado de los algoritmos con ALGORITHMS_CONFIG.
    Llamar después de cambiar la configuración.
    """
    manager = get_algorithm_manager()
    
    for algo in manager.algorithms:
        if algo.name in ALGORITHMS_CONFIG:
            config = ALGORITHMS_CONFIG[algo.name]
            
            # Actualizar estado enabled
            if config.get('enabled', False):
                algo.enable()
            else:
                algo.disable()
            
            # Actualizar parámetros
            if config.get('params'):
                algo.configure(**config['params'])


__all__ = [
    'BaseAlgorithm', 
    'AlgorithmManager', 
    'get_algorithm_manager',
    'sync_algorithms_from_config',
    'ALGORITHMS_CONFIG',
    'PRESETS',
    'apply_preset',
    'get_active_algorithms'
]

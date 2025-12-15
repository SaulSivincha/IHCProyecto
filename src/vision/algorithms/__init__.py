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
    """
    # Importar algoritmos
    from .algo_una_nota_por_accion import UnaNotaPorAccionAlgorithm
    
    # Registrar en orden de ejecución
    for algo_name in ['Una Nota Por Acción']:
        if algo_name == 'Una Nota Por Acción' and algo_name in ALGORITHMS_CONFIG:
            config = ALGORITHMS_CONFIG[algo_name]
            algo = UnaNotaPorAccionAlgorithm(enabled=config['enabled'])
            algo.configure(**config['params'])
            manager.register_algorithm(algo)


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

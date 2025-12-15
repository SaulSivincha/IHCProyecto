"""
Módulo de algoritmos de detección para piano virtual
Arquitectura modular y escalable
"""

from .base_algorithm import BaseAlgorithm
from .algorithm_manager import AlgorithmManager
from .algorithms_config import ALGORITHMS_CONFIG, PRESETS, apply_preset, get_active_algorithms

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
    from .algo_antirebote import AntireboteAlgorithm
    from .algo_histeresis import HisteresisAlgorithm
    from .algo_suavizado import SuavizadoAlgorithm
    from .algo_multinota import MultinotaAlgorithm
    from .algo_filtro_espacial import FiltroEspacialAlgorithm
    from .algo_zona_salida import ZonaSalidaAlgorithm
    
    # Crear instancias con configuración inicial
    algorithms = [
        ('Antirebote', AntireboteAlgorithm),
        ('Histéresis', HisteresisAlgorithm),
        ('Suavizado', SuavizadoAlgorithm),
        ('Filtro Espacial', FiltroEspacialAlgorithm),
        ('Zona Salida', ZonaSalidaAlgorithm),
        ('Multi-nota', MultinotaAlgorithm),
    ]
    
    for name, AlgoClass in algorithms:
        if name in ALGORITHMS_CONFIG:
            config = ALGORITHMS_CONFIG[name]
            try:
                # Los algoritmos reciben enabled como único parámetro del constructor
                algo = AlgoClass(enabled=config.get('enabled', False))
                
                # Configurar parámetros adicionales
                if config.get('params'):
                    algo.configure(**config['params'])
                    
                manager.register_algorithm(algo)
                print(f"  ✓ {name} inicializado")
            except Exception as e:
                print(f"⚠ Error inicializando {name}: {e}")


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

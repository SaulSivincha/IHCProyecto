#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada de algoritmos de detección
Permite activar/desactivar y configurar algoritmos desde un solo archivo
"""

# ==============================================================================
# CONFIGURACIÓN DE ALGORITMOS
# ==============================================================================

ALGORITHMS_CONFIG = {
    # ALGORITMO 1: Anti-rebote (Debouncing)
    # Previene activaciones múltiples rápidas de la misma tecla
    'Antirebote': {
        'enabled': True,  # ✓ Activar / ✗ Desactivar
        'params': {
            'debounce_time': 0.05  # Tiempo mínimo (s) entre activaciones (0.03-0.10)
        }
    },
    
    # ALGORITMO 2: Histéresis
    # Usa umbrales diferentes para presionar y soltar teclas
    'Histéresis': {
        'enabled': True,  # ✓ Activar / ✗ Desactivar
        'params': {
            'press_threshold': 3.0,    # Profundidad (cm) para activar (2.0-4.0)
            'release_threshold': 4.0   # Profundidad (cm) para liberar (3.0-5.0)
        }
    },
    
    # ALGORITMO 3: Suavizado de velocidad
    # Calcula velocidad promediando múltiples mediciones
    'Suavizado': {
        'enabled': True,  # ✓ Activar / ✗ Desactivar
        'params': {
            'smoothing_window': 7  # Número de mediciones para promediar (3-10)
        }
    },
    
    # ALGORITMO 4: Multi-nota (Acordes)
    # Detecta cuando múltiples teclas se presionan simultáneamente
    'Multi-nota': {
        'enabled': True,  # ✓ Activar / ✗ Desactivar
        'params': {
            'simultaneous_window': 0.05  # Ventana temporal (s) para acordes (0.03-0.10)
        }
    },
    
    # ALGORITMO 5: Filtrado espacial
    # Previene que dedos cercanos activen múltiples teclas adyacentes
    'Filtro Espacial': {
        'enabled': False,  # ✓ Activar / ✗ Desactivar
        'params': {
            'min_finger_distance': 35,      # Distancia mínima (px) entre dedos (25-50)
            'adjacent_keys_threshold': 2    # Máxima distancia (teclas) considerada adyacente (1-3)
        }
    },
    
    # ALGORITMO 8: Zona de salida
    # Previene titubeo cuando el dedo sale del borde inferior del teclado
    'Zona Salida': {
        'enabled': False,  # ✓ Activar / ✗ Desactivar (OFF por defecto)
        'params': {
            'exit_zone_margin': 30,    # Margen (px) desde borde inferior (20-50)
            'exit_grace_time': 0.3     # Tiempo de gracia (s) para confirmar salida (0.2-0.5)
        }
    }
}

# ==============================================================================
# ORDEN DE EJECUCIÓN
# ==============================================================================
# Los algoritmos se ejecutan en este orden:
# 1. Antirebote      → Filtra rebotes temporales
# 2. Histéresis      → Aplica umbrales inteligentes
# 3. Suavizado       → Reduce jitter en velocidad
# 4. Filtro Espacial → Resuelve conflictos de dedos cercanos
# 5. Zona Salida     → Previene titubeo en bordes
# 6. Multi-nota      → Detecta acordes (no filtra, solo registra)

EXECUTION_ORDER = [
    'Antirebote',
    'Histéresis',
    'Suavizado',
    'Filtro Espacial',
    'Zona Salida',
    'Multi-nota'
]

# ==============================================================================
# PRESETS RÁPIDOS
# ==============================================================================

PRESETS = {
    'default': {
        # Configuración estándar (equilibrada)
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.05}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 3.0, 'release_threshold': 4.0}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 7}},
        'Multi-nota': {'enabled': True, 'params': {'simultaneous_window': 0.05}},
        'Filtro Espacial': {'enabled': True, 'params': {'min_finger_distance': 35, 'adjacent_keys_threshold': 2}},
        'Zona Salida': {'enabled': False, 'params': {'exit_zone_margin': 30, 'exit_grace_time': 0.3}}
    },
    
    'sensitive': {
        # Configuración sensible (respuesta rápida)
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.03}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 2.5, 'release_threshold': 3.5}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 5}},
        'Multi-nota': {'enabled': True, 'params': {'simultaneous_window': 0.04}},
        'Filtro Espacial': {'enabled': True, 'params': {'min_finger_distance': 30, 'adjacent_keys_threshold': 1}},
        'Zona Salida': {'enabled': False, 'params': {'exit_zone_margin': 25, 'exit_grace_time': 0.2}}
    },
    
    'stable': {
        # Configuración estable (menos falsos positivos)
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.08}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 3.5, 'release_threshold': 4.5}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 9}},
        'Multi-nota': {'enabled': True, 'params': {'simultaneous_window': 0.06}},
        'Filtro Espacial': {'enabled': True, 'params': {'min_finger_distance': 40, 'adjacent_keys_threshold': 2}},
        'Zona Salida': {'enabled': True, 'params': {'exit_zone_margin': 35, 'exit_grace_time': 0.4}}
    },
    
    'minimal': {
        # Solo algoritmos esenciales
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.05}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 3.0, 'release_threshold': 4.0}},
        'Suavizado': {'enabled': False, 'params': {}},
        'Multi-nota': {'enabled': False, 'params': {}},
        'Filtro Espacial': {'enabled': False, 'params': {}},
        'Zona Salida': {'enabled': False, 'params': {}}
    }
}

# ==============================================================================
# FUNCIONES DE UTILIDAD
# ==============================================================================

def get_active_algorithms():
    """Retorna lista de nombres de algoritmos activos."""
    return [name for name, config in ALGORITHMS_CONFIG.items() if config['enabled']]


def get_algorithm_config(name):
    """Obtiene configuración de un algoritmo específico."""
    return ALGORITHMS_CONFIG.get(name, None)


def apply_preset(preset_name):
    """
    Aplica un preset de configuración.
    
    Args:
        preset_name: 'default', 'sensitive', 'stable' o 'minimal'
    """
    global ALGORITHMS_CONFIG
    
    if preset_name not in PRESETS:
        raise ValueError(f"Preset '{preset_name}' no existe. Disponibles: {list(PRESETS.keys())}")
    
    preset = PRESETS[preset_name]
    
    # Actualizar configuración global
    for algo_name, config in preset.items():
        if algo_name in ALGORITHMS_CONFIG:
            ALGORITHMS_CONFIG[algo_name] = config.copy()
    
    print(f"✓ Preset '{preset_name}' aplicado")


def print_config():
    """Imprime la configuración actual."""
    print("\n" + "="*70)
    print("CONFIGURACIÓN DE ALGORITMOS")
    print("="*70)
    
    for name, config in ALGORITHMS_CONFIG.items():
        status = "✓ ACTIVO" if config['enabled'] else "✗ INACTIVO"
        print(f"\n{name}: [{status}]")
        
        if config['params']:
            for param, value in config['params'].items():
                print(f"  - {param}: {value}")
    
    print("\n" + "="*70)
    print(f"Total: {len(get_active_algorithms())}/{len(ALGORITHMS_CONFIG)} activos")
    print("="*70 + "\n")


# ==============================================================================
# VALIDACIÓN
# ==============================================================================

def validate_config():
    """Valida que la configuración sea correcta."""
    errors = []
    
    for name, config in ALGORITHMS_CONFIG.items():
        if 'enabled' not in config:
            errors.append(f"'{name}' no tiene campo 'enabled'")
        
        if 'params' not in config:
            errors.append(f"'{name}' no tiene campo 'params'")
    
    if errors:
        print("⚠ ERRORES EN CONFIGURACIÓN:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✓ Configuración válida")
    return True


if __name__ == '__main__':
    # Validar y mostrar configuración
    validate_config()
    print_config()

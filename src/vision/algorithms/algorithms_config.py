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
    # ALGORITMO 0: Una Nota Por Dedo
    # Garantiza que cada dedo solo active UNA tecla a la vez
    'Una Nota Por Dedo': {
        'enabled': False,  # ← DESHABILITADO por defecto (habilitar en presets según necesidad)
        'params': {
            'selection_mode': 'depth',      # 'depth' (más profundo) o 'center' (más centrado)
            'min_depth_advantage': 0.3,     # cm de ventaja para cambiar de tecla
            'sticky_time': 0.1              # Tiempo (s) que una tecla permanece "pegajosa"
        },
        'description': 'Asegura que cada dedo físico solo active una tecla, evitando múltiples notas por imprecisión.'
    },
    
    # ALGORITMO 1: Anti-rebote (Debouncing)
    # Previene activaciones múltiples rápidas de la misma tecla
    'Antirebote': {
        'enabled': False,  # ← DESHABILITADO por defecto
        'params': {
            'debounce_time': 0.08  # Tiempo mínimo (s) entre activaciones (0.03-0.10)
        },
        'description': 'Evita que una tecla se active múltiples veces por vibración del dedo.'
    },
    
    # ALGORITMO 2: Histéresis
    # Usa umbrales diferentes para presionar y soltar teclas
    'Histéresis': {
        'enabled': False,  # ← DESHABILITADO por defecto
        'params': {
            'press_threshold': 2.0,    # Profundidad (cm) para activar (1.5-3.0)
            'release_threshold': 3.0   # Profundidad (cm) para liberar (2.5-4.0)
        },
        'description': 'Usa diferentes umbrales para presionar y soltar, evitando parpadeo.'
    },
    
    # ALGORITMO 3: Suavizado de velocidad
    # Calcula velocidad promediando múltiples mediciones
    'Suavizado': {
        'enabled': False,  # ← DESHABILITADO por defecto
        'params': {
            'smoothing_window': 5  # Número de mediciones para promediar (3-10)
        },
        'description': 'Suaviza las mediciones de profundidad para reducir ruido.'
    },
    
    # ALGORITMO 4: Multi-nota (Acordes)
    # Detecta cuando múltiples teclas se presionan simultáneamente
    'Multi-nota': {
        'enabled': False,  # Deshabilitado - puede causar problemas
        'params': {
            'simultaneous_window': 0.05  # Ventana temporal (s) para acordes (0.03-0.10)
        },
        'description': 'Permite tocar acordes (múltiples notas simultáneas). Puede causar falsas activaciones.'
    },
    
    # ALGORITMO 5: Filtrado espacial
    # Previene que dedos cercanos activen múltiples teclas adyacentes
    'Filtro Espacial': {
        'enabled': False,  # ← DESHABILITADO por defecto
        'params': {
            'min_finger_distance': 40,      # Distancia mínima (px) entre dedos (25-50)
            'adjacent_keys_threshold': 1    # Máxima distancia (teclas) considerada adyacente (1-3)
        },
        'description': 'Evita que dedos cercanos activen teclas adyacentes por error.'
    },
    
    # ALGORITMO 6: Zona de salida
    # Previene titubeo cuando el dedo sale del borde inferior del teclado
    'Zona Salida': {
        'enabled': False,  # ← DESHABILITADO por defecto
        'params': {
            'exit_zone_margin': 25,    # Margen (px) desde borde inferior (20-50)
            'exit_grace_time': 0.2     # Tiempo de gracia (s) para confirmar salida (0.2-0.5)
        },
        'description': 'Evita notas fantasma cuando el dedo sale del área del teclado.'
    }
}


EXECUTION_ORDER = [
    'Una Nota Por Dedo',  # ← PRIMERO: garantiza 1 dedo = 1 tecla
    'Filtro Espacial',     # Filtra dedos muy cercanos
    'Antirebote',          # Evita rebotes
    'Histéresis',          # Umbrales diferenciados
    'Suavizado',           # Suaviza mediciones
    'Zona Salida',         # Maneja salida del teclado
    'Multi-nota'           # Acordes (último)
]

PRESETS = {
    'none': {
        # SIN ALGORITMOS - Detección pura (para diagnóstico)
        # Todas las intersecciones pasan sin filtros
        'Una Nota Por Dedo': {'enabled': False, 'params': {}},
        'Antirebote': {'enabled': False, 'params': {}},
        'Histéresis': {'enabled': False, 'params': {}},
        'Suavizado': {'enabled': False, 'params': {}},
        'Multi-nota': {'enabled': False, 'params': {}},
        'Filtro Espacial': {'enabled': False, 'params': {}},
        'Zona Salida': {'enabled': False, 'params': {}}
    },
    
    'default': {
        # Configuración por defecto - TODOS los algoritmos esenciales habilitados
        'Una Nota Por Dedo': {'enabled': True, 'params': {'selection_mode': 'depth', 'min_depth_advantage': 0.3, 'sticky_time': 0.1}},
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.08}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 2.0, 'release_threshold': 3.0}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 5}},
        'Multi-nota': {'enabled': False, 'params': {'simultaneous_window': 0.05}},
        'Filtro Espacial': {'enabled': True, 'params': {'min_finger_distance': 40, 'adjacent_keys_threshold': 1}},
        'Zona Salida': {'enabled': True, 'params': {'exit_zone_margin': 25, 'exit_grace_time': 0.2}}
    },
    
    'sensitive': {
        # Respuesta rápida - para usuarios experimentados
        'Una Nota Por Dedo': {'enabled': True, 'params': {'selection_mode': 'depth', 'min_depth_advantage': 0.2, 'sticky_time': 0.05}},
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.04}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 1.5, 'release_threshold': 2.5}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 3}},
        'Multi-nota': {'enabled': False, 'params': {'simultaneous_window': 0.04}},
        'Filtro Espacial': {'enabled': True, 'params': {'min_finger_distance': 30, 'adjacent_keys_threshold': 1}},
        'Zona Salida': {'enabled': True, 'params': {'exit_zone_margin': 20, 'exit_grace_time': 0.15}}
    },
    
    'stable': {
        # Máxima estabilidad - menos falsos positivos
        'Una Nota Por Dedo': {'enabled': True, 'params': {'selection_mode': 'depth', 'min_depth_advantage': 0.5, 'sticky_time': 0.15}},
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.12}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 2.5, 'release_threshold': 4.0}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 7}},
        'Multi-nota': {'enabled': False, 'params': {'simultaneous_window': 0.06}},
        'Filtro Espacial': {'enabled': True, 'params': {'min_finger_distance': 50, 'adjacent_keys_threshold': 2}},
        'Zona Salida': {'enabled': True, 'params': {'exit_zone_margin': 35, 'exit_grace_time': 0.3}}
    },
    
    'minimal': {
        # Solo lo esencial - diagnóstico
        'Una Nota Por Dedo': {'enabled': True, 'params': {'selection_mode': 'depth', 'min_depth_advantage': 0.3, 'sticky_time': 0.1}},
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.06}},
        'Histéresis': {'enabled': False, 'params': {}},
        'Suavizado': {'enabled': False, 'params': {}},
        'Multi-nota': {'enabled': False, 'params': {}},
        'Filtro Espacial': {'enabled': False, 'params': {}},
        'Zona Salida': {'enabled': False, 'params': {}}
    },
    
    'acordes': {
        # Para tocar acordes (múltiples dedos)
        'Una Nota Por Dedo': {'enabled': True, 'params': {'selection_mode': 'depth', 'min_depth_advantage': 0.3, 'sticky_time': 0.1}},
        'Antirebote': {'enabled': True, 'params': {'debounce_time': 0.06}},
        'Histéresis': {'enabled': True, 'params': {'press_threshold': 2.0, 'release_threshold': 3.0}},
        'Suavizado': {'enabled': True, 'params': {'smoothing_window': 5}},
        'Multi-nota': {'enabled': True, 'params': {'simultaneous_window': 0.08}},
        'Filtro Espacial': {'enabled': False, 'params': {}},  # Deshabilitado para permitir acordes
        'Zona Salida': {'enabled': True, 'params': {'exit_zone_margin': 25, 'exit_grace_time': 0.2}}
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

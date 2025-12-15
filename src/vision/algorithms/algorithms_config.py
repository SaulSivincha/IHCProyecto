#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración de Algoritmos de Detección
Sistema limpio - Listo para agregar nuevos algoritmos
"""

# ==============================================================================
# CONFIGURACIÓN DE ALGORITMOS
# ==============================================================================

ALGORITHMS_CONFIG = {
    'Una Nota Por Acción': {
        'enabled': True,
        'params': {
            # Calibración en MESA:
            # 0 cm = Tocando (aprox)
            # +5 cm = Aire
            'profundidad_activacion': 2.0,   # Activa si está CERCA de la mesa (<= 2.0)
            'profundidad_reset': 4.0         # Resetea si SUBE (>= 4.0)
        },
        'description': 'Evita múltiples activaciones durante un solo gesto. Solo permite tocar de nuevo después de alejarse.'
    }
}

# Orden de ejecución de algoritmos
EXECUTION_ORDER = [
    'Una Nota Por Acción',  # Evita activaciones múltiples en un gesto
]


# ==============================================================================
# PRESETS (Configuraciones predefinidas)
# ==============================================================================

PRESETS = {
    'none': {
        # Sin algoritmos - Detección pura
    },
}


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def apply_preset(preset_name: str):
    """Aplica un preset de configuración."""
    if preset_name not in PRESETS:
        print(f"⚠️ Preset '{preset_name}' no existe")
        return False
    
    preset = PRESETS[preset_name]
    
    # Aplicar configuración del preset
    for algo_name, algo_config in preset.items():
        if algo_name in ALGORITHMS_CONFIG:
            ALGORITHMS_CONFIG[algo_name]['enabled'] = algo_config.get('enabled', False)
            if 'params' in algo_config:
                ALGORITHMS_CONFIG[algo_name]['params'].update(algo_config['params'])
    
    print(f"✓ Preset '{preset_name}' aplicado")
    return True


def get_active_algorithms():
    """Retorna lista de nombres de algoritmos activos."""
    return [name for name, config in ALGORITHMS_CONFIG.items() 
            if config.get('enabled', False)]


def print_config_summary():
    """Imprime resumen de configuración actual."""
    print("\n=== CONFIGURACIÓN DE ALGORITMOS ===")
    
    if not ALGORITHMS_CONFIG:
        print("  (Sin algoritmos configurados)")
        return
    
    active = get_active_algorithms()
    print(f"  Algoritmos totales: {len(ALGORITHMS_CONFIG)}")
    print(f"  Algoritmos activos: {len(active)}")
    
    if active:
        print("\n  Activos:")
        for name in active:
            params = ALGORITHMS_CONFIG[name].get('params', {})
            print(f"    ✓ {name}")
            if params:
                for param, value in params.items():
                    print(f"        {param}: {value}")
    
    print("=" * 35)

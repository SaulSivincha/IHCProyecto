#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyboardMap Modular - Sistema de detección refactorizado
Usa arquitectura modular con algoritmos independientes

@author: mherrera
@updated: 2025 - Modular Architecture
"""
import time
import numpy as np
from collections import deque
from src.config.app_config import AppConfig
from src.vision.stereo_config import StereoConfig

# Sistema modular de algoritmos - solo importar lo necesario
from src.vision.algorithms.algorithm_manager import AlgorithmManager


class KeyboardMapModular:
    """
    Mapeador de teclado modular con algoritmos independientes.
    
    Ventajas:
    - Algoritmos separados en archivos individuales
    - Fácil agregar/eliminar algoritmos
    - Configuración centralizada
    - Activar/desactivar sin tocar código
    """
    
    def __init__(self, depth_threshold=None, config_preset='default'):
        """
        Inicializa el mapeador con sistema modular.
        
        Args:
            depth_threshold: Profundidad máxima (cm) para detectar contacto
            config_preset: Preset de configuración ('default', 'sensitive', 'stable', 'minimal')
        """
        self.prev_map = np.empty(0, dtype=bool)
        self.depth_threshold = depth_threshold if depth_threshold is not None else StereoConfig.DEPTH_THRESHOLD
        self.finger_depths = {}
        
        # Sistema de velocidad (legacy, para compatibilidad)
        self.finger_depth_history = {}
        self.velocity_threshold = StereoConfig.VELOCITY_THRESHOLD
        self.velocity_enabled = StereoConfig.VELOCITY_ENABLED
        self.velocity_history_size = StereoConfig.VELOCITY_HISTORY_SIZE
        
        # Debugeo
        self._debug_frame_count = 0
        
        # NUEVO: Sistema modular de algoritmos - USAR SINGLETON GLOBAL
        from src.vision.algorithms import get_algorithm_manager
        self.algorithm_manager = get_algorithm_manager()
        
        # Configuración de suavizado de profundidad (dinámico desde algorithms_config)
        self._update_smoothing_config()
        
    def _update_smoothing_config(self):
        """Actualiza parámetros de suavizado desde algorithms_config."""
        from src.vision.algorithms.algorithms_config import ALGORITHMS_CONFIG
        
        smoothing_config = ALGORITHMS_CONFIG.get('Suavizado de Profundidad', {})
        self.smoothing_enabled = smoothing_config.get('enabled', True)
        params = smoothing_config.get('params', {})
        self.smoothing_window = params.get('smoothing_window', 3)
        self.outlier_threshold = params.get('outlier_threshold', 15.0)
        
    def _initialize_algorithms(self):
        """Inicializa y registra todos los algoritmos según configuración."""
        
        # NOTA: Este método ya no es necesario porque el manager global
        # ya está inicializado por get_algorithm_manager()
        # Se mantiene para compatibilidad pero no hace nada
        pass
    
    def set_depth_threshold(self, threshold):
        """Actualiza el umbral de profundidad."""
        self.depth_threshold = threshold
    
    def get_kayboard_map(self, virtual_keyboard, fingertips_pos, 
                        finger_depths=None, keyboard_n_key=13):
        """
        Genera el mapa de teclado usando el sistema modular de algoritmos.
        
        Args:
            virtual_keyboard: Instancia de VirtualKeyboard
            fingertips_pos: Lista de posiciones de dedos [(hand_id, tip_id, x, y), ...]
            finger_depths: Dict con profundidades {(hand_id, tip_id): depth_cm}
            keyboard_n_key: Número de teclas
            
        Returns:
            tuple: (on_map, off_map) - Arrays booleanos de teclas presionadas/liberadas
        """
        curr_map = np.full(keyboard_n_key, False, dtype=bool)
        on_map = np.full(keyboard_n_key, False, dtype=bool)
        off_map = np.full(keyboard_n_key, False, dtype=bool)
        
        # Inicializar prev_map si es primera vez
        if len(self.prev_map) == 0:
            self.prev_map = np.full(keyboard_n_key, False, dtype=bool)
        
        if finger_depths is None:
            finger_depths = {}
        
        # FASE 1: Recolectar detecciones brutas (TODAS las intersecciones)
        raw_detections = []
        current_time = time.time()
        
        for fingertip_pos in fingertips_pos:
            hand_id = fingertip_pos[0]
            tip_id = fingertip_pos[1]
            x_pos = fingertip_pos[2]
            y_pos = fingertip_pos[3]
            
            finger_id = (hand_id, tip_id)
            
            # OPTIMIZACIÓN: Verificar profundidad PRIMERO (operación más barata)
            # Si la mano está muy lejos (flotando), evitamos cálculos espaciales costosos
            if finger_id not in finger_depths:
                # [FIX] Sin datos de profundidad: SALTAR FRAME
                # ANTES: Usábamos depth=99.0, pero esto contaminaba el historial
                # de velocidad causando spikes masivos (vel=98cm/frame).
                # AHORA: Simplemente no procesamos este dedo este frame.
                # El historial se mantiene limpio y velocity se calcula
                # solo con datos válidos.
                continue
            else:
                depth = finger_depths[finger_id]
                
                # ESTRATEGIA DE VALIDACIÓN ESTRICTA (Sin Clamping)
                # Evitar "falsos positivos" cuando la mano está muy cerca de la cámara
                # 
                # Rango Físico Razonable para profundidad RELATIVA (depth = abs - mesa):
                # -5.0 cm: Presionando fuerte (dedo "atravesando" el plano virtual)
                # +25.0 cm: Mano levantada en el aire sobre la mesa
                
                if depth < -5.0 or depth > 25.0:
                    # Caso: Profundidad fuera de rango físico posible.
                    # - < -5.0: Error de calibración o mano muy cerca de cámara
                    # - > +25.0: Mano muy lejos del teclado (ignorar)
                    
                    if self._debug_frame_count % 30 == 0:
                        # print(f"[RECHAZADO] Dedo {finger_id} Depth={depth:.1f}cm (Fuera de rango -5 a +25)")
                        pass
                        
                    # Acción: DESCARTAR.
                    continue
            
            # AHORA verificar intersección con teclado (solo si está cerca)
            if virtual_keyboard.intersect((x_pos, y_pos)):
                key = virtual_keyboard.find_key(x_pos, y_pos)
                
                # Verificar que key no sea None y esté en rango válido
                if key is not None and 0 <= key < keyboard_n_key:
                    # Actualizar historial de profundidad
                    if finger_id not in self.finger_depth_history:
                        self.finger_depth_history[finger_id] = deque(maxlen=self.velocity_history_size)
                    self.finger_depth_history[finger_id].append(depth)
                    
                    # NUEVO: Suavizar profundidad para reducir ruido de tracking
                    depth_smoothed = depth
                    
                    if self.smoothing_enabled and len(self.finger_depth_history[finger_id]) >= self.smoothing_window:
                        history = list(self.finger_depth_history[finger_id])
                        # Filtrar outliers extremos antes de promediar
                        recent_values = history[-self.smoothing_window:]
                        median_val = sorted(recent_values)[len(recent_values)//2]
                        filtered = [v for v in recent_values if abs(v - median_val) < self.outlier_threshold]
                        if len(filtered) > 0:
                            depth_smoothed = sum(filtered) / len(filtered)
                    
                    # Calcular velocidad usando profundidad suavizada
                    velocity = 0.0
                    if len(self.finger_depth_history[finger_id]) >= 2:
                        history = list(self.finger_depth_history[finger_id])
                        velocity = history[-2] - history[-1]
                    
                    # AGREGAR a raw_detections
                    raw_detections.append((finger_id, key, depth_smoothed, velocity, x_pos, y_pos))
        
        # DEBUG INICIAL: Mostrar cuántas intersecciones se detectaron
        if not hasattr(self, '_debug_frame_count'):
            self._debug_frame_count = 0
        self._debug_frame_count += 1
        
        if len(raw_detections) > 0 and self._debug_frame_count % 30 == 0:
            print(f"\n[DEBUG FASE 1] Intersecciones detectadas: {len(raw_detections)}")
            for det in raw_detections[:3]:  # Mostrar primeras 3
                finger_id, key, depth, velocity, x, y = det
                print(f"  Dedo {finger_id}, Tecla {key}, Pos=({x:.0f},{y:.0f}), Depth={depth:.1f}cm, Vel={velocity:.2f}")
        
        # FASE 1.5: Aplicar filtro de profundidad SOLO si hay algoritmos activos
        has_active_algorithms = any(algo.is_enabled() for algo in self.algorithm_manager.algorithms)
        
        # DEBUG: Mostrar estado de filtrado
        if not hasattr(self, '_filter_debug_shown'):
            active_algos = [algo.name for algo in self.algorithm_manager.algorithms if algo.is_enabled()]
            if has_active_algorithms:
                # print(f"\n[KEYBOARD_MAPPER] Algoritmos activos: {active_algos}")
                # print(f"[KEYBOARD_MAPPER] [INFO] Filtro de profundidad ACTIVADO (umbral >= 10cm)")
                pass
            else:
                # print(f"\n[KEYBOARD_MAPPER] No hay algoritmos activos")
                # print(f"[KEYBOARD_MAPPER] [INFO] Filtro de profundidad DESACTIVADO")
                pass
            self._filter_debug_shown = True
        
        if has_active_algorithms:
            # Filtrar por profundidad (solo cuando hay algoritmos activos)
            filtered_by_depth = []
            # CONVENCIÓN DE SIGNOS (profundidad RELATIVA a la mesa):
            # depth > 0: dedo EN EL AIRE (más lejos de cámara que mesa)
            # depth ≈ 0: dedo TOCANDO la mesa
            # depth < 0: dedo PRESIONANDO (más cerca de cámara que mesa)
            # 
            # Queremos activar cuando depth <= threshold (cercano o tocando mesa)
            activation_threshold = self.depth_threshold  
            
            for detection in raw_detections:
                finger_id, key, depth, velocity, x_pos, y_pos = detection
                
                # FIX: Activar si depth <= threshold
                # Ejemplo: threshold=4.0
                # depth=+20.0 (aire lejano) → 20.0 <= 4.0 → NO activa ✓
                # depth=+3.0 (casi tocando) → 3.0 <= 4.0 → ACTIVA ✓
                # depth=0.0 (tocando) → 0.0 <= 4.0 → ACTIVA ✓  
                # depth=-2.0 (presionando) → -2.0 <= 4.0 → ACTIVA ✓
                should_activate = (depth <= activation_threshold)
                
                if should_activate:
                    filtered_by_depth.append(detection)
            
            # DEBUG: Mostrar resultado del filtro
            if self._debug_frame_count % 30 == 0 and len(raw_detections) > 0:
                # print(f"[DEBUG FILTRO] Antes: {len(raw_detections)}, Despues: {len(filtered_by_depth)}")
                if len(filtered_by_depth) == 0 and len(raw_detections) > 0:
                    pass
                    # print(f"[ALERTA] TODAS filtradas! Depths: {[d[2] for d in raw_detections[:3]]}")
            
            raw_detections = filtered_by_depth
        else:
            if len(raw_detections) > 0 and self._debug_frame_count % 30 == 0:
                pass
                # print(f"[DEBUG] Pasando {len(raw_detections)} intersecciones SIN filtrar")
        
        # FASE 2: Procesar detecciones a través de algoritmos modulares
        context = {
            'timestamp': current_time,
            'virtual_keyboard': virtual_keyboard,
            'keyboard_n_key': keyboard_n_key
        }
        
        # Aplicar cadena de algoritmos (REACTIVADO para filtrar rebotes y detectar acordes)
        filtered_detections = self.algorithm_manager.process_detections(raw_detections, context)
        
        # DEBUG: Mostrar resultado de algoritmos
        if self._debug_frame_count % 30 == 0 and len(raw_detections) > 0:
            # print(f"[DEBUG ALGORITMOS] Antes: {len(raw_detections)}, Despues: {len(filtered_detections)}")
            if len(filtered_detections) == 0 and len(raw_detections) > 0:
                pass
                # print(f"[ALERTA] ALGORITMOS bloquearon todo!")
        
        # FASE 3: Aplicar detecciones filtradas al mapa
        for detection in filtered_detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            curr_map[key] = True
            self.finger_depths[finger_id] = depth
        
        # FASE 4: Calcular cambios (on/off)
        on_map = np.logical_and(curr_map, np.logical_not(self.prev_map))
        off_map = np.logical_and(self.prev_map, np.logical_not(curr_map))
        
        # Actualizar prev_map
        self.prev_map = curr_map.copy()
        
        return on_map, off_map
    
    # ==================== MÉTODOS DE CONTROL ====================
    
    def enable_algorithm(self, name):
        """Activa un algoritmo específico."""
        self.algorithm_manager.enable_algorithm(name)
    
    def disable_algorithm(self, name):
        """Desactiva un algoritmo específico."""
        self.algorithm_manager.disable_algorithm(name)
    
    def configure_algorithm(self, name, **params):
        """Configura parámetros de un algoritmo."""
        # Si es suavizado de profundidad, actualizar también nuestra config local
        if name == 'Suavizado de Profundidad':
            # Actualizar en algorithms_config
            self.algorithm_manager.configure_algorithm(name, **params)
            # Recargar nuestra configuración local
            self._update_smoothing_config()
            print(f"✓ Suavizado actualizado: enabled={self.smoothing_enabled}, window={self.smoothing_window}, threshold={self.outlier_threshold}cm")
        else:
            self.algorithm_manager.configure_algorithm(name, **params)
    
    def reset_algorithms(self):
        """Reinicia el estado de todos los algoritmos."""
        self.algorithm_manager.reset_all()
    
    def get_algorithm_stats(self):
        """Obtiene estadísticas de todos los algoritmos."""
        return self.algorithm_manager.get_all_stats()
    
    def get_algorithm_configs(self):
        """Obtiene configuración de todos los algoritmos."""
        return self.algorithm_manager.get_all_configs()
    
    def print_algorithm_status(self):
        """Imprime el estado actual de todos los algoritmos."""
        self.algorithm_manager.print_status()
    
    def get_current_chord(self):
        """
        Obtiene el acorde actual detectado por el algoritmo Multi-nota.
        
        Returns:
            set: Conjunto de teclas en el acorde actual
        """
        multinota = self.algorithm_manager.get_algorithm('Multi-nota')
        if multinota and multinota.is_enabled():
            return multinota.get_current_chord()
        return set()


# Alias para compatibilidad con código existente
KeyboardMap = KeyboardMapModular

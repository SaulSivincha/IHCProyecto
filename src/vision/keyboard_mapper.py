#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 30 00:43:58 2021
Actualizado para usar visión estereoscópica y profundidad 3D
Con detección de velocidad para evitar toques accidentales

@author: mherrera
"""
import numpy as np
from collections import deque
from src.config.app_config import AppConfig


class KeyboardMap:
    def __init__(self, depth_threshold=None):
        """
        Inicializa el mapeador de teclado para visión estereoscópica.
        
        Args:
            depth_threshold: Profundidad máxima (cm) para detectar contacto con tecla.
                            Si es None, usa AppConfig.DEPTH_THRESHOLD
                            Valores típicos: 2-5 cm (ajustar según calibración)
        """
        self.prev_map = np.empty(0, dtype=bool)
        self.depth_threshold = depth_threshold if depth_threshold is not None else AppConfig.DEPTH_THRESHOLD
        self.finger_depths = {}  # Para rastrear profundidad de cada dedo
        
        # Sistema de detección de velocidad
        self.finger_depth_history = {}  # {finger_id: deque([z1, z2, z3], maxlen=N)}
        self.velocity_threshold = AppConfig.VELOCITY_THRESHOLD
        self.velocity_enabled = AppConfig.VELOCITY_ENABLED
        self.velocity_history_size = AppConfig.VELOCITY_HISTORY_SIZE

    def set_depth_threshold(self, threshold):
        """Ajusta dinámicamente el umbral de profundidad"""
        self.depth_threshold = threshold
        # También actualizar en AppConfig para consistencia
        AppConfig.DEPTH_THRESHOLD = threshold

    def get_kayboard_map(self,
                         virtual_keyboard,
                         fingertips_pos,
                         finger_depths=None,
                         keyboard_n_key=13):
        """
        Mapea la posición de dedos a teclas basándose en profundidad 3D.
        
        Args:
            virtual_keyboard: Objeto VirtualKeyboard con geometría del teclado
            fingertips_pos: Lista de posiciones de puntitas [hand_id, tip_id, x, y]
            finger_depths: Dict {finger_id: depth_distance} profundidad corregida (D - delta_y)
            keyboard_n_key: Número de teclas en el teclado
            
        Returns:
            (on_map, off_map): Arrays booleanos de teclas presionadas/liberadas
        """
        curr_map = np.full(keyboard_n_key, False, dtype=bool)
        on_map = np.full(keyboard_n_key, False, dtype=bool)
        off_map = np.full(keyboard_n_key, False, dtype=bool)

        # Inicializar prev_map si es la primera llamada
        if len(self.prev_map) == 0:
            self.prev_map = np.full(keyboard_n_key, False, dtype=bool)

        # Si no hay información de profundidad, usar parámetro anterior (compatibilidad)
        if finger_depths is None:
            finger_depths = {}
        
        for fingertip_pos in fingertips_pos:
            hand_id = fingertip_pos[0]
            tip_id = fingertip_pos[1]
            x_pos = fingertip_pos[2]
            y_pos = fingertip_pos[3]
            
            # Crear identificador único para el dedo
            finger_id = (hand_id, tip_id)
            
            # Verificar si intersecta con el teclado (posición XY)
            if virtual_keyboard.intersect((x_pos, y_pos)):
                key = virtual_keyboard.find_key(x_pos, y_pos)
                
                if key >= 0 and key < keyboard_n_key:
                    # CAMBIO CLAVE: Usar profundidad 3D + detección de velocidad
                    if finger_id in finger_depths:
                        depth = finger_depths[finger_id]
                        
                        # Actualizar historial de profundidad para este dedo
                        if finger_id not in self.finger_depth_history:
                            self.finger_depth_history[finger_id] = deque(maxlen=self.velocity_history_size)
                        self.finger_depth_history[finger_id].append(depth)
                        
                        # Verificar condición de activación
                        should_activate = False
                        
                        if self.velocity_enabled and len(self.finger_depth_history[finger_id]) >= 2:
                            # MODO VELOCIDAD: Requiere movimiento descendente pronunciado
                            history = list(self.finger_depth_history[finger_id])
                            
                            # Calcular velocidad (diferencia entre últimas posiciones)
                            # Velocidad negativa = movimiento hacia abajo (acercamiento)
                            velocity = history[-2] - history[-1]  # z_anterior - z_actual
                            
                            # Activar si:
                            # 1. Está dentro del threshold de profundidad
                            # 2. Tiene velocidad descendente suficiente
                            if depth <= self.depth_threshold and velocity >= self.velocity_threshold:
                                should_activate = True
                        else:
                            # MODO CLÁSICO: Solo threshold de profundidad
                            if depth <= self.depth_threshold:
                                should_activate = True
                        
                        if should_activate:
                            curr_map[key] = True
                    else:
                        # Fallback: si no hay profundidad, asumir que está presionando
                        # (compatibilidad con código anterior)
                        curr_map[key] = True
        
        # Lógica de detección de cambios (on/off)
        on_map = np.logical_and(curr_map, np.logical_not(self.prev_map))
        off_map = np.logical_and(self.prev_map, np.logical_not(curr_map))
            
        self.prev_map = curr_map.copy()
        return on_map, off_map

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI para Panel de Configuración de Detección
Permite ajustar parámetros en tiempo real

@author: mherrera
"""

import cv2
import numpy as np
from src.config.app_config import AppConfig


class ConfigUI:
    """Interfaz de usuario para configuración de detección"""
    
    def __init__(self, width, height):
        """
        Inicializa la UI de configuración
        
        Args:
            width: Ancho de la pantalla combinada
            height: Alto de la pantalla
        """
        self.width = width
        self.height = height
        
        # Índice del parámetro seleccionado
        self.selected_param = 0
        
        # Parámetros configurables
        self.params = [
            {
                'name': 'Umbral de Profundidad',
                'key': 'depth_threshold',
                'value': AppConfig.DEPTH_THRESHOLD,
                'min': 1.0,
                'max': 5.0,
                'step': 0.1,
                'unit': 'cm',
                'desc': 'Distancia máxima para activar tecla'
            },
            {
                'name': 'Velocidad Mínima',
                'key': 'velocity_threshold',
                'value': AppConfig.VELOCITY_THRESHOLD,
                'min': 0.5,
                'max': 4.0,
                'step': 0.1,
                'unit': 'cm/f',
                'desc': 'Velocidad descendente requerida'
            },
            {
                'name': 'Detección por Velocidad',
                'key': 'velocity_enabled',
                'value': AppConfig.VELOCITY_ENABLED,
                'min': 0,
                'max': 1,
                'step': 1,
                'unit': '',
                'desc': 'Activar/desactivar sistema velocidad'
            },
            {
                'name': 'Tamaño Historial',
                'key': 'velocity_history_size',
                'value': AppConfig.VELOCITY_HISTORY_SIZE,
                'min': 2,
                'max': 7,
                'step': 1,
                'unit': 'frames',
                'desc': 'Frames para calcular velocidad'
            }
        ]
        
        # Presets de sensibilidad
        self.presets = [
            {'name': 'Suave', 'key': 'soft'},
            {'name': 'Normal', 'key': 'normal'},
            {'name': 'Fuerte', 'key': 'hard'},
            {'name': 'Clásico', 'key': 'classic'}
        ]
        self.selected_preset = 1  # Normal por defecto
        
        # Colores
        self.bg_color = (30, 30, 30)
        self.text_color = (255, 255, 255)
        self.selected_color = (0, 255, 255)
        self.header_color = (100, 200, 255)
        self.value_color = (100, 255, 100)
    
    def navigate_up(self):
        """Navegar hacia arriba en la lista"""
        self.selected_param = max(0, self.selected_param - 1)
    
    def navigate_down(self):
        """Navegar hacia abajo en la lista"""
        self.selected_param = min(len(self.params) - 1, self.selected_param + 1)
    
    def increase_value(self):
        """Aumentar el valor del parámetro seleccionado"""
        param = self.params[self.selected_param]
        new_value = min(param['max'], param['value'] + param['step'])
        param['value'] = round(new_value, 2)
        self._apply_changes()
    
    def decrease_value(self):
        """Disminuir el valor del parámetro seleccionado"""
        param = self.params[self.selected_param]
        new_value = max(param['min'], param['value'] - param['step'])
        param['value'] = round(new_value, 2)
        self._apply_changes()
    
    def apply_preset(self, preset_key):
        """Aplicar preset de sensibilidad"""
        AppConfig.set_key_sensitivity(preset_key)
        # Actualizar valores en la UI
        self.params[0]['value'] = AppConfig.DEPTH_THRESHOLD
        self.params[1]['value'] = AppConfig.VELOCITY_THRESHOLD
        self.params[2]['value'] = int(AppConfig.VELOCITY_ENABLED)
        self.params[3]['value'] = AppConfig.VELOCITY_HISTORY_SIZE
    
    def _apply_changes(self):
        """Aplicar cambios a AppConfig"""
        AppConfig.DEPTH_THRESHOLD = self.params[0]['value']
        AppConfig.VELOCITY_THRESHOLD = self.params[1]['value']
        AppConfig.VELOCITY_ENABLED = bool(self.params[2]['value'])
        AppConfig.VELOCITY_HISTORY_SIZE = int(self.params[3]['value'])
    
    def draw_config_panel(self, frame):
        """
        Dibuja el panel de configuración sobre el frame
        
        Args:
            frame: Frame combinado (izquierda + derecha)
        
        Returns:
            frame con panel dibujado
        """
        # Crear overlay semi-transparente
        overlay = frame.copy()
        
        # Fondo del panel (centro de la pantalla)
        panel_width = 800
        panel_height = 550
        panel_x = (self.width - panel_width) // 2
        panel_y = (self.height - panel_height) // 2
        
        cv2.rectangle(overlay, 
                     (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height),
                     self.bg_color, -1)
        
        # Aplicar transparencia
        alpha = 0.92
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        # Título
        title = "CONFIGURACION DE DETECCION"
        cv2.putText(frame, title,
                   (panel_x + 30, panel_y + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.header_color, 2)
        
        # Línea separadora
        cv2.line(frame, 
                (panel_x + 20, panel_y + 55), 
                (panel_x + panel_width - 20, panel_y + 55),
                self.header_color, 2)
        
        # Dibujar parámetros
        y_offset = panel_y + 90
        for i, param in enumerate(self.params):
            is_selected = (i == self.selected_param)
            color = self.selected_color if is_selected else self.text_color
            
            # Flecha de selección
            if is_selected:
                cv2.putText(frame, ">",
                           (panel_x + 30, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.selected_color, 2)
            
            # Nombre del parámetro
            cv2.putText(frame, param['name'],
                       (panel_x + 60, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Valor
            if param['key'] == 'velocity_enabled':
                value_text = "ON" if param['value'] else "OFF"
            else:
                value_text = f"{param['value']:.1f} {param['unit']}"
            
            cv2.putText(frame, value_text,
                       (panel_x + 450, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.value_color, 2)
            
            # Descripción (texto pequeño)
            cv2.putText(frame, param['desc'],
                       (panel_x + 60, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            
            y_offset += 65
        
        # Línea separadora para presets
        y_offset += 10
        cv2.line(frame, 
                (panel_x + 20, y_offset), 
                (panel_x + panel_width - 20, y_offset),
                (100, 100, 100), 1)
        y_offset += 30
        
        # Presets
        cv2.putText(frame, "PRESETS:",
                   (panel_x + 30, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.header_color, 2)
        
        y_offset += 35
        preset_x = panel_x + 60
        for i, preset in enumerate(self.presets):
            text = f"[{i+1}] {preset['name']}"
            color = self.selected_color if i == self.selected_preset else (180, 180, 180)
            cv2.putText(frame, text,
                       (preset_x, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            preset_x += 150
        
        # Controles
        y_offset = panel_y + panel_height - 80
        cv2.line(frame, 
                (panel_x + 20, y_offset - 10), 
                (panel_x + panel_width - 20, y_offset - 10),
                (100, 100, 100), 1)
        
        controls = [
            "W/S: Navegar",
            "A/D: Ajustar valor",
            "1-4: Presets",
            "Q: Salir"
        ]
        
        control_x = panel_x + 40
        for control in controls:
            cv2.putText(frame, control,
                       (control_x, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            control_x += 180
        
        return frame
    
    def reset_selection(self):
        """Resetea la selección"""
        self.selected_param = 0

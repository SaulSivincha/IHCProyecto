#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de ayuda para interfaz de usuario mejorada
"""

import cv2
import numpy as np
from src.vision.stereo_config import StereoConfig
from src.config.theme import Theme


class UIHelper:
    """Clase para crear interfaz más amigable"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.show_instructions = True
        # Usar configuración centralizada
        self.instructions_timeout = StereoConfig.INSTRUCTIONS_TIMEOUT
        self.frame_count = 0
        self.input_buffer = ""
        self.input_active = False
        self.input_prompt = ""
        
    def draw_welcome_screen(self, frame):
        """
        Legacy method removed.
        """
        return frame

    
    def draw_instructions_bar(self, frame, game_mode):
        """
        Legacy method removed.
        """
        return frame

    
    def draw_improved_dashboard(self, frame, fps1, fps2, cps, X, Y, Z, D, Dr):
        """Dibuja dashboard mejorado y MÁS GRANDE"""
        panel_width = 350
        panel_height = 260
        panel_x = 20
        panel_y = self.height - panel_height - 20
        
        overlay = frame.copy()
        cv2.rectangle(overlay, 
                     (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height),
                     Theme.BG_PANEL, -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        cv2.rectangle(frame,
                     (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     Theme.BORDER_DEFAULT, 3)
        
        cv2.putText(frame, "STATUS", (panel_x + 15, panel_y + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, Theme.TEXT_HIGHLIGHT, 2)
        
        y_offset = panel_y + 70
        line_height = 35
        font_scale = 0.7
        
        fps_color = Theme.SUCCESS if (fps1 + fps2) / 2 > 20 else Theme.WARNING if (fps1 + fps2) / 2 > 15 else Theme.ERROR
        fps_text = f"FPS: {fps1}/{fps2} (Prom: {(fps1+fps2)//2})"
        cv2.putText(frame, fps_text, (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, fps_color, 2)
        y_offset += line_height
        
        cv2.putText(frame, f"CPS: {cps}", (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, Theme.TEXT_PRIMARY, 2)
        y_offset += line_height
        
        cv2.putText(frame, f"Posicion: X:{X:.1f} Y:{Y:.1f}", 
                   (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)
        y_offset += line_height
        
        cv2.putText(frame, f"Distancia: {D:.1f}cm (Ajuste: {Dr:.1f}cm)",
                   (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)
        
        return frame
    
    def draw_key_indicators(self, frame, active_keys, keyboard_x0, keyboard_y0, keyboard_x1, keyboard_y1):
        """Dibuja indicadores visuales de teclas presionadas"""
        if len(active_keys) == 0:
            return frame
        
        keyboard_width = keyboard_x1 - keyboard_x0
        key_width = keyboard_width / 8
        
        for key_num in active_keys:
            if 0 <= key_num < 13:
                key_x = int(keyboard_x0 + (key_num % 8) * key_width)
                key_w = int(key_width)
                
                overlay = frame.copy()
                cv2.rectangle(overlay, (key_x, keyboard_y0), 
                             (key_x + key_w, keyboard_y1), Theme.KEY_HIGHLIGHT_WHITE, -1)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        return frame
    
    def draw_fps_indicator(self, frame, fps, position=(20, 40)):
        """Dibuja indicador de FPS grande y visible"""
        fps_color = Theme.SUCCESS if fps >= 25 else Theme.WARNING if fps >= 20 else Theme.ERROR
        
        text = f"FPS: {fps}"
        font_scale = 1.0
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        
        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (position[0] - 10, position[1] - text_height - 10),
                     (position[0] + text_width + 10, position[1] + 10),
                     Theme.BG_PANEL, -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        cv2.putText(frame, text, position,
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, fps_color, 2)
        
        return frame
    
    def update(self):
        """Actualiza contador interno"""
        self.frame_count += 1
        if self.frame_count > self.instructions_timeout:
            self.show_instructions = False
    
    def reset_instructions(self):
        """Reinicia la pantalla de instrucciones"""
        self.show_instructions = True
        self.frame_count = 0
    
    def draw_setup_menu(self, frame):
        """
        Legacy method removed.
        """
        return frame

    
    def draw_calibration_progress(self, frame, message, progress_percent=0):
        """
        Legacy method removed.
        """
        return frame

    
    def draw_input_dialog(self, frame, prompt, current_value=""):
        """
        Legacy method removed.
        """
        return frame

    
    def draw_song_selector(self, frame, songs, selected_index=0):
        """
        Legacy method removed.
        """
        return frame

    
    def draw_game_results(self, frame, stats):
        """
        Legacy method removed.
        """
        return frame

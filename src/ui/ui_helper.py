#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de ayuda para interfaz de usuario mejorada
"""

import cv2
import numpy as np
from src.vision.stereo_config import StereoConfig


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
        Pantalla de bienvenida simplificada.
        Solo muestra el título 'PIANO' y una indicación para comenzar.
        """
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo con gradiente oscuro elegante
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # ========== TÍTULO PRINCIPAL (MÁS GRANDE) ==========
        title = "PIANO"
        title_font_scale = 4.0
        title_thickness = 6
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 
                                                  title_font_scale, title_thickness)
        title_x = (frame_width - title_w) // 2
        title_y = frame_height // 2 - 50
        
        # Sombra del título
        cv2.putText(frame, title, (title_x + 8, title_y + 8),
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 0, 0), title_thickness)
        # Título principal con gradiente de colores
        cv2.putText(frame, title, (title_x, title_y),
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 200, 255), title_thickness)
        
        # Subtitle - Mensaje de inicio
        subtitle = "Presione cualquier tecla para comenzar"
        sub_font_scale = 1.2
        (sub_w, sub_h), _ = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, sub_font_scale, 2)
        sub_x = (frame_width - sub_w) // 2
        sub_y = title_y + 120
        
        # ========== DISENO DE DOS COLUMNAS ==========
        col_y_start = 180
        col_spacing = 20
        col_width = (frame_width - col_spacing * 3) // 2
        left_col_x = col_spacing
        right_col_x = col_width + col_spacing * 2
        
        # ========== COLUMNA IZQUIERDA: INSTRUCCIONES ==========
        left_panel_h = 280
        
        left_bg = frame.copy()
        cv2.rectangle(left_bg, (left_col_x, col_y_start), 
                     (left_col_x + col_width, col_y_start + left_panel_h), (30, 30, 50), -1)
        cv2.rectangle(left_bg, (left_col_x, col_y_start), 
                     (left_col_x + col_width, col_y_start + left_panel_h), (0, 200, 255), 3)
        frame = cv2.addWeighted(frame, 0.6, left_bg, 0.4, 0)
        
        # Titulo de instrucciones
        section_title = "INSTRUCCIONES"
        cv2.putText(frame, section_title, (left_col_x + 20, col_y_start + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        
        # Linea decorativa
        cv2.line(frame, (left_col_x + 20, col_y_start + 45), 
                (left_col_x + col_width - 20, col_y_start + 45), (0, 200, 255), 2)
        
        # Instrucciones
        instructions = [
            "Coloca tus manos sobre la mesa",
            "Toca las teclas virtuales",
            "Manten contacto con la mesa",
            "Usa ambos dedos para tocar"
        ]
        
        y_offset = col_y_start + 70
        for instruction in instructions:
            cv2.circle(frame, (left_col_x + 35, y_offset - 5), 4, (0, 200, 255), -1)
            cv2.putText(frame, instruction, (left_col_x + 50, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            y_offset += 35
        
        # ========== COLUMNA DERECHA: CONTROLES ==========
        right_panel_h = 280
        
        right_bg = frame.copy()
        cv2.rectangle(right_bg, (right_col_x, col_y_start), 
                     (right_col_x + col_width, col_y_start + right_panel_h), (30, 30, 50), -1)
        cv2.rectangle(right_bg, (right_col_x, col_y_start), 
                     (right_col_x + col_width, col_y_start + right_panel_h), (255, 200, 0), 3)
        frame = cv2.addWeighted(frame, 0.6, right_bg, 0.4, 0)
        
        # Titulo de controles
        controls_title = "CONTROLES"
        cv2.putText(frame, controls_title, (right_col_x + 20, col_y_start + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2)
        
        # Linea decorativa
        cv2.line(frame, (right_col_x + 20, col_y_start + 45), 
                (right_col_x + col_width - 20, col_y_start + 45), (255, 200, 0), 2)
        
        # Controles
        controls = [
            "[G] Juego de ritmo",
            "[N] Canciones",
            "[F] Modo libre",
            "[L] Aprender teoria",
            "[C] Configuracion",
            "[D] Dashboard",
            "[Q] Salir"
        ]
        
        y_ctrl = col_y_start + 70
        for i, ctrl in enumerate(controls):
            key_bg_x = right_col_x + 25
            key_bg_y = y_ctrl + i * 35 - 20
            key_bg_w = col_width - 50
            key_bg_h = 22
            
            # Fondo destacado
            key_overlay = frame.copy()
            cv2.rectangle(key_overlay, (key_bg_x, key_bg_y), 
                         (key_bg_x + key_bg_w, key_bg_y + key_bg_h), (40, 40, 60), -1)
            frame = cv2.addWeighted(frame, 0.8, key_overlay, 0.2, 0)
            
            cv2.putText(frame, ctrl, (right_col_x + 30, y_ctrl + i * 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        
        # ========== MENSAJE DE INICIO (ya movido arriba, solo agregamos efecto visual) ==========
        # Efecto parpadeante para el subtítulo
        blink_alpha = 0.3 + 0.2 * np.sin(self.frame_count * 0.1)
        blink_bg = frame.copy()
        padding = 20
        cv2.rectangle(blink_bg, (sub_x - padding, sub_y - sub_h - padding), 
                     (sub_x + sub_w + padding, sub_y + padding), (0, 255, 255), -1)
        frame = cv2.addWeighted(frame, 1 - blink_alpha, blink_bg, blink_alpha, 0)
        
        # Redibujar el texto del subtítulo
        cv2.putText(frame, subtitle, (sub_x, sub_y),
                   cv2.FONT_HERSHEY_SIMPLEX, sub_font_scale, (0, 0, 0), 4)
        cv2.putText(frame, subtitle, (sub_x, sub_y),
                   cv2.FONT_HERSHEY_SIMPLEX, sub_font_scale, (180, 180, 255), 2)
        
        return frame
    
    def draw_instructions_bar(self, frame, game_mode):
        """
        Dibuja barra superior con opciones de Configuración y Menú.
        """
        bar_height = 50
        frame_width = frame.shape[1]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, bar_height), (20, 20, 20), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # Modo actual
        mode_text = "MODO JUEGO" if game_mode else "MODO LIBRE"
        mode_color = (0, 255, 0) if game_mode else (255, 255, 0)
        cv2.putText(frame, mode_text, (10, 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
        
        # Teclas disponibles
        if not game_mode:
            help_text = "G: Juego | N: Canciones | F: Libre | L: Teoria | C: Config | D: Dashboard | Q: Salir"
        else:
            help_text = "F: Salir del juego | D: Dashboard | Q: Salir"
        
        frame_width = frame.shape[1]
        text_size = cv2.getTextSize(help_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.putText(frame, help_text, (frame_width - text_size[0] - 10, 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
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
                     (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        cv2.rectangle(frame,
                     (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     (0, 255, 0), 3)
        
        cv2.putText(frame, "STATUS", (panel_x + 15, panel_y + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        y_offset = panel_y + 70
        line_height = 35
        font_scale = 0.7
        
        fps_color = (0, 255, 0) if (fps1 + fps2) / 2 > 20 else (0, 165, 255) if (fps1 + fps2) / 2 > 15 else (0, 0, 255)
        fps_text = f"FPS: {fps1}/{fps2} (Prom: {(fps1+fps2)//2})"
        cv2.putText(frame, fps_text, (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, fps_color, 2)
        y_offset += line_height
        
        cv2.putText(frame, f"CPS: {cps}", (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)
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
                             (key_x + key_w, keyboard_y1), (0, 255, 0), -1)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        return frame
    
    def draw_fps_indicator(self, frame, fps, position=(20, 40)):
        """Dibuja indicador de FPS grande y visible"""
        fps_color = (0, 255, 0) if fps >= 25 else (0, 165, 255) if fps >= 20 else (0, 0, 255)
        
        text = f"FPS: {fps}"
        font_scale = 1.0
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        
        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (position[0] - 10, position[1] - text_height - 10),
                     (position[0] + text_width + 10, position[1] + 10),
                     (0, 0, 0), -1)
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
        """Dibuja menú de configuración inicial (MÁS GRANDE)"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        title = "CONFIGURACION INICIAL"
        font_scale_title = 2.5
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, font_scale_title, 4)
        title_x = (frame_width - title_w) // 2
        cv2.putText(frame, title, (title_x, 100), cv2.FONT_HERSHEY_SIMPLEX, font_scale_title, (0, 200, 255), 4)
        
        y_start = 220
        line_height = 90
        
        options = [
            ("1", "USAR CALIBRACION GUARDADA", (0, 255, 0)),
            ("2", "NUEVA CALIBRACION", (255, 200, 0)),
            ("3", "SALTAR (usar por defecto)", (255, 100, 100))
        ]
        
        for i, (key, text, color) in enumerate(options):
            y = y_start + i * line_height
            opt_bg = frame.copy()
            cv2.rectangle(opt_bg, (80, y - 35), (frame_width - 80, y + 45), (30, 30, 50), -1)
            cv2.rectangle(opt_bg, (80, y - 35), (frame_width - 80, y + 45), color, 4)
            frame = cv2.addWeighted(frame, 0.7, opt_bg, 0.3, 0)
            cv2.rectangle(frame, (100, y - 30), (170, y + 30), color, -1)
            cv2.putText(frame, key, (115, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
            cv2.putText(frame, text, (200, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        
        instruction = "Presiona 1, 2 o 3"
        (instr_w, instr_h), _ = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
        instr_x = (frame_width - instr_w) // 2
        cv2.putText(frame, instruction, (instr_x, frame_height - 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 255, 100), 2)
        
        return frame
    
    def draw_calibration_progress(self, frame, message, progress_percent=0):
        """Dibuja pantalla de progreso de calibración (MÁS GRANDE)"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        title = "CALIBRANDO..."
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 2.2, 4)
        title_x = (frame_width - title_w) // 2
        cv2.putText(frame, title, (title_x, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 200, 255), 4)
        
        (msg_w, msg_h), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        msg_x = (frame_width - msg_w) // 2
        cv2.putText(frame, message, (msg_x, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 100), 3)
        
        bar_x = 150
        bar_y = 400
        bar_w = frame_width - 300
        bar_h = 60
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (0, 200, 255), 3)
        
        filled_w = int(bar_w * progress_percent / 100)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h), (0, 200, 255), -1)
        
        pct_text = f"{progress_percent}%"
        (pct_w, pct_h), _ = cv2.getTextSize(pct_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
        pct_x = (frame_width - pct_w) // 2
        cv2.putText(frame, pct_text, (pct_x, bar_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        return frame
    
    def draw_input_dialog(self, frame, prompt, current_value=""):
        """Dibuja diálogo de entrada (MÁS GRANDE)"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        panel_w = 700
        panel_h = 300
        panel_x = (frame_width - panel_w) // 2
        panel_y = (frame_height - panel_h) // 2
        
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 200, 255), 4)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        (prompt_w, prompt_h), _ = cv2.getTextSize(prompt, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        prompt_x = panel_x + (panel_w - prompt_w) // 2
        cv2.putText(frame, prompt, (prompt_x, panel_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 100), 3)
        
        input_box_x = panel_x + 50
        input_box_y = panel_y + 110
        input_box_w = panel_w - 100
        input_box_h = 60
        
        cv2.rectangle(frame, (input_box_x, input_box_y), (input_box_x + input_box_w, input_box_y + input_box_h), 
                     (255, 255, 255), 3)
        
        display_text = str(current_value) + "|"
        cv2.putText(frame, display_text, (input_box_x + 20, input_box_y + 45), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        
        instr = "Escribe y presiona ENTER"
        (instr_w, instr_h), _ = cv2.getTextSize(instr, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        instr_x = panel_x + (panel_w - instr_w) // 2
        cv2.putText(frame, instr, (instr_x, panel_y + 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 200, 100), 2)
        
        return frame
    
    def draw_song_selector(self, frame, songs, selected_index=0):
        """Dibuja menú para seleccionar canción (MÁS GRANDE)"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        title = "SELECCIONA UNA CANCION"
        title_font_scale = 2.2
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 
                                                  title_font_scale, 4)
        title_x = (frame_width - title_w) // 2
        cv2.putText(frame, title, (title_x, 80), cv2.FONT_HERSHEY_SIMPLEX, 
                   title_font_scale, (0, 200, 255), 4)
        
        panel_height = min(frame_height - 200, len(songs) * 90 + 60)
        panel_y = (frame_height - panel_height) // 2
        panel_x = (frame_width - 600) // 2
        panel_w = 600
        
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_height), 
                     (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_height), 
                     (100, 200, 255), 3)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        y_offset = panel_y + 40
        for i, song in enumerate(songs):
            is_selected = i == selected_index
            
            if is_selected:
                option_bg = frame.copy()
                cv2.rectangle(option_bg, (panel_x + 20, y_offset - 20),
                            (panel_x + panel_w - 20, y_offset + 50),
                            (100, 200, 255), -1)
                frame = cv2.addWeighted(frame, 0.7, option_bg, 0.3, 0)
                text_color = (0, 255, 0)
                prefix = "►"
            else:
                text_color = (200, 200, 200)
                prefix = " "
            
            song_text = f"{prefix} [{i+1}] {song.title} ({song.difficulty})"
            cv2.putText(frame, song_text, (panel_x + 40, y_offset + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2)
            
            bpm_text = f"BPM: {song.bpm}"
            cv2.putText(frame, bpm_text, (panel_x + 400, y_offset + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 255), 2)
            
            y_offset += 90
        
        instructions = [
            "USA NUMEROS 1-{} PARA SELECCIONAR".format(len(songs)),
            "PRESIONA ENTER PARA CONFIRMAR",
            "PRESIONA Q PARA CANCELAR"
        ]
        
        y_instr = panel_y + panel_height + 40
        for instr in instructions:
            (instr_w, _), _ = cv2.getTextSize(instr, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            instr_x = (frame_width - instr_w) // 2
            cv2.putText(frame, instr, (instr_x, y_instr),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 100), 2)
            y_instr += 35
        
        return frame
    
    def draw_game_results(self, frame, stats):
        """Dibuja resultados finales (MÁS GRANDE)"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (10, 10, 20), -1)
        frame = cv2.addWeighted(frame, 0.1, overlay, 0.9, 0)
        
        panel_width = 800
        panel_height = 650
        panel_x = (frame_width - panel_width) // 2
        panel_y = (frame_height - panel_height) // 2
        
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (0, 200, 255), 5)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        title = "RESULTADOS FINALES"
        title_font_scale = 2.5
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 
                                                  title_font_scale, 4)
        title_x = panel_x + (panel_width - title_w) // 2
        cv2.putText(frame, title, (title_x, panel_y + 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 200, 255), 4)
        
        y_offset = panel_y + 160
        line_height = 65
        font_scale = 1.3
        font_thickness = 3
        
        score_text = f"PUNTAJE: {stats['score']:,}"
        (text_w, _), _ = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale, font_thickness)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, score_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 215, 0), font_thickness)
        y_offset += line_height
        
        combo_text = f"COMBO MAXIMO: {stats['combo']}x"
        (text_w, _), _ = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale, font_thickness)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, combo_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 100, 255), font_thickness)
        y_offset += line_height + 30
        
        cv2.line(frame, (panel_x + 50, y_offset), (panel_x + panel_width - 50, y_offset),
                (100, 100, 150), 3)
        y_offset += line_height
        
        perfect_text = f"PERFECT: {stats['perfect']}"
        cv2.putText(frame, perfect_text, (panel_x + 100, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 100), font_thickness)
        y_offset += line_height
        
        good_text = f"GOOD: {stats['good']}"
        cv2.putText(frame, good_text, (panel_x + 100, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 0), font_thickness)
        y_offset += line_height
        
        miss_text = f"MISS: {stats['miss']}"
        cv2.putText(frame, miss_text, (panel_x + 100, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 50, 50), font_thickness)
        y_offset += line_height + 30
        
        cv2.line(frame, (panel_x + 50, y_offset), (panel_x + panel_width - 50, y_offset),
                (100, 100, 150), 3)
        y_offset += line_height
        
        total_text = f"TOTAL DE NOTAS: {stats['total_notes']}"
        (text_w, _), _ = cv2.getTextSize(total_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale, font_thickness)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, total_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness)
        y_offset += line_height
        
        accuracy = stats['accuracy']
        if accuracy >= 90:
            acc_color = (0, 255, 100)
        elif accuracy >= 70:
            acc_color = (255, 255, 0)
        else:
            acc_color = (255, 100, 100)
        
        accuracy_text = f"PRECISION: {accuracy:.1f}%"
        (text_w, _), _ = cv2.getTextSize(accuracy_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale + 0.3, font_thickness + 1)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, accuracy_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale + 0.3, acc_color, font_thickness + 1)
        
        instruction = "Presiona cualquier tecla para continuar"
        (instr_w, instr_h), _ = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 
                                                 1.0, 2)
        instr_x = panel_x + (panel_width - instr_w) // 2
        cv2.putText(frame, instruction, (instr_x, panel_y + panel_height - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 200, 255), 2)
        
        return frame
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
        """Dibuja pantalla de bienvenida moderna con diseño mejorado"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo con gradiente oscuro elegante
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # ========== TÍTULO PRINCIPAL ==========
        title = "PIANO VIRTUAL"
        title_font_scale = 2.2
        title_thickness = 4
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 
                                                  title_font_scale, title_thickness)
        title_x = (frame_width - title_w) // 2
        title_y = 100
        
        # Sombra del título
        cv2.putText(frame, title, (title_x + 3, title_y + 3),
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 0, 0), title_thickness)
        # Título principal con gradiente de colores (amarillo a naranja)
        cv2.putText(frame, title, (title_x, title_y),
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 200, 255), title_thickness)
        
        # Subtitle - Mensaje de inicio
        subtitle = "Presione cualquier tecla"
        (sub_w, sub_h), _ = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        sub_x = (frame_width - sub_w) // 2
        
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
        cv2.rectangle(blink_bg, (sub_x - 15, title_y + 50 - sub_h - 10), 
                     (sub_x + sub_w + 15, title_y + 50 + 10), (0, 255, 255), -1)
        frame = cv2.addWeighted(frame, 1 - blink_alpha, blink_bg, blink_alpha, 0)
        
        # Redibujar el texto del subtítulo sobre el fondo parpadeante
        cv2.putText(frame, subtitle, (sub_x, title_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
        cv2.putText(frame, subtitle, (sub_x, title_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 255), 2)
        
        return frame
    
    def draw_instructions_bar(self, frame, game_mode):
        """Dibuja barra de instrucciones en la parte superior"""
        bar_height = 40
        frame_height = frame.shape[0]
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
        """Dibuja dashboard mejorado con mejor diseño"""
        # Panel semi-transparente
        panel_width = 280
        panel_height = 200
        panel_x = 10
        panel_y = self.height - panel_height - 10
        
        overlay = frame.copy()
        cv2.rectangle(overlay, 
                     (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height),
                     (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # Borde del panel
        cv2.rectangle(frame,
                     (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     (0, 255, 0), 2)
        
        # Título
        cv2.putText(frame, "STATUS", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Información
        y_offset = panel_y + 50
        line_height = 25
        
        # FPS con indicador de color
        fps_color = (0, 255, 0) if (fps1 + fps2) / 2 > 20 else (0, 165, 255) if (fps1 + fps2) / 2 > 15 else (0, 0, 255)
        fps_text = f"FPS: {fps1}/{fps2} (Prom: {(fps1+fps2)//2})"
        cv2.putText(frame, fps_text, (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, fps_color, 1)
        y_offset += line_height
        
        cv2.putText(frame, f"CPS: {cps}", (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += line_height
        
        cv2.putText(frame, f"Posicion: X:{X:.1f} Y:{Y:.1f}", 
                   (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += line_height
        
        cv2.putText(frame, f"Distancia: {D:.1f}cm (Ajuste: {Dr:.1f}cm)",
                   (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def draw_key_indicators(self, frame, active_keys, keyboard_x0, keyboard_y0, keyboard_x1, keyboard_y1):
        """Dibuja indicadores visuales de teclas presionadas"""
        if len(active_keys) == 0:
            return frame
        
        keyboard_width = keyboard_x1 - keyboard_x0
        key_width = keyboard_width / 8  # 8 teclas blancas
        
        for key_num in active_keys:
            if 0 <= key_num < 13:
                # Calcular posición de la tecla (simplificado - necesita mapeo correcto)
                key_x = int(keyboard_x0 + (key_num % 8) * key_width)
                key_w = int(key_width)
                
                # Dibujar highlight verde cuando está activa
                overlay = frame.copy()
                cv2.rectangle(overlay, (key_x, keyboard_y0), 
                             (key_x + key_w, keyboard_y1), (0, 255, 0), -1)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        return frame
    
    def draw_fps_indicator(self, frame, fps, position=(10, 30)):
        """Dibuja indicador de FPS grande y visible"""
        fps_color = (0, 255, 0) if fps >= 25 else (0, 165, 255) if fps >= 20 else (0, 0, 255)
        
        # Fondo para el texto
        text = f"FPS: {fps}"
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        
        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (position[0] - 5, position[1] - text_height - 5),
                     (position[0] + text_width + 5, position[1] + 5),
                     (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        cv2.putText(frame, text, position,
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, fps_color, 2)
        
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
        """Dibuja menú de configuración inicial (calibración)"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo oscuro
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # TÍTULO
        title = "CONFIGURACION INICIAL"
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 3)
        title_x = (frame_width - title_w) // 2
        cv2.putText(frame, title, (title_x, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 200, 255), 3)
        
        # OPCIONES
        y_start = 160
        line_height = 70
        
        options = [
            ("1", "USAR CALIBRACION GUARDADA", (0, 255, 0)),
            ("2", "NUEVA CALIBRACION", (255, 200, 0)),
            ("3", "SALTAR (usar por defecto)", (255, 100, 100))
        ]
        
        for i, (key, text, color) in enumerate(options):
            y = y_start + i * line_height
            
            # Fondo de opción
            opt_bg = frame.copy()
            cv2.rectangle(opt_bg, (50, y - 25), (frame_width - 50, y + 35), (30, 30, 50), -1)
            cv2.rectangle(opt_bg, (50, y - 25), (frame_width - 50, y + 35), color, 3)
            frame = cv2.addWeighted(frame, 0.7, opt_bg, 0.3, 0)
            
            # Botón de tecla
            cv2.rectangle(frame, (70, y - 20), (130, y + 20), color, -1)
            cv2.putText(frame, key, (85, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
            
            # Texto de opción
            cv2.putText(frame, text, (150, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # INSTRUCCIÓN AL FINAL
        instruction = "Presiona 1, 2 o 3"
        (instr_w, instr_h), _ = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        instr_x = (frame_width - instr_w) // 2
        cv2.putText(frame, instruction, (instr_x, frame_height - 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 100), 2)
        
        return frame
    
    def draw_calibration_progress(self, frame, message, progress_percent=0):
        """Dibuja pantalla de progreso de calibración"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo oscuro
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # TÍTULO
        title = "CALIBRANDO..."
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 3)
        title_x = (frame_width - title_w) // 2
        cv2.putText(frame, title, (title_x, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 200, 255), 3)
        
        # MENSAJE
        (msg_w, msg_h), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        msg_x = (frame_width - msg_w) // 2
        cv2.putText(frame, message, (msg_x, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 100), 2)
        
        # BARRA DE PROGRESO
        bar_x = 100
        bar_y = 350
        bar_w = frame_width - 200
        bar_h = 40
        
        # Fondo de barra
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (0, 200, 255), 2)
        
        # Relleno de progreso
        filled_w = int(bar_w * progress_percent / 100)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h), (0, 200, 255), -1)
        
        # Porcentaje
        pct_text = f"{progress_percent}%"
        (pct_w, pct_h), _ = cv2.getTextSize(pct_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        pct_x = (frame_width - pct_w) // 2
        cv2.putText(frame, pct_text, (pct_x, bar_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def draw_input_dialog(self, frame, prompt, current_value=""):
        """Dibuja diálogo de entrada en la interfaz"""
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo oscuro
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # PANEL CENTRAL
        panel_w = 500
        panel_h = 200
        panel_x = (frame_width - panel_w) // 2
        panel_y = (frame_height - panel_h) // 2
        
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 200, 255), 3)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        # PROMPT
        (prompt_w, prompt_h), _ = cv2.getTextSize(prompt, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        prompt_x = panel_x + (panel_w - prompt_w) // 2
        cv2.putText(frame, prompt, (prompt_x, panel_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 100), 2)
        
        # INPUT BOX
        input_box_x = panel_x + 30
        input_box_y = panel_y + 80
        input_box_w = panel_w - 60
        input_box_h = 40
        
        cv2.rectangle(frame, (input_box_x, input_box_y), (input_box_x + input_box_w, input_box_y + input_box_h), 
                     (255, 255, 255), 2)
        
        # VALOR INGRESADO + CURSOR
        display_text = str(current_value) + "|"
        cv2.putText(frame, display_text, (input_box_x + 10, input_box_y + 28), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # INSTRUCCIONES
        instr = "Escribe y presiona ENTER"
        (instr_w, instr_h), _ = cv2.getTextSize(instr, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        instr_x = panel_x + (panel_w - instr_w) // 2
        cv2.putText(frame, instr, (instr_x, panel_y + 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 100), 1)
        
        return frame
    
    def draw_song_selector(self, frame, songs, selected_index=0):
        """
        Dibuja menú para seleccionar canción
        songs: lista de objetos Song
        selected_index: índice de la canción seleccionada
        """
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo oscuro
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # Título
        title = "SELECCIONA UNA CANCION"
        title_font_scale = 1.8
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 
                                                  title_font_scale, 3)
        title_x = (frame_width - title_w) // 2
        cv2.putText(frame, title, (title_x, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                   title_font_scale, (0, 200, 255), 3)
        
        # Panel de canciones
        panel_height = min(frame_height - 150, len(songs) * 70 + 40)
        panel_y = (frame_height - panel_height) // 2
        panel_x = (frame_width - 400) // 2
        panel_w = 400
        
        # Fondo del panel
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_height), 
                     (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_height), 
                     (100, 200, 255), 2)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        # Lista de canciones
        y_offset = panel_y + 30
        for i, song in enumerate(songs):
            is_selected = i == selected_index
            
            # Fondo de opción seleccionada
            if is_selected:
                option_bg = frame.copy()
                cv2.rectangle(option_bg, (panel_x + 15, y_offset - 15),
                            (panel_x + panel_w - 15, y_offset + 40),
                            (100, 200, 255), -1)
                frame = cv2.addWeighted(frame, 0.7, option_bg, 0.3, 0)
                color = (0, 255, 0)
                text_color = (0, 255, 0)
                prefix = "►"
            else:
                color = (200, 200, 200)
                text_color = (200, 200, 200)
                prefix = " "
            
            # Número y nombre de canción
            song_text = f"{prefix} [{i+1}] {song.title} ({song.difficulty})"
            cv2.putText(frame, song_text, (panel_x + 30, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
            
            # BPM
            bpm_text = f"BPM: {song.bpm}"
            cv2.putText(frame, bpm_text, (panel_x + 250, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 255), 1)
            
            y_offset += 70
        
        # Instrucciones
        instructions = [
            "USA NUMEROS 1-{} PARA SELECCIONAR".format(len(songs)),
            "PRESIONA ENTER PARA CONFIRMAR",
            "PRESIONA Q PARA CANCELAR"
        ]
        
        y_instr = panel_y + panel_height + 30
        for instr in instructions:
            (instr_w, _), _ = cv2.getTextSize(instr, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            instr_x = (frame_width - instr_w) // 2
            cv2.putText(frame, instr, (instr_x, y_instr),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 100), 1)
            y_instr += 25
        
        return frame
    
    def draw_game_results(self, frame, stats):
        """
        Dibuja pantalla de resultados finales del juego
        stats: diccionario con estadísticas del juego
        """
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Fondo oscuro con overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), (10, 10, 20), -1)
        frame = cv2.addWeighted(frame, 0.1, overlay, 0.9, 0)
        
        # Panel principal
        panel_width = 600
        panel_height = 500
        panel_x = (frame_width - panel_width) // 2
        panel_y = (frame_height - panel_height) // 2
        
        # Fondo del panel
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (0, 200, 255), 4)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        # TÍTULO
        title = "RESULTADOS FINALES"
        title_font_scale = 1.8
        (title_w, title_h), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 
                                                  title_font_scale, 3)
        title_x = panel_x + (panel_width - title_w) // 2
        cv2.putText(frame, title, (title_x, panel_y + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, title_font_scale, (0, 200, 255), 3)
        
        # Estadísticas
        y_offset = panel_y + 120
        line_height = 50
        font_scale = 1.0
        font_thickness = 2
        
        # Score
        score_text = f"PUNTAJE: {stats['score']:,}"
        (text_w, _), _ = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale, font_thickness)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, score_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 215, 0), font_thickness)
        y_offset += line_height
        
        # Combo máximo
        combo_text = f"COMBO MAXIMO: {stats['combo']}x"
        (text_w, _), _ = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale, font_thickness)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, combo_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 100, 255), font_thickness)
        y_offset += line_height + 20
        
        # Línea separadora
        cv2.line(frame, (panel_x + 50, y_offset), (panel_x + panel_width - 50, y_offset),
                (100, 100, 150), 2)
        y_offset += line_height
        
        # Perfect
        perfect_text = f"PERFECT: {stats['perfect']}"
        cv2.putText(frame, perfect_text, (panel_x + 80, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 100), font_thickness)
        y_offset += line_height
        
        # Good
        good_text = f"GOOD: {stats['good']}"
        cv2.putText(frame, good_text, (panel_x + 80, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 0), font_thickness)
        y_offset += line_height
        
        # Miss
        miss_text = f"MISS: {stats['miss']}"
        cv2.putText(frame, miss_text, (panel_x + 80, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 50, 50), font_thickness)
        y_offset += line_height + 20
        
        # Línea separadora
        cv2.line(frame, (panel_x + 50, y_offset), (panel_x + panel_width - 50, y_offset),
                (100, 100, 150), 2)
        y_offset += line_height
        
        # Total y precisión
        total_text = f"TOTAL DE NOTAS: {stats['total_notes']}"
        (text_w, _), _ = cv2.getTextSize(total_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale, font_thickness)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, total_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness)
        y_offset += line_height
        
        # Precisión con color según el porcentaje
        accuracy = stats['accuracy']
        if accuracy >= 90:
            acc_color = (0, 255, 100)  # Verde
        elif accuracy >= 70:
            acc_color = (255, 255, 0)  # Amarillo
        else:
            acc_color = (255, 100, 100)  # Rojo
        
        accuracy_text = f"PRECISION: {accuracy:.1f}%"
        (text_w, _), _ = cv2.getTextSize(accuracy_text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_scale + 0.2, font_thickness + 1)
        text_x = panel_x + (panel_width - text_w) // 2
        cv2.putText(frame, accuracy_text, (text_x, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale + 0.2, acc_color, font_thickness + 1)
        
        # Instrucción
        instruction = "Presiona cualquier tecla para continuar"
        (instr_w, instr_h), _ = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 
                                                 0.7, 2)
        instr_x = panel_x + (panel_width - instr_w) // 2
        cv2.putText(frame, instruction, (instr_x, panel_y + panel_height - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 200, 255), 2)
        
        return frame


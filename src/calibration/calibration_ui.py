#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaz de Usuario para el Proceso de Calibración
Pantallas visuales para guiar al usuario paso a paso
"""

import cv2
import numpy as np
from .calibration_config import CalibrationConfig


class CalibrationUI:
    """Maneja todas las pantallas visuales del proceso de calibración"""
    
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        
    def draw_input_screen(self, frame, prompt, current_value="", error_msg=""):
        """
        Dibuja pantalla de entrada de parámetros
        
        Args:
            frame: Frame base
            prompt: Texto del prompt
            current_value: Valor actual ingresado
            error_msg: Mensaje de error (opcional)
        """
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (15, 15, 30), -1)
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        
        # Panel central
        panel_w = 700
        panel_h = 300
        panel_x = (self.width - panel_w) // 2
        panel_y = (self.height - panel_h) // 2
        
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_h), 
                     (30, 30, 50), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y), 
                     (panel_x + panel_w, panel_y + panel_h), 
                     CalibrationConfig.COLOR_TITLE, 3)
        frame = cv2.addWeighted(frame, 0.6, panel_bg, 0.4, 0)
        
        # Título
        title = "CONFIGURACION DEL TABLERO"
        (title_w, title_h), _ = cv2.getTextSize(
            title, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2
        )
        title_x = panel_x + (panel_w - title_w) // 2
        cv2.putText(frame, title, (title_x, panel_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, CalibrationConfig.COLOR_TITLE, 2)
        
        # Prompt
        (prompt_w, prompt_h), _ = cv2.getTextSize(
            prompt, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2
        )
        prompt_x = panel_x + (panel_w - prompt_w) // 2
        cv2.putText(frame, prompt, (prompt_x, panel_y + 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, CalibrationConfig.COLOR_INFO, 2)
        
        # Input box
        input_box_x = panel_x + 50
        input_box_y = panel_y + 140
        input_box_w = panel_w - 100
        input_box_h = 50
        
        cv2.rectangle(frame, (input_box_x, input_box_y),
                     (input_box_x + input_box_w, input_box_y + input_box_h),
                     (255, 255, 255), 2)
        
        # Valor ingresado con cursor
        display_text = str(current_value) + "|"
        cv2.putText(frame, display_text, (input_box_x + 15, input_box_y + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # Mensaje de error
        if error_msg:
            cv2.putText(frame, error_msg, (panel_x + 50, panel_y + 215),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, CalibrationConfig.COLOR_ERROR, 2)
        
        # Instrucciones
        instr = "Escribe el valor y presiona ENTER | ESC para cancelar"
        (instr_w, _), _ = cv2.getTextSize(instr, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        instr_x = panel_x + (panel_w - instr_w) // 2
        cv2.putText(frame, instr, (instr_x, panel_y + 260),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, CalibrationConfig.COLOR_SUCCESS, 1)
        
        return frame
    
    def draw_capture_screen(self, frame, camera_name, photo_index, total_photos, 
                           detected, instruction):
        """
        Dibuja pantalla de captura de imágenes con instrucciones contextuales
        
        Args:
            frame: Frame de la cámara con overlay de detección
            camera_name: Nombre de la cámara ('Izquierda' o 'Derecha')
            photo_index: Índice de la foto actual (0-based)
            total_photos: Total de fotos a capturar
            detected: Si el tablero está detectado
            instruction: Instrucción específica para esta foto
        """
        frame_display = frame.copy()
        
        # Obtener categoría e instrucción
        cat_title, specific_instr, objetivo = CalibrationConfig.get_instruction_for_photo(photo_index)
        
        # ========== PANEL SUPERIOR: INFO DE CÁMARA Y PROGRESO ==========
        top_panel_h = 120
        overlay_top = frame_display.copy()
        cv2.rectangle(overlay_top, (0, 0), (self.width, top_panel_h), (20, 20, 20), -1)
        frame_display = cv2.addWeighted(frame_display, 0.7, overlay_top, 0.3, 0)
        
        # Título
        title = f"CALIBRACION - CAMARA {camera_name.upper()}"
        cv2.putText(frame_display, title, (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, CalibrationConfig.COLOR_TITLE, 2)
        
        # Contador de fotos
        counter_text = f"Foto {photo_index + 1} / {total_photos}"
        cv2.putText(frame_display, counter_text, (self.width - 250, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, CalibrationConfig.COLOR_INFO, 2)
        
        # Barra de progreso
        progress_bar_x = 20
        progress_bar_y = 60
        progress_bar_w = self.width - 40
        progress_bar_h = 25
        
        cv2.rectangle(frame_display, (progress_bar_x, progress_bar_y),
                     (progress_bar_x + progress_bar_w, progress_bar_y + progress_bar_h),
                     (50, 50, 50), -1)
        
        progress_fill = int((photo_index / total_photos) * progress_bar_w)
        cv2.rectangle(frame_display, (progress_bar_x, progress_bar_y),
                     (progress_bar_x + progress_fill, progress_bar_y + progress_bar_h),
                     CalibrationConfig.COLOR_SUCCESS, -1)
        
        cv2.rectangle(frame_display, (progress_bar_x, progress_bar_y),
                     (progress_bar_x + progress_bar_w, progress_bar_y + progress_bar_h),
                     (100, 100, 100), 2)
        
        # Porcentaje
        percent = int((photo_index / total_photos) * 100)
        cv2.putText(frame_display, f"{percent}%", (progress_bar_x + progress_bar_w // 2 - 30, progress_bar_y + 19),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # ========== PANEL IZQUIERDO: INSTRUCCIONES ==========
        left_panel_x = 10
        left_panel_y = top_panel_h + 20
        left_panel_w = 450
        left_panel_h = self.height - top_panel_h - 140
        
        overlay_left = frame_display.copy()
        cv2.rectangle(overlay_left, (left_panel_x, left_panel_y),
                     (left_panel_x + left_panel_w, left_panel_y + left_panel_h),
                     (25, 25, 40), -1)
        frame_display = cv2.addWeighted(frame_display, 0.7, overlay_left, 0.3, 0)
        
        cv2.rectangle(frame_display, (left_panel_x, left_panel_y),
                     (left_panel_x + left_panel_w, left_panel_y + left_panel_h),
                     CalibrationConfig.COLOR_INFO, 2)
        
        # Categoría actual
        cv2.putText(frame_display, cat_title, (left_panel_x + 15, left_panel_y + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, CalibrationConfig.COLOR_WARNING, 2)
        
        # Línea separadora
        cv2.line(frame_display, (left_panel_x + 10, left_panel_y + 45),
                (left_panel_x + left_panel_w - 10, left_panel_y + 45),
                CalibrationConfig.COLOR_INFO, 1)
        
        # Instrucción específica
        y_offset = left_panel_y + 75
        lines = self._wrap_text(specific_instr, 40)
        for line in lines:
            cv2.putText(frame_display, line, (left_panel_x + 15, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            y_offset += 30
        
        # Objetivo
        y_offset += 20
        cv2.putText(frame_display, "Objetivo:", (left_panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, CalibrationConfig.COLOR_SUCCESS, 1)
        y_offset += 25
        
        obj_lines = self._wrap_text(objetivo, 40)
        for line in obj_lines:
            cv2.putText(frame_display, line, (left_panel_x + 15, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
            y_offset += 22
        
        # ========== ESTADO DE DETECCIÓN ==========
        status_y = self.height - 120
        if detected:
            status_text = "✓ TABLERO DETECTADO"
            status_color = CalibrationConfig.COLOR_SUCCESS
            action_text = "Presiona ESPACIO para capturar"
        else:
            status_text = "✗ BUSCANDO TABLERO..."
            status_color = CalibrationConfig.COLOR_ERROR
            action_text = "Ajusta el tablero segun la instruccion"
        
        # Fondo para estado
        status_bg = frame_display.copy()
        cv2.rectangle(status_bg, (0, status_y - 15), (self.width, self.height),
                     (20, 20, 20), -1)
        frame_display = cv2.addWeighted(frame_display, 0.7, status_bg, 0.3, 0)
        
        # Texto de estado
        (status_w, _), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        status_x = (self.width - status_w) // 2
        cv2.putText(frame_display, status_text, (status_x, status_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)
        
        # Acción
        (action_w, _), _ = cv2.getTextSize(action_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        action_x = (self.width - action_w) // 2
        cv2.putText(frame_display, action_text, (action_x, status_y + 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Tips de debug (si no detecta)
        if not detected:
            tips = "Tips: Mejor luz | Tablero completo | Enfoque claro | Prueba mas cerca/lejos"
            (tips_w, _), _ = cv2.getTextSize(tips, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            tips_x = (self.width - tips_w) // 2
            cv2.putText(frame_display, tips, (tips_x, status_y + 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 150, 255), 1)
        
        # Controles
        controls = "ESC: Cancelar | Q: Salir"
        cv2.putText(frame_display, controls, (20, self.height - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        return frame_display
    
    def draw_summary_screen(self, frame, camera_name, total_captured, 
                           reprojection_error=None):
        """
        Dibuja pantalla de resumen después de capturar todas las fotos
        
        Args:
            frame: Frame base
            camera_name: Nombre de la cámara
            total_captured: Total de fotos capturadas
            reprojection_error: Error de reproyección (opcional)
        """
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (10, 15, 20), -1)
        frame = cv2.addWeighted(frame, 0.1, overlay, 0.9, 0)
        
        # Panel central
        panel_w = 700
        panel_h = 400
        panel_x = (self.width - panel_w) // 2
        panel_y = (self.height - panel_h) // 2
        
        panel_bg = frame.copy()
        cv2.rectangle(panel_bg, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h),
                     (30, 35, 45), -1)
        cv2.rectangle(panel_bg, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h),
                     CalibrationConfig.COLOR_SUCCESS, 4)
        frame = cv2.addWeighted(frame, 0.5, panel_bg, 0.5, 0)
        
        # Título
        title = f"CALIBRACION {camera_name.upper()} COMPLETADA"
        (title_w, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        title_x = panel_x + (panel_w - title_w) // 2
        cv2.putText(frame, title, (title_x, panel_y + 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, CalibrationConfig.COLOR_SUCCESS, 2)
        
        # Checkmark
        check_y = panel_y + 100
        cv2.circle(frame, (self.width // 2, check_y + 40), 50, CalibrationConfig.COLOR_SUCCESS, 5)
        cv2.line(frame, (self.width // 2 - 25, check_y + 40),
                (self.width // 2 - 5, check_y + 60), CalibrationConfig.COLOR_SUCCESS, 6)
        cv2.line(frame, (self.width // 2 - 5, check_y + 60),
                (self.width // 2 + 30, check_y + 20), CalibrationConfig.COLOR_SUCCESS, 6)
        
        # Información
        info_y = panel_y + 220
        info_text = f"Imagenes capturadas: {total_captured}"
        (info_w, _), _ = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        info_x = panel_x + (panel_w - info_w) // 2
        cv2.putText(frame, info_text, (info_x, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        if reprojection_error is not None:
            error_text = f"Error de reproyeccion: {reprojection_error:.4f} px"
            error_color = (CalibrationConfig.COLOR_SUCCESS if reprojection_error < 0.5 
                          else CalibrationConfig.COLOR_WARNING)
            (error_w, _), _ = cv2.getTextSize(error_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            error_x = panel_x + (panel_w - error_w) // 2
            cv2.putText(frame, error_text, (error_x, info_y + 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, error_color, 2)
        
        # Instrucción
        instr = "Presiona cualquier tecla para continuar"
        (instr_w, _), _ = cv2.getTextSize(instr, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        instr_x = panel_x + (panel_w - instr_w) // 2
        cv2.putText(frame, instr, (instr_x, panel_y + 350),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, CalibrationConfig.COLOR_INFO, 2)
        
        return frame
    
    def _wrap_text(self, text, max_chars):
        """Divide texto largo en múltiples líneas"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.strip())
        
        return lines

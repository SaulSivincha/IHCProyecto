#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI para el módulo de teoría musical
Menú de selección de lecciones y navegación
"""

import cv2
import numpy as np


class TheoryUI:
    """Interfaz de usuario para el modo teoría"""
    
    def __init__(self, frame_width, frame_height):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.selected_index = 0
        self.scroll_offset = 0
        self.max_visible = 8  # Lecciones visibles a la vez
    
    def draw_lesson_menu(self, frame, lessons):
        """
        Dibuja menú de selección de lecciones
        
        Args:
            frame: Frame donde dibujar
            lessons: Lista de tuplas (id, lesson_instance)
        
        Returns:
            frame modificado
        """
        h, w = frame.shape[:2]
        
        # Fondo
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        overlay[:] = (30, 30, 30)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        # Título
        title = "MODO TEORIA - Selecciona una leccion"
        cv2.putText(frame, title, (w//2 - 300, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Línea divisoria
        cv2.line(frame, (50, 80), (w - 50, 80), (100, 100, 100), 2)
        
        # Instrucciones
        instructions = [
            "W/S o Flechas: Navegar",
            "1-9 o ENTER: Seleccionar",
            "Q: Volver al modo libre"
        ]
        for i, inst in enumerate(instructions):
            cv2.putText(frame, inst, (w - 380, h - 80 + i*25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Lista de lecciones
        y_start = 120
        item_height = 50
        
        # Calcular rango visible
        start_idx = self.scroll_offset
        end_idx = min(start_idx + self.max_visible, len(lessons))
        
        for i in range(start_idx, end_idx):
            lesson_id, lesson = lessons[i]
            y = y_start + (i - start_idx) * item_height
            
            # Highlight para lección seleccionada
            if i == self.selected_index:
                cv2.rectangle(frame, (60, y - 5), (w - 60, y + 40), (80, 120, 200), -1)
                cv2.rectangle(frame, (60, y - 5), (w - 60, y + 40), (120, 160, 255), 2)
            else:
                cv2.rectangle(frame, (60, y - 5), (w - 60, y + 40), (50, 50, 50), 1)
            
            # Número
            num_text = f"{i + 1}."
            cv2.putText(frame, num_text, (80, y + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Nombre
            cv2.putText(frame, lesson.name, (130, y + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Dificultad
            difficulty_colors = {
                'Básico': (100, 255, 100),
                'Intermedio': (255, 200, 100),
                'Avanzado': (255, 100, 100)
            }
            color = difficulty_colors.get(lesson.difficulty, (200, 200, 200))
            cv2.putText(frame, f"[{lesson.difficulty}]", (w - 200, y + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        
        # Indicadores de scroll
        if start_idx > 0:
            cv2.putText(frame, "▲ Mas arriba", (w//2 - 60, y_start - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
        
        if end_idx < len(lessons):
            cv2.putText(frame, "▼ Mas abajo", (w//2 - 60, y_start + self.max_visible * item_height + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
        
        # Descripción de lección seleccionada
        if 0 <= self.selected_index < len(lessons):
            _, selected_lesson = lessons[self.selected_index]
            desc_y = h - 150
            cv2.rectangle(frame, (60, desc_y), (w - 60, h - 100), (40, 40, 40), -1)
            cv2.rectangle(frame, (60, desc_y), (w - 60, h - 100), (100, 100, 100), 1)
            
            cv2.putText(frame, "Descripcion:", (80, desc_y + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
            cv2.putText(frame, selected_lesson.description, (80, desc_y + 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        return frame
    
    def navigate_up(self, num_lessons):
        """Navega hacia arriba en el menú"""
        if self.selected_index > 0:
            self.selected_index -= 1
            # Ajustar scroll si es necesario
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
    
    def navigate_down(self, num_lessons):
        """Navega hacia abajo en el menú"""
        if self.selected_index < num_lessons - 1:
            self.selected_index += 1
            # Ajustar scroll si es necesario
            if self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1
    
    def get_selected_index(self):
        """Devuelve el índice de la lección seleccionada"""
        return self.selected_index
    
    def reset_selection(self):
        """Resetea la selección al inicio"""
        self.selected_index = 0
        self.scroll_offset = 0

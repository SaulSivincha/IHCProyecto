#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 2: Escalas Musicales
Aprende las escalas más comunes
"""

import cv2
import numpy as np
from ..lesson_base import BaseLesson


class ScalesLesson(BaseLesson):
    """Lección sobre escalas musicales"""
    
    def __init__(self):
        super().__init__()
        self.name = "Escalas Musicales"
        self.description = "Aprende escalas mayores, menores y patrones de tonos/semitonos"
        self.difficulty = "Básico"
        
        # Escalas (intervalos en semitonos desde la tónica)
        self.scales = [
            ("Escala Mayor", [0, 2, 4, 5, 7, 9, 11, 12], "T-T-st-T-T-T-st"),
            ("Escala Menor Natural", [0, 2, 3, 5, 7, 8, 10, 12], "T-st-T-T-st-T-T"),
            ("Escala Pentatónica Mayor", [0, 2, 4, 7, 9, 12], "Escala de 5 notas"),
            ("Escala Pentatónica Menor", [0, 3, 5, 7, 10, 12], "Común en blues/rock"),
            ("Escala Cromática", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "Todas las notas")
        ]
        self.current_scale = 0
        self.current_note = 0
        self.auto_play = False
    
    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """Ejecuta la lección de escalas"""
        
        # Header
        frame_left = self.draw_lesson_header(frame_left)
        
        # Info de escala actual
        scale_name, scale_notes, pattern = self.scales[self.current_scale]
        
        instructions = [
            f"Escala: {scale_name}",
            f"Patron: {pattern}",
            f"Notas: {len(scale_notes)} notas",
            "",
            "Controles:",
            "ESPACIO: Tocar nota actual",
            "D o FLECHA DER: Siguiente nota",
            "A o FLECHA IZQ: Nota anterior",
            "R: Auto-reproducir escala",
            "N: Siguiente escala | P: Escala anterior"
        ]
        frame_left = self.draw_instructions(frame_left, instructions, y_start=80)
        
        # Progreso en la escala
        frame_left = self.draw_progress_bar(frame_left, self.current_note + 1, 
                                           len(scale_notes), y=350)
        
        # Visualización de notas
        self._visualize_scale(frame_left, scale_notes)
        
        # Frame derecho
        frame_right = self.draw_lesson_header(frame_right, "Escalas")
        self._draw_scale_diagram(frame_right, scale_notes, pattern)
        
        return frame_left, frame_right, True
    
    def _visualize_scale(self, frame, scale_notes):
        """Visualiza las notas de la escala"""
        note_names = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
        
        y = 400
        x_start = 50
        for i, semitone in enumerate(scale_notes):
            note_name = note_names[semitone % 12]
            color = (100, 255, 100) if i == self.current_note else (200, 200, 200)
            
            cv2.putText(frame, note_name, (x_start + i * 60, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    
    def _draw_scale_diagram(self, frame, scale_notes, pattern):
        """Dibuja diagrama de la escala en frame derecho"""
        h, w = frame.shape[:2]
        
        cv2.putText(frame, "Estructura:", (50, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.putText(frame, pattern, (50, 160),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 255), 1, cv2.LINE_AA)
        
        cv2.putText(frame, f"{len(scale_notes)} notas", (50, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 100), 1, cv2.LINE_AA)
    
    def handle_key(self, key, synth, octave_base=60):
        """Maneja teclas de la lección"""
        scale_name, scale_notes, pattern = self.scales[self.current_scale]
        
        if key == ord(' '):  # Tocar nota actual
            note = octave_base + scale_notes[self.current_note]
            synth.noteon(0, note, 100)
            import time
            time.sleep(0.3)
            synth.noteoff(0, note)
            print(f"Nota {self.current_note + 1}: MIDI {note}")
            return True
        
        elif key == 83 or key == ord('d') or key == ord('D'):  # Flecha derecha o D
            self.current_note = (self.current_note + 1) % len(scale_notes)
            print(f"Nota {self.current_note + 1}/{len(scale_notes)}")
            return True
        
        elif key == 81 or key == ord('a') or key == ord('A'):  # Flecha izquierda o A
            self.current_note = (self.current_note - 1) % len(scale_notes)
            print(f"Nota {self.current_note + 1}/{len(scale_notes)}")
            return True
        
        elif key == ord('r') or key == ord('R'):  # Auto-reproducir (cambiado de 'a' a 'r')
            self._auto_play_scale(synth, octave_base, scale_notes)
            return True
        
        elif key == ord('n'):
            self.current_scale = (self.current_scale + 1) % len(self.scales)
            self.current_note = 0
            print(f"Escala: {self.scales[self.current_scale][0]}")
            return True
        
        elif key == ord('p'):
            self.current_scale = (self.current_scale - 1) % len(self.scales)
            self.current_note = 0
            print(f"Escala: {self.scales[self.current_scale][0]}")
            return True
        
        return False
    
    def _auto_play_scale(self, synth, octave_base, scale_notes):
        """Reproduce toda la escala automáticamente"""
        import time
        print(f"Reproduciendo escala completa...")
        for semitone in scale_notes:
            note = octave_base + semitone
            synth.noteon(0, note, 100)
            time.sleep(0.4)
            synth.noteoff(0, note)
            time.sleep(0.1)

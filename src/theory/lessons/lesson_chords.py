#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 3: Acordes Básicos
Aprende a tocar y reconocer acordes mayores y menores
"""

import cv2
import numpy as np
from ..lesson_base import BaseLesson


class ChordsLesson(BaseLesson):
    """Lección sobre acordes básicos"""
    
    def __init__(self):
        super().__init__()
        self.name = "Acordes Basicos"
        self.description = "Aprende acordes mayores, menores y su construccion (triadas)"
        self.difficulty = "Intermedio"
        
        # Acordes (nombre, notas en semitonos desde tónica, tipo)
        self.chords = [
            ("Do Mayor", [0, 4, 7], "Mayor: T + 3ªM + 5ªJ"),
            ("Do Menor", [0, 3, 7], "Menor: T + 3ªm + 5ªJ"),
            ("Re Mayor", [2, 6, 9], "Mayor"),
            ("Re Menor", [2, 5, 9], "Menor"),
            ("Mi Mayor", [4, 8, 11], "Mayor"),
            ("Mi Menor", [4, 7, 11], "Menor"),
            ("Fa Mayor", [5, 9, 12], "Mayor"),
            ("Sol Mayor", [7, 11, 14], "Mayor"),
            ("La Menor", [9, 12, 16], "Menor - Relativo de Do Mayor")
        ]
        self.current_chord = 0
        self.show_construction = False
    
    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """Ejecuta la lección de acordes"""
        
        # Header
        frame_left = self.draw_lesson_header(frame_left)
        
        chord_name, chord_notes, chord_info = self.chords[self.current_chord]
        
        instructions = [
            f"Acorde: {chord_name}",
            f"Info: {chord_info}",
            f"Notas: {len(chord_notes)} notas simultaneas",
            "",
            "Controles:",
            "ESPACIO: Tocar acorde (arpegiado)",
            "C: Tocar acorde completo (simultaneo)",
            "I: Mostrar/ocultar construccion",
            "N: Siguiente acorde | P: Anterior",
            "",
            "Tip: Los acordes se forman apilando intervalos"
        ]
        frame_left = self.draw_instructions(frame_left, instructions, y_start=80)
        
        # Progreso
        frame_left = self.draw_progress_bar(frame_left, self.current_chord + 1,
                                           len(self.chords), y=380)
        
        # Visualización del acorde
        self._visualize_chord(frame_left, chord_notes)
        
        # Frame derecho - construcción del acorde
        frame_right = self.draw_lesson_header(frame_right, "Acordes")
        if self.show_construction:
            self._draw_chord_construction(frame_right, chord_name, chord_notes)
        else:
            cv2.putText(frame_right, "Presiona I para ver", (100, 200),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1, cv2.LINE_AA)
            cv2.putText(frame_right, "la construccion", (100, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1, cv2.LINE_AA)
        
        return frame_left, frame_right, True
    
    def _visualize_chord(self, frame, chord_notes):
        """Visualiza las notas del acorde"""
        note_names = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
        
        y = 420
        cv2.putText(frame, "Notas del acorde:", (20, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        for i, semitone in enumerate(chord_notes):
            note_name = note_names[semitone % 12]
            x = 220 + i * 80
            
            # Círculo para cada nota
            cv2.circle(frame, (x, y - 5), 25, (100, 150, 255), -1)
            cv2.circle(frame, (x, y - 5), 25, (150, 200, 255), 2)
            
            cv2.putText(frame, note_name, (x - 15, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    
    def _draw_chord_construction(self, frame, chord_name, chord_notes):
        """Dibuja cómo se construye el acorde"""
        h, w = frame.shape[:2]
        
        cv2.putText(frame, f"Construccion de {chord_name}:", (50, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Mostrar intervalos
        intervals = []
        for i in range(1, len(chord_notes)):
            interval = chord_notes[i] - chord_notes[i-1]
            intervals.append(interval)
        
        y = 170
        cv2.putText(frame, f"Tonica: Nota base", (50, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 1, cv2.LINE_AA)
        
        y += 40
        if len(intervals) > 0:
            third_type = "3ª Mayor (4 st)" if intervals[0] == 4 else "3ª menor (3 st)"
            cv2.putText(frame, f"+ {third_type}", (50, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 100), 1, cv2.LINE_AA)
        
        y += 40
        if len(intervals) > 1:
            cv2.putText(frame, f"+ 5ª Justa ({intervals[1]} st)", (50, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 100), 1, cv2.LINE_AA)
        
        # Tipo de acorde
        y += 60
        chord_type = "MAYOR" if 4 in intervals else "MENOR"
        color = (100, 255, 100) if chord_type == "MAYOR" else (150, 150, 255)
        cv2.putText(frame, f"Tipo: {chord_type}", (50, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    
    def handle_key(self, key, synth, octave_base=60):
        """Maneja teclas de la lección"""
        chord_name, chord_notes, chord_info = self.chords[self.current_chord]
        
        if key == ord(' '):  # Arpegiado
            print(f"Arpeggiando: {chord_name}")
            import time
            for semitone in chord_notes:
                note = octave_base + semitone
                synth.noteon(0, note, 100)
                time.sleep(0.3)
                synth.noteoff(0, note)
                time.sleep(0.05)
            return True
        
        elif key == ord('c'):  # Acorde completo
            print(f"Acorde completo: {chord_name}")
            import time
            # Tocar todas las notas simultáneamente
            for semitone in chord_notes:
                note = octave_base + semitone
                synth.noteon(0, note, 100)
            
            time.sleep(1.0)
            
            for semitone in chord_notes:
                note = octave_base + semitone
                synth.noteoff(0, note)
            return True
        
        elif key == ord('i'):  # Toggle construcción
            self.show_construction = not self.show_construction
            return True
        
        elif key == ord('n'):
            self.current_chord = (self.current_chord + 1) % len(self.chords)
            print(f"Acorde: {self.chords[self.current_chord][0]}")
            return True
        
        elif key == ord('p'):
            self.current_chord = (self.current_chord - 1) % len(self.chords)
            print(f"Acorde: {self.chords[self.current_chord][0]}")
            return True
        
        return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 2: Escalas Musicales
Aprende las escalas más comunes
"""

import cv2
import numpy as np
import time
from ..lesson_base import BaseLesson


class ScalesLesson(BaseLesson):
    """Lección sobre escalas musicales"""
    
    def __init__(self):
        super().__init__()
        self.name = "Escalas Musicales"
        self.description = "Aprende escalas mayores, menores y sus patrones"
        self.difficulty = "Básico"
        
        # Escalas (intervalos en semitonos desde la tónica)
        # Escalas (intervalos en semitonos desde la tónica)
        self.scales = [
            ("Escala Mayor", [0, 2, 4, 5, 7, 9, 11, 12], "T - T - st - T - T - T - st"),
            ("Escala Menor Natural", [0, 2, 3, 5, 7, 8, 10, 12], "T - st - T - T - st - T - T"),
            ("Escala Pentatónica Mayor", [0, 2, 4, 7, 9, 12], "T - T - 1.5T - T - 1.5T"),
            ("Escala Pentatónica Menor", [0, 3, 5, 7, 10, 12], "1.5T - T - T - 1.5T - T"),
            ("Escala Cromática", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "Todas las notas (st)")
        ]
        self.current_scale = 0
        self.current_note_idx = 0
        
        # Variables de reproducción y estado
        self.play_state = None  # None, 'note', 'full_scale'
        self.play_start_time = 0
        self.scale_play_index = 0
        self.last_note_change_time = 0
        
        self.active_midi_notes = []
        self.octave_base = 60 # Do central
        
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Actualiza el texto de la interfaz"""
        scale_name, scale_notes, pattern = self.scales[self.current_scale]
        note_names = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
        
        # Determinar qué nota señalar (si estamos reproduciendo auto o manual)
        target_idx = self.scale_play_index if self.play_state == 'full_scale' else self.current_note_idx
        
        # Info cabecera
        text = f"=== {scale_name.upper()} ===\n"
        text += f"Patrón: {pattern}\n"
        text += f"Notas totales: {len(scale_notes)}\n\n"
        
        text += "--- NOTAS DE LA ESCALA ---\n"
        # Lista de notas con indicador
        for i, semitone in enumerate(scale_notes):
            marker = "➤" if i == target_idx else " "
            note_str = note_names[semitone % 12]
            # Añadir indicador de octava si pasa del Si (11)
            octave_shift = "" if semitone < 12 else "(Agudo)"
            text += f"{marker} {i+1}. {note_str} {octave_shift}\n"
        
        text += "\n--- CONTROLES ---\n"
        text += "• ESPACIO: Tocar nota señalada\n"
        text += "• R: Reproducir escala completa\n"
        text += "• D / FLECHA DER: Siguiente nota\n"
        text += "• A / FLECHA IZQ: Nota anterior\n"
        text += "• N / P: Cambiar de escala\n"
        
        self._instructions = text
        self._progress = int(((target_idx + 1) / len(scale_notes)) * 100)
        self._custom_info = f"Escala {self.current_scale + 1}/{len(self.scales)}"
    
    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """Lógica principal por frame"""
        current_time = time.time()
        scale_name, scale_notes, pattern = self.scales[self.current_scale]
        
        # --- Lógica de Reproducción ---
        
        # A) Reproducir UNA nota (Espacio)
        if self.play_state == 'note':
            elapsed = current_time - self.play_start_time
            if elapsed < 0.5: # Duración 0.5s
                note = self.octave_base + scale_notes[self.current_note_idx]
                if note not in self.active_midi_notes:
                    synth.noteon(0, note, 100)
                    self.active_midi_notes = [note]
            else:
                self._stop_all_notes(synth)
                self.play_state = None
        
        # B) Reproducir ESCALA COMPLETA (R)
        elif self.play_state == 'full_scale':
            # Tiempo por nota: 0.4s sonido + 0.1s silencio = 0.5s total
            NOTE_DURATION = 0.4
            GAP_DURATION = 0.1
            STEP_TIME = NOTE_DURATION + GAP_DURATION
            
            elapsed_total = current_time - self.play_start_time
            
            # Calcular en qué índice de nota deberíamos estar
            expected_index = int(elapsed_total / STEP_TIME)
            
            if expected_index < len(scale_notes):
                # Calcular tiempo dentro del paso actual
                time_in_step = elapsed_total % STEP_TIME
                
                # Actualizar UI si cambiamos de nota
                if expected_index != self.scale_play_index:
                    self.scale_play_index = expected_index
                    self._update_ui_state() # Mueve la flecha ➤
                
                # Gestionar sonido (Nota vs Silencio)
                if time_in_step < NOTE_DURATION:
                    # Tocar nota
                    note = self.octave_base + scale_notes[expected_index]
                    if note not in self.active_midi_notes:
                        self._stop_all_notes(synth) # Limpiar anterior
                        synth.noteon(0, note, 100)
                        self.active_midi_notes = [note]
                else:
                    # Breve silencio entre notas
                    self._stop_all_notes(synth)
            else:
                # Fin de la escala
                self._stop_all_notes(synth)
                self.play_state = None
                self.scale_play_index = 0
                self._update_ui_state() # Restaurar flecha al inicio o donde estaba
        
        # --- Visualización en Piano ---
        if virtual_keyboard and self.active_midi_notes:
            for midi_note in self.active_midi_notes:
                key_props = self._get_key_visual_props(virtual_keyboard, midi_note)
                if key_props:
                    (x, y, w, h), color = key_props
                    
                    # Overlay transparente
                    overlay = frame_left.copy()
                    cv2.rectangle(overlay, (x, y), (x+w, y+h), color, -1)
                    cv2.addWeighted(overlay, 0.6, frame_left, 0.4, 0, frame_left)
                    
                    # Borde blanco
                    cv2.rectangle(frame_left, (x, y), (x+w, y+h), (255, 255, 255), 2)
        
        return frame_left, frame_right, True

    def _get_key_visual_props(self, vk, midi_note):
        """Calcula coordenadas visuales de la tecla"""
        offset = midi_note - 60
        if offset < 0 or offset > 23: return None
        
        white_map = {0:0, 2:1, 4:2, 5:3, 7:4, 9:5, 11:6, 12:7, 14:8, 16:9, 17:10, 19:11, 21:12, 23:13}
        black_map = {1:0, 3:1, 6:3, 8:4, 10:5, 13:7, 15:8, 18:10, 20:11, 22:12}
        
        if offset in white_map:
            idx = white_map[offset]
            return (int(vk.kb_x0 + idx*vk.white_key_width), int(vk.kb_y0), 
                    int(vk.white_key_width), int(vk.kb_y1-vk.kb_y0)), (255, 255, 0) # Cian
        elif offset in black_map:
            idx = black_map[offset]
            x_center = vk.kb_x0 + vk.white_key_width * (idx + 1)
            idx_mod = idx % 7
            if idx_mod in (0, 3, 4): x = x_center - vk.black_key_width*(2/3)
            elif idx_mod in (1, 5): x = x_center - vk.black_key_width*(1/3)
            else: x = x_center - vk.black_key_width/2
            return (int(x), int(vk.kb_y0), int(vk.black_key_width), int(vk.black_key_heigth)), (255, 0, 255) # Magenta
        return None
    
    def handle_key(self, key, synth, octave_base=60):
        """Maneja teclas de la lección"""
        self.octave_base = octave_base
        scale_name, scale_notes, pattern = self.scales[self.current_scale]
        
        # ESPACIO: Tocar nota actual
        if key == ord(' '):
            self._stop_all_notes(synth)
            self.play_state = 'note'
            self.play_start_time = time.time()
            return True
        
        # R: Reproducir escala completa
        elif key == ord('r') or key == ord('R'):
            self._stop_all_notes(synth)
            self.play_state = 'full_scale'
            self.play_start_time = time.time()
            self.scale_play_index = 0
            return True
        
        # Navegación Notas (D/A o Flechas)
        elif key == 83 or key == ord('d') or key == ord('D'):  # Derecha
            self.current_note_idx = (self.current_note_idx + 1) % len(scale_notes)
            self._stop_all_notes(synth)
            self.play_state = None # Detener auto-play si me muevo
            self._update_ui_state()
            return True
        
        elif key == 81 or key == ord('a') or key == ord('A'):  # Izquierda
            self.current_note_idx = (self.current_note_idx - 1) % len(scale_notes)
            self._stop_all_notes(synth)
            self.play_state = None
            self._update_ui_state()
            return True
        
        # Navegación Escalas (N/P)
        elif key == ord('n') or key == ord('N'):
            self.current_scale = (self.current_scale + 1) % len(self.scales)
            self.current_note_idx = 0
            self._stop_all_notes(synth)
            self.play_state = None
            self._update_ui_state()
            return True
        
        elif key == ord('p') or key == ord('P'):
            self.current_scale = (self.current_scale - 1) % len(self.scales)
            self.current_note_idx = 0
            self._stop_all_notes(synth)
            self.play_state = None
            self._update_ui_state()
            return True
        
        return False
    
    def _stop_all_notes(self, synth):
        """Apaga notas activas"""
        if self.active_midi_notes:
            for note in self.active_midi_notes:
                synth.noteoff(0, note)
        self.active_midi_notes = []
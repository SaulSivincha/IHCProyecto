#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 3: Acordes Básicos
Aprende a tocar y reconocer acordes mayores y menores
"""

import cv2
import numpy as np
import time
from ..lesson_base import BaseLesson


class ChordsLesson(BaseLesson):
    """Lección sobre acordes básicos"""
    
    def __init__(self):
        super().__init__()
        self.name = "Acordes Basicos"
        self.description = "Aprende acordes mayores, menores y su construccion"
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
        
        # Variables para reproducción no bloqueante
        self.play_state = None  # None, 'arpeggio', 'chord'
        self.play_start_time = 0
        self.last_played_index = -1
        self.active_midi_notes = [] # Notas que deben sonar/iluminarse
        self.octave_base = 60 # Do central
        
        # Inicializar UI
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Actualiza el texto de instrucciones para la UI"""
        chord_name, chord_notes, chord_info = self.chords[self.current_chord]
        note_names = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
        
        notes_str_list = [note_names[n % 12] for n in chord_notes]
        notes_display = " - ".join(notes_str_list)
        
        text = f"=== ACORDE: {chord_name.upper()} ===\n"
        text += f"Notas: {notes_display}\n\n"
        
        text += "--- CONTROLES ---\n"
        text += "• ESPACIO: Arpegio (notas secuenciales)\n"
        text += "• C: Acorde Completo (simultáneo)\n"
        text += "• N / P: Cambiar de acorde\n"
        text += "• I: Ver información teórica\n\n"
        
        if self.show_construction:
            text += ">>> INFORMACIÓN TEÓRICA <<<\n"
            text += f"Estructura: {chord_info}\n"
            # Calcular intervalos
            intervals = []
            for i in range(1, len(chord_notes)):
                diff = chord_notes[i] - chord_notes[i-1]
                intervals.append(diff)
            
            if len(intervals) >= 1:
                third = "3ra Mayor (4 semitonos)" if intervals[0] == 4 else "3ra menor (3 semitonos)"
                text += f"1. Tónica -> 3ra: {third}\n"
            if len(intervals) >= 2:
                fifth_val = chord_notes[2] - chord_notes[0]
                text += f"2. Tónica -> 5ta: {fifth_val} semitonos (Justa)\n"
        else:
            text += "(Presiona 'I' para mostrar teoría)"
            
        self._instructions = text
        self._progress = int(((self.current_chord + 1) / len(self.chords)) * 100)
        self._custom_info = f"Acorde {self.current_chord + 1}/{len(self.chords)}"

    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """
        Ejecuta la lógica del frame. Maneja la reproducción de audio y visualización.
        """
        current_time = time.time()
        chord_name, chord_notes, chord_info = self.chords[self.current_chord]
        
        # --- Lógica de Reproducción (Audio) ---
        if self.play_state == 'arpeggio':
            note_duration = 0.5 
            elapsed = current_time - self.play_start_time
            note_index = int(elapsed / note_duration)
            
            if note_index < len(chord_notes):
                # Estamos en una nota válida
                if note_index != self.last_played_index:
                    # Apagar nota anterior
                    if self.last_played_index >= 0:
                        prev_note = self.octave_base + chord_notes[self.last_played_index]
                        synth.noteoff(0, prev_note)
                    
                    # Tocar nueva nota
                    current_note = self.octave_base + chord_notes[note_index]
                    synth.noteon(0, current_note, 100)
                    self.last_played_index = note_index
                    
                    # Actualizar visualización (solo la nota actual)
                    self.active_midi_notes = [current_note]
            else:
                # Fin del arpegio
                if self.last_played_index >= 0:
                    prev_note = self.octave_base + chord_notes[self.last_played_index]
                    synth.noteoff(0, prev_note)
                self.play_state = None
                self.active_midi_notes = []
                
        elif self.play_state == 'chord':
            elapsed = current_time - self.play_start_time
            if elapsed < 1.5: # Duración del acorde
                if self.last_played_index == -1: # Primera vez
                    self.active_midi_notes = []
                    for st in chord_notes:
                        note = self.octave_base + st
                        synth.noteon(0, note, 100)
                        self.active_midi_notes.append(note)
                    self.last_played_index = 0
            else:
                # Fin del acorde
                for st in chord_notes:
                    note = self.octave_base + st
                    synth.noteoff(0, note)
                self.play_state = None
                self.active_midi_notes = []

        # --- Visualización en el Piano (Corrección del Error) ---
        if virtual_keyboard and self.active_midi_notes:
            for midi_note in self.active_midi_notes:
                # Calculamos el rectángulo matemáticamente
                key_rect_data = self._get_key_visual_props(virtual_keyboard, midi_note)
                
                if key_rect_data:
                    (x, y, w, h), color = key_rect_data
                    
                    # Dibujar tecla resaltada (Overlay transparente)
                    overlay = frame_left.copy()
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
                    cv2.addWeighted(overlay, 0.5, frame_left, 0.5, 0, frame_left)
                    
                    # Borde brillante
                    cv2.rectangle(frame_left, (x, y), (x + w, y + h), (255, 255, 255), 2)

        # --- Indicador visual de Información ---
        if self.show_construction:
            if int(current_time * 2) % 2 == 0:
                cv2.putText(frame_left, "INFO: ON", (frame_left.shape[1]-160, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame_left, frame_right, True

    def _get_key_visual_props(self, vk, midi_note):
        """
        Calcula la posición visual de una tecla MIDI usando las propiedades del VirtualKeyboard.
        Retorna: ((x, y, w, h), color_bgr) o None
        """
        # Calcular offset desde C4 (60)
        offset = midi_note - 60
        if offset < 0 or offset > 23: return None # Fuera de rango (2 octavas)

        # Mapas de semitonos a índice visual (0-13) para teclas blancas
        # 0=Do, 1=Re, 2=Mi, 3=Fa, 4=Sol, 5=La, 6=Si...
        white_semitones_map = {
            0:0, 2:1, 4:2, 5:3, 7:4, 9:5, 11:6,
            12:7, 14:8, 16:9, 17:10, 19:11, 21:12, 23:13
        }
        
        # Mapa para teclas negras (asociadas a la tecla blanca anterior)
        # Offset -> Indice visual de la tecla blanca 'padre'
        black_semitones_map = {
            1:0, 3:1, 6:3, 8:4, 10:5,
            13:7, 15:8, 18:10, 20:11, 22:12
        }

        # Intentar como tecla blanca
        if offset in white_semitones_map:
            idx = white_semitones_map[offset]
            x = int(vk.kb_x0 + idx * vk.white_key_width)
            y = int(vk.kb_y0)
            w = int(vk.white_key_width)
            h = int(vk.kb_y1 - vk.kb_y0)
            return (x, y, w, h), (255, 255, 0) # Cian/Amarillo

        # Intentar como tecla negra
        elif offset in black_semitones_map:
            idx = black_semitones_map[offset]
            x_line = vk.kb_x0 + vk.white_key_width * (idx + 1)
            
            # Lógica de posición (copiada de VirtualKeyboard)
            # Grupos: (0, 3, 4) -> Izquierda | (1, 5) -> Derecha
            idx_mod = idx % 7
            
            if idx_mod in (0, 3, 4):
                x = int(x_line - vk.black_key_width * (2/3))
            elif idx_mod in (1, 5):
                x = int(x_line - vk.black_key_width * (1/3))
            else: # Caso por defecto (aunque no debería ocurrir con este mapa)
                x = int(x_line - vk.black_key_width / 2)
                
            y = int(vk.kb_y0)
            w = int(vk.black_key_width)
            h = int(vk.black_key_heigth)
            return (x, y, w, h), (255, 0, 255) # Magenta

        return None

    def handle_key(self, key, synth, octave_base=60):
        """Maneja teclas de la lección"""
        self.octave_base = octave_base
        
        if key == ord(' '):  # Arpegio
            print("Iniciando arpegio...")
            self.play_state = 'arpeggio'
            self.play_start_time = time.time()
            self.last_played_index = -1
            self.active_midi_notes = []
            return True
        
        elif key == ord('c') or key == ord('C'):  # Acorde completo
            print("Iniciando acorde...")
            self.play_state = 'chord'
            self.play_start_time = time.time()
            self.last_played_index = -1
            self.active_midi_notes = []
            return True
        
        elif key == ord('i') or key == ord('I'):  # Toggle info
            self.show_construction = not self.show_construction
            self._update_ui_state()
            return True
        
        elif key == ord('n') or key == ord('N') or key == 83: # Siguiente
            self._stop_current_sound(synth)
            self.current_chord = (self.current_chord + 1) % len(self.chords)
            self._update_ui_state()
            return True
        
        elif key == ord('p') or key == ord('P') or key == 81: # Anterior
            self._stop_current_sound(synth)
            self.current_chord = (self.current_chord - 1) % len(self.chords)
            self._update_ui_state()
            return True
        
        return False

    def _stop_current_sound(self, synth):
        """Detiene cualquier sonido activo"""
        if self.active_midi_notes:
            for note in self.active_midi_notes:
                synth.noteoff(0, note)
        self.play_state = None
        self.active_midi_notes = []
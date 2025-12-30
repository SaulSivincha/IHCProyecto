#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 4: Ritmo y Tempo
Aprende conceptos de duración de notas, tempo y patrones rítmicos
"""

import cv2
import numpy as np
import time
from ..lesson_base import BaseLesson


class RhythmLesson(BaseLesson):
    """Lección sobre ritmo y tempo musical"""
    
    def __init__(self):
        super().__init__()
        self.name = "Ritmo y Tempo"
        self.description = "Aprende duraciones de notas, tempo (BPM) y patrones rítmicos"
        self.difficulty = "Básico"
        
        # Conceptos de duración (en beats)
        self.note_durations = [
            ("Redonda", 4.0, "o", "4 tiempos"),
            ("Blanca", 2.0, "d", "2 tiempos"),
            ("Negra", 1.0, "q", "1 tiempo"),
            ("Corchea", 0.5, "e", "1/2 tiempo"),
            ("Semicorchea", 0.25, "s", "1/4 tiempo")
        ]
        
        # Patrones rítmicos (Nombre, [Lista de duraciones], Descripción)
        self.rhythm_patterns = [
            ("Escala Rítmica", [1.0, 1.0, 1.0, 1.0], "4 Negras (un compás)"),
            ("Blancas lentas", [2.0, 2.0], "2 Blancas"),
            ("Corcheas rápidas", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], "8 Corcheas"),
            ("Síncopa Básica", [0.5, 1.0, 0.5, 1.0, 1.0], "Contratiempos"),
            ("Tresillos", [0.33, 0.33, 0.34, 1.0, 1.0], "Tresillo + 2 Negras")
        ]
        
        # Tempos (BPM)
        self.tempos = [
            ("Largo", 40, "Muy lento"),
            ("Adagio", 60, "Lento"),
            ("Andante", 90, "Caminando"),
            ("Moderato", 120, "Moderado"),
            ("Allegro", 150, "Rápido"),
            ("Presto", 180, "Muy rápido")
        ]
        
        # Estado inicial
        self.current_duration_idx = 2  # Negra (1.0)
        self.current_pattern_idx = 0
        self.current_tempo_idx = 3     # Moderato (120 BPM)
        self.bpm = 120
        
        # Estados de reproducción
        self.play_state = None         # None, 'note', 'pattern'
        self.start_time = 0
        self.pattern_note_index = 0
        self.last_beat_time = 0        # Para el metrónomo
        
        # Variables de visualización
        self.active_midi_notes = []    # Notas iluminadas en el piano
        self.metronome_active = False
        self.metronome_flash = False   # Para el destello visual del beat
        
        # Nota para el metrónomo (Do agudo - Canal 0)
        self.METRONOME_NOTE = 96 
        
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Actualiza la interfaz de texto"""
        tempo_name, self.bpm, tempo_desc = self.tempos[self.current_tempo_idx]
        note_name, duration, symbol, note_desc = self.note_durations[self.current_duration_idx]
        pattern_name, pat_durs, pat_desc = self.rhythm_patterns[self.current_pattern_idx]
        
        text = "--- TEMPO (Velocidad) ---\n"
        text += f"Velocidad: {tempo_name} ({self.bpm} BPM)\n"
        text += f"Metrónomo: {'ENCENDIDO (M)' if self.metronome_active else 'Apagado (M)'}\n\n"
        
        text += "--- DURACIÓN DE NOTAS (1-5) ---\n"
        text += f"Selección: {note_name.upper()}\n"
        text += f"Valor: {note_desc} ({duration} beats)\n"
        text += f"Duración real: {duration * (60.0/self.bpm):.2f} segundos\n\n"
        
        text += "--- PATRÓN RÍTMICO ---\n"
        text += f"Patrón: {pattern_name}\n"
        text += f"Detalle: {pat_desc}\n\n"
        
        text += "--- CONTROLES ---\n"
        text += "• ESPACIO: Tocar nota seleccionada\n"
        text += "• 1-5: Cambiar duración (Redonda..Semicorchea)\n"
        text += "• M: Activar/Desactivar Metrónomo\n"
        text += "• P: Reproducir patrón rítmico\n"
        text += "• +/-: Cambiar velocidad (Tempo)\n"
        text += "• N: Cambiar patrón\n"
        
        self._instructions = text
        self._custom_info = f"BPM: {self.bpm} | Nota: {note_name}"

    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """Ejecuta la lógica del frame (Metrónomo + Reproducción + Visuales)"""
        current_time = time.time()
        beat_duration = 60.0 / self.bpm  # Segundos por beat
        
        # --- 1. LÓGICA DEL METRÓNOMO (Independiente) ---
        if self.metronome_active:
            if current_time - self.last_beat_time >= beat_duration:
                # ¡BEAT!
                self.last_beat_time = current_time
                self.metronome_flash = True
                
                # Sonido de click (Simulado con nota aguda de piano)
                # Usamos canal 0 (piano) nota 96, volumen fuerte (120)
                synth.noteon(0, self.METRONOME_NOTE, 120)
        
        # Reset visual y sonoro del metrónomo después de 100ms (para que sea corto)
        if self.metronome_flash and (current_time - self.last_beat_time > 0.1):
            self.metronome_flash = False
            synth.noteoff(0, self.METRONOME_NOTE)

        # --- 2. LÓGICA DE REPRODUCCIÓN (Nota o Patrón) ---
        
        # A) Reproducir UNA nota (Espacio)
        if self.play_state == 'note':
            _, dur_beats, _, _ = self.note_durations[self.current_duration_idx]
            duration_sec = dur_beats * beat_duration
            elapsed = current_time - self.start_time
            
            if elapsed < duration_sec:
                # Mantener nota sonando
                note = 60 # Do Central
                if note not in self.active_midi_notes:
                    synth.noteon(0, note, 100)
                    self.active_midi_notes = [note]
            else:
                # Terminar nota
                self._stop_all_notes(synth)
                self.play_state = None

        # B) Reproducir PATRÓN (P)
        elif self.play_state == 'pattern':
            _, pat_durs, _ = self.rhythm_patterns[self.current_pattern_idx]
            
            # Calcular en qué nota del patrón deberíamos estar
            elapsed_total = current_time - self.start_time
            accumulated_time = 0
            found_note = False
            
            for i, d_beat in enumerate(pat_durs):
                d_sec = d_beat * beat_duration
                
                # Intervalo de tiempo de esta nota específica
                start_n = accumulated_time
                end_n = accumulated_time + d_sec
                
                if start_n <= elapsed_total < end_n:
                    # Estamos dentro del tiempo de la nota 'i'
                    found_note = True
                    
                    # Si cambiamos de nota, actualizar sonido
                    if self.pattern_note_index != i:
                        self._stop_all_notes(synth)
                        # Usar escala para variar notas: Do, Re, Mi, Fa...
                        note = 60 + [0, 2, 4, 5, 7, 9, 11, 12][i % 8]
                        synth.noteon(0, note, 100)
                        self.active_midi_notes = [note]
                        self.pattern_note_index = i
                    break
                
                accumulated_time += d_sec
            
            if not found_note:
                # El patrón terminó
                self._stop_all_notes(synth)
                self.play_state = None

        # --- 3. VISUALIZACIÓN ---
        
        # A) Dibujar indicador de Metrónomo (Círculo pulsante)
        if self.metronome_active:
            color = (0, 255, 0) if self.metronome_flash else (50, 50, 50)
            radius = 20 if self.metronome_flash else 15
            # Esquina superior derecha
            cv2.circle(frame_left, (frame_left.shape[1] - 50, 50), radius, color, -1)
            cv2.circle(frame_left, (frame_left.shape[1] - 50, 50), radius, (255, 255, 255), 2)
            if self.metronome_flash:
                cv2.putText(frame_left, "BEAT", (frame_left.shape[1] - 90, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # B) Resaltar teclas en el piano
        if virtual_keyboard and self.active_midi_notes:
            for midi_note in self.active_midi_notes:
                key_props = self._get_key_visual_props(virtual_keyboard, midi_note)
                if key_props:
                    (x, y, w, h), color = key_props
                    
                    # Overlay
                    overlay = frame_left.copy()
                    cv2.rectangle(overlay, (x, y), (x+w, y+h), color, -1)
                    cv2.addWeighted(overlay, 0.6, frame_left, 0.4, 0, frame_left)
                    
                    # Borde
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
                    int(vk.white_key_width), int(vk.kb_y1-vk.kb_y0)), (255, 255, 0)
        elif offset in black_map:
            idx = black_map[offset]
            x_center = vk.kb_x0 + vk.white_key_width * (idx + 1)
            idx_mod = idx % 7
            if idx_mod in (0, 3, 4): x = x_center - vk.black_key_width*(2/3)
            elif idx_mod in (1, 5): x = x_center - vk.black_key_width*(1/3)
            else: x = x_center - vk.black_key_width/2
            return (int(x), int(vk.kb_y0), int(vk.black_key_width), int(vk.black_key_heigth)), (255, 0, 255)
        return None

    def handle_key(self, key, synth, octave_base=60):
        """Maneja las teclas de control"""
        
        # 1-5: Cambiar Duración
        if 49 <= key <= 53: 
            self.current_duration_idx = key - 49
            self._update_ui_state()
            return True
        
        # ESPACIO: Tocar nota
        elif key == ord(' '):
            self._stop_all_notes(synth)
            self.play_state = 'note'
            self.start_time = time.time()
            return True
        
        # M: Metrónomo
        elif key == ord('m') or key == ord('M'):
            self.metronome_active = not self.metronome_active
            self.last_beat_time = time.time()
            self._update_ui_state()
            return True
        
        # P: Reproducir Patrón
        elif key == ord('p') or key == ord('P'):
            self._stop_all_notes(synth)
            self.play_state = 'pattern'
            self.start_time = time.time()
            self.pattern_note_index = -1
            return True
        
        # +/-: Tempo
        elif key == ord('+') or key == ord('='):
            self.current_tempo_idx = min(len(self.tempos)-1, self.current_tempo_idx + 1)
            self._update_ui_state()
            return True
        elif key == ord('-') or key == ord('_'):
            self.current_tempo_idx = max(0, self.current_tempo_idx - 1)
            self._update_ui_state()
            return True
        
        # N: Siguiente Patrón
        elif key == ord('n') or key == ord('N'):
            self.current_pattern_idx = (self.current_pattern_idx + 1) % len(self.rhythm_patterns)
            self._update_ui_state()
            return True
            
        return False

    def _stop_all_notes(self, synth):
        if self.active_midi_notes:
            for n in self.active_midi_notes: synth.noteoff(0, n)
        self.active_midi_notes = []
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 1: Intervalos Musicales
Aprende a identificar intervalos entre notas
"""

import cv2
import numpy as np
import time
from ..lesson_base import BaseLesson


class IntervalsLesson(BaseLesson):
    """Lección sobre intervalos musicales"""
    
    def __init__(self):
        super().__init__()
        self.name = "Intervalos Musicales"
        self.description = "Aprende a identificar y tocar intervalos (distancia entre dos notas)"
        self.difficulty = "Básico"
        
        # Ejercicios
        self.intervals = [
            ("Segunda menor", 1, "Do - Do#"),
            ("Segunda mayor", 2, "Do - Re"),
            ("Tercera menor", 3, "Do - Mi bemol"),
            ("Tercera mayor", 4, "Do - Mi"),
            ("Cuarta justa", 5, "Do - Fa"),
            ("Quinta justa", 7, "Do - Sol"),
            ("Octava", 12, "Do - Do (Agudo)")
        ]
        self.current_interval = 0
        
        # Variables de estado para reproducción y visualización
        self.play_state = None  # None, 'playing'
        self.play_start_time = 0
        self.active_midi_notes = [] 
        self.octave_base = 60 # Do central
        
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Actualiza la interfaz de texto"""
        interval_name, semitones, example = self.intervals[self.current_interval]
        
        text = "--- CONCEPTO ---\n"
        text += "Un intervalo es la distancia de altura entre dos notas musicales.\n\n"
        
        text += f"=== INTERVALO: {interval_name.upper()} ===\n"
        text += f"Distancia: {semitones} semitonos\n"
        text += f"Ejemplo en Do: {example}\n\n"
        
        text += "--- EJERCICIO ---\n"
        text += "1. Presiona ESPACIO para escuchar y ver las notas.\n"
        text += "2. Intenta tocar esas dos notas en el piano virtual.\n"
        text += f"   (Nota base + {semitones} teclas a la derecha)\n\n"
        
        text += "--- CONTROLES ---\n"
        text += "• ESPACIO: Reproducir intervalo\n"
        text += "• N / FLECHA DER: Siguiente intervalo\n"
        text += "• P / FLECHA IZQ: Intervalo anterior\n"
        
        self._instructions = text
        self._progress = int(((self.current_interval + 1) / len(self.intervals)) * 100)
        self._custom_info = f"Intervalo {self.current_interval + 1}/{len(self.intervals)}"

    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """Ejecuta la lógica visual y auditiva por frame"""
        current_time = time.time()
        
        # --- Lógica de Reproducción (Secuencia Base -> Objetivo) ---
        if self.play_state == 'playing':
            elapsed = current_time - self.play_start_time
            interval_name, semitones, example = self.intervals[self.current_interval]
            
            base_note = self.octave_base
            target_note = base_note + semitones
            
            # Definir tiempos:
            # 0.0s - 0.8s: Nota Base
            # 0.8s - 0.9s: Silencio
            # 0.9s - 1.7s: Nota Objetivo
            
            if elapsed < 0.8:
                # Reproducir nota base
                if base_note not in self.active_midi_notes:
                    self._stop_all_notes(synth)
                    synth.noteon(0, base_note, 100)
                    self.active_midi_notes = [base_note]
            
            elif elapsed < 0.9:
                # Breve silencio entre notas
                self._stop_all_notes(synth)
                
            elif elapsed < 1.7:
                # Reproducir nota objetivo
                if target_note not in self.active_midi_notes:
                    self._stop_all_notes(synth)
                    synth.noteon(0, target_note, 100)
                    self.active_midi_notes = [target_note]
            
            else:
                # Fin de la secuencia
                self._stop_all_notes(synth)
                self.play_state = None
        
        # --- Visualización en el Piano (Resaltar teclas activas) ---
        if virtual_keyboard and self.active_midi_notes:
            for midi_note in self.active_midi_notes:
                key_rect_data = self._get_key_visual_props(virtual_keyboard, midi_note)
                
                if key_rect_data:
                    (x, y, w, h), color = key_rect_data
                    
                    # Dibujar tecla resaltada (Overlay transparente)
                    overlay = frame_left.copy()
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
                    cv2.addWeighted(overlay, 0.5, frame_left, 0.5, 0, frame_left)
                    
                    # Borde blanco brillante
                    cv2.rectangle(frame_left, (x, y), (x + w, y + h), (255, 255, 255), 2)
                    
                    # Etiqueta sobre la tecla
                    label = "Base" if midi_note == self.octave_base else "Obj"
                    cv2.putText(frame_left, label, (x, y + h - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)

        return frame_left, frame_right, True
    
    def _get_key_visual_props(self, vk, midi_note):
        """
        Calcula la posición visual de una tecla MIDI.
        Retorna: ((x, y, w, h), color_bgr) o None
        """
        # Calcular offset desde C4 (60)
        offset = midi_note - 60
        if offset < 0 or offset > 23: return None

        # Mapas de semitonos a índice visual
        white_semitones_map = {
            0:0, 2:1, 4:2, 5:3, 7:4, 9:5, 11:6,
            12:7, 14:8, 16:9, 17:10, 19:11, 21:12, 23:13
        }
        black_semitones_map = {
            1:0, 3:1, 6:3, 8:4, 10:5,
            13:7, 15:8, 18:10, 20:11, 22:12
        }

        # Tecla Blanca
        if offset in white_semitones_map:
            idx = white_semitones_map[offset]
            x = int(vk.kb_x0 + idx * vk.white_key_width)
            y = int(vk.kb_y0)
            w = int(vk.white_key_width)
            h = int(vk.kb_y1 - vk.kb_y0)
            return (x, y, w, h), (255, 255, 0) # Cian

        # Tecla Negra
        elif offset in black_semitones_map:
            idx = black_semitones_map[offset]
            x_line = vk.kb_x0 + vk.white_key_width * (idx + 1)
            
            idx_mod = idx % 7
            if idx_mod in (0, 3, 4):
                x = int(x_line - vk.black_key_width * (2/3))
            elif idx_mod in (1, 5):
                x = int(x_line - vk.black_key_width * (1/3))
            else:
                x = int(x_line - vk.black_key_width / 2)
                
            y = int(vk.kb_y0)
            w = int(vk.black_key_width)
            h = int(vk.black_key_heigth)
            return (x, y, w, h), (255, 0, 255) # Magenta

        return None
    
    def handle_key(self, key, synth, octave_base=60):
        """Maneja teclas de la lección"""
        self.octave_base = octave_base
        
        if key == ord(' '):  # ESPACIO: iniciar secuencia
            self.play_state = 'playing'
            self.play_start_time = time.time()
            self.active_midi_notes = []
            return True
        
        elif key == ord('n') or key == ord('N') or key == 83:  # Siguiente
            self._stop_all_notes(synth)
            self.current_interval = (self.current_interval + 1) % len(self.intervals)
            self._update_ui_state()
            return True
        
        elif key == ord('p') or key == ord('P') or key == 81:  # Anterior
            self._stop_all_notes(synth)
            self.current_interval = (self.current_interval - 1) % len(self.intervals)
            self._update_ui_state()
            return True
        
        return False

    def _stop_all_notes(self, synth):
        """Apaga todas las notas activas"""
        if self.active_midi_notes:
            for note in self.active_midi_notes:
                synth.noteoff(0, note)
        self.active_midi_notes = []
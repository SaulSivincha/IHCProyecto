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
        self.description = "Aprende duraciones de notas, tempo (BPM) y patrones rítmicos básicos"
        self.difficulty = "Básico"
        
        # Conceptos de duración (en beats)
        self.note_durations = [
            ("Redonda", 4.0, "o", "4 tiempos"),
            ("Blanca", 2.0, "d", "2 tiempos"),
            ("Negra", 1.0, "q", "1 tiempo"),
            ("Corchea", 0.5, "e", "1/2 tiempo"),
            ("Semicorchea", 0.25, "s", "1/4 tiempo")
        ]
        
        # Patrones rítmicos comunes
        self.rhythm_patterns = [
            ("Patrón básico", [1.0, 1.0, 1.0, 1.0], "4 negras"),
            ("Blancas", [2.0, 2.0], "2 blancas"),
            ("Corcheas", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], "8 corcheas"),
            ("Síncopa", [0.5, 1.0, 0.5, 1.0, 1.0], "Patrón sincopado"),
            ("Tresillo", [0.33, 0.33, 0.34, 1.0], "Tresillos + negra")
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
        
        self.current_duration = 0
        self.current_pattern = 0
        self.current_tempo = 3  # Moderato por defecto
        self.is_playing = False
        self.beat_visual_timer = 0
        self.last_beat_time = 0
        self.metronome_active = False
    
    def run(self, frame_left, frame_right, virtual_keyboard, synth, 
            hand_detector_left=None, hand_detector_right=None):
        """Ejecuta la lección de ritmo"""
        
        # Header
        frame_left = self.draw_lesson_header(frame_left)
        
        tempo_name, bpm, tempo_desc = self.tempos[self.current_tempo]
        
        instructions = [
            "SECCION 1: Duraciones de Notas",
            f"Duracion actual: {self.note_durations[self.current_duration][0]}",
            f"  -> {self.note_durations[self.current_duration][3]}",
            "",
            f"SECCION 2: Tempo - {tempo_name} ({bpm} BPM)",
            f"  -> {tempo_desc}",
            "",
            "Controles:",
            "ESPACIO: Tocar nota con duracion actual",
            "1-5: Cambiar duracion (1=Redonda, 5=Semicorchea)",
            "M: Activar/desactivar metronomo",
            "P: Reproducir patron ritmico",
            "+/-: Aumentar/disminuir tempo",
            "N: Siguiente patron"
        ]
        frame_left = self.draw_instructions(frame_left, instructions, y_start=80)
        
        # Visualización de duraciones
        self._draw_note_duration_chart(frame_left)
        
        # Visualización de tempo
        self._draw_tempo_indicator(frame_left, bpm)
        
        # Metrónomo visual
        if self.metronome_active:
            self._draw_metronome_beat(frame_left, bpm)
        
        # Frame derecho - Patrón rítmico
        frame_right = self.draw_lesson_header(frame_right, "Patrones Ritmicos")
        self._draw_rhythm_pattern(frame_right)
        
        return frame_left, frame_right, True
    
    def _draw_note_duration_chart(self, frame):
        """Dibuja tabla de duraciones de notas"""
        y = 320
        x_start = 20
        
        cv2.putText(frame, "Duraciones:", (x_start, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        y += 30
        for i, (name, duration, symbol, desc) in enumerate(self.note_durations):
            color = (100, 255, 100) if i == self.current_duration else (180, 180, 180)
            
            # Nombre
            text = f"{i+1}. {name:12} {symbol}  ({desc})"
            cv2.putText(frame, text, (x_start + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
            
            # Barra visual proporcional
            bar_width = int(duration * 40)
            cv2.rectangle(frame, (x_start + 300, y - 10), 
                         (x_start + 300 + bar_width, y), color, -1)
            
            y += 25
    
    def _draw_tempo_indicator(self, frame, bpm):
        """Dibuja indicador de tempo"""
        y = 320
        x = 420
        
        cv2.putText(frame, "Tempo (BPM):", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        y += 40
        cv2.putText(frame, str(bpm), (x + 30, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 200, 0), 2, cv2.LINE_AA)
        
        # Indicador visual de velocidad
        y += 40
        tempo_bar_width = int((bpm / 200.0) * 150)
        cv2.rectangle(frame, (x, y), (x + 150, y + 15), (50, 50, 50), -1)
        cv2.rectangle(frame, (x, y), (x + tempo_bar_width, y + 15), (255, 200, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 150, y + 15), (200, 200, 200), 1)
        
        # Etiquetas
        y += 35
        cv2.putText(frame, "Lento", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)
        cv2.putText(frame, "Rapido", (x + 110, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)
    
    def _draw_metronome_beat(self, frame, bpm):
        """Dibuja beat visual del metrónomo"""
        current_time = time.time()
        beat_interval = 60.0 / bpm  # Segundos por beat
        
        # Calcular si estamos en un beat
        time_in_measure = (current_time % (beat_interval * 4))
        beat_number = int(time_in_measure / beat_interval) + 1
        
        # Efecto visual de pulso
        time_since_beat = time_in_measure % beat_interval
        pulse_intensity = max(0, 1.0 - (time_since_beat / beat_interval))
        
        x = 550
        y = 80
        
        # Círculo pulsante
        radius = int(20 + pulse_intensity * 10)
        color_intensity = int(100 + pulse_intensity * 155)
        color = (color_intensity, color_intensity, 0) if beat_number == 1 else (0, color_intensity, 0)
        
        cv2.circle(frame, (x, y), radius, color, -1)
        cv2.circle(frame, (x, y), radius, (255, 255, 255), 2)
        
        # Número de beat
        cv2.putText(frame, str(beat_number), (x - 8, y + 8),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    
    def _draw_rhythm_pattern(self, frame, y_start=120):
        """Dibuja el patrón rítmico actual"""
        h, w = frame.shape[:2]
        
        pattern_name, durations, description = self.rhythm_patterns[self.current_pattern]
        
        cv2.putText(frame, f"Patron: {pattern_name}", (50, y_start),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.putText(frame, description, (50, y_start + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Representación gráfica del patrón
        y = y_start + 80
        x_start = 50
        total_duration = sum(durations)
        available_width = w - 100
        
        x = x_start
        for i, duration in enumerate(durations):
            # Ancho proporcional a la duración
            note_width = int((duration / total_duration) * available_width)
            
            # Color según duración
            if duration >= 2.0:
                color = (100, 100, 255)  # Azul para notas largas
            elif duration >= 1.0:
                color = (100, 255, 100)  # Verde para negras
            elif duration >= 0.5:
                color = (255, 200, 100)  # Naranja para corcheas
            else:
                color = (255, 100, 100)  # Rojo para semicorcheas
            
            # Dibujar nota
            cv2.rectangle(frame, (x, y), (x + note_width - 5, y + 40), color, -1)
            cv2.rectangle(frame, (x, y), (x + note_width - 5, y + 40), (255, 255, 255), 2)
            
            # Etiqueta de duración
            dur_text = f"{duration:.2f}".rstrip('0').rstrip('.')
            cv2.putText(frame, dur_text, (x + 5, y + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            
            x += note_width
        
        # Información adicional
        y += 70
        cv2.putText(frame, f"Total: {total_duration:.1f} tiempos", (50, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        y += 30
        tempo_name, bpm, tempo_desc = self.tempos[self.current_tempo]
        total_seconds = (total_duration / bpm) * 60
        cv2.putText(frame, f"Duracion: {total_seconds:.2f} segundos a {bpm} BPM", (50, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    
    def handle_key(self, key, synth, octave_base=60):
        """Maneja teclas de la lección"""
        
        # Cambiar duración con números 1-5
        if 49 <= key <= 53:  # Teclas 1-5
            self.current_duration = key - 49
            print(f"Duración: {self.note_durations[self.current_duration][0]}")
            return True
        
        # Tocar nota con duración actual
        elif key == ord(' '):
            note_name, duration, symbol, desc = self.note_durations[self.current_duration]
            tempo_name, bpm, tempo_desc = self.tempos[self.current_tempo]
            
            # Calcular duración en segundos según tempo
            beat_duration = 60.0 / bpm  # Duración de 1 beat en segundos
            note_duration_seconds = duration * beat_duration
            
            print(f"Tocando {note_name} ({duration} beats = {note_duration_seconds:.2f}s a {bpm} BPM)")
            
            note = octave_base
            synth.noteon(0, note, 100)
            time.sleep(note_duration_seconds)
            synth.noteoff(0, note)
            
            return True
        
        # Metrónomo
        elif key == ord('m') or key == ord('M'):
            self.metronome_active = not self.metronome_active
            status = "activado" if self.metronome_active else "desactivado"
            print(f"Metrónomo {status}")
            return True
        
        # Reproducir patrón rítmico
        elif key == ord('p') or key == ord('P'):
            self._play_rhythm_pattern(synth, octave_base)
            return True
        
        # Cambiar tempo
        elif key == ord('+') or key == ord('='):
            self.current_tempo = min(len(self.tempos) - 1, self.current_tempo + 1)
            tempo_name, bpm, tempo_desc = self.tempos[self.current_tempo]
            print(f"Tempo: {tempo_name} ({bpm} BPM) - {tempo_desc}")
            return True
        
        elif key == ord('-') or key == ord('_'):
            self.current_tempo = max(0, self.current_tempo - 1)
            tempo_name, bpm, tempo_desc = self.tempos[self.current_tempo]
            print(f"Tempo: {tempo_name} ({bpm} BPM) - {tempo_desc}")
            return True
        
        # Siguiente patrón
        elif key == ord('n') or key == ord('N'):
            self.current_pattern = (self.current_pattern + 1) % len(self.rhythm_patterns)
            pattern_name = self.rhythm_patterns[self.current_pattern][0]
            print(f"Patrón: {pattern_name}")
            return True
        
        return False
    
    def _play_rhythm_pattern(self, synth, octave_base):
        """Reproduce el patrón rítmico actual"""
        pattern_name, durations, description = self.rhythm_patterns[self.current_pattern]
        tempo_name, bpm, tempo_desc = self.tempos[self.current_tempo]
        
        print(f"Reproduciendo patrón: {pattern_name} a {bpm} BPM")
        
        beat_duration = 60.0 / bpm
        note = octave_base
        
        for i, duration in enumerate(durations):
            note_duration_seconds = duration * beat_duration
            
            # Tocar nota
            synth.noteon(0, note + (i % 3), 100)  # Variar ligeramente el tono
            time.sleep(note_duration_seconds * 0.9)  # 90% para articulación
            synth.noteoff(0, note + (i % 3))
            time.sleep(note_duration_seconds * 0.1)  # 10% de silencio
        
        print("Patrón completado")

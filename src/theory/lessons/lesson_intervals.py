#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección 1: Intervalos Musicales
Aprende a identificar intervalos entre notas
"""

import cv2
import numpy as np
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
            ("Tercera menor", 3, "Do - Mi♭"),
            ("Tercera mayor", 4, "Do - Mi"),
            ("Cuarta justa", 5, "Do - Fa"),
            ("Quinta justa", 7, "Do - Sol"),
            ("Octava", 12, "Do - Do")
        ]
        self.current_interval = 0
        self.play_count = 0
    
    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        """Ejecuta la lección de intervalos"""
        
        # Dibujar header
        frame_left = self.draw_lesson_header(frame_left)
        
        # Instrucciones
        instructions = [
            "Los intervalos son la distancia entre dos notas.",
            "",
            f"Intervalo actual: {self.intervals[self.current_interval][0]}",
            f"Ejemplo: {self.intervals[self.current_interval][2]}",
            f"Semitonos: {self.intervals[self.current_interval][1]}",
            "",
            "Presiona ESPACIO para escuchar el intervalo",
            "Presiona N para siguiente intervalo",
            "Presiona P para intervalo anterior"
        ]
        frame_left = self.draw_instructions(frame_left, instructions, y_start=80)
        
        # Barra de progreso
        frame_left = self.draw_progress_bar(frame_left, self.current_interval + 1, 
                                           len(self.intervals), y=400)
        
        # Visualización del intervalo en el teclado
        self._visualize_interval(frame_left, virtual_keyboard)
        
        # Mismo contenido en frame derecho (simplificado)
        frame_right = self.draw_lesson_header(frame_right, "Intervalos")
        cv2.putText(frame_right, self.intervals[self.current_interval][0], 
                   (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 2, cv2.LINE_AA)
        
        return frame_left, frame_right, True
    
    def _visualize_interval(self, frame, virtual_keyboard):
        """Dibuja el intervalo en el teclado virtual"""
        interval_name, semitones, example = self.intervals[self.current_interval]
        
        # Calcular posiciones en el teclado (asumiendo Do = tecla 0)
        base_key = 0  # Do
        target_key = semitones
        
        # Resaltar teclas en el frame
        # (esto es una aproximación; ajusta según tu VirtualKeyboard)
        info_text = f"Toca: tecla {base_key} y tecla {target_key}"
        cv2.putText(frame, info_text, (20, 450),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 1, cv2.LINE_AA)
    
    def handle_key(self, key, synth, octave_base=60):
        """
        Maneja teclas especiales de la lección
        Llamar desde main loop
        
        Args:
            key: Código de tecla presionada
            synth: Instancia de FluidSynth
            octave_base: Nota MIDI base
        
        Returns:
            bool: True si se manejó la tecla
        """
        interval_name, semitones, example = self.intervals[self.current_interval]
        
        if key == ord(' '):  # ESPACIO: reproducir intervalo
            base_note = octave_base
            target_note = base_note + semitones
            
            # Tocar nota base
            synth.noteon(0, base_note, 100)
            import time
            time.sleep(0.5)
            synth.noteoff(0, base_note)
            
            # Tocar nota objetivo
            synth.noteon(0, target_note, 100)
            time.sleep(0.5)
            synth.noteoff(0, target_note)
            
            self.play_count += 1
            print(f"Reproduciendo: {interval_name} ({example})")
            return True
        
        elif key == ord('n'):  # Siguiente
            self.current_interval = (self.current_interval + 1) % len(self.intervals)
            print(f"Siguiente: {self.intervals[self.current_interval][0]}")
            return True
        
        elif key == ord('p'):  # Anterior
            self.current_interval = (self.current_interval - 1) % len(self.intervals)
            print(f"Anterior: {self.intervals[self.current_interval][0]}")
            return True
        
        return False

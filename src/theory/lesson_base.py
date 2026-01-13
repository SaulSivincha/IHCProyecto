#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clase base abstracta para lecciones de teoría musical
Cada lección debe heredar de BaseLesson e implementar run()
"""

from abc import ABC, abstractmethod
import cv2
import numpy as np
from src.config.theme import Theme


class BaseLesson(ABC):
    """
    Clase base para todas las lecciones de teoría musical.
    
    Atributos que cada lección debe definir:
    - name: Nombre descriptivo de la lección
    - description: Breve descripción del contenido
    - difficulty: 'Básico', 'Intermedio', 'Avanzado'
    """
    
    def __init__(self):
        self.name = "Lección sin nombre"
        self.description = "Sin descripción"
        self.difficulty = "Básico"
        self.running = False
        
        # Datos de estado para PyQt6
        self._instructions = ""
        self._progress = 0
        self._custom_info = ""
        
        # Glosario de términos (palabra -> definición)
        self.glossary = {}
    
    def get_lesson_state(self):
        """
        Devuelve el estado actual de la lección para PyQt6
        
        Returns:
            dict: Diccionario con 'instructions', 'progress', 'custom_info'
        """
        return {
            'instructions': self._instructions,
            'progress': self._progress,
            'custom_info': self._custom_info
        }
    
    @abstractmethod
    def handle_key(self, key, synth, octave_base=60):
        """
        Maneja teclas presionadas durante la lección
        
        Args:
            key: Código de tecla (ord('a'), ord(' '), etc)
            synth: Instancia de FluidSynth
            octave_base: Nota MIDI base
        
        Returns:
            bool: True si se manejó la tecla
        """
        pass
    
    def get_info(self):
        """Devuelve información de la lección como diccionario"""
        return {
            'name': self.name,
            'description': self.description,
            'difficulty': self.difficulty
        }
    
    def start(self):
        """Inicializa la lección (llamado una vez al entrar)"""
        self.running = True
        print(f"Iniciando lección: {self.name}")
    
    def stop(self):
        """Finaliza la lección (llamado al salir)"""
        self.running = False
        print(f"Finalizando lección: {self.name}")
    
    def draw_lesson_header(self, frame, title=None):
        """
        Dibuja header estándar con título de lección y controles
        
        Args:
            frame: Frame donde dibujar
            title: Título personalizado (usa self.name si es None)
        """
        h, w = frame.shape[:2]
        title_text = title or self.name
        
        # Fondo semi-transparente para header
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), Theme.BG_HEADER, -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Título
        cv2.putText(frame, title_text, (10, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, Theme.TEXT_PRIMARY, 2, cv2.LINE_AA)
        
        # Controles
        cv2.putText(frame, "ESC: Volver | Q: Salir", (w - 300, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Theme.TEXT_SECONDARY, 1, cv2.LINE_AA)
        
        return frame
    
    def draw_instructions(self, frame, instructions, y_start=80):
        """
        Dibuja instrucciones en pantalla
        
        Args:
            frame: Frame donde dibujar
            instructions: Lista de strings con instrucciones
            y_start: Posición Y inicial
        """
        for i, instruction in enumerate(instructions):
            y = y_start + (i * 30)
            cv2.putText(frame, instruction, (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, Theme.TEXT_PRIMARY, 1, cv2.LINE_AA)
        
        return frame
    
    def draw_progress_bar(self, frame, current, total, x=20, y=400, width=300, height=20):
        """
        Dibuja barra de progreso
        
        Args:
            frame: Frame donde dibujar
            current: Valor actual
            total: Valor total
            x, y: Posición
            width, height: Dimensiones
        """
        # Fondo
        cv2.rectangle(frame, (x, y), (x + width, y + height), Theme.PROGRESS_BG, -1)
        
        # Progreso
        progress_width = int((current / total) * width) if total > 0 else 0
        cv2.rectangle(frame, (x, y), (x + progress_width, y + height), Theme.PROGRESS_FILL, -1)
        
        # Borde
        cv2.rectangle(frame, (x, y), (x + width, y + height), Theme.PROGRESS_BORDER, 2)
        
        # Texto
        text = f"{current}/{total}"
        cv2.putText(frame, text, (x + width + 10, y + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, Theme.TEXT_PRIMARY, 1, cv2.LINE_AA)
        
        return frame

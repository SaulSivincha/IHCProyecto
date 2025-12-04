#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de lecciones de teoría musical
Registra y carga lecciones disponibles
"""

import os
import importlib
import inspect
from pathlib import Path
from .lesson_base import BaseLesson


class LessonManager:
    """Gestor centralizado de lecciones de teoría musical"""
    
    def __init__(self):
        self._lessons = {}
        self._lesson_order = []
        self._load_lessons()
    
    def _load_lessons(self):
        """Carga automáticamente todas las lecciones del directorio lessons/"""
        lessons_dir = Path(__file__).parent / 'lessons'
        
        if not lessons_dir.exists():
            print(f"⚠ Directorio de lecciones no encontrado: {lessons_dir}")
            return
        
        # Buscar todos los archivos lesson_*.py
        for lesson_file in sorted(lessons_dir.glob('lesson_*.py')):
            module_name = lesson_file.stem
            
            try:
                # Importar el módulo
                module = importlib.import_module(f'src.theory.lessons.{module_name}')
                
                # Buscar clases que heredan de BaseLesson
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseLesson) and obj != BaseLesson:
                        lesson_instance = obj()
                        lesson_id = module_name.replace('lesson_', '')
                        self._lessons[lesson_id] = lesson_instance
                        self._lesson_order.append(lesson_id)
                        print(f"✓ Lección cargada: {lesson_instance.name} ({lesson_id})")
            
            except Exception as e:
                print(f"✗ Error al cargar {module_name}: {e}")
    
    def get_all_lessons(self):
        """
        Devuelve todas las lecciones disponibles en orden
        
        Returns:
            list: Lista de tuplas (id, lesson_instance)
        """
        return [(lid, self._lessons[lid]) for lid in self._lesson_order]
    
    def get_lesson(self, lesson_id):
        """
        Obtiene una lección específica por ID
        
        Args:
            lesson_id: Identificador de la lección
        
        Returns:
            BaseLesson o None si no existe
        """
        return self._lessons.get(lesson_id)
    
    def get_lesson_info(self, lesson_id):
        """Obtiene información de una lección sin instanciarla"""
        lesson = self.get_lesson(lesson_id)
        return lesson.get_info() if lesson else None
    
    def count(self):
        """Devuelve el número de lecciones disponibles"""
        return len(self._lessons)


# Instancia global del gestor
_lesson_manager = None

def get_lesson_manager():
    """Devuelve instancia única del gestor de lecciones"""
    global _lesson_manager
    if _lesson_manager is None:
        _lesson_manager = LessonManager()
    return _lesson_manager

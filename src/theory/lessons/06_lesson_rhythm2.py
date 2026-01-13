from src.theory.lesson_base import BaseLesson
import cv2

class Rhythm2Lesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = 'Ritmo II'
        self.description = (
            "¡Sube de nivel en el <a href='ritmo'>Ritmo</a>! "
            "Aprende sobre <a href='sincopa'>Síncopa</a> y cómo hacer la música más divertida. "
        )
        self.difficulty = 'Intermedio'
        
        self.glossary = {
            "sincopa": "La Síncopa es cuando acentuamos una nota en un momento inesperado. ¡Sorpresa!",
            "ritmo": "El Ritmo es el motor de la música."
        }
        
        self._instructions = "Próximamente ejercicios avanzados.\n\n¡Sigue practicando lo básico!"
        
    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        return frame_left, frame_right, True
        
    def handle_key(self, key, synth, octave_base=60):
        return False
        
    def get_lesson_state(self):
        return {
            "name": self.name,
            "progress": 0,
            "instructions": self._instructions
        }

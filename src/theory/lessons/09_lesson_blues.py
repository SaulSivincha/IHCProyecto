from src.theory.lesson_base import BaseLesson
import cv2

class BluesLesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = 'Blues'
        self.description = (
            "Siente el <a href='blues'>Blues</a>. "
            "Una música llena de sentimiento que usa la famosa <a href='notablue'>Nota Blue</a>."
        )
        self.difficulty = 'Avanzado'
        
        self.glossary = {
            "blues": "Un estilo de música que expresa sentimientos profundos, a veces tristes pero con esperanza.",
            "notablue": "Una nota especial que suena un poco 'desafinada' a propósito para dar sentimiento."
        }
        
        self._instructions = "Próximamente ejercicios de Blues.\n\n¡Toca con sentimiento!"
        
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

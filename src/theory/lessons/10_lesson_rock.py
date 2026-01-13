from src.theory.lesson_base import BaseLesson
import cv2

class RockLesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = 'Rock'
        self.description = (
            "¡Vamos a rockear! Aprende la energía del <a href='rock'>Rock</a> "
            "y los poderosos <a href='powerchord'>Power Chords</a>."
        )
        self.difficulty = 'Avanzado'
        
        self.glossary = {
            "rock": "Un estilo musical con mucha energía, guitarras eléctricas y ritmo fuerte.",
            "powerchord": "Un acorde poderoso y simple usado mucho en el Rock. ¡Suena muy fuerte!"
        }
        
        self._instructions = "Próximamente ejercicios de Rock.\n\n¡Súbele al volumen!"
        
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

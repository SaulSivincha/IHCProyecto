from src.theory.lesson_base import BaseLesson
import cv2

class JazzLesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = 'Jazz'
        self.description = (
            "¡El <a href='jazz'>Jazz</a> es pura libertad! "
            "Aprende sobre el ritmo <a href='swing'>Swing</a> y la improvisación."
        )
        self.difficulty = 'Avanzado'
        
        self.glossary = {
            "jazz": "Un estilo de música donde los músicos inventan parte de la música mientras tocan.",
            "swing": "Un ritmo especial que hace que quieras mover los pies 'saltando'."
        }
        
        self._instructions = "Próximamente ejercicios de Jazz.\n\n¡Siente el Swing!"
        
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

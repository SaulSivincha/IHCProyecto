from src.theory.lesson_base import BaseLesson
import cv2

class HarmonyLesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = 'Armonia'
        self.description = (
            "Descubre la <a href='armonia'>Armonía</a>. "
            "Es el arte de conectar los <a href='acorde'>Acordes</a> para crear música hermosa."
        )
        self.difficulty = 'Avanzado'
        
        self.glossary = {
            "armonia": "La Armonía estudia cómo se relacionan los acordes entre sí.",
            "acorde": "Grupo de notas sonando juntas."
        }
        
        self._instructions = "Próximamente ejercicios de Armonía.\n\n¡Sigue practicando!"
        
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

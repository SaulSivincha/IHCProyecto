from src.theory.lesson_base import BaseLesson

class Dummy(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = 'Rock'
        
    def handle_key(self, key_index):
        pass
        
    def update(self, frame_left, frame_right, left_hand_pos, right_hand_pos):
        return frame_left, frame_right, None
        
    def get_lesson_state(self):
        return {
            "name": self.name,
            "progress": 0.0,
            "instructions": "Leccion de prueba"
        }

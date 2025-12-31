from src.theory.lesson_base import BaseLesson
import cv2

class MelodyLesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = "Melodias Simples"
        self.description = "Aprende a tocar tu primera melodia: Estrellita donde estas."
        self.difficulty = "Facil"
        
    def start(self):
        super().start()
        print(f"Lección iniciada: {self.name}")

    def stop(self):
        super().stop()
        print(f"Lección detenida: {self.name}")

    def update(self, frame_left, frame_right, left_hand_pos, right_hand_pos):
        # Lógica dummy para dibujar en pantalla
        cv2.putText(frame_left, "LECCION 5: MELODIAS", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame_left, "Toca Do-Do-Sol-Sol...", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        return frame_left, frame_right, None

    def handle_key(self, key_index):
        # Dummy implementation
        pass

    def get_lesson_state(self):
        return {
            "name": self.name,
            "progress": 0.0,
            "instructions": "Sigue las notas en pantalla."
        }

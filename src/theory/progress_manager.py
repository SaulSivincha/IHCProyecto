import json
import os

class ProgressManager:
    def __init__(self, filepath="user_progress.json"):
        # Se guardará en la raíz del proyecto
        self.filepath = filepath
        self.completed_lessons = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    return data.get("completed", [])
            except:
                return []
        return []

    def is_unlocked(self, lesson_id, index):
        # La primera lección siempre está abierta
        if index == 0:
            return True
        # Las demás requieren que el ÍNDICE anterior esté completado
        return str(index - 1) in self.completed_lessons

    def save_completion(self, index):
        if str(index) not in self.completed_lessons:
            self.completed_lessons.append(str(index))
            with open(self.filepath, 'w') as f:
                json.dump({"completed": self.completed_lessons}, f)
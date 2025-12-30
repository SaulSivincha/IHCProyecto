import importlib
import os

class LessonManager:
    def __init__(self):
        self.lessons_path = "src/theory/lessons"
        self.lessons = self._discover_lessons()

    def _discover_lessons(self):
        lessons = []
        files = sorted([f for f in os.listdir(self.lessons_path) if f.endswith('.py') and not f.startswith('__')])
        for f in files:
            module_name = f"src.theory.lessons.{f[:-3]}"
            module = importlib.import_module(module_name)
            # Asumimos que cada archivo tiene una clase 'Lesson'
            lessons.append({"id": f[:-3], "class": module.Lesson})
        return lessons
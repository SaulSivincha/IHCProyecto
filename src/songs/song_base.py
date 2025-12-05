from abc import ABC, abstractmethod
import cv2
import time

class BaseSong(ABC):
    """
    Clase base para todas las canciones.
    Define la estructura que deben tener los archivos en chart_files.
    """
    
    # --- Configuración por defecto de una canción ---
    name: str = "Canción sin nombre"
    bpm: int = 120
    difficulty: str = "Básico"  # Básico, Intermedio, Avanzado
    scroll_speed: float = 1.0   # Multiplicador de velocidad (1.0 = normal)
    music_key: str = "C"        # Tonalidad (ej: C Mayor)
    
    # La estructura de notas: { "time": segundo, "keys": ["tecla"] }
    chart: list = []

    def __init__(self):
        self.running = False
        self.start_time = 0
        self.score = 0
        self.active_chart = [] # Copia del chart para jugar

    def start(self):
        """Reinicia el reloj y prepara las notas"""
        self.running = True
        self.start_time = time.time()
        self.score = 0
        self.active_chart = self.chart.copy()
        print(f"🎵 Iniciando: {self.name} ({self.bpm} BPM)")

    def stop(self):
        self.running = False
        print(f"⏹ Deteniendo: {self.name}")

    def get_info(self):
        return {
            'name': self.name,
            'bpm': self.bpm,
            'difficulty': self.difficulty
        }

    @abstractmethod
    def run(self, frame_left, frame_right, virtual_keyboard, synth):
        """
        Lógica del juego por cada frame.
        Debe devolver: (frame_left, frame_right, continue_song)
        """
        pass
    
    # --- Ayudas Visuales (Igual que en Theory) ---

    def draw_header(self, frame):
        """Dibuja la barra superior con info de la canción"""
        h, w = frame.shape[:2]
        
        # Fondo oscuro semitransparente
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), (30, 20, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Texto
        info_txt = f"{self.name} | BPM: {self.bpm} | Score: {self.score}"
        cv2.putText(frame, info_txt, (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Instrucciones de salida
        cv2.putText(frame, "Q: Salir", (w - 120, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame
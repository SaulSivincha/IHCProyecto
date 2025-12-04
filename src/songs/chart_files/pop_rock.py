from src.songs.song_base import BaseSong
import time
import cv2

class PopRockSong(BaseSong):
    name = "Pop Rock Style"
    bpm = 120
    difficulty = "Intermedio"
    music_key = "A Minor"
    scroll_speed = 1.2  # Un poco más rápido

    # El "mapa" de la canción
    chart = [
        { "time": 1.0, "keys": ["A"] },
        { "time": 1.5, "keys": ["A"] },
        { "time": 2.0, "keys": ["C"] },
        { "time": 3.0, "keys": ["E"] },
        { "time": 4.0, "keys": ["A", "C", "E"] }, # Acorde
        { "time": 5.0, "keys": ["G"] },
        { "time": 5.5, "keys": ["G"] },
        { "time": 6.0, "keys": ["A"] },
    ]

    def run(self, frame_left, frame_right, virtual_keyboard, synth):
        # 1. Dibujar Header y Linea de meta
        frame_left = self.draw_header(frame_left)
        h, w = frame_left.shape[:2]
        target_y = h - 100
        
        # Dibujar la línea donde deben tocar
        cv2.line(frame_left, (50, target_y), (w-50, target_y), (0, 255, 255), 2)
        cv2.putText(frame_left, "HIT HERE", (50, target_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)

        # 2. Calcular tiempo
        current_time = time.time() - self.start_time

        # 3. Lógica de notas cayendo
        for note in self.chart:
            time_diff = note["time"] - current_time
            
            # Si la nota está en rango visible (entre 3s antes y 0.2s después)
            if -0.2 < time_diff < 3.0:
                # Matemáticas de caída: 
                # Si time_diff es 3.0 (lejos), y_pos es pequeña (arriba).
                # Si time_diff es 0 (ahora), y_pos es target_y.
                pixels_per_second = 150 * self.scroll_speed
                y_pos = int(target_y - (time_diff * pixels_per_second))

                if 0 < y_pos < h:
                    # Dibujar nota
                    cv2.circle(frame_left, (w//2, y_pos), 25, (50, 100, 255), -1)
                    cv2.circle(frame_left, (w//2, y_pos), 25, (255, 255, 255), 2)
                    
                    # Texto de la tecla dentro de la nota
                    txt = "+".join(note["keys"])
                    cv2.putText(frame_left, txt, (w//2 - 10, y_pos + 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 4. Chequear fin de canción
        if current_time > self.chart[-1]["time"] + 2:
            self.running = False

        return frame_left, frame_right, self.running
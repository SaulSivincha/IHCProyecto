from src.songs.song_base import BaseSong
import cv2
import time

class TutorialSong(BaseSong):
    name = "Tutorial Básico"
    bpm = 100
    difficulty = "Básico"
    music_key = "C"
    
    # Definimos cuando caen las notas
    chart = [
        { "time": 2.0, "keys": ["C"] },
        { "time": 3.0, "keys": ["D"] },
        { "time": 4.0, "keys": ["E"] },
        { "time": 5.0, "keys": ["C", "E"] }, # Acorde
    ]

    def run(self, frame_left, frame_right, virtual_keyboard, synth):
        # 1. Header y Linea de Meta
        frame_left = self.draw_header(frame_left)
        h, w = frame_left.shape[:2]
        target_y = h - 100
        cv2.line(frame_left, (50, target_y), (w-50, target_y), (0, 255, 255), 2)

        # 2. Calcular tiempo
        current_time = time.time() - self.start_time
        
        # 3. Dibujar notas cayendo (Lógica visual simple)
        for note in self.chart:
            diff = note["time"] - current_time
            
            # Si la nota está cerca (entre 3 seg antes y 0.5 seg después)
            if -0.5 < diff < 3.0:
                # Calculamos posición Y (mientras más cerca a 0, más cerca a target_y)
                y_pos = int(target_y - (diff * 150)) 
                
                if 0 < y_pos < h:
                    # Dibujamos un círculo representando la nota
                    cv2.circle(frame_left, (w//2, y_pos), 25, (0, 255, 0), -1)
                    # Ponemos qué tecla es
                    label = "+".join(note["keys"])
                    cv2.putText(frame_left, label, (w//2 - 10, y_pos+5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)

        # 4. Verificar condición de salida (si pasó el tiempo de la última nota)
        last_note_time = self.chart[-1]["time"]
        if current_time > last_note_time + 3:
            print("Canción terminada")
            self.running = False

        return frame_left, frame_right, self.running
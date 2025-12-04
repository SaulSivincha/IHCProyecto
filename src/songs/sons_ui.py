import cv2
import numpy as np

class SongsUI:
    """Interfaz para seleccionar canciones"""
    
    def __init__(self, frame_width, frame_height):
        self.w = frame_width
        self.h = frame_height
        self.selected_index = 0
        self.scroll_offset = 0
        self.max_visible = 7

    def draw_song_menu(self, frame, songs_dict):
        # Convertimos dict a lista para poder usar índices
        songs_list = list(songs_dict.values())
        h, w = frame.shape[:2]

        # 1. Fondo (Tono Azulado/Purpura para diferenciar de Teoría)
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        overlay[:] = (40, 30, 60) 
        cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)

        # 2. Título
        cv2.putText(frame, "MODO RITMO - Selecciona Pista", (w//2 - 250, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # 3. Lista de canciones
        y_start = 120
        item_h = 50
        
        # Calcular límites de scroll
        start = self.scroll_offset
        end = min(start + self.max_visible, len(songs_list))

        for i in range(start, end):
            song = songs_list[i]
            y = y_start + (i - start) * item_h
            
            # Colores si está seleccionado
            if i == self.selected_index:
                color_bg = (150, 100, 200) # Morado claro
                thickness = 2
            else:
                color_bg = (60, 50, 80)    # Oscuro
                thickness = 1

            # Dibujar caja
            cv2.rectangle(frame, (100, y), (w-100, y+40), color_bg, -1)
            cv2.rectangle(frame, (100, y), (w-100, y+40), (200, 200, 200), thickness)
            
            # Texto
            text = f"{i+1}. {song.name}  [{song.bpm} BPM]"
            cv2.putText(frame, text, (120, y+28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
            
            # Dificultad a la derecha
            cv2.putText(frame, song.difficulty, (w-250, y+28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,255,200), 1)

        # 4. Instrucciones abajo
        cv2.putText(frame, "W/S: Navegar | ENTER: Jugar | Q: Volver", (100, h-50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        return frame

    def navigate(self, direction, total_songs):
        new_idx = self.selected_index + direction
        if 0 <= new_idx < total_songs:
            self.selected_index = new_idx
            # Ajustar scroll
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1

    def get_selected(self, songs_dict):
        l = list(songs_dict.values())
        if 0 <= self.selected_index < len(l):
            return l[self.selected_index]
        return None
    
    def get_selected_index(self):
        return self.selected_index
    
    def reset_selection(self):
        """Reinicia la selección al primer índice y scroll"""
        self.selected_index = 0
        self.scroll_offset = 0
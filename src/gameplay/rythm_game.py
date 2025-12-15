"""
Rhythm Game - Piano Virtual
Diseño visual mejorado y coherente con la interfaz principal
"""

import cv2
import numpy as np
import time
from src.vision.stereo_config import StereoConfig


# ============================================================
# PALETA DE COLORES - Coherente con la interfaz principal
# ============================================================
class Colors:
    # Fondo y paneles
    PANEL_BG = (25, 25, 30)
    PANEL_BORDER = (255, 200, 0)  # Dorado/Cian
    
    # Notas y zona de acierto
    NOTE_FILL = (255, 200, 0)      # Cian brillante
    NOTE_BORDER = (255, 255, 255)  # Blanco
    HIT_ZONE = (200, 150, 0)       # Cian oscuro
    PERFECT_LINE = (0, 255, 255)   # Amarillo
    
    # Calificaciones
    PERFECT = (0, 255, 150)        # Verde menta
    GOOD = (0, 200, 255)           # Naranja/Amarillo
    MISS = (80, 80, 255)           # Rojo suave
    
    # Texto
    WHITE = (255, 255, 255)
    GOLD = (0, 215, 255)           # Dorado
    CYAN = (255, 200, 0)           # Cian
    
    # Combo
    COMBO_LOW = (255, 200, 0)      # Cian
    COMBO_HIGH = (200, 100, 255)   # Magenta


class Song:
    """Representa una cancion del juego de ritmo"""
    def __init__(self, title, chart, difficulty, bpm):
        self.title = title
        self.chart = chart
        self.difficulty = difficulty
        self.bpm = bpm


class Note:
    """Representa una nota que cae"""
    def __init__(self, key_number, spawn_time, hit_time):
        self.key = key_number
        self.spawn_time = spawn_time
        self.hit_time = hit_time
        self.y_pos = 0
        self.hit = False
        self.missed = False


class HitFeedback:
    """Feedback visual cuando se acierta una nota"""
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.spawn_time = time.time()
        self.duration = 0.5  # segundos
        self.scale = 1.5
    
    def is_alive(self):
        return (time.time() - self.spawn_time) < self.duration
    
    def get_alpha(self):
        elapsed = time.time() - self.spawn_time
        return max(0, 1 - (elapsed / self.duration))
    
    def get_y_offset(self):
        elapsed = time.time() - self.spawn_time
        return int(-30 * (elapsed / self.duration))


class RhythmGame:
    """Logica del juego de ritmo con visual mejorado"""
    
    def __init__(self, num_keys=24):
        self.num_keys = num_keys
        self.notes = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect_count = 0
        self.good_count = 0
        self.miss_count = 0
        
        # Visual feedback
        self.feedbacks = []
        self.last_hit_result = None
        self.last_hit_time = 0
        
        # Configuracion
        self.note_speed = StereoConfig.NOTE_SPEED
        self.hit_zone_y = StereoConfig.HIT_ZONE_Y
        self.hit_zone_height = StereoConfig.HIT_ZONE_HEIGHT
        self.perfect_window = StereoConfig.PERFECT_WINDOW
        self.good_window = StereoConfig.GOOD_WINDOW
        
        # Control
        self.start_time = None
        self.is_playing = False
        self.game_finished = False
        self.show_results = False
        self.song_title = ""
        
    def start_game(self, song_chart):
        """Inicia el juego con una cancion"""
        self.start_time = time.time()
        self.is_playing = True
        self.game_finished = False
        self.show_results = False
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect_count = 0
        self.good_count = 0
        self.miss_count = 0
        self.notes = []
        self.feedbacks = []
        
        if isinstance(song_chart, Song):
            chart = song_chart.chart
            self.song_title = song_chart.title
        else:
            chart = song_chart
            self.song_title = "Cancion"
        
        for item in chart:
            if len(item) == 3:
                key, hit_time, duration = item
            else:
                key, hit_time = item
            
            travel_time = self.hit_zone_y / self.note_speed
            spawn_time = hit_time - travel_time
            self.notes.append(Note(key, spawn_time, hit_time))
    
    def stop_game(self):
        """Detiene el juego"""
        self.is_playing = False
        
    def is_game_finished(self):
        """Verifica si el juego termino"""
        if not self.is_playing:
            return self.game_finished
        
        current_time = time.time() - self.start_time
        
        for note in self.notes:
            if not note.hit and not note.missed:
                if current_time < note.hit_time + self.good_window * 2:
                    return False
        
        self.game_finished = True
        self.show_results = True
        return True
    
    def get_final_score(self):
        """Retorna estadisticas finales"""
        total_notes = len(self.notes)
        total_hit = self.perfect_count + self.good_count
        accuracy = (total_hit / total_notes * 100) if total_notes > 0 else 0
        
        return {
            'score': self.score,
            'combo': self.max_combo,
            'perfect': self.perfect_count,
            'good': self.good_count,
            'miss': self.miss_count,
            'total_notes': total_notes,
            'total_hit': total_hit,
            'accuracy': accuracy
        }
            
    def update(self):
        """Actualiza posiciones de notas"""
        if not self.is_playing:
            return
            
        current_time = time.time() - self.start_time
        
        for note in self.notes:
            if not note.hit and not note.missed:
                time_since_spawn = current_time - note.spawn_time
                if time_since_spawn < 0:
                    continue
                    
                note.y_pos = int(time_since_spawn * self.note_speed)
                
                if current_time > note.hit_time + self.good_window * 1.5:
                    note.missed = True
                    self.miss_count += 1
                    self.combo = 0
                    self.last_hit_result = "MISS"
                    self.last_hit_time = time.time()
                    
    def check_hit(self, key_pressed, keyboard_x0=0, key_width=50):
        """Verifica acierto de tecla"""
        if not self.is_playing:
            return None
            
        current_time = time.time() - self.start_time
        
        best_note = None
        best_diff = float('inf')
        
        for note in self.notes:
            if note.key == key_pressed and not note.hit and not note.missed:
                time_to_hit = note.hit_time - current_time
                
                if -self.good_window <= time_to_hit <= self.good_window:
                    time_diff = abs(time_to_hit)
                    
                    if time_diff < best_diff:
                        best_diff = time_diff
                        best_note = note
                    
        if best_note:
            best_note.hit = True
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            
            # Calcular posicion para feedback
            note_x = int(keyboard_x0 + best_note.key * key_width + key_width // 2)
            note_y = self.hit_zone_y
            
            if best_diff <= self.perfect_window:
                self.score += 100 * self.combo
                self.perfect_count += 1
                self.last_hit_result = "PERFECT"
                self.feedbacks.append(HitFeedback(note_x, note_y, "PERFECT", Colors.PERFECT))
            else:
                self.score += 50 * self.combo
                self.good_count += 1
                self.last_hit_result = "GOOD"
                self.feedbacks.append(HitFeedback(note_x, note_y, "GOOD", Colors.GOOD))
            
            self.last_hit_time = time.time()
            return self.last_hit_result
            
        return None
        
    def draw(self, frame, keyboard_x0, keyboard_x1, key_width):
        """Dibuja el juego con diseno mejorado"""
        has_notes = len(self.notes) > 0
        
        if not self.is_playing and not has_notes and not self.show_results:
            return frame
        
        keyboard_x0 = int(keyboard_x0)
        keyboard_x1 = int(keyboard_x1)
        frame_h, frame_w = frame.shape[:2]
        
        # Lineas de carril (sutiles)
        for i in range(self.num_keys + 1):
            x = int(keyboard_x0 + i * key_width)
            if keyboard_x0 <= x <= keyboard_x1:
                cv2.line(frame, (x, 0), (x, self.hit_zone_y + self.hit_zone_height), 
                        (40, 40, 50), 1)
        
        # Zona de acierto con gradiente
        for i in range(self.hit_zone_height):
            alpha = 0.15 + 0.1 * (i / self.hit_zone_height)
            y = self.hit_zone_y + i
            color = tuple(int(c * alpha) for c in Colors.HIT_ZONE)
            cv2.line(frame, (keyboard_x0, y), (keyboard_x1, y), color, 1)
        
        # Borde de zona de acierto
        cv2.rectangle(frame, 
                     (keyboard_x0, self.hit_zone_y),
                     (keyboard_x1, self.hit_zone_y + self.hit_zone_height),
                     Colors.CYAN, 2)
        
        # Linea de timing perfecto
        perfect_y = self.hit_zone_y + self.hit_zone_height // 2
        cv2.line(frame, (keyboard_x0, perfect_y), (keyboard_x1, perfect_y),
                Colors.PERFECT_LINE, 3)
        
        # Dibujar notas
        for note in self.notes:
            if not note.hit and not note.missed and 0 <= note.y_pos <= self.hit_zone_y + 100:
                self._draw_note(frame, note, keyboard_x0, key_width)
        
        # Dibujar feedbacks flotantes
        self._draw_feedbacks(frame)
        
        # Paneles de UI
        self._draw_score_panel(frame)
        self._draw_stats_panel(frame)
        
        # Indicador de ultimo acierto (grande en el centro)
        self._draw_hit_indicator(frame)
        
        # Pantalla de resultados
        if self.show_results:
            self._draw_results_screen(frame)
        
        return frame
    
    def _draw_note(self, frame, note, keyboard_x0, key_width):
        """Dibuja una nota individual con estilo"""
        x0 = int(keyboard_x0 + note.key * key_width + 3)
        x1 = int(keyboard_x0 + (note.key + 1) * key_width - 3)
        y0 = note.y_pos
        y1 = note.y_pos + 22
        
        # Relleno de nota
        cv2.rectangle(frame, (x0, y0), (x1, y1), Colors.NOTE_FILL, -1)
        
        # Brillo superior
        cv2.line(frame, (x0 + 2, y0 + 2), (x1 - 2, y0 + 2), (255, 255, 200), 1)
        
        # Borde
        cv2.rectangle(frame, (x0, y0), (x1, y1), Colors.NOTE_BORDER, 1)
    
    def _draw_feedbacks(self, frame):
        """Dibuja los mensajes flotantes de PERFECT/GOOD"""
        alive_feedbacks = []
        
        for fb in self.feedbacks:
            if fb.is_alive():
                alive_feedbacks.append(fb)
                
                alpha = fb.get_alpha()
                y_offset = fb.get_y_offset()
                
                # Texto con sombra
                text = fb.text
                pos = (fb.x - 40, fb.y + y_offset)
                
                # Escala basada en tiempo
                scale = 0.7 + 0.3 * alpha
                
                cv2.putText(frame, text, (pos[0] + 2, pos[1] + 2),
                           cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3)
                cv2.putText(frame, text, pos,
                           cv2.FONT_HERSHEY_SIMPLEX, scale, fb.color, 2)
        
        self.feedbacks = alive_feedbacks
    
    def _draw_hit_indicator(self, frame):
        """Muestra PERFECT/GOOD/MISS grande en el centro"""
        if time.time() - self.last_hit_time > 0.4:
            return
        
        frame_h, frame_w = frame.shape[:2]
        center_x = frame_w // 2
        center_y = frame_h // 3
        
        elapsed = time.time() - self.last_hit_time
        alpha = 1 - (elapsed / 0.4)
        scale = 1.5 + 0.5 * (1 - alpha)
        
        if self.last_hit_result == "PERFECT":
            color = Colors.PERFECT
            text = "PERFECT!"
        elif self.last_hit_result == "GOOD":
            color = Colors.GOOD
            text = "GOOD!"
        else:
            color = Colors.MISS
            text = "MISS"
        
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 3)
        x = center_x - tw // 2
        y = center_y
        
        # Sombra
        cv2.putText(frame, text, (x + 3, y + 3),
                   cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 5)
        cv2.putText(frame, text, (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, scale, color, 3)
    
    def _draw_score_panel(self, frame):
        """Panel de puntaje (izquierda)"""
        x, y = 15, 15
        w, h = 200, 130
        
        # Fondo
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), Colors.PANEL_BG, -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Borde
        cv2.rectangle(frame, (x, y), (x + w, y + h), Colors.CYAN, 2)
        
        # Titulo
        cv2.putText(frame, "PUNTAJE", (x + 15, y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Colors.WHITE, 1)
        
        # Score
        score_text = f"{self.score:,}"
        cv2.putText(frame, score_text, (x + 17, y + 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)
        cv2.putText(frame, score_text, (x + 15, y + 63),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, Colors.GOLD, 2)
        
        # Combo
        cv2.putText(frame, "COMBO", (x + 15, y + 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, Colors.WHITE, 1)
        
        combo_color = Colors.COMBO_HIGH if self.combo >= 10 else Colors.COMBO_LOW
        combo_text = f"{self.combo}x"
        cv2.putText(frame, combo_text, (x + 17, y + 118),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3)
        cv2.putText(frame, combo_text, (x + 15, y + 116),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, combo_color, 2)
    
    def _draw_stats_panel(self, frame):
        """Panel de estadisticas (derecha)"""
        frame_h, frame_w = frame.shape[:2]
        w, h = 180, 180
        x = frame_w - w - 15
        y = 15
        
        # Fondo
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), Colors.PANEL_BG, -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Borde
        cv2.rectangle(frame, (x, y), (x + w, y + h), Colors.CYAN, 2)
        
        # Titulo
        cv2.putText(frame, "STATS", (x + 15, y + 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Colors.WHITE, 1)
        
        # Perfect
        cv2.circle(frame, (x + 20, y + 55), 8, Colors.PERFECT, -1)
        cv2.putText(frame, f"PERFECT: {self.perfect_count}", (x + 35, y + 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, Colors.PERFECT, 1)
        
        # Good
        cv2.circle(frame, (x + 20, y + 85), 8, Colors.GOOD, -1)
        cv2.putText(frame, f"GOOD: {self.good_count}", (x + 35, y + 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, Colors.GOOD, 1)
        
        # Miss
        cv2.circle(frame, (x + 20, y + 115), 8, Colors.MISS, -1)
        cv2.putText(frame, f"MISS: {self.miss_count}", (x + 35, y + 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, Colors.MISS, 1)
        
        # Precision
        total = len(self.notes)
        hits = self.perfect_count + self.good_count
        acc = (hits / total * 100) if total > 0 else 0
        
        if acc >= 90:
            acc_color = Colors.PERFECT
        elif acc >= 70:
            acc_color = Colors.GOOD
        else:
            acc_color = Colors.MISS
        
        cv2.line(frame, (x + 15, y + 140), (x + w - 15, y + 140), (60, 60, 80), 1)
        cv2.putText(frame, f"PRECISION: {acc:.1f}%", (x + 15, y + 165),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, acc_color, 1)
    
    def _draw_results_screen(self, frame):
        """Pantalla de resultados al finalizar"""
        frame_h, frame_w = frame.shape[:2]
        
        # Overlay oscuro
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_w, frame_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Panel central
        panel_w, panel_h = 500, 400
        px = (frame_w - panel_w) // 2
        py = (frame_h - panel_h) // 2
        
        cv2.rectangle(frame, (px, py), (px + panel_w, py + panel_h), Colors.PANEL_BG, -1)
        cv2.rectangle(frame, (px, py), (px + panel_w, py + panel_h), Colors.GOLD, 3)
        
        # Titulo
        cv2.putText(frame, "RESULTADOS", (px + 150, py + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, Colors.GOLD, 2)
        
        # Estadisticas
        stats = self.get_final_score()
        y_off = py + 100
        
        cv2.putText(frame, f"Puntaje Final: {stats['score']:,}", (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, Colors.WHITE, 2)
        y_off += 40
        
        cv2.putText(frame, f"Max Combo: {stats['combo']}x", (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, Colors.COMBO_HIGH, 1)
        y_off += 35
        
        cv2.putText(frame, f"PERFECT: {stats['perfect']}", (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Colors.PERFECT, 1)
        y_off += 30
        
        cv2.putText(frame, f"GOOD: {stats['good']}", (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Colors.GOOD, 1)
        y_off += 30
        
        cv2.putText(frame, f"MISS: {stats['miss']}", (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Colors.MISS, 1)
        y_off += 40
        
        # Precision con calificacion
        acc = stats['accuracy']
        if acc >= 95:
            grade = "S"
            grade_color = Colors.GOLD
        elif acc >= 90:
            grade = "A"
            grade_color = Colors.PERFECT
        elif acc >= 80:
            grade = "B"
            grade_color = Colors.GOOD
        elif acc >= 70:
            grade = "C"
            grade_color = Colors.GOOD
        else:
            grade = "D"
            grade_color = Colors.MISS
        
        cv2.putText(frame, f"Precision: {acc:.1f}%", (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, Colors.WHITE, 2)
        
        # Calificacion grande
        cv2.putText(frame, grade, (px + 350, py + 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 4.0, (0, 0, 0), 8)
        cv2.putText(frame, grade, (px + 347, py + 197),
                   cv2.FONT_HERSHEY_SIMPLEX, 4.0, grade_color, 5)
        
        # Opciones
        y_off = py + panel_h - 70
        cv2.putText(frame, "[R] Reintentar    [S] Canciones    [ESC] Menu", 
                   (px + 50, y_off),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, Colors.CYAN, 1)
    
    def handle_results_input(self, key):
        """Maneja input en pantalla de resultados
        Retorna: 'retry', 'songs', 'menu', o None
        """
        if not self.show_results:
            return None
        
        if key == ord('r') or key == ord('R'):
            return 'retry'
        elif key == ord('s') or key == ord('S'):
            return 'songs'
        elif key == 27:  # ESC
            return 'menu'
        
        return None

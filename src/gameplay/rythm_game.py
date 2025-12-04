"""
Rhythm Game
"""

import cv2
import numpy as np
import time
from src.vision.stereo_config import StereoConfig

class Song:
    """Representa una canción del juego de ritmo"""
    def __init__(self, title, chart, difficulty, bpm):
        self.title = title
        self.chart = chart  # Lista de tuplas (key, time, duration)
        self.difficulty = difficulty
        self.bpm = bpm
        
class Note:
    """Representa una nota que cae"""
    def __init__(self, key_number, spawn_time, hit_time):
        self.key = key_number  # Tecla 0-23
        self.spawn_time = spawn_time  # Cuándo aparece
        self.hit_time = hit_time  # Cuándo debe presionarse
        self.y_pos = 0  # Posición vertical
        self.hit = False  # Si fue presionada
        self.missed = False  # Si se perdió
        
class RhythmGame:
    """Lógica del juego de ritmo"""
    
    def __init__(self, num_keys=24):
        self.num_keys = num_keys
        self.notes = []  # Lista de notas activas
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect_count = 0
        self.good_count = 0
        self.miss_count = 0
    
        # Configuración visual desde StereoConfig
        self.note_speed = StereoConfig.NOTE_SPEED
        self.hit_zone_y = StereoConfig.HIT_ZONE_Y
        self.hit_zone_height = StereoConfig.HIT_ZONE_HEIGHT
        
        # Ventanas de tiempo desde StereoConfig
        self.perfect_window = StereoConfig.PERFECT_WINDOW
        self.good_window = StereoConfig.GOOD_WINDOW
        
        # Control de tiempo
        self.start_time = None
        self.is_playing = False
        
    def start_game(self, song_chart):
        """
        Inicia el juego con una canción
        song_chart: objeto Song o lista de tuplas (tecla, tiempo_en_segundos)
        """
        self.start_time = time.time()
        self.is_playing = True
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect_count = 0
        self.good_count = 0
        self.miss_count = 0
        self.notes = []
        
        # Extraer chart de Song object si es necesario
        if isinstance(song_chart, Song):
            chart = song_chart.chart
        else:
            chart = song_chart
        
        # Crear notas desde el chart
        for item in chart:
            if len(item) == 3:  # (key, time, duration)
                key, hit_time, duration = item
            else:  # (key, time)
                key, hit_time = item
            
            # Calcular cuándo debe aparecer la nota
            travel_time = self.hit_zone_y / self.note_speed
            spawn_time = hit_time - travel_time
            self.notes.append(Note(key, spawn_time, hit_time))
    
    def stop_game(self):
        """Detiene el juego de ritmo"""
        self.is_playing = False
        
    def is_game_finished(self):
        """
        Verifica si el juego ha terminado (todas las notas procesadas)
        """
        if not self.is_playing:
            return False
        
        current_time = time.time() - self.start_time
        
        # Verificar si todas las notas han sido procesadas (hit o missed)
        for note in self.notes:
            if not note.hit and not note.missed:
                # Si la nota aún no ha pasado su tiempo de hit + margen, el juego continúa
                if current_time < note.hit_time + self.good_window * 2:
                    return False
        
        # Todas las notas han sido procesadas
        return True
    
    def get_final_score(self):
        """Retorna el score final y estadísticas completas"""
        total_notes = len(self.notes)
        total_hit = self.perfect_count + self.good_count
        total_miss = self.miss_count
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
        """Actualiza la posición de las notas"""
        if not self.is_playing:
            return
            
        current_time = time.time() - self.start_time
        
        # Actualizar posición de cada nota
        for note in self.notes:
            if not note.hit and not note.missed:
                # Calcular posición basada en tiempo
                time_since_spawn = current_time - note.spawn_time
                if time_since_spawn < 0:
                    continue  # Saltar notas que aún no deben aparecer
                    
                note.y_pos = int(time_since_spawn * self.note_speed)
                
                # Verificar si se pasó la nota
                if current_time > note.hit_time + self.good_window * 1.5:
                    note.missed = True
                    self.miss_count += 1
                    self.combo = 0
                    
    def check_hit(self, key_pressed):
        """
        Verifica si se presionó la tecla correcta en el momento correcto
        key_pressed: número de tecla (0-23)
        """
        if not self.is_playing:
            return None
            
        current_time = time.time() - self.start_time
        
        # Buscar la nota más cercana en esa tecla
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
            
            # Determinar calificación
            if best_diff <= self.perfect_window:
                self.score += 100 * self.combo
                self.perfect_count += 1
                return "PERFECT"
            elif best_diff <= self.good_window:
                self.score += 50 * self.combo
                self.good_count += 1
                return "GOOD"
            
        return None
        
    def draw(self, frame, keyboard_x0, keyboard_x1, key_width):
        """
        Dibuja las notas cayendo y la zona de acierto con diseño profesional
        Siempre dibuja las estadísticas si hay notas (incluso si el juego terminó)
        """
        # Siempre dibujar UI si hay notas, incluso si el juego terminó
        has_notes = len(self.notes) > 0
        
        if not self.is_playing and not has_notes:
            return frame
        
        keyboard_x0 = int(keyboard_x0)
        keyboard_x1 = int(keyboard_x1)
        
        # Color palette - Professional theme (sin overlay oscuro para mejor detección)
        HIT_ZONE_PRIMARY = (0, 200, 100)
        HIT_ZONE_SECONDARY = (0, 255, 150)
        NOTE_COLOR = (0, 200, 255)
        NOTE_GLOW = (100, 230, 255)
        LANE_DIVIDER = (60, 60, 80)
        
        # NO oscurecer la interfaz para mejor detección de dedos
        
        # Dibujar líneas de separación con estilo profesional
        for i in range(self.num_keys + 1):
            x = int(keyboard_x0 + i * key_width)
            if keyboard_x0 <= x <= keyboard_x1:
                cv2.line(frame, (x, 0), (x, self.hit_zone_y + self.hit_zone_height), 
                        LANE_DIVIDER, 1)
        
        # Dibujar zona de acierto con gradiente
        hit_zone_overlay = frame.copy()
        for i in range(self.hit_zone_height):
            ratio = i / self.hit_zone_height
            color = tuple(int(HIT_ZONE_PRIMARY[j] + (HIT_ZONE_SECONDARY[j] - HIT_ZONE_PRIMARY[j]) * ratio) 
                         for j in range(3))
            cv2.line(hit_zone_overlay, 
                    (keyboard_x0, self.hit_zone_y + i),
                    (keyboard_x1, self.hit_zone_y + i),
                    color, 1)
        frame = cv2.addWeighted(frame, 0.7, hit_zone_overlay, 0.3, 0)
        
        # Borde de zona de acierto
        cv2.rectangle(frame, 
                     (keyboard_x0, self.hit_zone_y),
                     (keyboard_x1, self.hit_zone_y + self.hit_zone_height),
                     HIT_ZONE_SECONDARY, 3)
        
        # Línea central de timing perfecto
        perfect_line_y = self.hit_zone_y + self.hit_zone_height // 2
        cv2.line(frame, (keyboard_x0, perfect_line_y), (keyboard_x1, perfect_line_y),
                (255, 255, 0), 2)
        
        # Dibujar notas con efecto de glow
        for note in self.notes:
            if not note.hit and not note.missed and 0 <= note.y_pos <= self.hit_zone_y + 100:
                note_x0 = int(keyboard_x0 + note.key * key_width + 5)
                note_x1 = int(keyboard_x0 + (note.key + 1) * key_width - 5)
                note_y0 = note.y_pos
                note_y1 = note.y_pos + 30
                
                if note_x0 >= keyboard_x0 and note_x1 <= keyboard_x1:
                    # Calcular distancia a la zona de hit para efecto glow
                    distance_to_hit = abs(note_y0 - perfect_line_y)
                    
                    # Efecto glow cuando se acerca a la zona de hit
                    if distance_to_hit < 80:
                        glow_intensity = 1.0 - (distance_to_hit / 80)
                        glow_overlay = frame.copy()
                        cv2.rectangle(glow_overlay, 
                                    (note_x0 - 3, note_y0 - 3), 
                                    (note_x1 + 3, note_y1 + 3), 
                                    NOTE_GLOW, -1)
                        frame = cv2.addWeighted(frame, 1.0, glow_overlay, 
                                              glow_intensity * 0.4, 0)
                    
                    # Nota principal
                    note_overlay = frame.copy()
                    cv2.rectangle(note_overlay, (note_x0, note_y0), 
                                (note_x1, note_y1), NOTE_COLOR, -1)
                    frame = cv2.addWeighted(frame, 0.7, note_overlay, 0.3, 0)
                    
                    # Borde brillante
                    cv2.rectangle(frame, (note_x0, note_y0), 
                                (note_x1, note_y1), (255, 255, 255), 2)
        
        # SIEMPRE dibujar UI profesional (incluso si el juego terminó, para mostrar estadísticas finales)
            self.notes.append(Note(key, spawn_time, hit_time))
    
    def stop_game(self):
        """Detiene el juego de ritmo"""
        self.is_playing = False
        
    def is_game_finished(self):
        """
        Verifica si el juego ha terminado (todas las notas procesadas)
        """
        if not self.is_playing:
            return False
        
        current_time = time.time() - self.start_time
        
        # Verificar si todas las notas han sido procesadas (hit o missed)
        for note in self.notes:
            if not note.hit and not note.missed:
                # Si la nota aún no ha pasado su tiempo de hit + margen, el juego continúa
                if current_time < note.hit_time + self.good_window * 2:
                    return False
        
        # Todas las notas han sido procesadas
        return True
    
    def get_final_score(self):
        """Retorna el score final y estadísticas completas"""
        total_notes = len(self.notes)
        total_hit = self.perfect_count + self.good_count
        total_miss = self.miss_count
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
        """Actualiza la posición de las notas"""
        if not self.is_playing:
            return
            
        current_time = time.time() - self.start_time
        
        # Actualizar posición de cada nota
        for note in self.notes:
            if not note.hit and not note.missed:
                # Calcular posición basada en tiempo
                time_since_spawn = current_time - note.spawn_time
                if time_since_spawn < 0:
                    continue  # Saltar notas que aún no deben aparecer
                    
                note.y_pos = int(time_since_spawn * self.note_speed)
                
                # Verificar si se pasó la nota
                if current_time > note.hit_time + self.good_window * 1.5:
                    note.missed = True
                    self.miss_count += 1
                    self.combo = 0
                    
    def check_hit(self, key_pressed):
        """
        Verifica si se presionó la tecla correcta en el momento correcto
        key_pressed: número de tecla (0-23)
        """
        if not self.is_playing:
            return None
            
        current_time = time.time() - self.start_time
        
        # Buscar la nota más cercana en esa tecla
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
            
            # Determinar calificación
            if best_diff <= self.perfect_window:
                self.score += 100 * self.combo
                self.perfect_count += 1
                return "PERFECT"
            elif best_diff <= self.good_window:
                self.score += 50 * self.combo
                self.good_count += 1
                return "GOOD"
            
        return None
        
    def draw(self, frame, keyboard_x0, keyboard_x1, key_width):
        """
        Dibuja las notas cayendo y la zona de acierto con diseño profesional
        Siempre dibuja las estadísticas si hay notas (incluso si el juego terminó)
        """
        # Siempre dibujar UI si hay notas, incluso si el juego terminó
        has_notes = len(self.notes) > 0
        
        if not self.is_playing and not has_notes:
            return frame
        
        keyboard_x0 = int(keyboard_x0)
        keyboard_x1 = int(keyboard_x1)
        
        # Color palette - Professional theme (sin overlay oscuro para mejor detección)
        HIT_ZONE_PRIMARY = (0, 200, 100)
        HIT_ZONE_SECONDARY = (0, 255, 150)
        NOTE_COLOR = (0, 200, 255)
        NOTE_GLOW = (100, 230, 255)
        LANE_DIVIDER = (60, 60, 80)
        
        # NO oscurecer la interfaz para mejor detección de dedos
        
        # Dibujar líneas de separación con estilo profesional
        for i in range(self.num_keys + 1):
            x = int(keyboard_x0 + i * key_width)
            if keyboard_x0 <= x <= keyboard_x1:
                cv2.line(frame, (x, 0), (x, self.hit_zone_y + self.hit_zone_height), 
                        LANE_DIVIDER, 1)
        
        # Dibujar zona de acierto con gradiente
        hit_zone_overlay = frame.copy()
        for i in range(self.hit_zone_height):
            ratio = i / self.hit_zone_height
            color = tuple(int(HIT_ZONE_PRIMARY[j] + (HIT_ZONE_SECONDARY[j] - HIT_ZONE_PRIMARY[j]) * ratio) 
                         for j in range(3))
            cv2.line(hit_zone_overlay, 
                    (keyboard_x0, self.hit_zone_y + i),
                    (keyboard_x1, self.hit_zone_y + i),
                    color, 1)
        frame = cv2.addWeighted(frame, 0.7, hit_zone_overlay, 0.3, 0)
        
        # Borde de zona de acierto
        cv2.rectangle(frame, 
                     (keyboard_x0, self.hit_zone_y),
                     (keyboard_x1, self.hit_zone_y + self.hit_zone_height),
                     HIT_ZONE_SECONDARY, 3)
        
        # Línea central de timing perfecto
        perfect_line_y = self.hit_zone_y + self.hit_zone_height // 2
        cv2.line(frame, (keyboard_x0, perfect_line_y), (keyboard_x1, perfect_line_y),
                (255, 255, 0), 2)
        
        # Dibujar notas con efecto de glow
        for note in self.notes:
            if not note.hit and not note.missed and 0 <= note.y_pos <= self.hit_zone_y + 100:
                note_x0 = int(keyboard_x0 + note.key * key_width + 5)
                note_x1 = int(keyboard_x0 + (note.key + 1) * key_width - 5)
                note_y0 = note.y_pos
                note_y1 = note.y_pos + 30
                
                if note_x0 >= keyboard_x0 and note_x1 <= keyboard_x1:
                    # Calcular distancia a la zona de hit para efecto glow
                    distance_to_hit = abs(note_y0 - perfect_line_y)
                    
                    # Efecto glow cuando se acerca a la zona de hit
                    if distance_to_hit < 80:
                        glow_intensity = 1.0 - (distance_to_hit / 80)
                        glow_overlay = frame.copy()
                        cv2.rectangle(glow_overlay, 
                                    (note_x0 - 3, note_y0 - 3), 
                                    (note_x1 + 3, note_y1 + 3), 
                                    NOTE_GLOW, -1)
                        frame = cv2.addWeighted(frame, 1.0, glow_overlay, 
                                              glow_intensity * 0.4, 0)
                    
                    # Nota principal
                    note_overlay = frame.copy()
                    cv2.rectangle(note_overlay, (note_x0, note_y0), 
                                (note_x1, note_y1), NOTE_COLOR, -1)
                    frame = cv2.addWeighted(frame, 0.7, note_overlay, 0.3, 0)
                    
                    # Borde brillante
                    cv2.rectangle(frame, (note_x0, note_y0), 
                                (note_x1, note_y1), (255, 255, 255), 2)
        
        # SIEMPRE dibujar UI profesional (incluso si el juego terminó, para mostrar estadísticas finales)
        self.draw_ui(frame)
        return frame
        
    def draw_ui(self, frame):
        """Dibuja UI con diseño profesional y colores unificados - MEJORADO PARA MAYOR VISIBILIDAD"""
        frame_height, frame_width = frame.shape[:2]
        
        # Colores profesionales
        PANEL_BG = (20, 20, 35)  # Más oscuro para mejor contraste
        SCORE_GOLD = (255, 215, 0)
        PERFECT_GREEN = (0, 255, 100)
        GOOD_YELLOW = (255, 255, 0)
        MISS_RED = (255, 50, 50)
        TEXT_WHITE = (255, 255, 255)
        COMBO_PURPLE = (255, 100, 255)
        COMBO_CYAN = (0, 255, 255)
        
        # Panel izquierdo - Score y Combo (MÁS GRANDE Y VISIBLE)
        panel_width = 320
        panel_height = 200
        panel_x = 10
        panel_y = 10
        
        # Fondo del panel con MÁS OPACIDAD para mejor visibilidad
        panel_overlay = frame.copy()
        cv2.rectangle(panel_overlay, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     PANEL_BG, -1)
        frame = cv2.addWeighted(frame, 0.5, panel_overlay, 0.5, 0)  # Más opaco
        
        # Borde del panel MÁS GRUESO
        cv2.rectangle(frame, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     SCORE_GOLD, 3)
        
        # Score con efecto dorado - MÁS GRANDE
        y_offset = panel_y + 50
        score_text = f'{self.score:,}'  # Con separador de miles
        score_label = 'PUNTAJE'
        
        # Label más pequeño
        cv2.putText(frame, score_label, (panel_x + 15, panel_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_WHITE, 2)
        
        # Score MÁS GRANDE con sombra
        cv2.putText(frame, score_text, (panel_x + 17, y_offset + 3),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 4)
        cv2.putText(frame, score_text, (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.3, SCORE_GOLD, 3)
        
        # Combo con escala dinámica - MÁS GRANDE Y LLAMATIVO
        y_offset += 70
        combo_label = 'COMBO'
        cv2.putText(frame, combo_label, (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_WHITE, 2)
        
        y_offset += 40
        combo_scale = min(1.5, 1.0 + (self.combo / 30))  # Escala más grande
        combo_text = f'{self.combo}x'
        combo_color = COMBO_CYAN if self.combo < 10 else COMBO_PURPLE
        
        # Sombra del combo
        cv2.putText(frame, combo_text, (panel_x + 17, y_offset + 3),
                   cv2.FONT_HERSHEY_SIMPLEX, combo_scale, (0, 0, 0), 4)
        cv2.putText(frame, combo_text, (panel_x + 15, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, combo_scale, combo_color, 3)
        
        # Panel derecho - Estadísticas (MÁS GRANDE Y VISIBLE)
        stats_panel_width = 280
        stats_panel_x = frame_width - stats_panel_width - 10
        stats_panel_y = 10
        stats_panel_height = 280
        
        # Fondo del panel de estadísticas MÁS OPACO
        stats_overlay = frame.copy()
        cv2.rectangle(stats_overlay, (stats_panel_x, stats_panel_y),
                     (stats_panel_x + stats_panel_width, stats_panel_y + stats_panel_height),
                     PANEL_BG, -1)
        frame = cv2.addWeighted(frame, 0.5, stats_overlay, 0.5, 0)  # Más opaco
        
        # Borde del panel MÁS GRUESO
        cv2.rectangle(frame, (stats_panel_x, stats_panel_y),
                     (stats_panel_x + stats_panel_width, stats_panel_y + stats_panel_height),
                     (100, 200, 255), 3)
        
        # Título del panel
        y_stat = stats_panel_y + 40
        cv2.putText(frame, 'ESTADISTICAS', (stats_panel_x + 15, y_stat),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, TEXT_WHITE, 2)
        
        y_stat += 50
        
        # Calcular estadísticas en tiempo real
        total_notes = len(self.notes)
        total_hit = self.perfect_count + self.good_count
        accuracy = (total_hit / total_notes * 100) if total_notes > 0 else 0
        
        # Perfect con icono visual MÁS GRANDE
        cv2.circle(frame, (stats_panel_x + 25, y_stat - 12), 10, PERFECT_GREEN, -1)
        cv2.circle(frame, (stats_panel_x + 25, y_stat - 12), 10, (255, 255, 255), 2)
        cv2.putText(frame, f'PERFECT: {self.perfect_count}', 
                   (stats_panel_x + 45, y_stat),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, PERFECT_GREEN, 2)
        
        y_stat += 50
        
        # Good con icono visual MÁS GRANDE
        cv2.circle(frame, (stats_panel_x + 25, y_stat - 12), 10, GOOD_YELLOW, -1)
        cv2.circle(frame, (stats_panel_x + 25, y_stat - 12), 10, (255, 255, 255), 2)
        cv2.putText(frame, f'GOOD: {self.good_count}', 
                   (stats_panel_x + 45, y_stat),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, GOOD_YELLOW, 2)
        
        y_stat += 50
        
        # Miss con icono visual MÁS GRANDE
        cv2.circle(frame, (stats_panel_x + 25, y_stat - 12), 10, MISS_RED, -1)
        cv2.circle(frame, (stats_panel_x + 25, y_stat - 12), 10, (255, 255, 255), 2)
        cv2.putText(frame, f'MISS: {self.miss_count}', 
                   (stats_panel_x + 45, y_stat),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, MISS_RED, 2)
        
        y_stat += 50
        
        # Línea separadora
        cv2.line(frame, (stats_panel_x + 15, y_stat), 
                (stats_panel_x + stats_panel_width - 15, y_stat),
                (100, 100, 150), 2)
        
        y_stat += 40
        
        # Precisión en tiempo real - MÁS GRANDE Y DESTACADA
        if accuracy >= 90:
            acc_color = PERFECT_GREEN
        elif accuracy >= 70:
            acc_color = GOOD_YELLOW
        else:
            acc_color = MISS_RED
        
        acc_text = f'{accuracy:.1f}%'
        cv2.putText(frame, 'PRECISION:', (stats_panel_x + 15, y_stat - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_WHITE, 2)
        cv2.putText(frame, acc_text, (stats_panel_x + 17, y_stat + 2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
        cv2.putText(frame, acc_text, (stats_panel_x + 15, y_stat),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, acc_color, 3)
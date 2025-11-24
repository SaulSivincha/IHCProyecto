#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 27 22:57:59 2021
@author: mherrera
"""

import cv2
import numpy as np
import math
from toolbox import round_half_up

class VirtualKeyboard():
    
    __white_map = {
        0: 0,   # Primera tecla blanca -> nota 0 (Do C4)
        1: 2,   # Segunda tecla blanca -> nota 2 (Re D4)
        2: 4,   # Tercera tecla blanca -> nota 4 (Mi E4)
        3: 5,   # Cuarta tecla blanca -> nota 5 (Fa F4)
        4: 7,   # Quinta tecla blanca -> nota 7 (Sol G4)
        5: 9,   # Sexta tecla blanca -> nota 9 (La A4)
        6: 11,  # Séptima tecla blanca -> nota 11 (Si B4)
        7: 12   # Octava tecla blanca -> nota 12 (Do C5)
    }
    
    __black_map = {
        0: 1,    # Tecla negra entre Do-Re -> nota 1 (Do#/Reb)
        1: 3,    # Tecla negra entre Re-Mi -> nota 3 (Re#/Mib)
        2: None, # No hay tecla negra entre Mi-Fa
        3: 6,    # Tecla negra entre Fa-Sol -> nota 6 (Fa#/Solb)
        4: 8,    # Tecla negra entre Sol-La -> nota 8 (Sol#/Lab)
        5: 10,   # Tecla negra entre La-Si -> nota 10 (La#/Sib)
        6: None, # No hay tecla negra entre Si-Do
        7: None  # No hay tecla negra después del último Do
    }
    
    __keyboard_piano_map = {
        0: 60,   # Do (C4)
        1: 61,   # Do# / Reb (C#4/Db4)
        2: 62,   # Re (D4)
        3: 63,   # Re# / Mib (D#4/Eb4)
        4: 64,   # Mi (E4)
        5: 65,   # Fa (F4)
        6: 66,   # Fa# / Solb (F#4/Gb4)
        7: 67,   # Sol (G4)
        8: 68,   # Sol# / Lab (G#4/Ab4)
        9: 69,   # La (A4)
        10: 70,  # La# / Sib (A#4/Bb4)
        11: 71,  # Si (B4)
        12: 72   # Do (C5)
    }
    
    # Nombres de las notas para las teclas blancas
    __note_names = {
        0: "Do",
        1: "Re",
        2: "Mi",
        3: "Fa",
        4: "Sol",
        5: "La",
        6: "Si",
        7: "Do"
    }
    
    def __init__(self, canvas_w, canvas_h, kb_white_n_keys):
        self.img = None
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        if self.canvas_w == 640 and self.canvas_h == 480:
            self.kb_x0 = int(round_half_up(canvas_w * 0.20))
            self.kb_y0 = int(round_half_up(canvas_h * 0.35))
            self.kb_x1 = int(round_half_up(canvas_w * 0.80))
            self.kb_y1 = int(round_half_up(canvas_h * 0.55))
            
        self.kb_white_n_keys = kb_white_n_keys
        self.kb_len = self.kb_x1 - self.kb_x0
        print('virtual_keyboard:kb_len:{}'.format(self.kb_len))
        self.white_kb_height = self.kb_y1 - self.kb_y0
        print('virtual_keyboard:kb_height:{}'.format(self.white_kb_height))
        self.white_key_width = self.kb_len/kb_white_n_keys
        print('virtual_keyboard:key_width:{}'.format(self.white_key_width))
        self.black_key_width = self.white_key_width*(0.54/0.93)
        print('virtual_keyboard:black_key_width:{}'.format(self.black_key_width))
        self.black_key_heigth = self.white_kb_height * 2/3
        print('virtual_keyboard:black_key_heigth:{}'.format(self.black_key_heigth))
        self.keys_without_black = \
            list({none_keys for none_keys in self.__black_map
                  if self.__black_map[none_keys] is None})
        self.key_id = None
        self.rectangle = []
        self.upper_zone_divisions = []
    
    def new_key(self, key_id, top_left, bottom_rigth):
        self.key_id = key_id
        self.rectangle = [top_left, bottom_rigth]
        return key_id, self.rectangle
    
    def draw_song_guide(self, img):
        """Dibuja un cuadro con una canción fácil para tocar en la esquina superior derecha"""
        # Dimensiones del cuadro
        box_width = 220
        box_height = 140
        margin = 10
        
        # Posición en esquina superior derecha
        box_x = self.canvas_w - box_width - margin
        box_y = margin
        
        # Fondo semi-transparente del cuadro
        overlay = img.copy()
        cv2.rectangle(overlay, 
                     (box_x, box_y), 
                     (box_x + box_width, box_y + box_height),
                     (250, 250, 250), 
                     -1)
        cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
        
        # Borde del cuadro
        cv2.rectangle(img, 
                     (box_x, box_y), 
                     (box_x + box_width, box_y + box_height),
                     (100, 150, 200), 
                     2)
        
        # Título
        title = "Cancion"
        cv2.putText(img, title,
                   (box_x + 10, box_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.5,
                   (50, 50, 150),
                   2)
        
        # Línea separadora
        cv2.line(img, 
                (box_x + 5, box_y + 28), 
                (box_x + box_width - 5, box_y + 28),
                (150, 150, 150), 
                1)
        
        # Canción: "Estrellita dónde estás"
        song_lines = [
            '"Estrellita donde estas"',
            '',
            'Do - Do - Sol - Sol',
            'La - La - Sol',
            'Fa - Fa - Mi - Mi',
            'Re - Re - Do'
        ]
        
        y_offset = box_y + 45
        for i, line in enumerate(song_lines):
            if line == '':  # Línea vacía
                y_offset += 8
                continue
            
            # Determinar tamaño y color según el tipo de línea
            if i == 0:  # Título de la canción
                font_scale = 0.4
                color = (80, 80, 80)
                thickness = 1
            else:  # Notas musicales
                font_scale = 0.45
                color = (0, 0, 0)
                thickness = 1
            
            cv2.putText(img, line,
                       (box_x + 10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       font_scale,
                       color,
                       thickness)
            y_offset += 20

    def draw_virtual_keyboard(self, img):
        # NUEVO: Dibujar guía de canción primero
        self.draw_song_guide(img)
        
        # PASO 1: Dibujar fondo blanco del teclado con transparencia
        shapes = np.zeros_like(img, np.uint8)
        cv2.rectangle(
            img=shapes,
            pt1=(self.kb_x0, self.kb_y0),
            pt2=(self.kb_x1, self.kb_y1),
            color=(255, 255, 255),
            thickness=cv2.FILLED)
        
        alpha = 0.6
        mask = shapes.astype(bool)
        img[mask] = cv2.addWeighted(img, alpha, shapes, 1 - alpha, 0)[mask]
        
        # PASO 2: Dibujar líneas verticales y teclas negras
        for p in range(self.kb_white_n_keys):
            x_line_pos = self.kb_x0 + self.white_key_width * (p+1)
            
            # Dibujar teclas negras
            if p not in self.keys_without_black:
                if p in (0, 3, 4):
                    b_bk_x0 = int(round_half_up(
                        x_line_pos - self.black_key_width*(2/3)))
                    b_bk_x1 = int(round_half_up(
                        x_line_pos + self.black_key_width*(1/3)))
                elif p in (1, 5):
                    b_bk_x0 = int(round_half_up(
                        x_line_pos - self.black_key_width*(1/3)))
                    b_bk_x1 = int(round_half_up(
                        x_line_pos + self.black_key_width*(2/3)))
                else:
                    b_bk_x0 = int(round_half_up(
                        x_line_pos - self.black_key_width/2))
                    b_bk_x1 = int(round_half_up(
                        x_line_pos + self.black_key_width/2))
                
                cv2.rectangle(
                    img=img,
                    pt1=(b_bk_x0, self.kb_y0),
                    pt2=(b_bk_x1, int(
                        round_half_up(self.kb_y0 + self.black_key_heigth))),
                    color=(30, 30, 30),
                    thickness=cv2.FILLED)
                
                # Borde gris para teclas negras (mejora visual)
                cv2.rectangle(
                    img=img,
                    pt1=(b_bk_x0, self.kb_y0),
                    pt2=(b_bk_x1, int(
                        round_half_up(self.kb_y0 + self.black_key_heigth))),
                    color=(80, 80, 80),
                    thickness=2)
                
                key_coord = \
                    self.new_key(p,
                                (b_bk_x0, self.kb_y0),
                                (b_bk_x1,
                                 int(
                                     round_half_up(self.kb_y0 +
                                                   self.black_key_heigth))))
                self.upper_zone_divisions.append(key_coord)
            
            # Dibujar líneas verticales entre teclas blancas
            cv2.line(img=img,
                    pt1=(int(round_half_up(x_line_pos)), self.kb_y0),
                    pt2=(int(round_half_up(x_line_pos)), self.kb_y1),
                    color=(100, 100, 100),
                    thickness=2)
        
        # PASO 3: Dibujar nombres de notas en teclas blancas
        for p in range(self.kb_white_n_keys):
            x_center = int(self.kb_x0 + self.white_key_width * p + self.white_key_width / 2)
            
            note_name = self.__note_names[p]
            font_scale = 0.6
            text_size = cv2.getTextSize(note_name, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            text_x = x_center - text_size[0] // 2
            text_y = self.kb_y1 - 12
            
            # Sombra del texto
            cv2.putText(img=img, 
                       text=note_name,
                       org=(text_x + 1, text_y + 1),
                       fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                       fontScale=font_scale,
                       color=(150, 150, 150),
                       thickness=2)
            
            # Texto principal
            cv2.putText(img=img, 
                       text=note_name,
                       org=(text_x, text_y),
                       fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                       fontScale=font_scale,
                       color=(0, 0, 0),
                       thickness=2)
        
        # PASO 4: Dibujar borde del teclado (mejora visual)
        cv2.rectangle(img, 
                     (self.kb_x0, self.kb_y0),
                     (self.kb_x1, self.kb_y1), 
                     (50, 100, 200), 
                     3)

    def intersect(self, pointXY):
        if pointXY[0] > self.kb_x0 and pointXY[0] < self.kb_x1 and \
           pointXY[1] > self.kb_y0 and pointXY[1] < self.kb_y1:
            return True
        return False

    def find_key_in_upper_zone(self, x_kb_pos, y_kb_pos):
        key_id = -1
        for k in self.upper_zone_divisions:
            if x_kb_pos > k[1][0][0] and x_kb_pos < k[1][1][0]:
                key_id = k[0]
                break
        return key_id

    def find_key(self, x_pos, y_pos):
        x = x_pos - self.kb_x0
        y = y_pos - self.kb_y0
        
        if y < self.black_key_heigth:
            key = x/self.white_key_width*2
            key = math.floor(key)
            key = self.find_key_in_upper_zone(x_pos, y_pos)
            
            if key == -1:
                key = x/self.white_key_width
                key = math.floor(key)
                return self.__white_map[int(key)]
            else:
                return self.__black_map[int(key)]
        else:
            key = x/self.white_key_width
            key = math.floor(key)
            return self.__white_map[int(key)]

    def note_from_key(self, key):
        return self.__keyboard_piano_map[key]
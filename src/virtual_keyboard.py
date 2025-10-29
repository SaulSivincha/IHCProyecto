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

# black keys averaging 13.7 mm (0.54 in) and
# white keys about 23.5 mm (0.93 in) at the
# base, disregarding space between keys
# => 13.7 / 23.5 0


class VirtualKeyboard():
    __white_map = {
        0: 0,   # Primera tecla blanca -> nota 0
        1: 1,   # Segunda tecla blanca -> nota 2
        2: 2,   # Tercera tecla blanca -> nota 4
        3: 3    # Cuarta tecla blanca -> nota 5
    }

    __black_map = {
        0: None,
        1: None,
        2: None,
        3: None
    }

    __keyboard_piano_map = {
        0: 60,  # DO (C4)
        1: 62,  # RE (D4)
        2: 64,  # MI (E4)
        3: 65   # FA (F4)
    }

    def __init__(self, canvas_w, canvas_h, kb_white_n_keys):
        self.img = None
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h

        if self.canvas_w == 640 and self.canvas_h == 480:
            # If camera are on the front of the user, the left keyboard
            # image (on the right of the screen) must be centered at left
            
            self.kb_x0 = int(round_half_up(canvas_w * 0.20))  # 30
            self.kb_y0 = int(round_half_up(canvas_h * 0.35))  # 50 + 100

            self.kb_x1 = int(round_half_up(canvas_w * 0.80))  # 610
            self.kb_y1 = int(round_half_up(canvas_h * 0.55))  # 190 + 100

        # print('Piano Coords: (x0,y0) (x1,y1): ({},{}) ({}, {})'.format(
        #     self.kb_x0, self.kb_y0, self.kb_x1, self.kb_y1))

        self.kb_white_n_keys = kb_white_n_keys

        self.kb_len = self.kb_x1 - self.kb_x0
        print('virtual_keyboard:kb_len:{}'.format(self.kb_len))
        self.white_kb_height = self.kb_y1 - self.kb_y0
        print('virtual_keyboard:kb_height:{}'.format(self.white_kb_height))

        self.white_key_width = self.kb_len/kb_white_n_keys
        print('virtual_keyboard:key_width:{}'.format(self.white_key_width))

        # (13.7 / 23.5)
        self.black_key_width = self.white_key_width*(0.54/0.93)

        print('virtual_keyboard:black_key_width:{}'.
              format(self.black_key_width))
        self.black_key_heigth = self.white_kb_height * 2/3
        print('virtual_keyboard:black_key_heigth:{}'.
              format(self.black_key_heigth))

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

    # def add_key_key_upper_zone(self):

    def draw_virtual_keyboard(self, img):
        # TODO: Mejorar esto para hacerlo solo una vez
        # Prepara shapes
        # Initialize blank mask image of same dimensions for drawing the shapes
        shapes = np.zeros_like(img, np.uint8)
        cv2.rectangle(
            img=shapes,
            pt1=(self.kb_x0, self.kb_y0),
            pt2=(self.kb_x1, self.kb_y1),
            color=(255, 255, 255),
            thickness=cv2.FILLED)

        # Generate output by blending image with shapes image, using the shapes
        # images also as mask to limit the blending to those parts
        alpha = 0.5  #   Alpha transparency
        mask = shapes.astype(bool)
        img[mask] = cv2.addWeighted(img, alpha, shapes, 1 - alpha, 0)[mask]

        for p in range(self.kb_white_n_keys):
            x_line_pos = self.kb_x0 + self.white_key_width * (p+1)

            # Draw black keys

            if p not in self.keys_without_black:
                if p in (0, 3, 7, 10, 14, 17):
                    b_bk_x0 = int(round_half_up(
                        x_line_pos - self.black_key_width*(2/3)))
                    b_bk_x1 = int(round_half_up(
                        x_line_pos + self.black_key_width*(1/3)))
                elif p in (1, 5, 8, 12, 15, 19):
                    b_bk_x0 = int(round_half_up(
                        x_line_pos - self.black_key_width*(1/3)))
                    b_bk_x1 = int(round_half_up(
                        x_line_pos + self.black_key_width*(2/3)))
                else:
                    b_bk_x0 = int(round_half_up(
                        x_line_pos - self.black_key_width/2))
                    b_bk_x1 = int(round_half_up(
                        x_line_pos + self.black_key_width/2))

                key_coord = \
                    self.new_key(p,
                                 (b_bk_x0, self.kb_y0),
                                 (b_bk_x1,
                                  int(
                                      round_half_up(self.kb_y0 +
                                                    self.black_key_heigth))))
                self.upper_zone_divisions.append(key_coord)

                cv2.rectangle(
                    img=img,
                    pt1=(b_bk_x0, self.kb_y0),
                    pt2=(b_bk_x1, int(
                        round_half_up(self.kb_y0 + self.black_key_heigth))),
                    color=(0, 0, 0),
                    thickness=cv2.FILLED)

            cv2.line(img=img,
                     pt1=(int(round_half_up(x_line_pos)), self.kb_y0),
                     pt2=(int(round_half_up(x_line_pos)), self.kb_y1),
                     color=(0, 0, 0),
                     thickness=2)

            if p != 7:  # Do central
                c_color = (0, 255, 0)
            else:
                c_color = (0, 0, 0)

            cv2.circle(img=img,
                       center=(int(x_line_pos - self.white_key_width/2),
                               int(self.kb_y0 + self.white_kb_height*3/4)),
                       radius=7,
                       color=c_color,
                       thickness=cv2.FILLED
                       )

            cv2.putText(img=img, text=str(p+1),
                        org=(int(round_half_up(
                            x_line_pos-self.white_key_width/2))-7,
                            int(round_half_up(
                                self.kb_y0 + self.white_kb_height*3/4))+3),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.4,
                        color=(0, 0, 255))

        cv2.rectangle(img, (self.kb_x0, self.kb_y0),
                      (self.kb_x1, self.kb_y1), (255, 0, 0), 2)

    def intersect(self, pointXY):
        if pointXY[0] > self.kb_x0 and pointXY[0] < self.kb_x1 and \
                pointXY[1] > self.kb_y0 and pointXY[1] < self.kb_y1:
            return True
        return False

    # def find_key(self, x_pos):
    #     print('find_key:x_pos {}'.format(x_pos))
    #     key = (x_pos/self.white_key_width)
    #     print('find_key:key {}'.format(key))
    #     key = math.floor(key)
    #     print('find_key:ceil key {}'.format(key))
    #     return int(key-1)

    def find_key_in_upper_zone(self, x_kb_pos, y_kb_pos):
        # print('find_key_in_upper_zone:x_pos:{}'.format(x_kb_pos))

        key_id = -1
        for k in self.upper_zone_divisions:
            if x_kb_pos > k[1][0][0] and x_kb_pos < k[1][1][0]:

                # print('k:{}'.format(k))
                # print('k[0]:{}'.format(k[0]))
                # print('k[1][0][0]:{}'.format(k[1][0][0]))
                # print('k[1][1][0]:{}'.format(k[1][1][0]))

                key_id = k[0]
                # print('Key_id:{}'.format(key_id))
                break
        return key_id

    def find_key(self, x_pos, y_pos):
        # print('find_key:x_pos {}'.format(x_pos))
        # print('find_key:y_pos {}'.format(y_pos))

        x = x_pos - self.kb_x0
        y = y_pos - self.kb_y0

        if y < self.black_key_heigth:
            key = x/self.white_key_width*2
            key = math.floor(key)

            key = self.find_key_in_upper_zone(x_pos, y_pos)
            # print('find_key:upper zone key {}'.format(key))
            if key == -1:
                key = x/self.white_key_width
                # print('find_key:key {}'.format(key))
                key = math.floor(key)
                # print('find_key:ceil key {}'.format(key))
                print(f"Tecla superior detectada: {key}")  # DEBUG
                return self.__white_map[int(key)]
            else:
                return self.__black_map[int(key)]
        else:
            key = x/self.white_key_width
            # print('find_key:key {}'.format(key))
            key = math.floor(key)
            # print('find_key:ceil key {}'.format(key))
            print(f"Tecla inferior detectada: {key}")  # DEBUG
            return self.__white_map[int(key)]

    def note_from_key(self, key):
        return self.__keyboard_piano_map[key]

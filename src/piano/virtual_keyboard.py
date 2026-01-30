#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
from src.utils import round_half_up
from src.vision.stereo_config import StereoConfig

class VirtualKeyboard():
    # Mapas de notas MIDI para 2 octavas (60=Do central)
    __white_map = {
        0: 0,   1: 2,   2: 4,   3: 5,   4: 7,   5: 9,   6: 11,
        7: 12,  8: 14,  9: 16,  10: 17, 11: 19, 12: 21, 13: 23
    }

    __black_map = {
        0: 1,   1: 3,   2: None, 3: 6,   4: 8,   5: 10,  6: None,
        7: 13,  8: 15,  9: None, 10: 18, 11: 20, 12: 22, 13: None
    }

    __keyboard_piano_map = {
        0: 60, 1: 61, 2: 62, 3: 63, 4: 64, 5: 65, 6: 66, 7: 67, 8: 68, 9: 69, 10: 70, 11: 71,
        12: 72, 13: 73, 14: 74, 15: 75, 16: 76, 17: 77, 18: 78, 19: 79, 20: 80, 21: 81, 22: 82, 23: 83
    }

    def __init__(self, canvas_w, canvas_h, kb_white_n_keys=14):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.kb_white_n_keys = 14 # Forzamos 14 para 2 octavas reales
        self.ar_mode_active = False
        self.screen_key_polygons = []
        self.M_inv = None
        self.white_key_names = ["Do", "Re", "Mi", "Fa", "Sol", "La", "Si"]
        self.white_keys_ids = [self.__white_map[i] for i in range(14)]

        # Lógica de Esquinas (Fase 4)
        if StereoConfig.TABLE_CORNERS is not None and len(StereoConfig.TABLE_CORNERS) == 4:
            raw_corners = StereoConfig.TABLE_CORNERS
            calib_w = getattr(StereoConfig, 'CALIB_PIXEL_WIDTH', 1280) or 1280
            calib_h = getattr(StereoConfig, 'CALIB_PIXEL_HEIGHT', 720) or 720
            
            # 1. Transformar a DISPLAY y ORDENAR para evitar pianos deformes
            display_corners = [StereoConfig.transform_point_for_display(pt, calib_w, calib_h) for pt in raw_corners]
            pts = np.array(display_corners, dtype="float32")
            s = pts.sum(axis=1)
            diff = np.diff(pts, axis=1)
            self.ordered_corners = np.zeros((4, 2), dtype="float32")
            self.ordered_corners[0] = pts[np.argmin(s)]       # Top-Left
            self.ordered_corners[2] = pts[np.argmax(s)]       # Bottom-Right
            self.ordered_corners[1] = pts[np.argmin(diff)]    # Top-Right
            self.ordered_corners[3] = pts[np.argmax(diff)]    # Bottom-Left

            self.kb_x0, self.kb_y0 = self.ordered_corners[0][0], self.ordered_corners[0][1]
            self.kb_x1, self.kb_y1 = self.ordered_corners[2][0], self.ordered_corners[2][1]
        else:
            self.kb_x0, self.kb_y0 = canvas_w * 0.08, canvas_h * 0.52
            self.kb_x1, self.kb_y1 = canvas_w * 0.92, canvas_h * 0.82
            self.ordered_corners = None

        self.kb_len = self.kb_x1 - self.kb_x0
        self.white_key_width = self.kb_len / self.kb_white_n_keys
        self.black_key_heigth = (self.kb_y1 - self.kb_y0) * 0.65

    def draw_virtual_keyboard(self, img, active_keys=None):
        """Método principal llamado por main.py"""
        if self.ar_mode_active and self.ordered_corners is not None:
            self.draw_perspective(img, self.ordered_corners, active_keys)
        else:
            self.draw_virtual_keyboard_flat(img)

    def draw_virtual_keyboard_flat(self, img):
        """Dibujo simple en 2D"""
        x0, y0, x1, y1 = int(self.kb_x0), int(self.kb_y0), int(self.kb_x1), int(self.kb_y1)
        w_key = int(self.white_key_width)
        for i in range(self.kb_white_n_keys):
            kx = x0 + (i * w_key)
            cv2.rectangle(img, (kx, y0), (kx + w_key - 2, y1), (245, 245, 245), -1)
            cv2.rectangle(img, (kx, y0), (kx + w_key - 2, y1), (100, 100, 100), 1)
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)

    def generate_logical_key_geometries(self):
        geometries = []
        for p in range(self.kb_white_n_keys):
            x_s = self.kb_x0 + (p * self.white_key_width)
            x_e = x_s + self.white_key_width
            pts = [[x_s, self.kb_y0], [x_e, self.kb_y0], [x_e, self.kb_y1], [x_s, self.kb_y1]]
            geometries.append({'id': self.__white_map[p], 'black': False, 'pts': np.array([pts], dtype=np.float32)})
            if p in self.__black_map and self.__black_map[p] is not None:
                bw = self.white_key_width * 0.6
                pts_b = [[x_e - bw/2, self.kb_y0], [x_e + bw/2, self.kb_y0], [x_e + bw/2, self.kb_y0 + self.black_key_heigth], [x_e - bw/2, self.kb_y0 + self.black_key_heigth]]
                geometries.append({'id': self.__black_map[p], 'black': True, 'pts': np.array([pts_b], dtype=np.float32)})
        return geometries

    def _render_hd_buffer(self, active_keys=None):
        # Renderizado estético para modo AR
        buf = np.zeros((400, 1200, 3), dtype=np.uint8)
        w_key = 1200 // 14
        for i in range(14):
            color = (255, 255, 255) if self.white_keys_ids[i] not in (active_keys or []) else (0, 255, 0)
            cv2.rectangle(buf, (i*w_key, 0), ((i+1)*w_key-2, 400), color, -1)
        return buf

    def draw_perspective(self, img, corners, active_keys=None):
        hd_kb = self._render_hd_buffer(active_keys)
        h, w = hd_kb.shape[:2]
        src_pts = np.float32([[0,0], [w,0], [w,h], [0,h]])
        matrix = cv2.getPerspectiveTransform(src_pts, np.float32(corners))
        warped = cv2.warpPerspective(hd_kb, matrix, (img.shape[1], img.shape[0]))
        mask = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) > 0
        img[mask] = cv2.addWeighted(img[mask], 0.2, warped[mask], 0.8, 0)

    def intersect(self, pointXY): return True
    def find_key(self, x, y):
        # Lógica de detección simplificada por polígonos
        for poly in reversed(self.screen_key_polygons):
            if cv2.pointPolygonTest(poly['contour'], (x, y), False) >= 0:
                return poly['id']
        return None

    def note_from_key(self, key): return 60 + key
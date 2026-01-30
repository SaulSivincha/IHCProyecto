#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from src.utils import round_half_up
from src.vision.stereo_config import StereoConfig

class VirtualKeyboard():
    # Mapeo MIDI: Do4 (60) a Si5 (83) para 2 octavas (24 notas totales)
    __white_map = {i: v for i, v in enumerate([0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23])}
    __black_map = {0: 1, 1: 3, 3: 6, 4: 8, 5: 10, 7: 13, 8: 15, 10: 18, 11: 20, 12: 22}

    def __init__(self, canvas_w, canvas_h, kb_white_n_keys=14):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.kb_white_n_keys = 14  # Forzamos 14 para 2 octavas consistentes
        self.ar_mode_active = False
        self.screen_key_polygons = []
        self.ordered_corners = None

        # Cargar esquinas de calibración si existen (Fase 4)
        if StereoConfig.TABLE_CORNERS and len(StereoConfig.TABLE_CORNERS) == 4:
            self._setup_ar_geometry()
        else:
            # Fallback: Posicionamiento estándar
            self.kb_x0, self.kb_y0 = canvas_w * 0.08, canvas_h * 0.52
            self.kb_x1, self.kb_y1 = canvas_w * 0.92, canvas_h * 0.82

        self.kb_len = self.kb_x1 - self.kb_x0
        self.white_key_width = self.kb_len / self.kb_white_n_keys
        self.black_key_heigth = (self.kb_y1 - self.kb_y0) * 0.65

    def _setup_ar_geometry(self):
        """Prepara las coordenadas basadas en la calibración"""
        raw = StereoConfig.TABLE_CORNERS
        cal_w = getattr(StereoConfig, 'CALIB_PIXEL_WIDTH', 1280) or 1280
        cal_h = getattr(StereoConfig, 'CALIB_PIXEL_HEIGHT', 720) or 720
        pts = np.array([StereoConfig.transform_point_for_display(p, cal_w, cal_h) for p in raw], dtype="float32")
        
        # Ordenar: Top-Left, Top-Right, Bottom-Right, Bottom-Left
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        self.ordered_corners = np.array([
            pts[np.argmin(s)], pts[np.argmin(diff)], pts[np.argmax(s)], pts[np.argmax(diff)]
        ])
        self.kb_x0, self.kb_y0 = self.ordered_corners[0]
        self.kb_x1, self.kb_y1 = self.ordered_corners[2]

    def generate_logical_key_geometries(self):
        """MÉTODO REQUERIDO POR LA CALIBRACIÓN: Genera la lista de teclas"""
        geometries = []
        for p in range(self.kb_white_n_keys):
            x_s = self.kb_x0 + (p * self.white_key_width)
            x_e = x_s + self.white_key_width
            
            # Tecla Blanca
            pts_w = np.array([[[x_s, self.kb_y0], [x_e, self.kb_y0], [x_e, self.kb_y1], [x_s, self.kb_y1]]], dtype=np.float32)
            geometries.append({'id': self.__white_map[p], 'black': False, 'pts': pts_w})
            
            # Tecla Negra
            if p in self.__black_map:
                bw = self.white_key_width * 0.6
                pts_b = np.array([[[x_e - bw/2, self.kb_y0], [x_e + bw/2, self.kb_y0], 
                                   [x_e + bw/2, self.kb_y0 + self.black_key_heigth], 
                                   [x_e - bw/2, self.kb_y0 + self.black_key_heigth]]], dtype=np.float32)
                geometries.append({'id': self.__black_map[p], 'black': True, 'pts': pts_b})
        return geometries

    def draw_virtual_keyboard(self, img, active_keys=None):
        """Dibujo compatible con main.py"""
        self._draw_logic(img, active_keys)

    def draw_perspective(self, img, corners, active_keys=None):
        """Dibujo compatible con Modo Libre y Calibración"""
        self.ar_mode_active = True
        if corners is not None: self.ordered_corners = np.float32(corners)
        self._draw_logic(img, active_keys)

    def _draw_logic(self, img, active_keys=None):
        """Lógica unificada de renderizado y actualización de polígonos"""
        self.screen_key_polygons = []
        active_keys = active_keys or []
        geoms = self.generate_logical_key_geometries()
        
        # Dibujar Blancas primero
        for g in [x for x in geoms if not x['black']]:
            poly = g['pts'][0].astype(np.int32)
            color = (0, 255, 0) if g['id'] in active_keys else (245, 245, 245)
            cv2.fillPoly(img, [poly], color)
            cv2.polylines(img, [poly], True, (150, 150, 150), 1)
            self.screen_key_polygons.append({'id': g['id'], 'contour': poly})

        # Dibujar Negras encima
        for g in [x for x in geoms if x['black']]:
            poly = g['pts'][0].astype(np.int32)
            color = (0, 255, 0) if g['id'] in active_keys else (30, 30, 30)
            cv2.fillPoly(img, [poly], color)
            self.screen_key_polygons.insert(0, {'id': g['id'], 'contour': poly})

    def intersect(self, pointXY):
        """Requerido por keyboard_mapper.py"""
        x, y = pointXY
        margin = 15
        return (self.kb_x0 - margin <= x <= self.kb_x1 + margin and 
                self.kb_y0 - margin <= y <= self.kb_y1 + margin)

    def find_key(self, x, y):
        """Identifica la tecla bajo el dedo"""
        for poly in self.screen_key_polygons:
            if cv2.pointPolygonTest(poly['contour'], (float(x), float(y)), False) >= 0:
                return poly['id']
        return None

    def note_from_key(self, key_id):
        """Convierte ID a nota MIDI (Do4 = 60)"""
        return 60 + key_id
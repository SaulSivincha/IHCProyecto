#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import cv2
from src.vision.stereo_config import StereoConfig

class KeyboardProcessor:
    def __init__(self, keyboard_mapper, angler, depth_estimator, synth, octave_base, keyboard_total_keys, camera_separation, use_stereo_calibration=True):
        self.km = keyboard_mapper
        self.angler = angler
        self.depth_estimator = depth_estimator
        self.synth = synth
        self.octave_base = octave_base
        self.keyboard_total_keys = keyboard_total_keys
        self.camera_separation = camera_separation
        self.use_stereo_calibration = use_stereo_calibration and depth_estimator is not None
        self.prev_active_keys = []
        
    def process_and_play(self, frame_left, frame_right, virtual_keyboard, hand_detector_left, hand_detector_right, game_mode=False, rhythm_game=None, display_frame_left=None, rotate_hands=False):
        
        # Frame de dibujo (AR)
        frame_draw = display_frame_left if display_frame_left is not None else frame_left
        h_raw, w_raw = frame_left.shape[:2]
        should_rotate = (display_frame_left is not None)

        # 1. Detección
        hands_L = hand_detector_left.findHands(frame_left)
        hands_R = hand_detector_right.findHands(frame_right)
        
        fingers_L = []
        if hands_L: _, fingers_L = hand_detector_left.getFingerTipsPos(w_raw, h_raw)
        
        fingers_R = []
        if hands_R: _, fingers_R = hand_detector_right.getFingerTipsPos(w_raw, h_raw)

        # 2. Dibujo (Ahora usará la función corregida en hand_detector)
        virtual_keyboard.draw_virtual_keyboard(frame_draw, self.prev_active_keys, [])
        if hands_L:
            hand_detector_left.drawTips(frame_draw, rotate_180=should_rotate)

        # 3. Fusión de Datos (Con Rescate Monocular)
        unified_depths = {}
        map_R = {(f[0], f[1]): f for f in fingers_R}
        
        for f_left in fingers_L:
            fid = (f_left[0], f_left[1])
            depth = -0.2 # VALOR POR DEFECTO: Contacto (Rescate Monocular)
            
            # Intentar Estéreo para mayor precisión
            if fid in map_R:
                f_right = map_R[fid]
                calc = self._calculate_depth(f_left, f_right)
                if calc is not None:
                    depth = calc
            
            unified_depths[fid] = depth

        # 4. Transformar Coordenadas
        visual_fingers = []
        for fid, depth in unified_depths.items():
            f_orig = next((f for f in fingers_L if (f[0], f[1]) == fid), None)
            if f_orig:
                x_raw, y_raw = f_orig[2], f_orig[3]
                vx, vy = StereoConfig.transform_point_for_display((x_raw, y_raw), w_raw, h_raw)
                visual_fingers.append([fid[0], fid[1], vx, vy])

        # 5. Mapeo y Audio
        on_map, off_map = self.km.get_kayboard_map(virtual_keyboard, visual_fingers, unified_depths, self.keyboard_total_keys)
        
        if hasattr(self.km, 'prev_map'):
             self.prev_active_keys = np.where(self.km.prev_map)[0].tolist()

        if np.any(on_map):
            for k, is_on in enumerate(on_map):
                if is_on: self.synth.noteon(0, virtual_keyboard.note_from_key(k) + self.octave_base, 100)
        
        if np.any(off_map):
             for k, is_off in enumerate(off_map):
                if is_off: self.synth.noteoff(0, virtual_keyboard.note_from_key(k) + self.octave_base)

        return frame_draw, frame_right

    def _calculate_depth(self, f_l, f_r):
        if self.use_stereo_calibration and self.depth_estimator:
            try:
                pt_l = self.depth_estimator.rectify_point((f_l[2], f_l[3]), 'left')
                pt_r = self.depth_estimator.rectify_point((f_r[2], f_r[3]), 'right')
                res_3d = self.depth_estimator.triangulate_point(pt_l, pt_r, method='DLT')
                if res_3d: return self.depth_estimator.get_depth_relative_to_plane(f_l[2], f_l[3], res_3d[2])
            except: pass
        return None

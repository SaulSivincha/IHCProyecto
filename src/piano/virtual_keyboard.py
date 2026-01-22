#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 27 22:57:59 2021

@author: mherrera
Modified for visual improvement
"""

import cv2
import numpy as np
import math
from src.utils import round_half_up
from src.config.theme import Theme
from src.vision.stereo_config import StereoConfig

class VirtualKeyboard():
    __white_map = {
        # Primera octava: C, D, E, F, G, A, B
        0: 0,   1: 2,   2: 4,   3: 5,   4: 7,   5: 9,   6: 11,
        # Segunda octava: C, D, E, F, G, A, B
        7: 12,  8: 14,  9: 16,  10: 17, 11: 19, 12: 21, 13: 23
    }

    __black_map = {
        # Primera octava: C#, D#, F#, G#, A#
        0: 1,   1: 3,   2: None, 3: 6,   4: 8,   5: 10,  6: None,
        # Segunda octava: C#, D#, F#, G#, A#
        7: 13,  8: 15,  9: None, 10: 18, 11: 20, 12: 22, 13: None
    }

    __keyboard_piano_map = {
        # Primera octava (C4=60 a B4=71)
        0: 60,   1: 61,   2: 62,   3: 63,   4: 64,   5: 65,   6: 66,   7: 67,
        8: 68,   9: 69,  10: 70,  11: 71,
        # Segunda octava (C5=72 a B5=83)
        12: 72,  13: 73,  14: 74,  15: 75,  16: 76,  17: 77,  18: 78,  19: 79,
        20: 80,  21: 81,  22: 82,  23: 83
    }


    def __init__(self, canvas_w, canvas_h, kb_white_n_keys):
        self.img = None
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.kb_white_n_keys = kb_white_n_keys

        # Calcular coordenadas del teclado
        # PRIORIDAD: TABLE_CORNERS (Fase 4) > Ratios fijos
        if StereoConfig.TABLE_CORNERS is not None and len(StereoConfig.TABLE_CORNERS) == 4:
            # Usar esquinas de la calibración Fase 4
            # NOTA: Las esquinas YA están en coordenadas del frame rotado/transformado
            # porque durante la calibración el usuario ve el frame con apply_display_transform
            corners = StereoConfig.TABLE_CORNERS
            
            # Obtener resolución de calibración
            calib_w = getattr(StereoConfig, 'CALIB_PIXEL_WIDTH', 1280) or 1280
            calib_h = getattr(StereoConfig, 'CALIB_PIXEL_HEIGHT', 720) or 720
            
            print(f"[VirtualKeyboard] TABLE_CORNERS: {corners}")
            print(f"[VirtualKeyboard] Calib res: {calib_w}x{calib_h}, Canvas: {canvas_w}x{canvas_h}")
            
            # Calcular bounding box del área calibrada
            all_x = [pt[0] for pt in corners]
            all_y = [pt[1] for pt in corners]
            min_x = min(all_x)
            max_x = max(all_x)
            min_y = min(all_y)
            max_y = max(all_y)
            
            # Factor de escala de calibración a resolución actual
            scale_x = canvas_w / calib_w
            scale_y = canvas_h / calib_h
            
            # Escalar a resolución actual
            self.kb_x0 = int(min_x * scale_x)
            self.kb_y0 = int(min_y * scale_y)
            self.kb_x1 = int(max_x * scale_x)
            self.kb_y1 = int(max_y * scale_y)
            
            print(f"[VirtualKeyboard] Usando TABLE_CORNERS (Fase 4)")
            print(f"[VirtualKeyboard] BBox original: ({min_x},{min_y})-({max_x},{max_y})")
            print(f"[VirtualKeyboard] Escala: {scale_x:.2f}x, {scale_y:.2f}y")
        else:
            # Fallback: usar ratios fijos
            self.kb_x0 = int(round_half_up(canvas_w * StereoConfig.KEYBOARD_X0_RATIO))
            self.kb_y0 = int(round_half_up(canvas_h * StereoConfig.KEYBOARD_Y0_RATIO))
            self.kb_x1 = int(round_half_up(canvas_w * StereoConfig.KEYBOARD_X1_RATIO))
            self.kb_y1 = int(round_half_up(canvas_h * StereoConfig.KEYBOARD_Y1_RATIO))
            print(f"[VirtualKeyboard] Usando ratios fijos (sin Fase 4)")

        self.kb_len = self.kb_x1 - self.kb_x0
        
        print(f"[VirtualKeyboard] Init: {self.canvas_w}x{self.canvas_h}")
        print(f"[VirtualKeyboard] Coords: ({self.kb_x0},{self.kb_y0}) to ({self.kb_x1},{self.kb_y1})")
        
        self.white_kb_height = self.kb_y1 - self.kb_y0
        self.white_key_width = int(self.kb_len / self.kb_white_n_keys)
        
        # Ajuste visual: Tecla negra ~55-60% del ancho de la blanca
        self.black_key_width = int(self.white_key_width * 0.6)
        self.black_key_heigth = self.white_kb_height * StereoConfig.BLACK_KEY_HEIGHT_RATIO

        self.keys_without_black = \
            list({none_keys for none_keys in self.__black_map
                  if self.__black_map[none_keys] is None})

        self.key_id = None
        self.rectangle = []
        self.upper_zone_divisions = []
        
        # Lista de nombres de notas para visualización
        self.white_key_names = ["Do", "Re", "Mi", "Fa", "Sol", "La", "Si"]
        
        # Matriz inversa para corrección de clicks en AR
        self.M_inv = None
        self.ar_mode_active = False
        self.screen_key_polygons = [] # Poligonos de teclas en coordenadas de pantalla
        
        # Generar lista plana de IDs para renderizado (Fix AttributeError)
        self.white_keys_ids = [self.__white_map.get(i, -1) for i in range(self.kb_white_n_keys)]



    def new_key(self, key_id, top_left, bottom_rigth):
        self.key_id = key_id
        self.rectangle = [top_left, bottom_rigth]
        return key_id, self.rectangle

    def generate_logical_key_geometries(self):
        """Genera geometrías base (rectángulos) para todas las teclas en coordenadas lógicas (planas)"""
        geometries = [] # Lista de dicts {id, black, pts}
        
        # 1. Teclas Blancas
        # Usar float width para evitar error acumulado en la derecha
        float_width = float(self.kb_len) / float(self.kb_white_n_keys)
        
        for p in range(self.kb_white_n_keys):
            # Calcular posiciones exactas en float
            x_start_f = self.kb_x0 + float_width * p
            x_end_f = self.kb_x0 + float_width * (p + 1)
            
            x_line_pos = int(round_half_up(x_start_f))
            x_next_pos = int(round_half_up(x_end_f)) # Usar siguiente exacto para cerrar huecos
            
            # [FIX] Revertido logical infinite bottom (ineficaz con perspectiva fuerte)
            # Se maneja ahora en draw_perspective (Screen Space)
            
            # Rectángulo completo de la tecla blanca
            pts = [
                [x_line_pos, self.kb_y0],
                [x_next_pos, self.kb_y0],
                [x_next_pos, self.kb_y1], 
                [x_line_pos, self.kb_y1] 
            ]
            
            # Map visual index p to key_id
            key_id = -1
            if p in self.__white_map:
                key_id = self.__white_map[p]
                
            if key_id != -1:
                geometries.append({
                    'id': key_id,
                    'black': False,
                    'pts': np.array([pts], dtype=np.float32)
                })
                # DEBUG: Log white key generation (only once)
                if not hasattr(self, '_gen_logged'):
                    print(f"[GEN_WHITE] visual_pos={p}, key_id={key_id}, x_range=({x_line_pos},{x_next_pos})")

        # 2. Teclas Negras
        for p in range(self.kb_white_n_keys):
            # Posicion visual aproximada (Float)
            x_line_pos_next = self.kb_x0 + float_width * (p+1)
            
            # Lógica de posición tecla negra (copiada de draw_flat con logica estándar)
            # Simplificación: Usamos la logica estándar para calcular el rect
            # NOTA: Esta lógica asume el layout estándar sin espejo para la geometría base.
            # El espejo se maneja visualmente o invirtiendo coordenadas después.
            
            # [FIX] Usar modulo para octavas
            # Lógica sincronizada con _render_hd_buffer para WYSIWYG
            # octave_idx: 0=Do, 1=Re, 2=Mi, 3=Fa, 4=Sol, 5=La, 6=Si
            octave_idx = p % 7
            
            shift = 0.0
            bk_w_float = float(self.black_key_width)
            
            if octave_idx == 0: shift = -bk_w_float/3.0
            elif octave_idx == 1: shift = bk_w_float/3.0
            elif octave_idx == 3: shift = -bk_w_float/3.0
            elif octave_idx == 4: shift = 0.0
            elif octave_idx == 5: shift = bk_w_float/3.0
            
            # Centro teórico: inicio de la siguiente tecla blanca (Float)
            center_x = x_line_pos_next
            
            b_bk_x0 = int(round_half_up(center_x - (bk_w_float / 2.0) + shift))
            b_bk_x1 = int(round_half_up(center_x + (bk_w_float / 2.0) + shift))
            
            # Teclas que TIENEN negra a su derecha
            # 0(Do), 1(Re), 3(Fa), 4(Sol), 5(La) -> tienen negra
            # 7(Do), 8(Re), ...
            has_black = octave_idx in (0, 1, 3, 4, 5)
            
            if has_black:
                # Validar key_id negra
                 if p in self.__black_map and self.__black_map[p] is not None:
                    key_id = self.__black_map[p]
                    pts = [
                        [b_bk_x0, self.kb_y0],
                        [b_bk_x1, self.kb_y0],
                        [b_bk_x1, int(round_half_up(self.kb_y0 + self.black_key_heigth))],
                        [b_bk_x0, int(round_half_up(self.kb_y0 + self.black_key_heigth))]
                    ]
                    geometries.append({
                        'id': key_id,
                        'black': True,
                        'pts': np.array([pts], dtype=np.float32)
                    })
                    # DEBUG: Log black key generation (only once)
                    if not hasattr(self, '_gen_logged'):
                        print(f"[GEN_BLACK] visual_pos={p}, key_id={key_id}, x_range=({b_bk_x0},{b_bk_x1})")
        
        # Mark as logged
        self._gen_logged = True
        return geometries



    def _render_hd_buffer(self, active_keys=None):
        """
        Genera una imagen HD del teclado plano con efectos visuales de alta calidad.
        Retorna: imagen (h, w, 3)
        """
        if active_keys is None:
            active_keys = []
            
        base_w = 1200
        base_h = 400
        
        # Buffer caching
        if not hasattr(self, '_base_buffer') or self._base_buffer.shape[1] != base_w:
            self._base_buffer = np.zeros((base_h, base_w, 3), dtype=np.uint8)
        
        canvas = self._base_buffer
        canvas[:] = 0 # Limpiar
        
        n_keys = self.kb_white_n_keys
        w_key = base_w // n_keys
        b_key_w = int(w_key * 0.6)
        b_key_h = int(base_h * 0.65)
        
        is_mirrored = getattr(StereoConfig, 'MIRROR_HORIZONTAL', False)
        
        # === 1. TECLAS BLANCAS ===
        for i in range(n_keys):
            # Mapeo visual a lógico
            logical_id = self.white_keys_ids[i] # IDs de notas blancas: 0, 2, 4...
            
            # En modo espejo, el dibujo va de izq a der, pero representa notas al revés
            # PERO self.white_keys_ids ya está ordenado asc.
            # Visual index i=0 (izq) -> logical_id=0 (Do) si normal.
            # Si mirror: visual i=0 -> logical_id=final
            
            current_id = logical_id
            if is_mirrored:
                # El id correspondiente a esta pos visual i
                # i=0 es la izquierda. Si espejo, es la nota más aguda.
                current_id = self.white_keys_ids[n_keys - 1 - i]

            is_active = current_id in active_keys
            
            x0 = i * w_key
            x1 = x0 + w_key - 2
            
            # Colores
            if is_active:
                # Color activo (Cyan brillante o similar)
                col_top = (255, 255, 200) # Cyan muy claro
                col_bottom = (200, 200, 0) # Cyan oscuro
            else:
                col_top = (240, 240, 240)
                col_bottom = (255, 255, 255)
            
            # Dibujar cuerpo
            cv2.rectangle(canvas, (x0, 0), (x1, base_h), col_top, -1)
            cv2.rectangle(canvas, (x0, base_h-40), (x1, base_h), col_bottom, -1)
            
            # Sombra lateral
            cv2.line(canvas, (x1, 0), (x1, base_h), (150, 150, 150), 2)
            
            # Texto
            note_name = self.white_key_names[(i if not is_mirrored else (n_keys - 1 - i)) % 7]
            if True:
                font_scale = 1.2
                thickness = 2
                (tw, th), _ = cv2.getTextSize(note_name, cv2.FONT_HERSHEY_PLAIN, font_scale, thickness)
                tx = x0 + (w_key - tw) // 2
                ty = base_h - 15
                col_text = (0, 100, 100) if is_active else (50, 50, 50)
                cv2.putText(canvas, note_name, (tx, ty), cv2.FONT_HERSHEY_PLAIN, font_scale, col_text, thickness, cv2.LINE_AA)

        # === 2. TECLAS NEGRAS ===
        for p in range(n_keys):
            visual_p = n_keys - 1 - p if is_mirrored else p
            
            keys_without_black = [2, 6, 9, 13]
            check_p = visual_p % 14
            octave_idx = check_p % 7
            has_black = octave_idx not in (2, 6)
            
            if has_black:
                # Identificar ID lógico de la negra
                # La negra está a la derecha de la blanca 'visual_p' (en lógica normal DO -> DO#)
                # DO(0) -> DO#(1).
                # Si estamos en modo espejo, visual_p va decreciendo.
                
                # Simplificación: Usar mapa de negras
                # self.__black_map mapea white_id -> black_id
                # Necesitamos el white_id de la tecla actual
                white_logical = self.white_keys_ids[visual_p] # ID real de la blanca
                black_logical = self.__black_map.get(white_logical, None)
                
                is_active = False
                if black_logical is not None:
                     is_active = black_logical in active_keys

                x_line = (p + 1) * w_key
                shift = 0
                if octave_idx == 0: shift = -b_key_w//3
                elif octave_idx == 1: shift = b_key_w//3
                elif octave_idx == 3: shift = -b_key_w//3
                elif octave_idx == 4: shift = 0
                elif octave_idx == 5: shift = b_key_w//3
                
                if is_mirrored: shift = -shift

                bk_x0 = x_line - b_key_w//2 + shift
                bk_x1 = bk_x0 + b_key_w
                
                # Sombra
                cv2.rectangle(canvas, (bk_x0+5, 5), (bk_x1+10, b_key_h+10), (0,0,0, 100), -1)
                
                # Cuerpo
                if is_active:
                    col_bk = (200, 200, 50) # Azulado activo
                    col_spec = (255, 255, 200)
                else:
                    col_bk = (20, 20, 20)
                    col_spec = (80, 80, 80)
                
                cv2.rectangle(canvas, (bk_x0, 0), (bk_x1, b_key_h), col_bk, -1)
                cv2.rectangle(canvas, (bk_x0+2, b_key_h-15), (bk_x1-2, b_key_h-5), col_spec, -1)
                
        return canvas

    def draw_perspective(self, img, corners, active_keys=None, hand_landmarks=None):
        """
        Dibuja el teclado usando esquinas AR Reales y renderizado HD.
        """
        if active_keys is None: active_keys = []
        
        # 1. Generar keyboard HD
        hd_keyboard = self._render_hd_buffer(active_keys)
        h_buf, w_buf = hd_keyboard.shape[:2]
        
        # 2. Warp AR
        src_pts = np.float32([[0, 0], [w_buf, 0], [w_buf, h_buf], [0, h_buf]])
        dst_pts = np.float32(corners)
        
        try:
            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            self.M_inv = np.linalg.inv(matrix) # Para inputs
            self.ar_mode_active = True
            
            # --- Visualización ---
            warped = cv2.warpPerspective(hd_keyboard, matrix, (img.shape[1], img.shape[0]))
            
            # Blending inteligente
            gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            
            # Aplicar sobre imagen
            # Usar un alpha alto para que se vea sólido y bonito
            alpha = 0.90 
            
            roi = img[mask > 0]
            fg = warped[mask > 0]
            blended = cv2.addWeighted(roi, 1-alpha, fg, alpha, 0)
            img[mask > 0] = blended
            
            # --- Lógica de Detección (Polígonos) ---
            # Para mantener la lógica de clic, proyectamos los puntos lógicos
            # usando una matriz paralela.
            # La geometría lógica (self.generate_logical_key_geometries)
            # está en coordenadas del canvas "kb_x0, kb_y0...".
            # Pero nuestro warp se basó en el buffer HD (0,0 -> w_buf, h_buf).
            
            # Calculamos matriz auxiliar para polígonos
            # Origen: Geometría lógica plana (kb_x0...)
            # Destino: Corners AR
            src_logic = np.float32([
                [self.kb_x0, self.kb_y0], [self.kb_x1, self.kb_y0],
                [self.kb_x1, self.kb_y1], [self.kb_x0, self.kb_y1]
            ])
            matrix_logic = cv2.getPerspectiveTransform(src_logic, dst_pts)
            
            self.screen_key_polygons = []
            logical_geoms = self.generate_logical_key_geometries()
            
            for key_geom in logical_geoms:
                pts_src = key_geom['pts']
                pts_dst = cv2.perspectiveTransform(pts_src, matrix_logic)[0]
                
                # [FIX] "Screen-Space Infinite Bottom"
                # Forzar que los vértices inferiores de las teclas BLANCAS lleguen al fondo de la pantalla
                # pts_dst es [TL, TR, BR, BL] (según generate_logical...)
                # BR es idx 2, BL es idx 3
                
                if not key_geom['black']:
                     # Extender masivamente hacia abajo en espacio de pantalla 
                     # para cubrir dedos "debajo" del teclado visual por perspectiva
                     screen_bottom = img.shape[0] + 500 # 500px margen seguridad bajo pantalla
                     pts_dst[2][1] = float(screen_bottom)
                     pts_dst[3][1] = float(screen_bottom)
                
                self.screen_key_polygons.append({
                    'id': key_geom['id'],
                    'black': key_geom['black'],
                    'contour': pts_dst.astype(np.int32)
                })
            
            # DEBUG: Log polygon order (only once)
            if not hasattr(self, '_polygon_order_logged'):
                print(f"\n[POLYGON_ORDER] Generated {len(self.screen_key_polygons)} polygons:")
                for i, poly in enumerate(self.screen_key_polygons[:5]):  # Show first 5
                    print(f"  [{i}] key_id={poly['id']}, black={poly['black']}")
                if len(self.screen_key_polygons) > 5:
                    print(f"  ... ({len(self.screen_key_polygons) - 5} more)")
                self._polygon_order_logged = True
                
        except Exception as e:
            # Fallback a dibujar normal si falla la matriz
            print(f"Error perspective: {e}")
            
    def get_note_name(self, key_id):
        """Retorna el nombre solfeo de la tecla"""
        notes = ["Do", "Re", "Mi", "Fa", "Sol", "La", "Si"]
        # Mapa simple asumiendo inicio en Do (octava 0)
        # key_id va 0..23 (2 octavas)
        # Blancas: 0,1,2,3,4,5,6...
        # Mapeo real depende de __white_map y __black_map
        # Simplificación: usar modulo 7 para blancas
        
        # Encontrar índice de blanca
        white_idx = -1
        for p, kid in self.__white_map.items():
            if kid == key_id:
                white_idx = p
                break
        
        if white_idx != -1:
            return notes[white_idx % 7]
        return ""

    def draw_virtual_keyboard(self, img, active_keys=None, hand_landmarks=None, rotated_display=True):
        """Dibuja el teclado virtual sobre la imagen.
        
        Args:
            img: Frame donde dibujar
            active_keys: Teclas activas (opcional)
            hand_landmarks: Landmarks de manos (opcional)
            rotated_display: Si True, el frame está rotado 180° y se transforman coordenadas
        """
        try:
            self.draw_virtual_keyboard_flat(img, rotated_display=rotated_display)
        except Exception as e:
            print(f"[FLAT ERROR] {e}")
            import traceback
            traceback.print_exc()

    def draw_virtual_keyboard_flat(self, img, rotated_display=True):
        """
        Dibuja el teclado DIRECTAMENTE sobre la imagen (modo simple y robusto).
        """
        # Reiniciar divisiones
        self.upper_zone_divisions = []
        
        # Coordenadas del teclado
        x0, y0 = self.kb_x0, self.kb_y0
        x1, y1 = self.kb_x1, self.kb_y1
        
        h_img, w_img = img.shape[:2]
        
        # Validar que las coordenadas estén dentro de la imagen
        x0 = max(0, min(x0, w_img - 1))
        x1 = max(0, min(x1, w_img - 1))
        y0 = max(0, min(y0, h_img - 1))
        y1 = max(0, min(y1, h_img - 1))
        
        n_keys = self.kb_white_n_keys
        
        kb_width = x1 - x0
        kb_height = y1 - y0
        
        if kb_width <= 0 or kb_height <= 0:
            print(f"[FLAT ERROR] Invalid keyboard size: {kb_width}x{kb_height}")
            return
            
        key_width = kb_width // n_keys
        
        # Altura tecla negra
        black_height = int(kb_height * 0.65)
        black_width = int(key_width * 0.6)
        
        # === DIBUJAR TECLAS BLANCAS ===
        for i in range(n_keys):
            kx0 = x0 + i * key_width
            kx1 = kx0 + key_width - 2  # -2 para separación visual
            
            # Fondo blanco
            cv2.rectangle(img, (kx0, y0), (kx1, y1), (240, 240, 240), -1)
            # Borde
            cv2.rectangle(img, (kx0, y0), (kx1, y1), (100, 100, 100), 1)
            
            # Nombre de nota
            note_name = self.white_key_names[i % 7]
            font_scale = 0.5
            (tw, th), _ = cv2.getTextSize(note_name, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            tx = kx0 + (key_width - tw) // 2
            ty = y1 - 10
            cv2.putText(img, note_name, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (50, 50, 50), 1, cv2.LINE_AA)
        
        # === DIBUJAR TECLAS NEGRAS ===
        # Patrón: Do#, Re#, [skip Mi], Fa#, Sol#, La#, [skip Si]
        black_pattern = [True, True, False, True, True, True, False]  # C#, D#, skip, F#, G#, A#, skip
        
        for i in range(n_keys - 1):  # -1 porque la última blanca no tiene negra a su derecha
            octave_pos = i % 7
            if black_pattern[octave_pos]:
                # Centro entre teclas blancas
                center_x = x0 + (i + 1) * key_width
                bx0 = center_x - black_width // 2
                bx1 = center_x + black_width // 2
                by0 = y0
                by1 = y0 + black_height
                
                # Dibujar tecla negra
                cv2.rectangle(img, (bx0, by0), (bx1, by1), (30, 30, 30), -1)
                cv2.rectangle(img, (bx0, by0), (bx1, by1), (0, 0, 0), 1)
        
        # Borde exterior del teclado completo
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)

    def intersect(self, pointXY):
        # Transforma el punto si estamos en modo AR
        x_check, y_check = pointXY
        
        if self.ar_mode_active and self.M_inv is not None:
             # Convertir punto a formato np (1, 1, 2) para perspectiveTransform
             pt_np = np.array([[[float(x_check), float(y_check)]]], dtype=np.float32)
             pt_transformed = cv2.perspectiveTransform(pt_np, self.M_inv)
             x_check = float(pt_transformed[0][0][0])
             y_check = float(pt_transformed[0][0][1])
        
        # CORREGIDO: Ampliar tolerancia de 0px a 20px para bordes
        margin = 20
        if x_check > (self.kb_x0 - margin) and x_check < (self.kb_x1 + margin) and \
                y_check > (self.kb_y0 - margin) and y_check < (self.kb_y1 + margin):
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
        # [FIX] COORDENADAS: RAW vs DISPLAY
        # Las coordenadas de entrada (x_pos, y_pos) vienen del detector de manos (RAW frame).
        
        input_x, input_y = x_pos, y_pos
        
        # === MODO AR (WYSIWYG) ===
        # En modo AR, los polígonos están en el espacio de coordenadas del frame RAW
        # (porque draw_perspective dibuja sobre el frame sin transformar).
        # Por lo tanto, usamos las coordenadas RAW directamente sin transformación.
        if self.ar_mode_active and hasattr(self, 'screen_key_polygons') and self.screen_key_polygons:
            # DEBUG: Mostrar coordenadas de entrada vs rango de poligonos
            if not hasattr(self, '_debug_coord_shown'):
                first_poly = self.screen_key_polygons[0]
                last_poly = self.screen_key_polygons[-1]
                x1,y1,w1,h1 = cv2.boundingRect(first_poly['contour'])
                x2,y2,w2,h2 = cv2.boundingRect(last_poly['contour'])
                print(f"[DEBUG] Using RAW coords in AR: ({input_x:.0f},{input_y:.0f})")
                print(f"[DEBUG] Poly Range: FirstKey({x1},{y1} to {x1+w1},{y1+h1}), LastKey({x2},{y2} to {x2+w2},{y2+h2})")
                self._debug_coord_shown = True
            
            found_key_id = None
            found_poly_type = ""
            
            # Buscar primero en teclas negras (están encima)
            # Usar coordenadas RAW directamente
            check_x, check_y = input_x, input_y
            
            for poly in reversed(self.screen_key_polygons):
                # PointPolygonTest: (contour, pt, measureDist)
                # Returns: +ve distance (inside), -ve distance (outside), 0 (on edge)
                # IMPORTANT: measureDist=True to get pixel distance for tolerance check
                dist = cv2.pointPolygonTest(poly['contour'], (check_x, check_y), True)
                
                # FIX: Tolerancia reducida para mayor precisión
                # -10px = margen pequeño para compensar jitter de tracking
                # Antes: -30 (causaba activación de teclas adyacentes)
                if dist >= -10: 
                    found_key_id = poly['id']
                    found_poly_type = "Black" if poly['black'] else "White"
                    # DEBUG: Log key detection
                    midi_note = self.__keyboard_piano_map.get(found_key_id, -1)
                    print(f"[FIND_KEY] coords=({check_x:.0f},{check_y:.0f}) → key_id={found_key_id} ({found_poly_type}) → MIDI={midi_note}")
                    if poly['black']:
                        break
                    break
            
            if found_key_id is not None:
                # print(f"[KEY_DEBUG] AR HIT! ({check_x:.0f},{check_y:.0f}) -> {found_key_id} ({found_poly_type})")
                return found_key_id
            
            return None

        # === MODO PLANO (FALLBACK) ===
        # CORREGIDO: NO aplicar transform_point_for_display aquí porque
        # las coordenadas ya vienen transformadas desde qt_free_mode_window.py
        # Solo aplicar espejo si está activo
        
        # Si está activado el modo espejo, invertir la posición X
        if getattr(StereoConfig, 'MIRROR_HORIZONTAL', False):
            # Invertir X respecto al centro del teclado
            x_pos = self.kb_x0 + (self.kb_x1 - x_pos)
        
        x = x_pos - self.kb_x0
        y = y_pos - self.kb_y0

        # DEBUG: Mostrar cálculo de tecla
        if not hasattr(self, '_find_key_debug_counter'):
            self._find_key_debug_counter = 0
        self._find_key_debug_counter += 1
        
        if self._find_key_debug_counter % 30 == 0:
            key_index = x / self.white_key_width if self.white_key_width > 0 else -1
            print(f"[FIND_KEY] input=({x_pos:.0f},{y_pos:.0f}), kb_x0={self.kb_x0}, kb_x1={self.kb_x1}")
            print(f"[FIND_KEY] x_rel={x:.0f}, key_width={self.white_key_width}, key_index={key_index:.2f}")

        key_found = None
        if y < self.black_key_heigth:
            key = x/self.white_key_width*2
            key = math.floor(key)

            key = self.find_key_in_upper_zone(x_pos, y_pos)
            if key == -1:
                key = x/self.white_key_width
                key = math.floor(key)
                if int(key) in self.__white_map:
                    key_found = self.__white_map[int(key)]
            else:
                if int(key) in self.__black_map:
                    key_found = self.__black_map[int(key)]
        else:
            key = x/self.white_key_width
            key = math.floor(key)
            if int(key) in self.__white_map:
                key_found = self.__white_map[int(key)]
             
        return key_found

    def note_from_key(self, key):
        midi_note = self.__keyboard_piano_map[key]
        print(f"[NOTE_FROM_KEY] key_id={key} → MIDI={midi_note}")
        return midi_note
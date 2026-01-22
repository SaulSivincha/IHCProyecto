#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo centralizado para procesar el teclado virtual
Maneja detección de manos, triangulación 3D, y reproducción de audio
"""

import numpy as np
from collections import deque
from src.config.app_config import AppConfig
from src.vision.stereo_config import StereoConfig


class KeyboardProcessor:
    """
    Clase que centraliza todo el procesamiento del teclado virtual:
    - Detección de manos
    - Triangulación 3D de profundidad
    - Mapeo de contactos con teclas
    - Reproducción de audio
    """
    
    def __init__(self, keyboard_mapper, angler, depth_estimator, 
                 synth, octave_base, keyboard_total_keys, camera_separation,
                 use_stereo_calibration=True):
        """
        Args:
            keyboard_mapper: Instancia de KeyboardMap
            angler: Instancia de Frame_Angles para triangulación
            depth_estimator: DepthEstimator para cálculo 3D (opcional)
            synth: Sintetizador FluidSynth
            octave_base: Nota base (MIDI)
            keyboard_total_keys: Número total de teclas
            camera_separation: Separación entre cámaras (cm)
            use_stereo_calibration: Usar calibración estéreo si está disponible
        """
        self.km = keyboard_mapper
        self.angler = angler
        self.depth_estimator = depth_estimator
        self.synth = synth
        self.octave_base = octave_base
        self.keyboard_total_keys = keyboard_total_keys
        self.camera_separation = camera_separation
        self.use_stereo_calibration = use_stereo_calibration and depth_estimator is not None
        
        # Buffer de suavizado temporal para reducir jitter
        # [VISUAL] Buffer para feedback visual en el siguiente frame
        self.prev_active_keys = []
        
    def process_and_play(self, frame_left, frame_right, virtual_keyboard, 
                        hand_detector_left, hand_detector_right, 
                        game_mode=False, rhythm_game=None, 
                        display_frame_left=None, rotate_hands=False):
        """
        Procesa ambos frames, detecta manos, calcula profundidad y reproduce audio
        
        Args:
            frame_left: Frame de cámara izquierda (RAW para detección)
            frame_right: Frame de cámara derecha (RAW para detección)
            virtual_keyboard: Instancia de VirtualKeyboard
            hand_detector_left: Detector de manos izquierdo
            hand_detector_right: Detector de manos derecho
            game_mode: Si está en modo juego (rhythm game)
            rhythm_game: Instancia de RhythmGame (si game_mode=True)
            display_frame_left: Frame opcional para DIBUJAR (puede estar rotado/espejado)
            rotate_hands: Si True, indicamos al detector que rote las coordenadas al dibujar
            
        Returns:
            tuple: (frame_to_display, frame_right) frame_to_display es display_frame_left si existe, o frame_left
        """
        # Frame donde vamos a dibujar (si no se pasa uno específico, usamos el original)
        frame_draw = display_frame_left if display_frame_left is not None else frame_left
        
        # === PASO 1: Detectar manos (sin dibujar todavía) en frames RAW ===
        hands_detected_left = hand_detector_left.findHands(frame_left)
        hands_detected_right = hand_detector_right.findHands(frame_right)
        
        hands_left_image = []
        fingers_left_image = []
        hands_right_image = []
        fingers_right_image = []
        
        # Obtener dimensiones reales del frame
        h_raw, w_raw = frame_left.shape[:2]
        
        if hands_detected_left:
            hands_left_image, fingers_left_image = hand_detector_left.getFingerTipsPos(
                img_width=w_raw, 
                img_height=h_raw
            )
        
        if hands_detected_right:
            hands_right_image, fingers_right_image = hand_detector_right.getFingerTipsPos(
                img_width=w_raw, 
                img_height=h_raw
            )
        
        # [AR OCCLUSION] Obtener TODOS los landmarks de las manos para oclusión visual
        hand_landmarks_for_occlusion = []
        if hands_detected_left:
            hand_landmarks_for_occlusion.extend(hand_detector_left.getAllLandmarks())
        
        # === PASO 2: Dibujar teclado PRIMERO (debajo de las manos) ===
        # Siempre dibujamos en el frame de visualización
        # [VISUAL] Pasamos las teclas activas del frame ANTERIOR para feedback
        # [AR] Pasamos landmarks para oclusión de manos
        virtual_keyboard.draw_virtual_keyboard(frame_draw, self.prev_active_keys, hand_landmarks_for_occlusion)
        
        # === PASO 3: Si es modo juego, dibujar notas cayendo ===
        if game_mode and rhythm_game:
            rhythm_game.update()
            frame_draw = rhythm_game.draw(
                frame_draw,
                virtual_keyboard.kb_x0,
                virtual_keyboard.kb_x1,
                virtual_keyboard.white_key_width
            )
        
        # === PASO 4: Dibujar manos AL FINAL (encima del teclado y notas) ===
        # Nota: drawHands internamente dibuja sobre la imagen que se le pasa.
        # Si rotate_hands=True y el detector lo soporta, ajustará coordenadas.
        # Por ahora asumimos que si display_frame está rotado 180, necesitamos que
        # las coordenadas (x,y) se inviertan visualmente 180.
        
        # IMPORTANTE: Los detectores actuales tienen métodos simples.
        # Para rotar visualmente las manos en una imagen rotada sin recalcular todo,
        # necesitamos que el detector tenga opción de rotar o hacerlo manualmente.
        # Como parche eficiente:
        # Si estamos rotados 180, las coordenadas (x,y) detectadas en RAW (0,0 es top-left)
        # corresponden a (w-x, h-y) en la imagen rotada.
        
        if hands_detected_left:
            # Si se solicita rotación y el frame es diferente, idealmente el detector manejaría esto.
            # Aquí usamos el frame de dibujo directamente.
            
            # NOTA: Si display_frame_left está rotado, MediaPipe dibuja en coordenadas RAW.
            # Esto hará que las manos se vean mal (espejadas/rotadas incorrectamente) si dibujamos directo.
            # SOLUCIÓN: Usar la función custom de dibujo con puntos transformados si es necesario.
            if rotate_hands and display_frame_left is not None:
                h, w, c = display_frame_left.shape
                hand_detector_left.drawHands(frame_draw, rotate_180=True)
                hand_detector_left.drawTips(frame_draw, rotate_180=True)
            else:
                hand_detector_left.drawHands(frame_draw)
                hand_detector_left.drawTips(frame_draw)
        
        if hands_detected_right:
            if rotate_hands and display_frame_left is not None:
                h, w, c = display_frame_left.shape
                # Solo dibujamos manos derechas si queremos debuggear, normalmente en piano solo izquierda domina visual o ambas
                hand_detector_right.drawHands(frame_right) # Right generalmente es auxiliar, no display principal
                # Si quisieramos mostrar ambas cámaras unidas, aquí habría lógica extra.
            else:
                hand_detector_right.drawHands(frame_right)
                hand_detector_right.drawTips(frame_right)
        
        # === PASO 5: Procesar contactos (Lógica Híbrida Mono/Stereo) ===
        # Iteramos sobre dedos izquierdos (Cámara primaria) para asegurar detección
        if len(fingers_left_image) > 0:
            finger_depths_dict = {}
            
            # Map para búsqueda rápida de pares derechos
            right_fingers_map = {(f[0], f[1]): f for f in fingers_right_image}
            
            for finger_left in fingers_left_image:
                # Clave única del dedo: (hand_id, tip_id)
                finger_id = (finger_left[0], finger_left[1])
                
                final_depth = None
                
                # A. Intentar Estéreo (Si existe par y calibración)
                if finger_id in right_fingers_map:
                     finger_right = right_fingers_map[finger_id]
                     try:
                         # Triangular
                         depth_absolute = self._calculate_depth(finger_left, finger_right)
                         
                         if self.depth_estimator and self.depth_estimator.keyboard_distance_cm:
                             kb_dist = self.depth_estimator.keyboard_distance_cm
                             # Aplicar offset de seguridad calibrado (SUMAR para subir mesa)
                             offset = getattr(StereoConfig, 'KEYBOARD_OFFSET_CM', 0.0)
                             kb_dist += offset
                             
                             # CORREGIDO: depth_absolute - kb_dist
                             # Si dedo está MÁS CERCA de cámara que mesa → rel_depth > 0 → TOQUE
                             # Si dedo está MÁS LEJOS de cámara que mesa → rel_depth < 0 → AIRE
                             rel_depth = depth_absolute - kb_dist
                             # Filtro básico de rango (-50 a +50 cm)
                             if abs(rel_depth) < 50:
                                 final_depth = rel_depth
                         else:
                             # MATCH Estéreo pero sin calibración de profundidad -> Asumir toque
                             final_depth = 1.0
                     except:
                         pass
                
                # B. Fallback Monocular (Si falló estéreo)
                if final_depth is None:
                    # Asumimos que si está en cámara izquierda, el usuario quiere tocar
                    final_depth = 1.0 # 1cm positivo = Toque
                
                # Guardar en dict (SOLO FLOAT para KeyboardMapper)
                finger_depths_dict[finger_id] = final_depth
            
            # Preparar coordenadas para mapeo (Transformar RAW -> VISUAL)
            # para coincidir con el frame donde se dibujó el teclado (que puede estar rotado)
            h_raw, w_raw = frame_left.shape[:2]
            fingers_visual = []
            
            for f in fingers_left_image:
                 # f = [hand_id, tip_id, x, y]
                 # StereoConfig maneja la rotación si es necesaria
                 vx, vy = StereoConfig.transform_point_for_display((f[2], f[3]), w_raw, h_raw)
                 fingers_visual.append([f[0], f[1], vx, vy])

            # Obtener mapa de teclas presionadas
            on_map, off_map = self.km.get_kayboard_map(
                virtual_keyboard=virtual_keyboard,
                fingertips_pos=fingers_visual, # USAR VISUAL
                finger_depths=finger_depths_dict, # Diccionario usa IDs originales, funciona bien
                keyboard_n_key=self.keyboard_total_keys
            )
            
            # [VISUAL] Actualizar teclas activas para el siguiente frame
            # Usamos el estado actual del mapa (prev_map en km es el current al final de get_keyboard_map)
            if hasattr(self.km, 'prev_map'):
                self.prev_active_keys = np.where(self.km.prev_map)[0].tolist()
            
            # === PASO 6: Reproducir audio según el modo ===
            if game_mode and rhythm_game:
                # Modo juego: verificar aciertos
                active_keys = np.where(on_map)[0]
                for k_pos in active_keys:
                    hit_result = rhythm_game.check_hit(k_pos)
                    if hit_result:
                        # RECUPERAR VELOCIDAD CALCULADA (fallback a 80)
                        velocity = getattr(self.km, 'active_velocities', {}).get(k_pos, 80)
                        self.synth.noteon(
                            chan=0,
                            key=virtual_keyboard.note_from_key(k_pos) + self.octave_base,
                            vel=velocity
                        )
            else:
                # Modo libre/songs: reproducir todas las teclas
                if np.any(on_map):
                    for k_pos, on_key in enumerate(on_map):
                        if on_key:
                            # RECUPERAR VELOCIDAD CALCULADA (fallback a 80)
                            velocity = getattr(self.km, 'active_velocities', {}).get(k_pos, 80)
                            print(f"♪ NOTE ON: {k_pos} (Vel: {velocity})")
                            self.synth.noteon(
                                chan=0,
                                key=virtual_keyboard.note_from_key(k_pos) + self.octave_base,
                                vel=velocity
                            )
                
                if np.any(off_map):
                    for k_pos, off_key in enumerate(off_map):
                        if off_key:
                            self.synth.noteoff(
                                chan=0,
                                key=virtual_keyboard.note_from_key(k_pos) + self.octave_base
                            )
        
        # === PASO 7: Dibujar centros de cámara ===
        # Solo dibujamos crosshairs si está habilitado en config (opcional)
        # self.angler.frame_add_crosshairs(frame_draw) 
        
        return frame_draw, frame_right
    
    def _calculate_depth(self, finger_left, finger_right):
        """
        Calcula la profundidad 3D de un dedo usando triangulación
        
        Args:
            finger_left: Datos del dedo en cámara izquierda (hand_id, tip_id, x, y)
            finger_right: Datos del dedo en cámara derecha (hand_id, tip_id, x, y)
            
        Returns:
            float: Profundidad corregida en cm
        """
        if self.use_stereo_calibration and self.depth_estimator:
            # ========== MÉTODO PRECISO: Calibración Estéreo ==========
            try:
                point_left = (finger_left[2], finger_left[3])
                point_right = (finger_right[2], finger_right[3])
                
                # 1. Rectificar puntos antes de triangular
                pt_l_rect = self.depth_estimator.rectify_point(point_left, 'left')
                pt_r_rect = self.depth_estimator.rectify_point(point_right, 'right')
                
                # Triangular con calibración completa
                result_3d = self.depth_estimator.triangulate_point(pt_l_rect, pt_r_rect)
                
                if result_3d is not None:
                    X_raw, Y_raw, Z_raw = result_3d
                    
                    # NOTA: El factor de corrección ya se aplica dentro de DepthEstimator
                    X_local = X_raw
                    Y_local = Y_raw
                    Z_local = Z_raw 
                    
                    # APLICAR SUAVIZADO TEMPORAL para reducir jitter
                    finger_id = (finger_left[0], finger_left[1])
                    
                    # Inicializar buffer de suavizado si no existe
                    if finger_id not in self.depth_estimator.finger_position_history:
                        self.depth_estimator.finger_position_history[finger_id] = deque(maxlen=5)
                    
                    # Agregar posición actual al buffer
                    self.depth_estimator.finger_position_history[finger_id].append(
                        (X_local, Y_local, Z_local)
                    )
                    
                    # Calcular promedio de últimas 5 posiciones
                    if len(self.depth_estimator.finger_position_history[finger_id]) > 0:
                        history = np.array(list(self.depth_estimator.finger_position_history[finger_id]))
                        X_local, Y_local, Z_local = np.mean(history, axis=0)
                    
                    return Z_local  # Profundidad = coordenada Z
                else:
                    # Fallback si falla triangulación
                    return 0
            except Exception as e:
                # Fallback al método de ángulos si hay error
                return self._triangulate_angles(finger_left, finger_right)
        else:
            # ========== MÉTODO FALLBACK: Triangulación por ángulos ==========
            return self._triangulate_angles(finger_left, finger_right)
    
    def _triangulate_angles(self, finger_left, finger_right):
        """
        Triangulación usando ángulos (método fallback)
        
        Args:
            finger_left: Datos del dedo en cámara izquierda
            finger_right: Datos del dedo en cámara derecha
            
        Returns:
            float: Profundidad corregida en cm
        """
        # Obtener ángulos desde los centros de cámara
        xlangle, ylangle = self.angler.angles_from_center(
            x=finger_left[2], y=finger_left[3],
            top_left=True, degrees=True
        )
        xrangle, yrangle = self.angler.angles_from_center(
            x=finger_right[2], y=finger_right[3],
            top_left=True, degrees=True
        )
        
        # Triangular
        X_local, Y_local, Z_local, D_local = self.angler.location(
            self.camera_separation,
            (xlangle, ylangle),
            (xrangle, yrangle),
            center=True,
            degrees=True
        )
        
        # Normalización de ángulo
        delta_y = (0.006509695290859 * X_local * X_local + 
                  0.039473684210526 * -1 * X_local)
        depth_corrected = D_local - delta_y
        
        return depth_corrected

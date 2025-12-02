#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 22 15:27:37 2021
Proyecto de Integracion: Virtual Piano Keyboard

Fuentes:
    OpenCV
    https://opencv.org/

    Clayton Darwin
    https://www.youtube.com/watch?v=sW4CVI51jDY

    Nicolai Høirup Nielsen  (The Coding Lib)
    https://github.com/niconielsen32/ComputerVision/tree/master/StereoVisionDepthEstimation
    https://www.youtube.com/watch?v=t3LOey68Xpg -


    Kaustubh Sadekar - Satya Mallick
    https://learnopencv.com/making-a-low-cost-stereo-camera-using-opencv/#steps-to-create-the-stereo-camera-setup

    Fernando Souza
    https://medium.com/vacatronics/3-ways-to-calibrate-your-camera-using-opencv-and-python-395528a51615

    Daniel Lee
    https://erget.wordpress.com/2014/02/28/calibrating-a-stereo-pair-with-python/
    https://erget.wordpress.com/2014/02/01/calibrating-a-stereo-camera-with-opencv/


    LearnTechWithUs
    https://github.com/LearnTechWithUs/Stereo-Vision/issues/10

    Najam R. Syed
    https://nrsyed.com/2018/07/05/multithreading-with-opencv-python-to-improve-video-processing-performance/

    Murtaza's Workshop - Robotics and AI
    https://www.youtube.com/watch?v=NZde8Xt78Iw

    Google -Mediapipe
    https://ai.googleblog.com/2019/08/on-device-real-time-hand-tracking-with.html


    Nathan Whitehead
    https://github.com/nwhitehead/pyfluidsynth

    y otros

    Referencias:
    Python
    https://www.python.org/dev/peps/pep-0008/#package-and-module-names


# TODOES:
# TODO1: Crear una cola (queue) para estabilizar con un promedio la posición xy de los dedos
# TODO2: Calcular distancia angular para detectar cuando un dedo está bajo el umbral para tocar la tecla virtual
# TODO3: Incluir todos los dedos al mapa de XY + Depth
# TODO4: Mejorar performance, primera opcion GPU, y optimización

@author: mherrera
"""

import time
import traceback
import cv2
import numpy as np
import fluidsynth

# --- Vision ---
from src.vision import video_thread, angles
from src.vision.hand_detector import HandDetector
from src.vision import keyboard_mapper as kbm
from src.vision.stereo_config import StereoConfig

# --- Calibration ---
from src.calibration import CalibrationManager

# --- Piano ---
from src.piano import virtual_keyboard as vkb
from src.piano.virtual_keyboard import VirtualKeyboard

# --- Gameplay ---
from src.gameplay.rythm_game import RhythmGame
from src.gameplay.song_chart import TUTORIAL_FACIL

# --- UI ---
from src.ui.ui_helper import UIHelper

# --- Theory ---
from src.theory import get_lesson_manager, TheoryUI

# --- Common ---
from src.common.toolbox import round_half_up

def frame_add_crosshairs(frame,
                         x,
                         y,
                         r=20,
                         lc=(0, 0, 255),
                         cc=(0, 0, 255),
                         lw=2,
                         cw=1):

    x = int(round(x, 0))
    y = int(round(y, 0))
    r = int(round(r, 0))

    cv2.line(frame, (x, y-r*2), (x, y+r*2), lc, lw)
    cv2.line(frame, (x-r*2, y), (x+r*2, y), lc, lw)

    cv2.circle(frame, (x, y), r, cc, cw)

def show_calibration_menu(ui_helper, pixel_width, pixel_height):
    """Muestra menú de configuración inicial y retorna la opción seleccionada"""
    window_name = 'Configuración Inicial'
    cv2.namedWindow(window_name)
    cv2.moveWindow(window_name, (pixel_width//2), (pixel_height//2))
    
    while True:
        # Frame negro para el menú
        menu_frame = np.zeros((pixel_height, pixel_width * 2, 3), dtype=np.uint8)
        menu_frame = ui_helper.draw_setup_menu(menu_frame)
        cv2.imshow(window_name, menu_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('1'):
            cv2.destroyWindow(window_name)
            return 1  # Usar calibración guardada
        elif key == ord('2'):
            cv2.destroyWindow(window_name)
            return 2  # Nueva calibración
        elif key == ord('3'):
            cv2.destroyWindow(window_name)
            return 3  # Saltar (valores por defecto)
        elif key == ord('q'):
            cv2.destroyWindow(window_name)
            return None  # Salir

def run_calibration_process(ui_helper, pixel_width, pixel_height, config):
    """Ejecuta el proceso de calibración con el nuevo sistema profesional"""
    try:
        # Crear gestor de calibración
        calibration_manager = CalibrationManager(
            cam_left_id=config.LEFT_CAMERA_SOURCE,
            cam_right_id=config.RIGHT_CAMERA_SOURCE,
            resolution=(pixel_width, pixel_height)
        )
        
        # Ejecutar calibración completa (Fase 1)
        success = calibration_manager.run_full_calibration()
        
        if not success:
            print("✗ Calibración fallida o cancelada")
            return False
        
        # Solicitar parámetros adicionales (separación y distancia del teclado)
        window_name = 'Configuración Adicional'
        cv2.namedWindow(window_name)
        cv2.moveWindow(window_name, (pixel_width//2), (pixel_height//2))
        
        calib_frame = np.zeros((pixel_height, pixel_width * 2, 3), dtype=np.uint8)
        
        # Solicitar separación entre cámaras
        input_value = ""
        
        while True:
            display_frame = calib_frame.copy()
            display_frame = ui_helper.draw_input_dialog(
                display_frame,
                "Distancia entre camaras (cm):",
                input_value
            )
            cv2.imshow(window_name, display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 13:  # ENTER
                try:
                    separation = float(input_value)
                    if 1 < separation < 50:
                        config.CAMERA_SEPARATION = separation
                        break
                    else:
                        input_value = ""
                except ValueError:
                    input_value = ""
            elif key == 8 and len(input_value) > 0:  # BACKSPACE
                input_value = input_value[:-1]
            elif 48 <= key <= 57:  # Números 0-9
                input_value += chr(key)
            elif key == 46:  # Punto decimal
                if '.' not in input_value:
                    input_value += '.'
            elif key == ord('q'):
                cv2.destroyWindow(window_name)
                return False
        
        # Solicitar distancia del teclado
        input_value = ""
        
        while True:
            display_frame = calib_frame.copy()
            display_frame = ui_helper.draw_input_dialog(
                display_frame,
                "Distancia del teclado (cm):",
                input_value
            )
            cv2.imshow(window_name, display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 13:  # ENTER
                try:
                    kb_distance = float(input_value)
                    if 30 < kb_distance < 200:
                        config.VKB_CENTER_DISTANCE = kb_distance
                        break
                    else:
                        input_value = ""
                except ValueError:
                    input_value = ""
            elif key == 8 and len(input_value) > 0:  # BACKSPACE
                input_value = input_value[:-1]
            elif 48 <= key <= 57:  # Números 0-9
                input_value += chr(key)
            elif key == 46:  # Punto decimal
                if '.' not in input_value:
                    input_value += '.'
            elif key == ord('q'):
                cv2.destroyWindow(window_name)
                return False
        
        # Mensaje de éxito
        calib_frame = ui_helper.draw_calibration_progress(
            calib_frame,
            "Configuracion completada!",
            100
        )
        cv2.imshow(window_name, calib_frame)
        cv2.waitKey(2000)
        
        cv2.destroyWindow(window_name)
        return True
        
    except Exception as e:
        print(f"✗ Error durante calibración: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():

    try:
        # Cargar configuración estéreo centralizada
        config = StereoConfig()
        
        # Dimensiones para la interfaz
        pixel_width = config.PIXEL_WIDTH
        pixel_height = config.PIXEL_HEIGHT
        
        # Inicializar UI Helper para menú de configuración
        ui_helper_menu = UIHelper(pixel_width * 2, pixel_height)
        ui_helper_menu.show_instructions = False  # No mostrar bienvenida aún
        
        # Mostrar menú de configuración
        setup_option = show_calibration_menu(ui_helper_menu, pixel_width, pixel_height)
        
        if setup_option is None:
            print("Saliendo...")
            return
        elif setup_option == 1:
            # Usar calibración guardada
            print("Cargando calibración guardada...")
            loaded = config.load_calibration()
            if not loaded:
                print("⚠ No se pudo cargar calibración. Usando valores por defecto.")
        elif setup_option == 2:
            # Nueva calibración
            print("Iniciando proceso de calibración...")
            success = run_calibration_process(ui_helper_menu, pixel_width, pixel_height, config)
            if not success:
                print("⚠ Calibración cancelada. Usando valores por defecto.")
        else:  # setup_option == 3
            print("Usando valores por defecto (sin calibración)")
        
        config.print_config()

        # ------------------------------
        # set up cameras
        # ------------------------------

        # cameras variables
        left_camera_source = config.LEFT_CAMERA_SOURCE
        right_camera_source = config.RIGHT_CAMERA_SOURCE
        pixel_width = config.PIXEL_WIDTH
        pixel_height = config.PIXEL_HEIGHT

        # Logi C920s HD Pro Webcam - Calibración óptica
        camera_hFoV = config.CAMERA_H_FOV
        camera_vFoV = config.CAMERA_V_FOV
        hFoV_angle_rectification = config.H_FOV_RECTIFICATION
        vFoV_angle_rectification = config.V_FOV_RECTIFICATION

        angle_width = config.ANGLE_WIDTH
        angle_height = config.ANGLE_HEIGHT

        # FPS
        frame_rate = config.FRAME_RATE
        camera_separation = config.CAMERA_SEPARATION

        camera_in_front_of_you = config.CAMERA_IN_FRONT_OF_YOU

        # Virtual Keyboard Center point distance (cms)
        vkb_center_point_camera_dist = config.VKB_CENTER_DISTANCE

            # cam_resource = video_thread.VideoThread(
            #     video_source=c_id,
            #     video_width=pixel_width,
            #     video_height=pixel_height,
            #     video_frame_rate=frame_rate,
            #     buffer_all=False,
            #     try_to_reconnect=False
            # )
        # left camera 1
        cam_left = video_thread.VideoThread(
            video_source=left_camera_source,
            video_width=pixel_width,
            video_height=pixel_height,
            video_frame_rate=frame_rate,
            buffer_all=False,
            try_to_reconnect=False)

        # right camera 2
        cam_right = video_thread.VideoThread(
            video_source=right_camera_source,
            video_width=pixel_width,
            video_height=pixel_height,
            video_frame_rate=frame_rate,
            buffer_all=False,
            try_to_reconnect=False)

        # start cameras
        cam_left.start()
        cam_right.start()

        time.sleep(1)
        if camera_in_front_of_you:
            main_window_name = 'In fron of you: rigth+left cam'
        else:
            main_window_name = 'Same Point of View: left+rigth cam'

        cv2.namedWindow(main_window_name)
        cv2.moveWindow(main_window_name,
                       (pixel_width//2),
                       (pixel_height//2))        
        
        if cam_left.is_available():
            print('Name:{}'.format(main_window_name))
            print('cam_left.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE:{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE)))
            print('cam_left.resource.get(cv2.CAP_PROP_EXPOSURE:{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_EXPOSURE)))
            print('cam_left.resource.get(cv2.CAP_PROP_AUTOFOCUS):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_AUTOFOCUS)))
            print('cam_left.resource.get(cv2.CAP_PROP_BUFFERSIZE):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_BUFFERSIZE)))
            print('cam_left.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)))

            print('cam_left.resource.get(cv2.CAP_PROP_HW_DEVICE):{}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_HW_DEVICE)))
            print('cam_left.resource.get(cv2.CAP_PROP_FRAME_COUNT):{:03f}'.
                  format(cam_left.resource.get(cv2.CAP_PROP_FRAME_COUNT)))
                

        if cam_right.is_available():
            print('Name:{}'.format(main_window_name))
            print('cam_right.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE:{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_AUTO_EXPOSURE)))
            print('cam_right.resource.get(cv2.CAP_PROP_EXPOSURE:{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_EXPOSURE)))
            print('cam_right.resource.get(cv2.CAP_PROP_AUTOFOCUS):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_AUTOFOCUS)))
            print('cam_right.resource.get(cv2.CAP_PROP_BUFFERSIZE):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_BUFFERSIZE)))
            print('cam_right.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)))

            print('cam_right.resource.get(cv2.CAP_PROP_HW_DEVICE):{}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_HW_DEVICE)))
            print('cam_right.resource.get(cv2.CAP_PROP_FRAME_COUNT):{:03f}'.
                  format(cam_right.resource.get(cv2.CAP_PROP_FRAME_COUNT)))


        # left_window_name = 'frame left'
        # cv2.namedWindow(left_window_name)
        # cv2.moveWindow(left_window_name,
        #                (pixel_width//2),
        #                (pixel_height//2))

        # right_window_name = 'frame right'
        # cv2.namedWindow(right_window_name)
        # cv2.moveWindow(right_window_name,
        #                (pixel_width//2)+640,
        #                (pixel_height//2))



        # ------------------------------
        # set up virtual keyboards
        # ------------------------------

        N_BANK = 0
        N_MAYOR_NOTES_X_BANK = 0

        KEYBOARD_WHIITE_N_KEYS = config.KEYBOARD_WHITE_KEYS

        KEYBOARD_TOT_KEYS = config.KEYBOARD_TOTAL_KEYS
        print('KEYBOARD_TOT_KEYS:{}'.format(KEYBOARD_TOT_KEYS))
        octave_base = config.OCTAVE_BASE

        vk_left = vkb.VirtualKeyboard(pixel_width, pixel_height,
                                      KEYBOARD_WHIITE_N_KEYS)
        vk_right = vkb.VirtualKeyboard(pixel_width, pixel_height,
                                      KEYBOARD_WHIITE_N_KEYS)
        # Inicializar juego de ritmo
        rhythm_game = RhythmGame(num_keys=KEYBOARD_TOT_KEYS)
        game_mode = False  # False = modo libre, True = modo juego
        
        # Inicializar módulo de teoría
        lesson_manager = get_lesson_manager()
        theory_ui = TheoryUI(pixel_width * 2, pixel_height)
        theory_mode = False  # False = otros modos, True = modo teoría
        in_lesson = False  # True cuando está dentro de una lección
        current_lesson = None
        current_lesson_id = None

        # ------------------------------
        # set up keyboards map
        # -----------------------------
        km = kbm.KeyboardMap(depth_threshold=config.DEPTH_THRESHOLD)

        # ------------------------------
        # set up angles
        # ------------------------------
        # cameras are the same, so only 1 needed
        angler = angles.Frame_Angles(pixel_width, pixel_height, angle_width,
                                     angle_height)
        angler.build_frame()

        left_detector = HandDetector(staticImageMode=False,
                                                  detectionCon=config.HAND_DETECTION_CONFIDENCE,
                                                  trackCon=config.HAND_TRACKING_CONFIDENCE)
        right_detector = HandDetector(staticImageMode=False,
                                                   detectionCon=config.HAND_DETECTION_CONFIDENCE,
                                                   trackCon=config.HAND_TRACKING_CONFIDENCE)

        # ------------------------------
        # set up synth
        # ------------------------------

        fs = fluidsynth.Synth()
        fs.start(driver='dsound') # Windows
        sfid = fs.sfload(config.SOUNDFONT_PATH)


        # 000-000 Yamaha Grand Piano
        fs.program_select(chan=0, sfid=sfid, bank=0, preset=0)

        # # 008-014 Church Bell
        # fs.program_select(chan=0, sfid=sfid, bank=8, preset=14)
        # # 008-026 Hawaiian Guitar
        # fs.program_select(chan=0, sfid=sfid, bank=8, preset=26)
        # # Standard
        # fs.program_select(chan=0, sfid=sfid, bank=128, preset=0)
        # # 000-103 Star Theme
        # fs.program_select(chan=0, sfid=sfid, bank=0, preset=103)

        # ------------------------------
        # stabilize
        # ------------------------------
        time.sleep(0.5)

        # variables
        # ------------------------------

        # length of target queues, positive target frames required
        # to reset set X,Y,Z,D
        queue_len = 3

        # target queues
        #fingers_left_queue, y1k = [], []
        #fingers_right_queue, y2k = [], []
        x_left_finger_screen_pos = 0
        y_left_finger_screen_pos = 0
        

        # mean values to stabilize the coordinates
        # x1m, y1m, x2m, y2m = 0, 0, 0, 0
        # X1_left_hand_ref, Y1_left_hand_ref = 0, 0
        
        # last positive target
        # from camera baseline midpoint
        X, Y, Z, D, = 0, 0, 0, 0
        delta_y = 0

        cycles = 0
        fps = 0
        start = time.time()
        display_dashboard = config.DISPLAY_DASHBOARD_DEFAULT
        finger_depths_dict = {}  # Inicializar para evitar referencias no definidas
        
        # Inicializar UI Helper
        ui_helper = UIHelper(pixel_width * 2, pixel_height)  # Ancho total de ambas cámaras
        
        # Optimización: cachear transformaciones de flip
        while True:
            cycles += 1
            # get frames - reducir wait en modo juego para mejor respuesta
            wait_time = 0.0 if game_mode else 0.1  # Sin delay en modo juego
            finished_left, frame_left = cam_left.next(black=True, wait=wait_time)
            finished_right, frame_right = cam_right.next(black=True, wait=wait_time)

            # Aplicar flip una sola vez al principio (Selfie point of view)
            frame_left = cv2.flip(frame_left, -1)
            frame_right = cv2.flip(frame_right, -1)

            hands_left_image = fingers_left_image = []
            hands_right_image = fingers_right_image = []

            # Dibujar teclado siempre
            vk_left.draw_virtual_keyboard(frame_left)
            
            # Detect Hands
            if left_detector.findHands(frame_left):
                left_detector.drawHands(frame_left)
                left_detector.drawTips(frame_left)
                
                hands_left_image, fingers_left_image = \
                    left_detector.getFingerTipsPos()
            else:
                hands_left_image = fingers_left_image = []

            if right_detector.findHands(frame_right):
                #vk_right.draw_virtual_keyboard(frame_right)
                right_detector.drawHands(frame_right)
                right_detector.drawTips(frame_right)

                hands_right_image, fingers_right_image = \
                    right_detector.getFingerTipsPos()

            # check 1: motion in both frames:
            if (len(fingers_left_image) > 0 and len(fingers_right_image) > 0):

                fingers_dist = []
                finger_depths_dict = {}  # Dict para pasar profundidades a KeyboardMap
                
                for finger_left, finger_right in \
                    zip(fingers_left_image, fingers_right_image):
                    # print('finger_left:{}'.format(finger_left))
                    # print('finger_right:{}'.format(finger_right))
                    # get angles from camera centers
                    xlangle, ylangle = angler.angles_from_center(
                        x = finger_left[2], y = finger_left[3],
                        top_left=True, degrees=True)
                    xrangle, yrangle = angler.angles_from_center(
                        x = finger_right[2], y = finger_right[3],
                        top_left=True, degrees=True)

                    # triangulate
                    X_local, Y_local, Z_local, D_local = angler.location(
                        camera_separation,
                        (xlangle, ylangle),
                        (xrangle, yrangle),
                        center=True,
                        degrees=True)
                    # angle normalization
                    delta_y = 0.006509695290859 * X_local * X_local + \
                        0.039473684210526 * -1 * X_local # + vkb_center_point_camera_dist
                    depth_corrected = D_local - delta_y
                    fingers_dist.append(depth_corrected)
                    
                    # Guardar profundidad corregida para cada dedo
                    finger_id = (finger_left[0], finger_left[1])
                    finger_depths_dict[finger_id] = depth_corrected
                    
                    # if finger_left[0] == 0 and 
                    if finger_left[0] == 0 and finger_left[1] == left_detector.mpHands.HandLandmark.INDEX_FINGER_TIP:
                        x_left_finger_screen_pos =  finger_left[2]
                        y_left_finger_screen_pos = finger_left[3]
                        X = X_local
                        Y = Y_local
                        Z = Z_local
                        D = D_local
                        

                on_map, off_map = km.get_kayboard_map(
                    virtual_keyboard=vk_left,
                    fingertips_pos=fingers_left_image,
                    finger_depths=finger_depths_dict,  # Pasar profundidades 3D
                    keyboard_n_key=KEYBOARD_TOT_KEYS)
                
                if game_mode:
                    # Actualizar juego ANTES de verificar hits para mejor sincronización
                    rhythm_game.update()
                    
                    # Verificar aciertos cuando se presiona una tecla - optimizado
                    # Solo verificar teclas que están activas (más eficiente)
                    active_keys = np.where(on_map)[0]
                    for k_pos in active_keys:
                        hit_result = rhythm_game.check_hit(k_pos)
                        if hit_result:
                            print(f"Tecla {k_pos}: {hit_result}")
                            # Reproducir audio solo en modo juego
                            fs.noteon(
                                chan=0,
                                key=vk_left.note_from_key(k_pos)+octave_base,
                                vel=127*2//3)
                    
                    # Dibujar el juego de ritmo sobre el frame
                    frame_left = rhythm_game.draw(
                        frame_left, 
                        vk_left.kb_x0, 
                        vk_left.kb_x1,
                        vk_left.white_key_width
                    )
                else:
                    # Modo libre: reproducir audio en todas las teclas
                    if np.any(on_map):
                        for k_pos, on_key in enumerate(on_map):
                            if on_key:
                                fs.noteon(
                                    chan=0,
                                    key=vk_left.note_from_key(k_pos)+octave_base,
                                    vel=127*2//3)

                    if np.any(off_map):
                        for k_pos, off_key in enumerate(off_map):
                            if off_key:
                                fs.noteoff(
                                    chan=0,
                                    key=vk_left.note_from_key(k_pos)+octave_base
                                    )

            # display camera centers
            angler.frame_add_crosshairs(frame_left)
            angler.frame_add_crosshairs(frame_right)

            # Actualizar UI Helper
            ui_helper.update()
            
            # === MODO TEORÍA ===
            if theory_mode:
                if in_lesson and current_lesson:
                    # Ejecutar lección activa
                    frame_left, frame_right, continue_lesson = current_lesson.run(
                        frame_left, frame_right, vk_left, fs,
                        left_detector, right_detector
                    )
                    
                    if not continue_lesson:
                        # Salir de la lección
                        current_lesson.stop()
                        in_lesson = False
                        current_lesson = None
                        print("Saliendo de la lección...")
                else:
                    # Mostrar menú de lecciones
                    lessons = lesson_manager.get_all_lessons()
                    if camera_in_front_of_you:
                        h_frames = np.concatenate((frame_right, frame_left), axis=1)
                    else:
                        h_frames = np.concatenate((frame_left, frame_right), axis=1)
                    
                    h_frames = theory_ui.draw_lesson_menu(h_frames, lessons)
                    cv2.imshow(main_window_name, h_frames)
                    
                    # Manejar teclas del menú
                    key = cv2.waitKey(1) & 0xFF
                    # Flecha arriba (múltiples códigos para compatibilidad)
                    if key == 82 or key == ord('w') or key == ord('W'):  # Flecha arriba o W
                        theory_ui.navigate_up(len(lessons))
                        print(f"Navegando: lección {theory_ui.get_selected_index() + 1}/{len(lessons)}")
                    # Flecha abajo
                    elif key == 84 or key == ord('s') or key == ord('S'):  # Flecha abajo o S
                        theory_ui.navigate_down(len(lessons))
                        print(f"Navegando: lección {theory_ui.get_selected_index() + 1}/{len(lessons)}")
                    # Números 1-9 para selección directa
                    elif 49 <= key <= 57:  # Teclas 1-9
                        selected_idx = key - 49  # Convertir a índice (0-8)
                        if 0 <= selected_idx < len(lessons):
                            lesson_id, lesson = lessons[selected_idx]
                            current_lesson = lesson
                            current_lesson_id = lesson_id
                            current_lesson.start()
                            in_lesson = True
                            print(f"Iniciando lección: {lesson.name}")
                    # ENTER
                    elif key == 13:  # ENTER
                        selected_idx = theory_ui.get_selected_index()
                        if 0 <= selected_idx < len(lessons):
                            lesson_id, lesson = lessons[selected_idx]
                            current_lesson = lesson
                            current_lesson_id = lesson_id
                            current_lesson.start()
                            in_lesson = True
                            print(f"Iniciando lección: {lesson.name}")
                    elif key == ord('q') or key == ord('Q'):
                        theory_mode = False
                        theory_ui.reset_selection()
                        print("Saliendo del modo teoría...")
                    elif key == 27:  # ESC
                        theory_mode = False
                        theory_ui.reset_selection()
                    elif key != 255:  # Mostrar código de cualquier otra tecla para debug
                        print(f"Tecla presionada en menú teoría: código {key}")
                    continue  # Saltar el resto del loop principal
            
            # Combinar frames antes de procesar UI
            if camera_in_front_of_you:
                h_frames = np.concatenate((frame_right, frame_left), axis=1)
            else:
                h_frames = np.concatenate((frame_left, frame_right), axis=1)
            
            # Mostrar pantalla de bienvenida si es necesario
            if ui_helper.show_instructions:
                welcome_frame = np.zeros((pixel_height, pixel_width * 2, 3), dtype=np.uint8)
                welcome_frame = ui_helper.draw_welcome_screen(welcome_frame)
                cv2.imshow(main_window_name, welcome_frame)
                
                # Esperar a que se presione una tecla para continuar
                key = cv2.waitKey(1) & 0xFF
                if key != 255:  # Cualquier tecla
                    ui_helper.show_instructions = False
                    ui_helper.frame_count = ui_helper.instructions_timeout  # No volver a mostrar
                continue

            if display_dashboard:
                # Display dashboard data
                fps1 = int(cam_left.current_frame_rate)
                fps2 = int(cam_right.current_frame_rate)
                cps_avg = int(round_half_up(fps))  # Average Cycles per second
                text = 'X: {:3.1f}\nY: {:3.1f}\nZ: {:3.1f}\nD: {:3.1f}\nDr: {:3.1f}\nDepth Thr: {:.2f}\nFPS:{}/{}\nCPS:{}'.format(X, Y, Z, D, D-delta_y, km.depth_threshold, fps1, fps2, cps_avg)
                lineloc = 0
                lineheight = 30
                for t in text.split('\n'):
                    lineloc += lineheight
                    cv2.putText(frame_left,
                                t,
                                (10, lineloc),              # location
                                cv2.FONT_HERSHEY_PLAIN,     # font
                                # cv2.FONT_HERSHEY_SIMPLEX, # font
                                1.5,                        # size
                                (0, 255, 0),                # color
                                2,                          # line width
                                cv2.LINE_AA,
                                False)
                
                # Re-combinar frames después de actualizar el izquierdo
                if camera_in_front_of_you:
                    h_frames = np.concatenate((frame_right, frame_left), axis=1)
                else:
                    h_frames = np.concatenate((frame_left, frame_right), axis=1)

            # Display current target
            # if fingers_left_queue:
            #     frame_add_crosshairs(frame_left, x1m, y1m, 24)
            #     frame_add_crosshairs(frame_right, x2m, y2m, 24)

            # if fingers_left_queue:
            #     frame_add_crosshairs(frame_left, x1m, y1m, 24)
            #     frame_add_crosshairs(frame_right, x2m, y2m, 24)
            # if X > 0 and Y > 0:
            frame_add_crosshairs(frame_left, x_left_finger_screen_pos, y_left_finger_screen_pos, 24)
            # Pendiente : ...frame_add_crosshairs(frame_right, x_left_finger_screen_pos, y_left_finger_screen_pos, 24)



            # Display frames
            cv2.imshow(main_window_name, h_frames)



            if (cycles % 10 == 0):
                # End time
                end = time.time()
                # Time elapsed
                seconds = end - start
                # print ("Time taken : {0} seconds".format(seconds))
                # Calculate frames per second
                fps = 10 / seconds
                start = time.time()

            # Detect control keys
            key = cv2.waitKey(1) & 0xFF
            if cv2.getWindowProperty(
                main_window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
            elif key == ord('q'):
                break
            elif key == ord('d'):
                if display_dashboard:
                    display_dashboard = False
                else:
                    display_dashboard = True
            elif key == ord('g'):  # ========== NUEVA TECLA ==========
                game_mode = True
                rhythm_game.start_game(TUTORIAL_FACIL)
                print("¡Juego de ritmo iniciado! Presiona 'f' para volver al modo libre")
                ui_helper.reset_instructions()  # Mostrar instrucciones del juego
            elif key == ord('f'):  # ========== NUEVA TECLA ==========
                # Detener juego si está activo
                if game_mode and rhythm_game.is_playing:
                    rhythm_game.stop_game()
                game_mode = False
                theory_mode = False
                print("Modo libre activado")
                ui_helper.reset_instructions()  # Mostrar instrucciones del modo libre
            elif key == ord('l'):  # ========== MODO TEORÍA ==========
                theory_mode = True
                game_mode = False
                if rhythm_game.is_playing:
                    rhythm_game.stop_game()
                theory_ui.reset_selection()
                print("¡Modo Teoría activado! Selecciona una lección. Presiona Q para salir.")
            elif key == ord('t'):  # Subir nivel de mesa (ESTÉREO: aumentar umbral de profundidad)
                new_threshold = km.depth_threshold + 0.2
                km.set_depth_threshold(new_threshold)
                print(f"Umbral de profundidad aumentado a: {new_threshold:.2f} cm")
            elif key == ord('b'):  # Bajar nivel de mesa (ESTÉREO: disminuir umbral de profundidad)
                new_threshold = max(0.5, km.depth_threshold - 0.2)
                km.set_depth_threshold(new_threshold)
                print(f"Umbral de profundidad disminuido a: {new_threshold:.2f} cm")
            elif key == ord('p'):  # Mostrar profundidades detectadas
                if display_dashboard:
                    print(f"Profundidades detectadas (D - delta_y):")
                    for fid, depth in finger_depths_dict.items():
                        print(f"  Dedo {fid}: {depth:.2f} cm")
            elif key == 27 and in_lesson:  # ESC dentro de lección
                if current_lesson:
                    current_lesson.stop()
                in_lesson = False
                current_lesson = None
                print("Volviendo al menú de lecciones...")
            elif in_lesson and current_lesson:  # Pasar teclas a la lección activa
                current_lesson.handle_key(key, fs, octave_base)
            elif key != 255:
                print('KEY PRESS:', [chr(key)])

    # ------------------------------
    # full error catch
    # ------------------------------
    except Exception:
        print(traceback.format_exc())

    # ------------------------------
    # close all
    # ------------------------------

    # Fluidsynth
    try:
        fs.delete()
    except Exception:
        pass
    # close camera1
    try:
        cam_left.stop()
    except Exception:
        pass

    # close camera2
    try:
        cam_right.stop()
    except Exception:
        pass

    # kill frames
    cv2.destroyAllWindows()

    # done
    print('DONE')


# ------------------------------
# Call to Main
# ------------------------------

if __name__ == '__main__':
    main()

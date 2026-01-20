#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 00:03:20 2021

Se asume que la relación entre lista de manos detectadas y los landmark
tienen una relación de posición. Se detecta que no existe una relación entre
hand.index y el primer campo del landmark (asumido como tip_id).

@author: mherrera
"""

import mediapipe as mp
import cv2


class HandDetector():

    # Indices de landmarks de MediaPipe Hands
    # 0: MUNECA
    # 1-4: PULGAR (CMC, MCP, IP, TIP)
    # 5-8: INDICE (MCP, PIP, DIP, TIP)
    # 9-12: MEDIO (MCP, PIP, DIP, TIP)
    # 13-16: ANULAR (MCP, PIP, DIP, TIP)
    # 17-20: MENIQUE (MCP, PIP, DIP, TIP)

    def __init__(self, staticImageMode=False, maxHands=2, detectionCon=0.5,
                 trackCon=0.5, img_width=640, img_height=480):

        self.mode = staticImageMode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon
        self.img_width = img_width
        self.img_height = img_height

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.maxHands,
            model_complexity=0,  # [OPTIMIZACIÓN] 0=Lite (Rápido), 1=Full. Usamos Lite para menor latencia.
            min_detection_confidence=self.detectionCon,
            min_tracking_confidence=self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils

        self.results = []

        self.fingerTips = [self.mpHands.HandLandmark.THUMB_TIP,
                           self.mpHands.HandLandmark.INDEX_FINGER_TIP,
                           self.mpHands.HandLandmark.MIDDLE_FINGER_TIP,
                           self.mpHands.HandLandmark.RING_FINGER_TIP,
                           self.mpHands.HandLandmark.PINKY_TIP
                           ]

    def setImageDims(self, width, height):
        self.__image_width = width
        self.__image_height = height

    def findHands(self, img):

        # Para mejorar el rendimiento, opcionalmente marcar la imagen como no escribible
        # para pasar por referencia.
        img.flags.writeable = False
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img.flags.writeable = True

        self.results = self.hands.process(imgRGB)

        # print(results.multi_hand_landmark)
        found = False
        if self.results.multi_handedness:
            # print('{}:multi_handedness:\n{}'.format(
            #     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            #     self.results.multi_handedness))
            found = True
        return found

    def drawHands(self, img, mirror=False, rotate_180=False):
        """
        Dibuja las conexiones de las manos en la imagen.
        
        Args:
            img: Imagen donde dibujar
            mirror: Si es True, invierte X (modo espejo)
            rotate_180: Si es True, invierte X e Y (modo rotación 180)
        """
        if self.results.multi_hand_landmarks:
            for handLandmarks in self.results.multi_hand_landmarks:
                if rotate_180:
                    import copy
                    modified_landmarks = copy.deepcopy(handLandmarks)
                    for lm in modified_landmarks.landmark:
                        lm.x = 1.0 - lm.x
                        lm.y = 1.0 - lm.y
                    self.mpDraw.draw_landmarks(img, modified_landmarks, self.mpHands.HAND_CONNECTIONS)
                elif mirror:
                    import copy
                    modified_landmarks = copy.deepcopy(handLandmarks)
                    for lm in modified_landmarks.landmark:
                        lm.x = 1.0 - lm.x
                    self.mpDraw.draw_landmarks(img, modified_landmarks, self.mpHands.HAND_CONNECTIONS)
                else:
                    self.mpDraw.draw_landmarks(img, handLandmarks, self.mpHands.HAND_CONNECTIONS)

    # # TODO: No es necesario pasar la img, solo por w+h???
    # def getJoints(self, img, handNo=0, draw=False):
    #     lmList = []
    #     if self.results.multi_hand_landmarks:
    #         myHand = self.results.multi_hand_landmarks[handNo]
    #         for id, lm in enumerate(myHand.landmark):
    #             # print(id, lm)
    #             h, w, _ = img.shape
    #             cx, cy = int(lm.x*w), int(lm.y*h)
    #             # print(id, cx, cy)
    #             lmList.append([id, cx, cy])
    #             if draw:
    #                 cv2.circle(img, (cx,cy), 7, (255,0,255), cv2.FILLED)
    #     return lmList

    # def drawJoints(self, img):
    #     if self.results.multi_hand_landmarks:
    #         for handLandmarks in self.results.multi_hand_landmarks:
    #             self.mpDraw.draw_landmarks(
    #                 img, handLandmarks,
    #                 self.mpHands.HAND_CONNECTIONS)

    def drawTips(self, img, mirror=False, rotate_180=False):
        if self.results.multi_hand_landmarks:
            # Usar dimensiones del frame real, no las guardadas
            h, w = img.shape[:2]
            
            for id, handLandmarks in enumerate(
                    self.results.multi_hand_landmarks):
                # print('handLandmarks=id:{}'.format(id))
                for indx_tips in self.fingerTips:
                    lx, ly = handLandmarks.landmark[indx_tips].x, handLandmarks.landmark[indx_tips].y
                    
                    if rotate_180:
                        cx = (1.0 - lx) * w
                        cy = (1.0 - ly) * h
                    elif mirror:
                        cx = (1.0 - lx) * w
                        cy = ly * h
                    else:
                        cx = lx * w
                        cy = ly * h
                        
                    cv2.circle(img, (int(cx), int(cy)),
                               7, (255, 0, 0), cv2.FILLED)

                # self.mpHands.HandLandmark.INDEX_FINGER_TIP].x

    def getFingerTipsPos(self, rotate_180=False, img_width=None, img_height=None):
        """
        Obtiene las posiciones de las puntas de los dedos.
        
        Args:
            rotate_180: Si True, transforma las coordenadas para frame rotado 180°
                       (debe coincidir con cómo se dibuja el frame)
            img_width: Ancho del frame (si None, usa self.img_width)
            img_height: Alto del frame (si None, usa self.img_height)
        """
        # Usar dimensiones proporcionadas o las por defecto
        w = img_width if img_width is not None else self.img_width
        h = img_height if img_height is not None else self.img_height
        
        fingertips = []
        if self.results.multi_hand_landmarks:
            for hand_id, handLandmarks in enumerate(
                    self.results.multi_hand_landmarks):
                for indx_tips in self.fingerTips:
                    tip_id = indx_tips
                    lx = handLandmarks.landmark[indx_tips].x
                    ly = handLandmarks.landmark[indx_tips].y
                    
                    if rotate_180:
                        # Transformar igual que drawTips con rotate_180=True
                        cx = (1.0 - lx) * w
                        cy = (1.0 - ly) * h
                    else:
                        cx = lx * w
                        cy = ly * h
                    
                    fingertips.append([hand_id, tip_id, cx, cy])

        hands = []
        if self.results.multi_handedness:
            for handedness in self.results.multi_handedness:
                # print('handedness.classification:\nindex: {}\nscore: {}\nlabel: {}'.\
                #       format(
                #           handedness.classification[0].index,
                #           handedness.classification[0].score,
                #           handedness.classification[0].label
                #     )
                # )
                hands.append(handedness.classification[0])

        return [hands, fingertips]

    def getAllLandmarks(self):
        """
        Retorna una lista de listas con TODOS los landmarks de todas las manos
        en coordenadas de pixel [(x, y), ...].
        Útil para dibujar máscaras de oclusión.
        """
        all_landmarks_px = []
        if self.results.multi_hand_landmarks:
            for handLandmarks in self.results.multi_hand_landmarks:
                hand_px = []
                for lm in handLandmarks.landmark:
                    cx = int(lm.x * self.img_width)
                    cy = int(lm.y * self.img_height)
                    hand_px.append([cx, cy])
                all_landmarks_px.append(hand_px)
        return all_landmarks_px

    # TODO: Obtener la referencia W y H una sola vez sin pasar la img
    def getIndexFingerTipPos(self):
        indexTips = []
        if self.results.multi_hand_landmarks:
            for handLandmarks in self.results.multi_hand_landmarks:
                x = handLandmarks.landmark[
                    self.mpHands.HandLandmark.INDEX_FINGER_TIP].x * \
                    self.img_width
                y = handLandmarks.landmark[
                    self.mpHands.HandLandmark.INDEX_FINGER_TIP].y * \
                    self.img_height
                z = handLandmarks.landmark[
                    self.mpHands.HandLandmark.INDEX_FINGER_TIP].z * \
                    1  # self.img_width

                indexTips.append((x, y, z))

        hands = []
        if self.results.multi_handedness:
            for handedness in self.results.multi_handedness:
                # print('handedness.classification:\nindex: {}\nscore: {}\nlabel: {}'.\
                #       format(
                #           handedness.classification[0].index,
                #           handedness.classification[0].score,
                #           handedness.classification[0].label
                #     )
                # )
                hands.append(handedness.classification[0])

        return hands, indexTips

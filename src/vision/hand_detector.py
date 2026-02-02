import cv2
import mediapipe as mp

class HandDetector:
    def __init__(self, mode=False, maxHands=2, detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(self.mode, self.maxHands,
                                        min_detection_confidence=self.detectionCon,
                                        min_tracking_confidence=self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils
        self.tipIds = [4, 8, 12, 16, 20]
        self.results = None
        
        # COLORES ÚNICOS PARA 10 DEDOS
        self.FINGER_COLORS = {
            (0, 4): (0, 255, 255), (0, 8): (255, 0, 255), (0, 12): (0, 255, 0), (0, 16): (255, 100, 0), (0, 20): (0, 0, 255),
            (1, 4): (255, 255, 0), (1, 8): (128, 0, 255), (1, 12): (0, 128, 0), (1, 16): (255, 0, 128), (1, 20): (0, 0, 128)
        }

    def findHands(self, img, draw=False):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        if self.results.multi_hand_landmarks and draw:
            for handLms in self.results.multi_hand_landmarks:
                self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
        return img if draw else (self.results.multi_hand_landmarks is not None)

    def getFingerTipsPos(self, img_width, img_height, draw=False, img=None, rotate_180=False):
        """
        Obtiene coordenadas de las puntas de los dedos.
        CORRECCIÓN: Ahora acepta 'rotate_180' para evitar el crash en qt_free_mode_window.
        """
        hands_data = []
        fingers_data = []
        
        if self.results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(self.results.multi_hand_landmarks):
                hand_points = []
                for id, lm in enumerate(hand_landmarks.landmark):
                    # 1. Calcular coordenadas base
                    cx, cy = int(lm.x * img_width), int(lm.y * img_height)
                    
                    # 2. Aplicar rotación si se solicita (Soluciona el desface visual)
                    if rotate_180:
                        cx = img_width - cx
                        cy = img_height - cy

                    hand_points.append([id, cx, cy])
                    
                    if id in self.tipIds:
                        # Guardar datos del dedo
                        fingers_data.append([hand_idx, id, cx, cy])
                        
                        # Dibujar si se solicita
                        if draw and img is not None:
                            color = self.FINGER_COLORS.get((hand_idx, id), (200, 200, 200))
                            cv2.circle(img, (cx, cy), 12, color, 2)       # Borde
                            cv2.circle(img, (cx, cy), 6, color, cv2.FILLED) # Centro
                            
                hands_data.append(hand_points)
                
        return hands_data, fingers_data

    # Métodos de compatibilidad y dibujo auxiliar
    def getAllLandmarks(self): 
        return self.results.multi_hand_landmarks if self.results.multi_hand_landmarks else []

    def drawHands(self, img, rotate_180=False, highlight_finger_id=8): 
        """
        Dibuja el esqueleto completo de la mano.
        Soporta rotación de 180 grados para alinearse con el display.
        """
        if not self.results.multi_hand_landmarks:
            return

        h, w = img.shape[:2]
        
        for handLms in self.results.multi_hand_landmarks:
            # Dibujar conexiones primero
            for connection in self.mpHands.HAND_CONNECTIONS:
                id1, id2 = connection
                lm1 = handLms.landmark[id1]
                lm2 = handLms.landmark[id2]
                
                cx1, cy1 = int(lm1.x * w), int(lm1.y * h)
                cx2, cy2 = int(lm2.x * w), int(lm2.y * h)
                
                if rotate_180:
                    cx1, cy1 = w - cx1, h - cy1
                    cx2, cy2 = w - cx2, h - cy2
                
                cv2.line(img, (cx1, cy1), (cx2, cy2), (255, 255, 255), 2)
            
            # Dibujar puntos
            for id, lm in enumerate(handLms.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                if rotate_180:
                    cx, cy = w - cx, h - cy
                
                # Color base: Amarillo para mayor visibilidad
                color = (0, 255, 255) if id > 0 else (255, 255, 255)
                radius = 7 # Aumentado de 5
                
                # Resaltar dedo específico en Rojo (ej: índice para Fase 3)
                if id == highlight_finger_id:
                    color = (0, 0, 255) # Rojo puro para el dedo de medición
                    radius = 10 # Aumentado de 8
                    cv2.circle(img, (cx, cy), radius + 5, (0, 0, 255), 1) # Aura roja
                
                cv2.circle(img, (cx, cy), radius, color, cv2.FILLED)
                cv2.circle(img, (cx, cy), radius, (20, 20, 20), 1) # Borde oscuro fino

    def drawTips(self, img, rotate_180=False):
        # Reutilizamos la lógica centralizada
        self.getFingerTipsPos(img.shape[1], img.shape[0], draw=True, img=img, rotate_180=rotate_180)

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

    def drawHands(self, img, rotate_180=False): 
        # Nota: draw_landmarks estándar no soporta rotación fácil. 
        # Si rotate_180 es True, evitamos dibujar el esqueleto para no ensuciar la pantalla con líneas invertidas.
        if self.results.multi_hand_landmarks and not rotate_180:
            for h in self.results.multi_hand_landmarks: 
                self.mpDraw.draw_landmarks(img, h, self.mpHands.HAND_CONNECTIONS)

    def drawTips(self, img, rotate_180=False):
        # Reutilizamos la lógica centralizada
        self.getFingerTipsPos(img.shape[1], img.shape[0], draw=True, img=img, rotate_180=rotate_180)

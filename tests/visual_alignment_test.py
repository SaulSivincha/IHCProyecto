import sys
import os
import cv2
import numpy as np

# Añadir src al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.vision.depth_estimator import load_depth_estimator
from src.vision.hand_detector import HandDetector
from src.config.app_config import AppConfig

def main():
    print("="*60)
    print(" 📏 TEST DE ALINEACIÓN ESTÉREO (RECTIFICACIÓN)")
    print("="*60)
    print("OBJETIVO: Los dedos en ambas cámaras deben tocar la MISMA línea horizontal.")
    print("Si hay una diferencia vertical notable, la calibración falló.\n")

    # 1. Cargar calibración
    try:
        estimator = load_depth_estimator()
        print("[OK] Calibración cargada.")
    except Exception as e:
        print(f"[ERROR] No se pudo cargar la calibración: {e}")
        return

    # 2. Iniciar cámaras
    # IMPORTANTE: Usamos los IDs configurados en AppConfig
    id_l = 2  # Ajusta si es necesario
    id_r = 1  # Ajusta si es necesario
    
    cap_l = cv2.VideoCapture(id_l + cv2.CAP_DSHOW)
    cap_r = cv2.VideoCapture(id_r + cv2.CAP_DSHOW)
    
    # Configurar resolución
    w, h = 1280, 720
    cap_l.set(3, w); cap_l.set(4, h)
    cap_r.set(3, w); cap_r.set(4, h)
    
    # Detector de manos
    detector = HandDetector(maxHands=1, detectionCon=0.5, trackCon=0.5)

    while True:
        ret_l, frame_l = cap_l.read()
        ret_r, frame_r = cap_r.read()
        
        if not ret_l or not ret_r:
            print("Error leyendo cámaras")
            break

        # 3. RECTIFICAR IMÁGENES (Paso Crítico)
        # Usamos la función interna del estimator para ver lo que ve el algoritmo
        rect_l, rect_r = estimator.rectify_images(frame_l, frame_r)
        
        # 4. Detectar manos en imágenes rectificadas
        # Izquierda
        detector.findHands(rect_l)
        _, lm_l = detector.getIndexFingerTipPos() # Retorna ([hands], [[x,y,z]])
        
        # Derecha (Limpiamos detector o instanciamos otro, pero findHands limpia results)
        detector.findHands(rect_r)
        _, lm_r = detector.getIndexFingerTipPos()

        # 5. Dibujar Guías Visuales
        # Unir imágenes lado a lado
        vis = np.hstack((rect_l, rect_r))
        vis_h, vis_w, _ = vis.shape
        half_w = vis_w // 2

        # Dibujar líneas epipolares (Horizontales)
        for y in range(0, vis_h, 50):
            cv2.line(vis, (0, y), (vis_w, y), (0, 255, 0), 1)

        # 6. Analizar coincidencia
        pt_l = None
        pt_r = None
        
        if lm_l:
            # lm_l[0] es la mano, [0] es el tip (x,y,z)
            x_l, y_l = int(lm_l[0][0]), int(lm_l[0][1])
            pt_l = (x_l, y_l)
            # Dibujar en lado izquierdo
            cv2.circle(vis, (x_l, y_l), 8, (0, 0, 255), -1)
            cv2.putText(vis, f"L: {y_l}", (x_l+10, y_l), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)

        if lm_r:
            x_r, y_r = int(lm_r[0][0]), int(lm_r[0][1])
            pt_r = (x_r, y_r)
            # Dibujar en lado derecho (offset x + half_w)
            cv2.circle(vis, (x_r + half_w, y_r), 8, (0, 0, 255), -1)
            cv2.putText(vis, f"R: {y_r}", (x_r + half_w + 10, y_r), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)

        # 7. Diagnóstico numérico en pantalla
        if pt_l and pt_r:
            y_diff = abs(pt_l[1] - pt_r[1])
            x_diff = pt_l[0] - pt_r[0] # Disparidad
            
            # Estado
            status = "OK"
            color = (0, 255, 0)
            
            if y_diff > 10: # Umbral de tolerancia vertical
                status = "ERROR VERTICAL"
                color = (0, 0, 255)
            elif x_diff < 0:
                status = "ERROR CRUZADO (Swap Cam)"
                color = (0, 255, 255)
            
            # Texto central
            cv2.putText(vis, f"Y-Diff: {y_diff} px", (half_w - 100, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(vis, f"Disp: {x_diff} px", (half_w - 100, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(vis, status, (half_w - 100, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # Dibujar línea de conexión para evidenciar el error
            cv2.line(vis, (pt_l[0], pt_l[1]), (pt_r[0] + half_w, pt_r[1]), color, 2)

        # Redimensionar para que quepa en pantalla
        scale = 0.6
        preview = cv2.resize(vis, (0, 0), fx=scale, fy=scale)
        cv2.imshow("Test de Alineacion (Q para salir)", preview)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
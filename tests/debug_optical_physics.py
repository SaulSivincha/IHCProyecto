import sys
import os
import cv2
import numpy as np
import json

# Añadir src al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.vision.hand_detector import HandDetector
from src.calibration.qt_calibration_manager import StereoConfig

def main():
    print("🔬 DIAGNÓSTICO DE FÍSICA ÓPTICA (SIN CORRECCIONES)")
    print("==================================================")
    
    # 1. Cargar datos crudos del JSON
    calib_file = "camcalibration/calibration.json"
    if not os.path.exists(calib_file):
        print("❌ No se encontró calibration.json")
        return

    with open(calib_file, 'r') as f:
        data = json.load(f)

    # Extraer parámetros clave
    # NOTA: En tu JSON la matriz suele ser [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
    fx = data['left_camera']['camera_matrix'][0][0]
    fy = data['left_camera']['camera_matrix'][1][1]
    focal_pixels = (fx + fy) / 2
    
    # Baseline (Separación)
    T = np.array(data['stereo']['translation_vector'])
    baseline_cm = np.linalg.norm(T)
    
    # Auto-detectar unidades del baseline (m vs cm vs mm)
    if baseline_cm < 0.2:     # Probablemente metros (ej: 0.10 m)
        baseline_cm *= 100
    elif baseline_cm > 20.0:  # Probablemente mm (ej: 100 mm)
        baseline_cm /= 10
    # Si está entre 2 y 20, asumimos cm (ej: 10.73 cm)

    print(f"📊 DATOS CARGADOS:")
    print(f"   Focal (f):    {focal_pixels:.1f} píxeles")
    print(f"   Baseline (B): {baseline_cm:.2f} cm")
    
    # Calcular Z teórico para 41 cm
    target_z = 41.0
    expected_disparity = (focal_pixels * baseline_cm) / target_z
    
    print(f"\n🧠 PREDICCIÓN MATEMÁTICA:")
    print(f"   Para medir {target_z} cm, la disparidad debería ser: {expected_disparity:.1f} píxeles")
    print("   (Es decir, la mano izquierda y derecha deberían verse separadas por esa distancia)")

    print("\n🎥 INICIANDO CÁMARAS... (Pon tu mano a 41cm)")
    
    cap_l = cv2.VideoCapture(2 + cv2.CAP_DSHOW)
    cap_r = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
    
    # Forzar resolución 1280x720
    w, h = 1280, 720
    cap_l.set(3, w); cap_l.set(4, h)
    cap_r.set(3, w); cap_r.set(4, h)
    
    # IMPORTANTE: Inicializar detector con el tamaño CORRECTO de imagen
    # Si no, las coordenadas saldrán escaladas a 640x480 y fallará el cálculo
    detector = HandDetector(maxHands=1, img_width=w, img_height=h)
    
    while True:
        ret_l, img_l = cap_l.read()
        ret_r, img_r = cap_r.read()
        
        if not ret_l or not ret_r: break
        
        # Aplicar rotación
        img_l = StereoConfig.apply_camera_transforms(img_l)
        img_r = StereoConfig.apply_camera_transforms(img_r)
        
        # Copias para dibujar
        disp_l = img_l.copy()
        
        # --- PROCESO CORREGIDO PARA TU HAND_DETECTOR ---
        
        # 1. Detectar en Izquierda
        detector.findHands(img_l)
        _, tips_l = detector.getIndexFingerTipPos() # Retorna (hands, tips_list)
        
        # 2. Detectar en Derecha
        detector.findHands(img_r)
        _, tips_r = detector.getIndexFingerTipPos()
        
        if tips_l and tips_r:
            # tips_l es una lista de [(x, y, z), ...]. Tomamos el primero.
            x_l, y_l = tips_l[0][0], tips_l[0][1]
            x_r, y_r = tips_r[0][0], tips_r[0][1]
            
            # CALCULO REAL EN VIVO
            disparity = abs(x_l - x_r)
            
            if disparity > 0:
                z_raw = (focal_pixels * baseline_cm) / disparity
            else:
                z_raw = 0
            
            # Mostrar datos visuales
            color = (0, 255, 0) if abs(z_raw - 41) < 5 else (0, 0, 255)
            
            info = f"Disp: {disparity:.1f}px | Z_RAW: {z_raw:.1f} cm"
            cv2.putText(disp_l, info, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # Dibujar puntos
            cv2.circle(disp_l, (int(x_l), int(y_l)), 8, (255, 0, 0), -1)
            # Dibujamos dónde "caería" el punto derecho sobre la imagen izquierda
            # para ver la disparidad visualmente
            cv2.circle(disp_l, (int(x_r), int(y_r)), 8, (0, 255, 255), -1) 
            cv2.line(disp_l, (int(x_l), int(y_l)), (int(x_r), int(y_r)), (255,255,255), 1)

            # Verificar Rectificación Vertical (Y debe ser igual)
            y_diff = abs(y_l - y_r)
            cv2.putText(disp_l, f"Y-Diff: {y_diff:.1f}px", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            if y_diff > 30:
                cv2.putText(disp_l, "¡MALA RECTIFICACION!", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Redimensionar para mostrar
        scale = 0.7
        preview = cv2.resize(disp_l, (0, 0), fx=scale, fy=scale)
        
        cv2.imshow("Test Fisico (Q para salir)", preview)
        if cv2.waitKey(1) == ord('q'):
            break
            
    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
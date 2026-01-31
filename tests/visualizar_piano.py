import cv2
import numpy as np
from src.piano.virtual_keyboard import VirtualKeyboard
from src.vision.stereo_config import StereoConfig

def test_visualizer():
    # 1. Configuración de pantalla
    canvas_w, canvas_h = 1280, 720
    
    # 2. Forzar carga de tus esquinas actuales (829, 598, etc.)
    # El sistema las transformará automáticamente si aplicaste el 'Cambio 1'
    vk = VirtualKeyboard(canvas_w, canvas_h, 14)
    
    # 3. Crear fondo para el dibujo
    frame = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 50
    
    # Dibujar cuadrícula de referencia
    for x in range(0, canvas_w, 100): cv2.line(frame, (x, 0), (x, canvas_h), (80, 80, 80), 1)
    for y in range(0, canvas_h, 100): cv2.line(frame, (0, y), (canvas_w, y), (80, 80, 80), 1)

    # 4. Dibujar el piano tal cual lo verías en el programa
    vk.draw_virtual_keyboard(frame, active_keys=[])

    # 5. Dibujar los puntos de calibración reales para ver dónde caen
    if StereoConfig.TABLE_CORNERS:
        for pt in StereoConfig.TABLE_CORNERS:
            # Transformar punto (asumiendo rotación 180 si la tienes activa)
            disp_pt = StereoConfig.transform_point_for_display(pt, canvas_w, canvas_h)
            cv2.circle(frame, disp_pt, 10, (0, 0, 255), -1)
            cv2.putText(frame, f"{pt}", (disp_pt[0]+10, disp_pt[1]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    cv2.putText(frame, "VISUALIZADOR DE PIANO IHC", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    cv2.imshow("Alineacion de Piano", frame)
    print("Mira la ventana de OpenCV. Presiona cualquier tecla para salir.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_visualizer()
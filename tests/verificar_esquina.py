import cv2
import numpy as np
import glob
import os

# CONFIGURACIÓN (Debe coincidir con tu tablero real)
COLS = 7
ROWS = 7
PATTERN_SIZE = (COLS, ROWS)

def main():
    # Buscar imágenes estéreo guardadas
    left_images = sorted(glob.glob("camcalibration/images/stereo/stereo_left_*.jpg"))
    right_images = sorted(glob.glob("camcalibration/images/stereo/stereo_right_*.jpg"))

    if not left_images:
        print("❌ No encontré imágenes en camcalibration/images/stereo/")
        return

    print(f"🔍 Analizando {len(left_images)} pares de imágenes...")
    print("🔴 = PUNTO 0 (Inicio) | 🟢 = PUNTO FINAL")

    for left_path, right_path in zip(left_images, right_images):
        img_l = cv2.imread(left_path)
        img_r = cv2.imread(right_path)
        
        # Detectar esquinas
        ret_l, corners_l = cv2.findChessboardCorners(img_l, PATTERN_SIZE, None)
        ret_r, corners_r = cv2.findChessboardCorners(img_r, PATTERN_SIZE, None)

        if ret_l and ret_r:
            # Dibujar todas las esquinas (arcoiris)
            cv2.drawChessboardCorners(img_l, PATTERN_SIZE, corners_l, ret_l)
            cv2.drawChessboardCorners(img_r, PATTERN_SIZE, corners_r, ret_r)

            # DIBUJAR PUNTO 0 EN GIGANTE (ROJO)
            # Izquierda
            p0_l = tuple(map(int, corners_l[0].ravel()))
            cv2.circle(img_l, p0_l, 15, (0, 0, 255), -1) # Rojo
            cv2.putText(img_l, "0", p0_l, cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            
            # Derecha
            p0_r = tuple(map(int, corners_r[0].ravel()))
            cv2.circle(img_r, p0_r, 15, (0, 0, 255), -1) # Rojo
            cv2.putText(img_r, "0", p0_r, cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

            # Unir imágenes para comparar
            h, w = img_l.shape[:2]
            combined = np.hstack((img_l, img_r))
            
            # Redimensionar para ver en pantalla
            scale = 0.5
            preview = cv2.resize(combined, (0,0), fx=scale, fy=scale)
            
            cv2.imshow("Verificacion de Esquinas (Q para salir, Tecla para siguiente)", preview)
            key = cv2.waitKey(0)
            if key == ord('q'):
                break
        else:
            print(f"⚠️ No se detectó tablero en: {os.path.basename(left_path)}")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
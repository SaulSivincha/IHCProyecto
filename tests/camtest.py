import cv2
import time

print("\n============== BUSCANDO CAMARAS ==============\n")

windows = []      # Para guardar los nombres de ventanas abiertas
captures = []     # Para guardar las capturas activas

MAX_CAMERAS = 10
BACKEND = cv2.CAP_DSHOW   # Mejor backend para Windows

for i in range(MAX_CAMERAS):
    cap = cv2.VideoCapture(i, BACKEND)

    if not cap.isOpened():
        print(f"[{i}] No disponible")
        continue

    ret, frame = cap.read()
    backend = cap.getBackendName()
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"[{i}] Disponible | Backend: {backend} | {w}x{h} | frame={ret}")

    window_name = f"Cam {i} ({backend})"
    windows.append(window_name)
    captures.append(cap)

    # Crear ventana individual
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)

print("\n================================================\n")

if not captures:
    print("❌ No se encontraron cámaras disponibles.")
    exit()

print("Presione cualquier tecla en una ventana para cerrar...")

# Mostrar todas las cámaras en tiempo real
while True:
    for window_name, cap in zip(windows, captures):
        ret, frame = cap.read()
        if ret:
            cv2.imshow(window_name, frame)
        else:
            cv2.imshow(window_name, 
                255 * np.ones((480, 640, 3), dtype=np.uint8))  # pantalla blanca si falla

    if cv2.waitKey(1) != -1:   # cualquier tecla
        break

# Liberar recursos
for cap in captures:
    cap.release()

cv2.destroyAllWindows()

# Documentación de Lógica del Sistema (Virtual Piano)

Nunca implementes errores hardcodeados ni soluciones momentaneas, el sistema debe funcionar de manera correcta y los problemas se solucionaran buscando el origen del problema. 


Este documento detalla la arquitectura, flujos de datos y algoritmos clave del sistema de piano virtual estereoscópico. Está diseñado para que cualquier IA o desarrollador entienda rápidamente cómo funciona el proyecto.

## 1. Arquitectura General

El sistema sigue un flujo lineal de procesamiento de video en tiempo real:

`Hardware (Cámaras)` -> `VideoThread` -> `Interfaz (Qt)` -> `Visión (Detección/Estéreo)` -> `Lógica (Mapper)` -> `Salida (Audio/UI)`

### Componentes Principales

*   **`src/calibration/qt_calibration_manager.py`**: Gestiona la calibración de cámaras (intrínseca, estéreo y de plano). Genera `calibration.json`.
*   **`src/vision/video_thread.py`**: Capa de abstracción sobre OpenCV. Maneja la captura asíncrona en hilos para maximizar FPS.
*   **`src/vision/stereo_config.py`**: Singleton de configuración. Carga `calibration.json` y define constantes físicas (separación de cámaras, FOV).
*   **`src/vision/depth_estimator.py`**: Núcleo matemático. Realiza rectificación de imágenes y triangulación 3D.
*   **`src/vision/keyboard_mapper.py`**: Determina qué tecla se está tocando basándose en la posición (X,Y) y profundidad (Z) de los dedos.
*   **`src/piano/keyboard_processor.py`**: Orquestador para modos de juego y canciones. (En Modo Libre, `qt_free_mode_window.py` replica parte de esta lógica para visualizar).

---

## 2. Flujo de Visión Estereoscópica

El sistema utiliza dos cámaras para calcular profundidad (Z) mediante triangulación.

### Paso A: Captura y Sincronización
Se capturan frames de Cámara Izquierda (L) y Derecha (R). Idealmente sincronizados, aunque en USB puede haber ligero desfase.

### Paso B: Detección de Manos (MediaPipe)
Se ejecuta MediaPipe Hands independientemente en L y R.
*   **Output**: Landmarks 2D (x, y) para cada mano visible.

### Paso C: Matching (Emparejamiento)
El sistema debe decidir qué mano en L corresponde a qué mano en R.
*   **Método Actual**: **Matching por ID**. Se asume que MediaPipe asigna ID 0 a la primera mano vista en ambas cámaras.
    *   *Limitación*: Si una cámara ve una mano y la otra no, o si se cruzan, las IDs pueden desincronizarse (Swap).
    *   *Solución*: Si no coinciden IDs, se ignora el frame (dropout momentáneo) o se asume "Aire" (Depth=99).

### Paso D: Rectificación
Antes de triangular, los puntos 2D (x,y) se "rectifican" usando las matrices de calibración (`calibration.json`). Esto alinea las imágenes para que un punto en L tenga la misma coordenada Y que su par en R (Geometría Epipolar).

### Paso E: Triangulación
Usando la *disparidad* (diferencia en X entre punto L y punto R rectificados) y la separación de cámaras base (`CAMERA_SEPARATION`), se calcula Z (Profundidad Absoluta desde la cámara). Plus X e Y reales.

---

## 3. Lógica de Detección de Teclas

### Concepto de Profundidad Relativa
La "Profundidad Absoluta" (distancia a la cámara) no es útil por sí sola porque la mano se mueve en 3D. Lo que importa es la distancia al **Plano del Teclado**.

1.  **Fase 3 de Calibración**: Calcula `keyboard_distance_cm` (distancia promedio de la mesa a las cámaras, ej. 42cm).
2.  **Cálculo en Tiempo Real (CORREGIDO 2026-01-17)**:
    ```python
    # Fórmula correcta:
    Relativa = Depth_Absoluta - keyboard_distance_cm
    ```
    *   **Relativa > 0**: La mano está MÁS CERCA de la cámara que la mesa (TOCANDO).
    *   **Relativa ≈ 0**: La mano está al nivel de la mesa.
    *   **Relativa < 0**: La mano está MÁS LEJOS de la cámara que la mesa (AIRE).
    
    > **NOTA HISTÓRICA**: Antes se usaba `kb_dist - depth_abs` que invertía la lógica.

### Validación y Filtrado (CRÍTICO)
Para evitar "fantasmas" y spikes de velocidad:
*   **Rango Físico**: Se descartan profundidades fuera de [-10cm, +30cm] relativos.
*   **Skip Frame**: Si el tracking estéreo falla por 1 frame (oclusión, mov rápido), **SE SALTA EL FRAME**.
    *   *Historia*: Anteriormente se usaba un fallback `depth=99.0`. Esto causaba que la velocidad saltara de 0cm a 99cm en 1 frame (`vel=99cm/frame`), rompiendo los filtros de detección.
    *   *Regla*: Si no hay datos, no hay cálculo. Mantener el historial limpio.
*   **Umbral de Activación**: `DEPTH_THRESHOLD = 2.0cm` (activar si `depth >= -2.0cm`).

## 3.5 Modo AR y Detección "WYSIWYG"

El modo AR introduce una complejidad adicional: la **alineación visual**.

*   **Problema**: El video se muestra típicamente rotado 180° (para que coincida con la perspectiva del usuario).
*   **Detección WYSIWYG (What You See Is What You Get)**:
    *   En lugar de transformar coordenadas complejas, dibujamos los polígonos de detección directamente sobre el frame RAW de la cámara.
    *   Usamos las coordenadas RAW de MediaPipe (sin rotar) para verificar colisiones.
    *   **Resultado**: Donde el usuario ve su dedo (y el polígono verde/rojo), ahí detecta. Tolerancia de `30px` para usabilidad.

---

## 4. Problemas Comunes y Soluciones

### A. "Fantasmas" a 1cm de la cámara
*   **Causa**: A muy corta distancia, las cámaras no tienen campo de visión común suficiente para triangular. El matching falla.
*   **Solución**: El código detecta la falta de coincidencia y asigna profundidad "infinita" (no toque).

### B. Silencio a la distancia correcta (42cm)
*   **Causa**: Calibración deficiente (RMS alto). La rectificación distorsiona los puntos, haciendo que la triangulación falle o de valores fuera de rango.
*   **Solución**:
    1. Usar el valor REAL de `CAMERA_SEPARATION` en `StereoConfig` (9.62cm vs 14cm).
    2. Recalibrar si el error RMS > 1.0.

### C. Teclas "pegadas" o rebotes
*   **Causa**: Ruido en la detección Z frame a frame.
*   **Solución**: `algorithms/algorithm_manager.py` puede aplicar filtros como "Una Nota Por Acción" o suavizado temporal.

---

## 5. Archivos de Configuración Clave

*   **`camcalibration/calibration.json`**: La "verdad absoluta" de la geometría de tus cámaras. Creado por el proceso de calibración. **NO EDITAR MANUALMENTE**.
*   **`src/vision/stereo_config.py`**: Carga los valores de arriba. Debe estar sincronizado con la realidad física (ej. separación de cámaras).


archivos importantes


src/vision/video_thread.py
Función: Captura las imágenes crudas de las cámaras.
Importancia: Si esto falla o va lento, todo el sistema sufre.
src/vision/hand_detector.py
 (Usa MediaPipe)
Función: Detecta las manos en 2D en cada imagen por separado.
Salida: Coordenadas (u, v) de los dedos en la pantalla (píxeles).
src/vision/stereo_config.py
Función: El "Cerebro de Configuración". Contiene la separación física de las cámaras (9.62cm) y carga el 
calibration.json
.
Importancia: Si CAMERA_SEPARATION está mal, la profundidad sale mal.
src/vision/depth_estimator.py
 (MATEMÁTICAS PURAS)
Función: Realiza la Triangulación.
Métodos clave: 
rectify_point
 (alinea las imágenes) y 
triangulate_point
 (calcula Z usando disparidad).
Aquí es donde ocurren los errores de "Z negativo" o "500cm".
src/ui/qt_free_mode_window.py
 (El Orquestador)
Función: Es el bucle principal en Modo Libre.
Lógica: Llama a los detectores, pide la triangulación a 
depth_estimator
, aplica filtros (como el que acabamos de poner para Z<=0) y decide si llamar al mapper.
src/vision/keyboard_mapper.py
Función: Recibe la profundidad (Z) y posición (X,Y). Decide si el dedo está "tocando" una tecla virtual.
Lógica: Tiene el umbral 
depth_threshold
 (ej. 5cm) y logic de "Aire" vs "Toque".
camcalibration/calibration.json
Función: Archivo de datos con las matrices de distorsión y geometría. Es la base de todo cálculo.
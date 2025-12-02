# Módulo de Calibración Estereoscópica Profesional

## 📁 Estructura del Módulo

```
src/calibration/
├── __init__.py                  # Exportaciones del módulo
├── calibration_config.py        # Configuración y constantes
├── calibration_manager_v2.py    # Gestor principal (orquestador con Fase 2)
├── camera_calibrator.py         # Calibración individual de cámaras
├── stereo_calibrator.py         # Calibración estéreo (Fase 2)
├── calibration_ui.py            # Interfaz visual
└── run_calibration.py           # Script standalone
```

## 🎯 Características

### ✅ Implementado

**Fase 1 - Calibración Individual:**
- **Calibración individual de cada cámara** usando método de tablero de ajedrez
- **25 fotos estratégicamente distribuidas** en 4 categorías:
  - **A. Variar Distancia** (5 fotos): Información sobre focal y distorsión
  - **B. Variar Posición** (8 fotos): Estimación del centro óptico
  - **C. Variar Inclinación** (7 fotos): Modelar distorsiones angulares
  - **D. Variar Perspectiva** (5 fotos): Robustez en detección

**Fase 2 - Calibración Estéreo:**
- **Calibración estéreo completa** con `cv2.stereoCalibrate()`
- **8-15 pares simultáneos** de imágenes
- **Mapas de rectificación estéreo** con `stereoRectify()`
- **Cálculo de baseline** y parámetros extrínsecos (R, T, E, F)
- **Validación geométrica** del par estéreo

**General:**
- **Interfaz visual profesional** que guía paso a paso
- **Sistema inteligente** que detecta fases completadas y permite reanudar
- **Validación de calidad** con error de reproyección
- **Guardado automático** de imágenes y parámetros

## 📋 Requisitos Previos

### 1. Hardware

- **2 cámaras USB** (ej. Logitech C920)
- **Tablero de ajedrez impreso** (recomendado: 9x6 esquinas internas)
- **Buena iluminación** uniforme y estable

### 2. Tablero de Calibración

**Imprimir:**
- Patrón de tablero de ajedrez (disponible en: [OpenCV Chessboard](https://docs.opencv.org/master/pattern.png))
- Tamaño recomendado: cuadrados de 25mm x 25mm
- Pegar sobre superficie rígida (cartón, madera)

**Medir con precisión:**
- Tamaño de cada cuadrado en milímetros
- Contar esquinas internas (NO cuadrados externos)

Ejemplo: Tablero 10x7 → 9x6 esquinas internas

## 🚀 Uso

### Opción 1: Desde el juego principal

```bash
python -m src.main
```

Selecciona "Nueva calibración" en el menú inicial.

### Opción 2: Standalone

```bash
python -m src.calibration.run_calibration
```

## 📸 Proceso de Captura

### Reglas Generales

- ✅ Mantén el tablero **COMPLETO** dentro del encuadre
- ✅ Evita reflejos o sombras intensas
- ✅ Mantén la **cámara fija**, solo mueve el tablero
- ✅ No uses enfoque automático si genera cambios bruscos
- ✅ Mantén iluminación estable

### Distribución de 25 Fotos

#### A. Variar Distancia (5 fotos)
```
1. Tablero MUY CERCA (ocupa casi toda la imagen)
2. Tablero CERCA (75% del frame)
3. Tablero a DISTANCIA MEDIA (50% del frame)
4. Tablero UN POCO LEJOS
5. Tablero MUY LEJOS (pero visible claramente)
```

#### B. Variar Posición (8 fotos)
```
1. Superior izquierda
2. Superior derecha
3. Inferior izquierda
4. Inferior derecha
5. Centro exacto
6. Desplazado a la derecha
7. Desplazado a la izquierda
8. Ligeramente abajo del centro
```

#### C. Variar Inclinación (7 fotos)
```
1. Inclinación HACIA DELANTE (cae hacia cámara)
2. Inclinación HACIA ATRÁS (alejándose)
3. Inclinación HACIA LA IZQUIERDA
4. Inclinación HACIA LA DERECHA
5. Tablero ROTADO COMO ROMBO (45°)
6. Tablero ROTADO 20-30° IZQUIERDA
7. Tablero ROTADO 20-30° DERECHA
```

#### D. Variar Perspectiva (5 fotos)
```
1. Ángulo BAJO (cámara mira hacia arriba)
2. Ángulo ALTO (cámara mira hacia abajo)
3. Perspectiva FUERTE desde UN COSTADO
4. Perspectiva FUERTE desde OTRO COSTADO
5. ROTACIÓN LEVE + PERSPECTIVA combinada
```

## 🎮 Controles

Durante la captura:
- **ESPACIO**: Capturar imagen (cuando tablero está detectado)
- **Q**: Finalizar captura anticipada (mín. 15 fotos)
- **ESC**: Cancelar proceso

## 📊 Salida

### Archivos Generados

```
camcalibration/
├── calibration.json          # Parámetros de calibración
└── images/
    ├── left/                 # Imágenes de cámara izquierda
    │   ├── calib_001.jpg
    │   ├── calib_002.jpg
    │   └── ...
    └── right/                # Imágenes de cámara derecha
        ├── calib_001.jpg
        ├── calib_002.jpg
        └── ...
```

### Formato de calibration.json

```json
{
    "version": "2.0",
    "board_config": {
        "cols": 9,
        "rows": 6,
        "square_size_mm": 25.0
    },
    "left_camera": {
        "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
        "distortion_coeffs": [k1, k2, p1, p2, k3],
        "reprojection_error": 0.234,
        "num_images": 25,
        "image_width": 1280,
        "image_height": 720
    },
    "right_camera": { ... },
    "camera_ids": {
        "left": 1,
        "right": 2
    },
    "resolution": {
        "width": 1280,
        "height": 720
    }
}
```

## 📈 Calidad de Calibración

### Error de Reproyección

- **< 0.5 píxeles**: Excelente ✅
- **0.5 - 1.0 píxeles**: Aceptable ⚠️
- **> 1.0 píxeles**: Pobre ❌ (recalibrar)

### Consejos para Mejorar

Si el error es alto:
1. Usa mejor iluminación (sin sombras)
2. Asegúrate de que el tablero esté completamente plano
3. Captura más fotos con mayor variedad de ángulos
4. Verifica que el tamaño del cuadrado sea exacto
5. Usa un tablero más grande si es posible

## 🔧 Configuración Avanzada

Editar `calibration_config.py`:

```python
# Cambiar número de fotos requeridas
MIN_IMAGES = 15
RECOMMENDED_IMAGES = 25

# Cambiar criterios de calidad
MAX_REPROJECTION_ERROR = 1.0

# Cambiar resolución
resolution = (1920, 1080)
```

## 🐛 Solución de Problemas

### Tablero no detectado

- Verifica que el tablero tenga el patrón correcto
- Asegúrate de ingresar el número correcto de esquinas internas
- Mejora la iluminación
- Reduce reflejos (usar tablero mate)

### Error alto de reproyección

- Recaptura con mejor calidad de imágenes
- Aumenta la variedad de ángulos y distancias
- Verifica que la medida del cuadrado sea exacta
- Mantén el enfoque de la cámara fijo

### Cámara no se abre

- Verifica que los IDs de cámara sean correctos (0, 1, 2...)
- Cierra otras aplicaciones que usen las cámaras
- Verifica permisos de acceso a cámaras

## 📚 Referencias

- [OpenCV Camera Calibration](https://docs.opencv.org/master/dc/dbb/tutorial_py_calibration.html)
- [Stereo Vision Tutorial](https://docs.opencv.org/master/dd/d53/tutorial_py_depthmap.html)
- [Camera Calibration Paper (Zhang)](http://www.vision.caltech.edu/bouguetj/calib_doc/papers/zhan99.pdf)

## 🎓 Teoría

### ¿Por qué calibrar?

Las cámaras reales tienen:
- **Distorsión de lente**: Los bordes de la imagen se curvan (efecto barril/almohada)
- **Parámetros intrínsecos desconocidos**: Distancia focal, centro óptico
- **Parámetros extrínsecos**: Posición relativa entre cámaras

La calibración determina matemáticamente estos parámetros para:
- Corregir distorsiones
- Calcular posiciones 3D precisas (triangulación)
- Mejorar detección de profundidad

### Matriz de Cámara

```
K = [fx  0   cx]
    [0   fy  cy]
    [0   0   1 ]
```

- **fx, fy**: Distancia focal en píxeles
- **cx, cy**: Centro óptico (principal point)

### Coeficientes de Distorsión

```
distCoeffs = [k1, k2, p1, p2, k3]
```

- **k1, k2, k3**: Distorsión radial
- **p1, p2**: Distorsión tangencial

## 📝 Licencia

Parte del proyecto IHC Piano Virtual - Universidad Nacional de Ingeniería

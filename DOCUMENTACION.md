# 📚 Documentación Completa - Piano Virtual con Visión Estéreo

> **Versión:** 2.0.0  
> **Autor:** mherrera  
> **Última actualización:** Enero 2026

---

## 📋 Índice

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Instalación y Requisitos](#3-instalación-y-requisitos)
4. [Sistema de Calibración](#4-sistema-de-calibración)
   - [Fase 0: Rectificación de Cámaras](#fase-0-rectificación-de-cámaras-rotación)
   - [Fase 1: Calibración Individual](#fase-1-calibración-individual-de-cámaras)
   - [Fase 2: Calibración Estéreo](#fase-2-calibración-estéreo)
   - [Fase 3: Calibración de Profundidad](#fase-3-calibración-de-profundidad)
   - [Fase 4: Definición del Teclado AR](#fase-4-definición-del-teclado-ar)
5. [Sistema de Visión](#5-sistema-de-visión)
   - [Detección de Manos](#51-detección-de-manos)
   - [Estimación de Profundidad](#52-estimación-de-profundidad)
   - [Algoritmos de Detección](#53-algoritmos-de-detección)
6. [Sistema del Piano Virtual](#6-sistema-del-piano-virtual)
   - [Teclado Virtual](#61-teclado-virtual)
   - [Mapeo de Teclas](#62-mapeo-de-teclas)
   - [Procesamiento de Pulsaciones](#63-procesamiento-de-pulsaciones)
7. [Sistema de Gameplay](#7-sistema-de-gameplay)
   - [Juego de Ritmo](#71-juego-de-ritmo)
   - [Formato de Canciones](#72-formato-de-canciones)
8. [Sistema de Lecciones](#8-sistema-de-lecciones)
9. [Interfaz de Usuario](#9-interfaz-de-usuario)
10. [Configuración](#10-configuración)
11. [Solución de Problemas](#11-solución-de-problemas)
12. [Referencia de API](#12-referencia-de-api)

---

## 1. Descripción General

### ¿Qué es este proyecto?

Este es un sistema de **piano virtual con realidad aumentada** que utiliza **visión estéreo** para detectar la posición 3D de los dedos del usuario. Permite "tocar" un piano virtual en el aire, donde las teclas se superponen sobre una superficie real (mesa/teclado físico).

### Características principales

- 🎹 **Piano virtual de 2 octavas** (24 teclas, MIDI 60-83)
- 👁️ **Visión estéreo 3D** con dos cámaras web
- ✋ **Detección de manos** con MediaPipe
- 🎮 **Juego de ritmo** con canciones y puntuación
- 📖 **Lecciones de teoría musical** interactivas
- 🎵 **Síntesis de audio** con FluidSynth

### Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.10.11 |
| GUI | PyQt6 |
| Visión por computador | OpenCV 4.x |
| Detección de manos | MediaPipe |
| Audio MIDI | FluidSynth + pyFluidSynth |
| Cálculos | NumPy, SciPy |

---

## 2. Arquitectura del Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APLICACIÓN PRINCIPAL                         │
│                            (main.py)                                 │
└─────────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────┐        ┌─────────────────┐        ┌─────────────────┐
│   UI (PyQt6)  │        │  CORE RESOURCES │        │  CONFIGURACIÓN  │
│               │        │                 │        │                 │
│ • MainMenu    │        │ • Cámaras       │        │ • AppConfig     │
│ • FreeMode    │        │ • Detectores    │        │ • GameConfig    │
│ • SongsMenu   │        │ • Sintetizador  │        │ • Theme         │
│ • TheoryMenu  │        │ • DepthEstim.   │        │ • StereoConfig  │
└───────────────┘        └─────────────────┘        └─────────────────┘
        │                          │
        ▼                          ▼
┌───────────────────────────────────────────────────────────────────┐
│                        CAPA DE PROCESAMIENTO                       │
├───────────────┬─────────────────┬─────────────────┬───────────────┤
│    VISIÓN     │      PIANO      │    GAMEPLAY     │    TEORÍA     │
│               │                 │                 │               │
│ • HandDetect  │ • VirtualKeyb   │ • RhythmGame    │ • Lessons     │
│ • DepthEstim  │ • KeyboardProc  │ • SongChart     │ • Progress    │
│ • KeyboardMap │ • AudioSynth    │ • Scoring       │ • Manager     │
│ • Algorithms  │                 │                 │               │
└───────────────┴─────────────────┴─────────────────┴───────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                      SISTEMA DE CALIBRACIÓN                        │
│                                                                    │
│  Fase 0: Rotación → Fase 1: Individual → Fase 2: Estéreo →        │
│  Fase 3: Profundidad → Fase 4: Definición AR                       │
└───────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos Principal

```
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────────┐
│ Cámara   │───▶│ Cámara   │───▶│ Rectificar │───▶│  Detectar    │
│ Izquierda│    │ Derecha  │    │  Imágenes  │    │    Manos     │
└──────────┘    └──────────┘    └────────────┘    └──────────────┘
                                                         │
                                                         ▼
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────────┐
│  Tocar   │◀───│  Mapear  │◀───│ Calcular   │◀───│ Triangular   │
│  Sonido  │    │  Teclas  │    │Profundidad │    │  Puntos 3D   │
└──────────┘    └──────────┘    └────────────┘    └──────────────┘
```

---

## 3. Instalación y Requisitos

### Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| CPU | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 |
| RAM | 8 GB | 16 GB |
| Cámaras | 2× USB webcam 720p | 2× Logitech C920 1080p |
| GPU | Integrada | Dedicada (para MediaPipe) |

### Requisitos de Software

```bash
# Python 3.10.11 (recomendado)
python --version

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias Principales (requirements.txt)

```
opencv-contrib-python>=4.8.0
opencv-python>=4.8.0
mediapipe>=0.10.0
pyFluidSynth>=1.3.0
PyQt6>=6.5.0
numpy>=1.24.0
scipy>=1.10.0
```

### Dependencias Externas

1. **FluidSynth** - Motor de síntesis MIDI
   - Ubicación: `utils/fluidsynth/bin/`
   - DLL necesaria: `libfluidsynth-3.dll`

2. **SoundFont** - Banco de sonidos de piano
   - Archivo: `FluidR3_GM.sf2`
   - Ubicación: `utils/fluid/fluid/`

### Configuración de Cámaras

⚠️ **IMPORTANTE**: Las cámaras deben estar:
- Montadas a la misma altura
- Separadas horizontalmente (10-20 cm recomendado)
- Apuntando en la misma dirección
- **ROTADAS 180°** si están montadas boca abajo

---

## 4. Sistema de Calibración

El sistema de calibración es **CRÍTICO** para el funcionamiento correcto. Una mala calibración resulta en detección imprecisa de profundidad.

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `src/calibration/camera_calibrator.py` | Calibración individual |
| `src/calibration/stereo_calibrator.py` | Calibración estéreo |
| `src/calibration/depth_calibrator.py` | Calibración de profundidad |
| `src/calibration/calibration_config.py` | Configuración de patrones |
| `src/calibration/qt_calibration_window.py` | Interfaz de calibración |
| `camcalibration/calibration.json` | Datos guardados |

### Patrón de Calibración

Se utiliza un **tablero de ajedrez** con las siguientes configuraciones disponibles:

| Preset | Tamaño | Esquinas Internas | Cuadro |
|--------|--------|-------------------|--------|
| Estándar | 8×8 | 7×7 | 30mm |
| Profesional | 10×7 | 9×6 | 25mm |
| Grande | 12×9 | 11×8 | 30mm |

---

### Fase 0: Rectificación de Cámaras (Rotación)

#### ¿Por qué las cámaras deben estar niveladas?

La **geometría epipolar** asume que ambas cámaras están perfectamente alineadas horizontalmente. Si una cámara está rotada:

- Las líneas epipolares no serán horizontales
- La rectificación será imprecisa
- El cálculo de disparidad fallará
- **La profundidad será incorrecta**

#### Proceso

1. Se muestra una **línea guía horizontal** en ambas vistas
2. El usuario debe **rotar físicamente** las cámaras hasta que un borde horizontal (mesa, libro) se alinee con la guía
3. Se puede ajustar la posición de la guía con las flechas ↑↓

```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  CÁMARA IZQUIERDA               │  │  CÁMARA DERECHA                 │
│                                 │  │                                 │
│  ─────────────────────────────  │  │  ─────────────────────────────  │
│         ↑ Línea guía            │  │         ↑ Línea guía            │
│                                 │  │                                 │
│    ┌─────────────┐              │  │    ┌─────────────┐              │
│    │   LIBRO     │ ← Alinear    │  │    │   LIBRO     │ ← Alinear    │
│    └─────────────┘              │  │    └─────────────┘              │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

#### Código Relevante

```python
# En qt_calibration_window.py
def _draw_guide_line(self, frame):
    """Dibuja línea guía horizontal para alineación"""
    h, w = frame.shape[:2]
    y_pos = int(h * self.guide_line_ratio)
    cv2.line(frame, (0, y_pos), (w, y_pos), (0, 255, 255), 2)
```

---

### Fase 1: Calibración Individual de Cámaras

#### Objetivo

Calcular los **parámetros intrínsecos** de cada cámara:

- **Matriz de cámara K** (3×3): focal length, centro óptico
- **Coeficientes de distorsión D** (5 valores): corrección de lente

#### Proceso

1. Mostrar tablero de ajedrez en diferentes posiciones
2. Capturar mínimo **15 imágenes** por cámara (recomendado: 25)
3. Variar: distancia, posición, inclinación, perspectiva

#### Categorías de Capturas

| Categoría | Cantidad | Descripción |
|-----------|----------|-------------|
| Distancia | 5 | Cerca, medio, lejos |
| Posición | 8 | Esquinas y centro |
| Inclinación | 7 | Rotado en X/Y |
| Perspectiva | 5 | Ángulos extremos |

#### Algoritmo

```python
# En camera_calibrator.py
def calibrate(self):
    # Encontrar esquinas del tablero
    ret, corners = cv2.findChessboardCorners(gray, board_size)
    
    # Refinar con sub-pixel accuracy
    corners = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
    
    # Calibrar cámara
    ret, K, D, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, image_size, None, None
    )
    
    # ret = error de reproyección (píxeles)
```

#### Métricas de Calidad

| Error de Reproyección | Calidad |
|-----------------------|---------|
| < 0.5 píxeles | ⭐ Excelente |
| < 1.0 píxeles | ✅ Bueno |
| < 1.5 píxeles | ⚠️ Aceptable |
| > 1.5 píxeles | ❌ Recalibrar |

#### Salida

```json
{
  "left_camera": {
    "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
    "distortion": [k1, k2, p1, p2, k3],
    "reprojection_error": 0.42
  }
}
```

---

### Fase 2: Calibración Estéreo

#### Objetivo

Calcular los **parámetros extrínsecos** (relación entre cámaras):

- **Matriz de rotación R** (3×3): orientación relativa
- **Vector de traslación T** (3×1): posición relativa (baseline)
- **Matrices de rectificación** R1, R2, P1, P2, Q

#### Proceso

1. Capturar **pares sincronizados** del tablero (mínimo 8 pares)
2. El tablero debe ser visible en AMBAS cámaras simultáneamente
3. Variar posiciones similar a Fase 1

#### Algoritmo

```python
# En stereo_calibrator.py
def calibrate_stereo(self):
    # Calibración estéreo
    ret, K1, D1, K2, D2, R, T, E, F = cv2.stereoCalibrate(
        objpoints, 
        imgpoints_left, imgpoints_right,
        K1, D1, K2, D2,
        image_size,
        flags=cv2.CALIB_FIX_INTRINSIC  # Usar intrínsecos de Fase 1
    )
    
    # Calcular rectificación
    R1, R2, P1, P2, Q, roi1, roi2 = cv2.stereoRectify(
        K1, D1, K2, D2, image_size, R, T
    )
    
    # Crear mapas de rectificación
    map1x, map1y = cv2.initUndistortRectifyMap(K1, D1, R1, P1, size, cv2.CV_32FC1)
    map2x, map2y = cv2.initUndistortRectifyMap(K2, D2, R2, P2, size, cv2.CV_32FC1)
```

#### Baseline (Separación de Cámaras)

```python
baseline_cm = np.linalg.norm(T) / 10  # T está en mm → cm
```

El baseline típico es **10-20 cm**. Un baseline mayor mejora la precisión de profundidad a distancias grandes, pero reduce el rango mínimo.

#### Métricas de Calidad

| RMS Error | Calidad |
|-----------|---------|
| < 0.3 | ⭐ Excelente |
| < 0.6 | ✅ Bueno |
| < 1.0 | ⚠️ Aceptable |
| > 1.0 | ❌ Recalibrar |

#### Verificación Visual

Después de la rectificación, las líneas epipolares deben ser **perfectamente horizontales**:

```
Antes de rectificar:          Después de rectificar:
┌─────────┐ ┌─────────┐       ┌─────────┐ ┌─────────┐
│    •    │ │  •      │       │    •────│─│────•    │  ← Mismo Y
│  •      │ │      •  │       │  •──────│─│──────•  │  ← Mismo Y
│      •  │ │    •    │       │      •──│─│──•      │  ← Mismo Y
└─────────┘ └─────────┘       └─────────┘ └─────────┘
```

---

### Fase 3: Calibración de Profundidad

#### Objetivo

Ajustar la **escala de profundidad** para que las mediciones en centímetros sean precisas.

#### ¿Por qué es necesario?

La triangulación estéreo calcula profundidad relativa. Para convertir a unidades reales, necesitamos un **punto de referencia conocido**.

#### Proceso

1. Colocar el dedo índice sobre la superficie del teclado/mesa
2. El sistema detecta y triangula la posición 3D
3. El usuario ingresa la **distancia real medida** (con regla)
4. Se calcula el **factor de corrección**

#### Algoritmo

```python
# En depth_calibrator.py
def calibrate_depth(self, measured_depth, real_distance):
    """
    measured_depth: Profundidad calculada por triangulación (cm)
    real_distance: Distancia real medida por el usuario (cm)
    """
    self.depth_correction_factor = real_distance / measured_depth
    self.keyboard_distance = real_distance
```

#### Salida

```json
{
  "depth_correction_factor": 1.05,
  "keyboard_distance": 45.0
}
```

---

### Fase 4: Definición del Teclado AR

#### Objetivo

Definir la **región rectangular** donde se dibujará el teclado virtual superpuesto.

#### Proceso

1. El usuario arrastra para definir un rectángulo
2. O hace clic en las 4 esquinas del área deseada
3. Se guarda como array de puntos

#### Salida

```json
{
  "keyboard_corners": [
    [100, 300],   // Esquina superior izquierda
    [540, 300],   // Esquina superior derecha
    [540, 450],   // Esquina inferior derecha
    [100, 450]    // Esquina inferior izquierda
  ]
}
```

---

## 5. Sistema de Visión

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `src/vision/hand_detector.py` | Detección de manos |
| `src/vision/depth_estimator.py` | Cálculo de profundidad 3D |
| `src/vision/keyboard_mapper.py` | Mapeo dedos → teclas |
| `src/vision/stereo_config.py` | Configuración estéreo |
| `src/vision/video_thread.py` | Captura asíncrona |
| `src/vision/angles.py` | Cálculos angulares |
| `src/vision/algorithms/` | Pipeline de algoritmos |

---

### 5.1 Detección de Manos

#### Tecnología: MediaPipe Hands

MediaPipe detecta **21 landmarks** por mano:

```
        8   12  16  20
        │   │   │   │
    4   7   11  15  19
    │   │   │   │   │
    ┴───6───10──14──18
        │   │   │   │
        5───9───13──17
            │
            0 (muñeca)
```

#### Landmarks Importantes

| Índice | Nombre | Uso |
|--------|--------|-----|
| 4 | Pulgar (punta) | Detección de pulsación |
| 8 | Índice (punta) | Detección de pulsación |
| 12 | Medio (punta) | Detección de pulsación |
| 16 | Anular (punta) | Detección de pulsación |
| 20 | Meñique (punta) | Detección de pulsación |

#### Configuración de MediaPipe

```python
# En hand_detector.py
class HandDetector:
    def __init__(self):
        self.hands = mp.solutions.hands.Hands(
            model_complexity=0,          # Lite (0) vs Full (1)
            max_num_hands=2,             # Máximo 2 manos
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
```

#### Métodos Principales

```python
# Detectar si hay manos en el frame
has_hands = detector.detect(frame)  # → bool

# Obtener puntas de los dedos (5 puntos por mano)
fingertips = detector.get_fingertips()  # → [(x,y), ...]

# Obtener todos los landmarks (21 puntos por mano)
landmarks = detector.get_all_landmarks()  # → [[(x,y), ...], ...]

# Dibujar visualización
detector.draw_hands(frame)
detector.draw_fingertips(frame)
```

---

### 5.2 Estimación de Profundidad

#### Principio de Triangulación Estéreo

Cuando un punto es visto desde dos cámaras separadas, su posición 3D puede calcularse por **triangulación**:

```
        Punto P (x, y, z)
              *
             /|\
            / | \
           /  |  \
          /   |   \
         /    |z   \
        /     |     \
       /      |      \
      *───────┼───────*
    Cam L   baseline   Cam R
    
    Disparidad = x_left - x_right
```

#### Fórmula Básica

```
Z = (focal_length × baseline) / disparidad

X = (x_left - cx) × Z / focal
Y = (y_left - cy) × Z / focal
```

Donde:
- `focal_length`: Distancia focal en píxeles
- `baseline`: Separación entre cámaras (cm)
- `disparidad`: Diferencia de posición X entre vistas
- `cx, cy`: Centro óptico

#### Implementación

```python
# En depth_estimator.py
class DepthEstimator:
    def triangulate_simple(self, point_left, point_right):
        """Triangulación basada en disparidad"""
        # Rectificar puntos
        p1 = self.rectify_point(point_left, 'left')
        p2 = self.rectify_point(point_right, 'right')
        
        # Calcular disparidad
        disparity = p1[0] - p2[0]
        
        if disparity <= 0:
            return None
            
        # Calcular profundidad
        Z = (self.focal * self.baseline) / disparity
        X = (p1[0] - self.cx) * Z / self.focal
        Y = (p1[1] - self.cy) * Z / self.focal
        
        # Aplicar corrección de calibración
        Z *= self.depth_correction_factor
        
        return (X, Y, Z)
```

#### Método DLT (Direct Linear Transform)

Para mayor precisión, se usa triangulación por SVD:

```python
def triangulate_dlt(self, point_left, point_right):
    """Triangulación usando Direct Linear Transform"""
    # Construir matriz A del sistema Ax = 0
    A = np.array([
        point_left[0] * P1[2] - P1[0],
        point_left[1] * P1[2] - P1[1],
        point_right[0] * P2[2] - P2[0],
        point_right[1] * P2[2] - P2[1]
    ])
    
    # Resolver por SVD
    _, _, Vt = np.linalg.svd(A)
    X = Vt[-1]
    X = X[:3] / X[3]  # Convertir de homogéneo
    
    return X
```

---

### 5.3 Algoritmos de Detección

El sistema usa un **pipeline de algoritmos** para filtrar falsos positivos y mejorar la detección.

#### Arquitectura

```python
# En algorithms/__init__.py
class AlgorithmManager:
    def __init__(self):
        self.algorithms = []
        
    def add_algorithm(self, algo):
        self.algorithms.append(algo)
        
    def process(self, finger_data):
        for algo in self.algorithms:
            finger_data = algo.process(finger_data)
        return finger_data
```

#### Algoritmos Disponibles

##### 1. Suavizado de Profundidad (Depth Smoothing)

**Problema:** El ruido en la detección causa profundidades erráticas.

**Solución:** Promedio temporal de las últimas N mediciones.

```python
# En algo_suavizado.py
class DepthSmoothingAlgorithm(BaseAlgorithm):
    def __init__(self):
        self.history_size = 5
        self.max_variation = 3.0  # cm
        self.history = {}
        
    def process(self, finger_id, depth):
        if finger_id not in self.history:
            self.history[finger_id] = []
            
        # Agregar a historial
        self.history[finger_id].append(depth)
        if len(self.history[finger_id]) > self.history_size:
            self.history[finger_id].pop(0)
            
        # Retornar promedio
        return np.mean(self.history[finger_id])
```

##### 2. Una Nota Por Acción

**Problema:** Un dedo puede activar múltiples notas al bajar lentamente.

**Solución:** Requiere levantar el dedo antes de poder activar otra nota.

```python
# En algo_una_nota.py
class OneNotePerActionAlgorithm(BaseAlgorithm):
    def __init__(self):
        self.reset_threshold = 10.0  # cm - debe subir este tanto
        self.finger_state = {}  # 'ready' | 'pressed'
        
    def can_press(self, finger_id, depth_relative):
        state = self.finger_state.get(finger_id, 'ready')
        
        if state == 'pressed':
            # Verificar si levantó lo suficiente
            if depth_relative < -self.reset_threshold:
                self.finger_state[finger_id] = 'ready'
            return False
            
        return True
        
    def mark_pressed(self, finger_id):
        self.finger_state[finger_id] = 'pressed'
```

##### 3. Filtro de Dirección

**Problema:** Notas fantasma al levantar el dedo (rebote).

**Solución:** Solo activar cuando el dedo se mueve HACIA ABAJO.

```python
# En algo_filtro_direccion.py
class DirectionFilterAlgorithm(BaseAlgorithm):
    def __init__(self):
        self.min_velocity = 0.5  # cm/frame hacia abajo
        self.last_depth = {}
        
    def process(self, finger_id, depth):
        last = self.last_depth.get(finger_id, depth)
        velocity = depth - last  # Positivo = bajando
        self.last_depth[finger_id] = depth
        
        # Solo permitir si está bajando
        return velocity > self.min_velocity
```

#### Configuración de Algoritmos

```python
# En stereo_config.py
class StereoConfig:
    # Umbrales de detección
    DEPTH_ACTIVATION_THRESHOLD = 2.0   # cm - profundidad para activar tecla
    DEPTH_RELEASE_THRESHOLD = 5.0      # cm - profundidad para soltar tecla
    MAX_DEPTH_VELOCITY = 15.0          # cm/frame - velocidad máxima válida
    SMOOTHING_WINDOW = 5               # frames de historial
```

---

## 6. Sistema del Piano Virtual

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `src/piano/virtual_keyboard.py` | Renderizado del teclado |
| `src/piano/keyboard_processor.py` | Procesamiento central |

---

### 6.1 Teclado Virtual

#### Layout: 2 Octavas (24 teclas)

```
    │C#│D#│   │F#│G#│A#│   │C#│D#│   │F#│G#│A#│
    │ 1│ 3│   │ 6│ 8│10│   │13│15│   │18│20│22│
┌───┴┬─┴┬─┴───┴┬─┴┬─┴┬─┴───┴┬─┴┬─┴───┴┬─┴┬─┴┬─┴───┐
│ C  │ D│  E   │ F│ G│  A   │ B│  C   │ D│ E│  F  │...
│ 0  │ 2│  4   │ 5│ 7│  9   │11│ 12  │14│16│ 17  │
└────┴──┴──────┴──┴──┴──────┴──┴──────┴──┴──┴─────┘
  Octava 4 (MIDI 60-71)         Octava 5 (MIDI 72-83)
```

#### Mapeo MIDI

| Tecla | Nota | MIDI |
|-------|------|------|
| 0 | C4 | 60 |
| 1 | C#4 | 61 |
| 2 | D4 | 62 |
| ... | ... | ... |
| 12 | C5 | 72 |
| ... | ... | ... |
| 23 | B5 | 83 |

#### Renderizado con Perspectiva AR

```python
# En virtual_keyboard.py
class VirtualKeyboard:
    def draw_ar(self, frame, corners, active_keys=None):
        """Dibuja teclado con transformación de perspectiva"""
        # Definir teclado rectangular
        src_points = np.array([
            [0, 0], [self.width, 0],
            [self.width, self.height], [0, self.height]
        ], dtype=np.float32)
        
        # Esquinas destino (del usuario)
        dst_points = np.array(corners, dtype=np.float32)
        
        # Calcular matriz de perspectiva
        M = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Crear imagen del teclado
        keyboard_img = self._render_keyboard(active_keys)
        
        # Aplicar transformación
        warped = cv2.warpPerspective(keyboard_img, M, (frame.shape[1], frame.shape[0]))
        
        # Superponer con transparencia
        mask = warped[:,:,3] / 255.0
        for c in range(3):
            frame[:,:,c] = frame[:,:,c] * (1-mask) + warped[:,:,c] * mask
```

#### Colores del Teclado (BGR)

```python
# En config/theme.py
class Theme:
    # Teclas blancas
    AR_WHITE_KEY_IDLE = (240, 240, 240)    # Gris claro
    AR_WHITE_KEY_ACTIVE = (80, 160, 255)   # Naranja
    
    # Teclas negras  
    AR_BLACK_KEY_IDLE = (40, 40, 40)       # Gris oscuro
    AR_BLACK_KEY_ACTIVE = (60, 140, 230)   # Naranja oscuro
```

---

### 6.2 Mapeo de Teclas

#### Lógica de Detección de Pulsación

```python
# En keyboard_mapper.py
class KeyboardMapper:
    def map_finger_to_key(self, finger_pos, depth_relative):
        """
        finger_pos: (x, y) en píxeles
        depth_relative: profundidad respecto al teclado (cm)
                       positivo = tocando/debajo
                       negativo = encima (en el aire)
        """
        # 1. Verificar si está dentro del área del teclado
        if not self.is_in_keyboard_region(finger_pos):
            return None
            
        # 2. Verificar profundidad
        if depth_relative > self.DEPTH_THRESHOLD:  # 2.0 cm
            # Está presionando
            key = self.get_key_at_position(finger_pos)
            return key
            
        return None
```

#### Sistema de Estados

```python
# Mantener estado anterior para detectar cambios
def process_frame(self, fingers_data):
    current_keys = set()
    
    for finger in fingers_data:
        key = self.map_finger_to_key(finger.pos, finger.depth)
        if key is not None:
            current_keys.add(key)
    
    # Detectar nuevas pulsaciones y liberaciones
    pressed = current_keys - self.previous_keys
    released = self.previous_keys - current_keys
    
    self.previous_keys = current_keys
    
    return pressed, released
```

---

### 6.3 Procesamiento de Pulsaciones

#### Flujo Completo

```python
# En keyboard_processor.py
class KeyboardProcessor:
    def process_frame(self, frame_left, frame_right, display_frame):
        # 1. Detectar manos en ambas cámaras
        self.detector_left.detect(frame_left)
        self.detector_right.detect(frame_right)
        
        # 2. Obtener puntas de dedos
        tips_left = self.detector_left.get_fingertips()
        tips_right = self.detector_right.get_fingertips()
        
        # 3. Dibujar teclado AR
        self.keyboard.draw_ar(display_frame, self.corners)
        
        # 4. Para cada dedo, calcular 3D y mapear
        for i, (tip_l, tip_r) in enumerate(zip(tips_left, tips_right)):
            # Triangular posición 3D
            pos_3d = self.depth_estimator.triangulate(tip_l, tip_r)
            
            if pos_3d is None:
                continue
                
            # Calcular profundidad relativa al teclado
            depth_relative = pos_3d[2] - self.keyboard_distance
            
            # Mapear a tecla
            key = self.mapper.map_finger_to_key(tip_l, depth_relative)
            
            if key is not None:
                # Tocar nota
                midi_note = 60 + key
                self.synth.noteon(0, midi_note, 100)
```

---

## 7. Sistema de Gameplay

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `src/gameplay/rythm_game.py` | Motor del juego de ritmo |
| `src/gameplay/song_chart.py` | Definición de charts |
| `src/songs/song_base.py` | Clase base de canciones |
| `src/songs/song_manager.py` | Gestor de canciones |
| `src/songs/chart_files/` | Archivos de canciones |

---

### 7.1 Juego de Ritmo

#### Mecánica

1. Las notas **caen desde arriba** hacia una línea de impacto
2. El jugador debe presionar la tecla correcta cuando la nota llega
3. Se evalúa **timing** y se otorgan puntos

```
┌────────────────────────────────────────┐
│  ♪        ♪                       ♪    │  ← Notas cayendo
│       ♪           ♪                    │
│                        ♪               │
│═══════════════════════════════════════│  ← Línea de impacto
│  │C│D│E│F│G│A│B│C│D│E│F│G│A│B│  │    │  ← Teclado
└────────────────────────────────────────┘
```

#### Sistema de Puntuación

| Timing | Puntos | Tolerancia |
|--------|--------|------------|
| PERFECT | 100 × combo | ±0.1 segundos |
| GOOD | 50 × combo | ±0.25 segundos |
| MISS | 0 (rompe combo) | > 0.25 segundos |

#### Implementación

```python
# En rythm_game.py
class RhythmGame:
    def __init__(self):
        self.note_speed = 300        # píxeles/segundo
        self.hit_line_y = 400        # posición Y de impacto
        self.perfect_window = 0.1    # segundos
        self.good_window = 0.25      # segundos
        
    def update(self, dt):
        """Actualizar posiciones de notas"""
        for note in self.active_notes:
            note.y += self.note_speed * dt
            
            # Verificar si pasó sin ser tocada
            if note.y > self.hit_line_y + self.miss_threshold:
                self.miss(note)
                
    def check_hit(self, key_pressed):
        """Verificar si una tecla presionada coincide con nota"""
        for note in self.active_notes:
            if note.key != key_pressed:
                continue
                
            # Calcular diferencia de timing
            time_diff = abs(note.expected_time - self.current_time)
            
            if time_diff <= self.perfect_window:
                return self.perfect(note)
            elif time_diff <= self.good_window:
                return self.good(note)
                
        return None  # No había nota para esa tecla
```

---

### 7.2 Formato de Canciones

#### Documentación Oficial

Ver archivo: `src/songs/chart_files/FORMATO_CANCIONES.md`

#### Estructura de NoteEvent

```python
from dataclasses import dataclass

@dataclass
class NoteEvent:
    key: int        # Tecla del teclado (0-23)
    time: float     # Tiempo en segundos desde inicio
    duration: float # Duración en segundos (para notas largas)
```

#### Ejemplo de Canción

```python
# En chart_files/tutorial.py
class TutorialSong(SongBase):
    name = "Tutorial"
    artist = "Sistema"
    bpm = 90
    difficulty = "Muy Fácil"
    key_signature = "C Mayor"
    
    def get_chart(self):
        return [
            NoteEvent(key=0, time=0.0, duration=0.5),    # C4
            NoteEvent(key=2, time=0.5, duration=0.5),    # D4
            NoteEvent(key=4, time=1.0, duration=0.5),    # E4
            NoteEvent(key=5, time=1.5, duration=0.5),    # F4
            NoteEvent(key=7, time=2.0, duration=1.0),    # G4 (larga)
        ]
```

#### Notación Alternativa

```python
# Usando nombres de notas
chart = [
    ("C4", 0.0, 0.5),
    ("D4", 0.5, 0.5),
    ("E4", 1.0, 0.5),
]

# El sistema convierte:
# C4 → key 0
# D4 → key 2
# E4 → key 4
```

---

## 8. Sistema de Lecciones

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `src/theory/lesson_base.py` | Clase base abstracta |
| `src/theory/lesson_manager.py` | Gestor de lecciones |
| `src/theory/progress_manager.py` | Progreso del usuario |
| `src/theory/lessons/` | Archivos de lecciones |

### Lecciones Disponibles

| # | Archivo | Tema |
|---|---------|------|
| 1 | `01_lesson_rhythm.py` | Ritmo y Tempo |
| 2 | `02_lesson_intervals.py` | Intervalos |
| 3 | `03_lesson_scales.py` | Escalas |
| 4 | `04_lesson_chords.py` | Acordes Básicos |
| 5 | `05_lesson_melody.py` | Melodía |
| 6 | `06_lesson_rhythm2.py` | Ritmo Avanzado |
| 7 | `07_lesson_harmony.py` | Armonía |
| 8 | `08_lesson_jazz.py` | Jazz |
| 9 | `09_lesson_blues.py` | Blues |
| 10 | `10_lesson_rock.py` | Rock |

### Estructura de Lección

```python
# En theory/lessons/01_lesson_rhythm.py
from theory.lesson_base import LessonBase

class RhythmLesson(LessonBase):
    id = "01_rhythm"
    title = "Ritmo y Tempo"
    description = "Aprende los fundamentos del ritmo musical"
    
    glossary = {
        "BPM": "Beats Por Minuto - velocidad de la música",
        "Tempo": "Velocidad general de una pieza",
        "Pulso": "Latido regular de la música",
    }
    
    def get_content(self):
        return [
            {
                "type": "text",
                "content": "El ritmo es la base de toda la música..."
            },
            {
                "type": "interactive",
                "action": "play_metronome",
                "bpm": 60
            },
            {
                "type": "exercise",
                "instruction": "Toca C4 cada vez que escuches el beat",
                "target_notes": [0, 0, 0, 0]
            }
        ]
```

### Sistema de Progreso

```python
# En progress_manager.py
class ProgressManager:
    PROGRESS_FILE = "user_progress.json"
    
    def is_lesson_unlocked(self, lesson_id):
        """Primera lección siempre desbloqueada"""
        if lesson_id == "01_rhythm":
            return True
            
        # Requiere completar la anterior
        previous = self.get_previous_lesson(lesson_id)
        return self.is_completed(previous)
        
    def mark_completed(self, lesson_id):
        progress = self.load_progress()
        progress["completed"].append(lesson_id)
        self.save_progress(progress)
```

---

## 9. Interfaz de Usuario

### Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `src/ui/qt_main_menu.py` | Menú principal |
| `src/ui/qt_initial_menu.py` | Pantalla inicial |
| `src/ui/qt_free_mode_window.py` | Modo libre |
| `src/ui/qt_songs_menu.py` | Menú de canciones |
| `src/ui/qt_theory_menu.py` | Menú de teoría |
| `src/ui/qt_song_window.py` | Ventana de juego |
| `src/ui/qt_lesson_window.py` | Ventana de lección |
| `src/ui/qt_camera_config.py` | Config. de cámaras |
| `src/ui/qt_advanced_config.py` | Config. avanzada |

### Flujo de Navegación

```
┌─────────────────┐
│  MENÚ PRINCIPAL │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌─────────┐ ┌───────┐
│ RITMO │ │ LIBRE │ │ TEORÍA  │ │CONFIG │
└───┬───┘ └───┬───┘ └────┬────┘ └───┬───┘
    │         │          │          │
    ▼         ▼          ▼          ├→ Cámaras
┌───────┐ ┌───────┐ ┌─────────┐    ├→ Calibrar
│Menú   │ │Free   │ │Menú     │    └→ Algoritmos
│Cancio-│ │Mode   │ │Lecciones│
│nes    │ │Window │ │         │
└───┬───┘ └───────┘ └────┬────┘
    │                    │
    ▼                    ▼
┌───────┐          ┌─────────┐
│Song   │          │Lesson   │
│Window │          │Window   │
└───────┘          └─────────┘
```

### Estilo Visual

El proyecto usa un estilo "Modo Aventura" con colores brillantes:

```python
# En config/theme.py
class Theme:
    # Colores principales
    PRIMARY = (255, 180, 50)      # Amarillo dorado
    SECONDARY = (100, 200, 255)   # Azul cielo
    ACCENT = (255, 100, 100)      # Rojo coral
    
    # Fondos
    BG_MAIN = (30, 30, 50)        # Azul oscuro
    BG_PANEL = (45, 45, 70)       # Azul medio
    
    # Texto
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_SECONDARY = (180, 180, 200)
```

---

## 10. Configuración

### Archivos de Configuración

| Archivo | Descripción |
|---------|-------------|
| `src/config/app_config.py` | Configuración general |
| `src/config/game_config.py` | Configuración de juego |
| `src/config/theme.py` | Colores y estilos |
| `src/vision/stereo_config.py` | Parámetros estéreo |
| `camcalibration/calibration.json` | Datos de calibración |

### Configuración de Cámaras

```python
# En stereo_config.py
class StereoConfig:
    # IDs de dispositivo
    LEFT_CAMERA_ID = 0
    RIGHT_CAMERA_ID = 1
    
    # Resolución
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    FPS = 30
    
    # ¿Cámaras intercambiadas?
    CAMERAS_SWAPPED = False
```

### Configuración de Detección

```python
# En stereo_config.py
class StereoConfig:
    # Óptica (Logitech C920)
    FOCAL_LENGTH = 600.0      # píxeles
    BASELINE = 15.0           # cm
    
    # Umbrales
    DEPTH_ACTIVATION = 2.0    # cm - para activar tecla
    DEPTH_RELEASE = 5.0       # cm - para soltar tecla
    MAX_VELOCITY = 15.0       # cm/frame - filtro de ruido
    
    # Suavizado
    SMOOTHING_WINDOW = 5      # frames
```

### Configuración de Audio

```python
# En app_config.py
class AppConfig:
    # MIDI
    BASE_MIDI_NOTE = 60  # C4
    
    # FluidSynth
    SOUNDFONT_PATH = "utils/fluid/fluid/FluidR3_GM.sf2"
    AUDIO_DRIVER = "dsound"  # Windows
```

---

## 11. Solución de Problemas

### Problema: Calibración con alto error de reproyección

**Síntomas:**
- Error > 1.5 píxeles en calibración individual
- Error RMS > 1.0 en calibración estéreo

**Causas y soluciones:**

| Causa | Solución |
|-------|----------|
| Tablero borroso | Mejorar iluminación, reducir velocidad de movimiento |
| Pocas imágenes | Capturar más de 20 imágenes por cámara |
| Poca variación | Incluir más ángulos y distancias |
| Detección incorrecta | Verificar tamaño de tablero en configuración |
| Cámaras movidas | Volver a calibrar desde el inicio |

### Problema: Profundidad incorrecta

**Síntomas:**
- Z reportada no coincide con distancia real
- Activación inconsistente de teclas

**Soluciones:**

1. Verificar que la calibración estéreo tiene RMS < 0.6
2. Re-hacer Fase 3 (calibración de profundidad) con medición precisa
3. Verificar que `depth_correction_factor` es cercano a 1.0 (0.8-1.2)

### Problema: Notas fantasma (activación sin presionar)

**Síntomas:**
- Notas se activan sin tocar
- Múltiples notas por un solo toque

**Soluciones:**

1. Activar algoritmo "Filtro de Dirección"
2. Aumentar `DEPTH_ACTIVATION_THRESHOLD`
3. Aumentar `SMOOTHING_WINDOW`
4. Verificar iluminación (evitar sombras fuertes)

### Problema: No se detectan las manos

**Síntomas:**
- MediaPipe no encuentra manos
- Detección intermitente

**Soluciones:**

1. Mejorar iluminación (evitar contraluz)
2. Usar fondo contrastante
3. Reducir `min_detection_confidence` a 0.4
4. Verificar que las manos están completamente visibles

### Problema: Cámaras intercambiadas

**Síntomas:**
- La cámara "izquierda" muestra vista derecha
- Triangulación da valores negativos

**Solución:**

```python
# En stereo_config.py
CAMERAS_SWAPPED = True
```

O intercambiar físicamente los cables USB.

### Problema: Audio no funciona

**Síntomas:**
- No se escucha sonido al presionar teclas
- Error al inicializar FluidSynth

**Soluciones:**

1. Verificar que `libfluidsynth-3.dll` existe en `utils/fluidsynth/bin/`
2. Verificar que `FluidR3_GM.sf2` existe en `utils/fluid/fluid/`
3. Instalar Visual C++ Redistributable si hay errores de DLL

---

## 12. Referencia de API

### Módulo: vision.hand_detector

```python
class HandDetector:
    """Detector de manos usando MediaPipe"""
    
    def detect(self, frame: np.ndarray) -> bool:
        """Detecta manos en el frame. Retorna True si encontró alguna."""
        
    def get_fingertips(self) -> List[Tuple[int, int]]:
        """Retorna lista de (x, y) para las 5 puntas de dedos."""
        
    def get_all_landmarks(self) -> List[List[Tuple[int, int]]]:
        """Retorna todos los 21 landmarks por cada mano detectada."""
        
    def draw_hands(self, frame: np.ndarray) -> None:
        """Dibuja esqueleto de manos en el frame."""
        
    def draw_fingertips(self, frame: np.ndarray, color=(0,255,0), radius=8) -> None:
        """Dibuja círculos en las puntas de los dedos."""
```

### Módulo: vision.depth_estimator

```python
class DepthEstimator:
    """Estimador de profundidad estéreo"""
    
    @staticmethod
    def create(calibration_path: str) -> 'DepthEstimator':
        """Factory: carga calibración y crea instancia."""
        
    def rectify_frames(self, left: np.ndarray, right: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Rectifica par estéreo usando mapas precalculados."""
        
    def rectify_point(self, point: Tuple[int, int], camera: str) -> Tuple[float, float]:
        """Rectifica un punto 2D. camera = 'left' | 'right'."""
        
    def triangulate_simple(self, p_left: Tuple, p_right: Tuple) -> Optional[Tuple[float, float, float]]:
        """Triangulación por disparidad. Retorna (X, Y, Z) en cm."""
        
    def triangulate_dlt(self, p_left: Tuple, p_right: Tuple) -> Optional[Tuple[float, float, float]]:
        """Triangulación DLT (más precisa). Retorna (X, Y, Z) en cm."""
```

### Módulo: piano.virtual_keyboard

```python
class VirtualKeyboard:
    """Teclado virtual AR de 2 octavas"""
    
    def draw_ar(self, frame: np.ndarray, corners: List, active_keys: Set[int] = None) -> None:
        """Dibuja teclado con perspectiva AR sobre el frame."""
        
    def is_in_bounds(self, point: Tuple[int, int]) -> bool:
        """Verifica si el punto está dentro del área del teclado."""
        
    def get_key_at_position(self, point: Tuple[int, int]) -> Optional[int]:
        """Retorna número de tecla (0-23) en la posición, o None."""
        
    def key_to_midi(self, key: int) -> int:
        """Convierte tecla (0-23) a nota MIDI (60-83)."""
```

### Módulo: gameplay.rythm_game

```python
class RhythmGame:
    """Motor del juego de ritmo"""
    
    def start(self, song: SongBase) -> None:
        """Inicia juego con la canción especificada."""
        
    def update(self, dt: float) -> None:
        """Actualiza estado del juego. dt = delta time en segundos."""
        
    def check_input(self, keys_pressed: Set[int]) -> List[str]:
        """Verifica input del jugador. Retorna lista de resultados."""
        
    def draw(self, frame: np.ndarray) -> None:
        """Dibuja notas y UI del juego."""
        
    def get_stats(self) -> Dict:
        """Retorna estadísticas: score, combo, max_combo, accuracy."""
```

### Módulo: calibration.camera_calibrator

```python
class CameraCalibrator:
    """Calibrador de cámara individual"""
    
    def add_image(self, frame: np.ndarray) -> bool:
        """Agrega imagen de calibración. Retorna True si detectó tablero."""
        
    def calibrate(self) -> Dict:
        """Ejecuta calibración. Retorna dict con K, D, error."""
        
    def get_progress(self) -> Dict:
        """Retorna progreso: total_images, by_category."""
```

### Módulo: calibration.stereo_calibrator

```python
class StereoCalibrator:
    """Calibrador estéreo"""
    
    def add_pair(self, left: np.ndarray, right: np.ndarray) -> bool:
        """Agrega par de imágenes. Retorna True si tablero visible en ambas."""
        
    def calibrate(self, K1, D1, K2, D2) -> Dict:
        """Ejecuta calibración estéreo. Retorna R, T, E, F, RMS, baseline."""
        
    def compute_rectification(self) -> Dict:
        """Calcula matrices de rectificación R1, R2, P1, P2, Q."""
```

---

## Apéndice A: Estructura de calibration.json

```json
{
  "version": "2.0",
  "timestamp": "2026-01-19T10:30:00",
  
  "cameras": {
    "left_id": 0,
    "right_id": 1,
    "resolution": [640, 480],
    "swapped": false
  },
  
  "left_camera": {
    "camera_matrix": [
      [600.0, 0.0, 320.0],
      [0.0, 600.0, 240.0],
      [0.0, 0.0, 1.0]
    ],
    "distortion": [-0.05, 0.1, 0.0, 0.0, -0.02],
    "reprojection_error": 0.45
  },
  
  "right_camera": {
    "camera_matrix": [...],
    "distortion": [...],
    "reprojection_error": 0.48
  },
  
  "stereo": {
    "rotation_matrix": [...],
    "translation_vector": [...],
    "essential_matrix": [...],
    "fundamental_matrix": [...],
    "baseline_cm": 15.2,
    "rms_error": 0.35
  },
  
  "rectification": {
    "R1": [...],
    "R2": [...],
    "P1": [...],
    "P2": [...],
    "Q": [...]
  },
  
  "depth": {
    "correction_factor": 1.02,
    "keyboard_distance_cm": 45.0
  },
  
  "keyboard_ar": {
    "corners": [
      [100, 300],
      [540, 300],
      [540, 450],
      [100, 450]
    ]
  }
}
```

---

## Apéndice A.2: Problemas Conocidos y Soluciones en Progreso

### Problema: Desalineación entre Teclado Visual y Funcional (Enero 2026)

#### Descripción del Problema
El usuario observa que el teclado visual (donde se dibuja el piano AR) está en la posición correcta, pero el teclado funcional (donde se detectan las pulsaciones) está desplazado hacia la derecha. Esto causa que al tocar una tecla visible, el sistema registre una tecla diferente.

#### Diagnóstico Implementado
Se implementó visualización de debug con círculos de colores:
- **AZUL**: Puntos de MediaPipe dibujados por `drawTips()`
- **ROJO (MAP)**: Coordenadas que usa `KeyboardMapper` para detectar teclas
- **AMARILLO (ROT)**: Coordenadas intermedias de diagnóstico

**Síntomas observados:**
- Círculos ROJOS desplazados respecto a AZULES
- Disparidad NEGATIVA (`x_diff=-132`) en lugar de positiva
- Las coordenadas reportadas no coincidían con la posición visual

#### Causa Raíz Identificada
El problema era la arquitectura de transformación de coordenadas:

1. **Flujo problemático (antes):**
   ```
   frame_left (RAW) → findHands() → landmarks en espacio RAW
   frame_left → apply_display_transform() → frame_left_display (ROTADO 180°)
   drawTips(frame_left_display, rotate_180=True) → doble transformación
   getFingerTipsPos(rotate_180=True) → coordenadas transformadas
   ```
   
   El problema: `drawTips` dibujaba sobre un frame ya rotado Y aplicaba transformación de coordenadas, resultando en doble transformación visual pero simple transformación de datos.

2. **Flujo corregido (después):**
   ```
   frame_left_display (ROTADO) → findHands() → landmarks en espacio ROTADO
   drawTips(frame_left_display, rotate_180=False) → sin transformación adicional
   getFingerTipsPos(rotate_180=False) → coordenadas directas
   ```
   
   Solución: Detectar manos sobre el frame YA ROTADO. Así MediaPipe trabaja en el mismo sistema de coordenadas que el display y el teclado AR.

#### Solución Implementada

1. **Cambio de arquitectura** en `qt_free_mode_window.py`:
   ```python
   # ANTES (incorrecto):
   self.hand_detector_left.findHands(frame_left)  # Frame RAW
   hl_hands, hl_tips = self.hand_detector_left.getFingerTipsPos(rotate_180=True)
   self.hand_detector_left.drawTips(frame_left_display, rotate_180=True)
   
   # DESPUÉS (correcto):
   self.hand_detector_left.findHands(frame_left_display)  # Frame YA ROTADO
   hl_hands, hl_tips = self.hand_detector_left.getFingerTipsPos(rotate_180=False)
   self.hand_detector_left.drawTips(frame_left_display, rotate_180=False)
   ```

2. **Principio clave**: Detectar en el mismo espacio de coordenadas donde se dibuja y mapea.

#### Estado Actual
- ✅ Arquitectura corregida - detección sobre frame rotado
- 🔄 Pendiente verificación visual (círculos ROJO, AMARILLO y AZUL deben coincidir)
- 🔄 Pendiente prueba de funcionalidad (tocar tecla correcta)

#### Archivos Modificados
- `src/vision/hand_detector.py` - Líneas 95-115 (`getFingerTipsPos` con parámetro `rotate_180`)
- `src/ui/qt_free_mode_window.py` - Líneas 217-230 (detección sobre frame rotado)

#### Nota sobre Estéreo
El cambio afecta solo la cámara izquierda (display principal). La cámara derecha sigue detectando sobre frame RAW para mantener coherencia geométrica en triangulación estéreo. Esto puede requerir ajustes adicionales si el matching estéreo presenta problemas.

---

## Apéndice B: Glosario

| Término | Definición |
|---------|------------|
| **Baseline** | Distancia física entre los centros ópticos de las dos cámaras |
| **Disparidad** | Diferencia en posición X de un punto entre vista izquierda y derecha |
| **Epipolar** | Relacionado con la geometría que conecta puntos correspondientes entre vistas |
| **Intrínsecos** | Parámetros internos de la cámara (focal, centro óptico, distorsión) |
| **Extrínsecos** | Parámetros de posición/orientación relativa entre cámaras |
| **Landmark** | Punto clave detectado en la mano por MediaPipe |
| **MIDI** | Musical Instrument Digital Interface - protocolo estándar de música digital |
| **Rectificación** | Proceso de transformar imágenes para que líneas epipolares sean horizontales |
| **RMS** | Root Mean Square - medida de error promedio |
| **Triangulación** | Cálculo de posición 3D a partir de dos vistas 2D |

---

## Apéndice C: Licencia y Créditos

- **MediaPipe**: Apache License 2.0 - Google
- **OpenCV**: Apache License 2.0 - OpenCV team
- **FluidSynth**: LGPL 2.1
- **FluidR3_GM SoundFont**: GPL

---

*Documentación generada para Piano Virtual v2.0.0*
*© 2026 mherrera*

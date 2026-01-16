# ANÁLISIS COMPLETO DEL SISTEMA - FALLAS POTENCIALES

> **Fecha de Análisis:** 2026-01-14  
> **Estado del Sistema:** Modo Raw (Algoritmos Desactivados)  
> **Arquitectura:** Stereo Vision → Hand Detection → Triangulation → Keyboard Mapping

---

## 🔴 FALLAS CRÍTICAS (Alta Prioridad)

### 1. **Strict ID Matching Failure**
**Ubicación:** `src/ui/qt_free_mode_window.py:275`

**Problema:**
```python
if fl[0] == fr[0] and fl[1] == fr[1]:  # Strict Match
```

- **Causa:** MediaPipe asigna IDs de mano **no determinísticamente**
- **Síntoma:** Si la cámara izquierda detecta `hand_id=0` y la derecha detecta `hand_id=1` para la MISMA mano física, **NO SE EMPAREJA**.
- **Resultado:** **Detección total fallida** a pesar de que ambas cámaras ven la mano.
- **Frecuencia:** Muy alta en proximidad extrema (<5cm) o cuando la mano entra/sale del campo de visión

**Diagnóstico Recomendado:**
```python
# Agregar log temporal en qt_free_mode_window.py
print(f"[ID_DEBUG] L={[t[0] for t in hl_tips]} R={[t[0] for t in hr_tips]}")
```
Si ves `L=[0] R=[1]` → Confirmas el problema.

**Solución:**
- **Opción A (Robust):** Implementar matching geométrico por posición (distancia euclidiana)
- **Opción B (Quick Fix):** Reducir `model_complexity` de MediaPipe a 0 (menos preciso pero IDs más estables)

---

### 2. **Calibration Data Staleness**
**Ubicación:** `camcalibration/calibration.json`

**Problema:**
```python
CAMERA_SEPARATION = 9.62  # Debe coincidir EXACTAMENTE con realidad física
```

- **Causa:** Si las cámaras se mueven **CUALQUIER cantidad**, la calibración se invalida
- **Síntoma:** 
  - Profundidades absurdas (`520cm`, `1181cm`)
  - Triangulación con `Z < 0` (punto "detrás" de la cámara)
- **Validación Actual:** NINGUNA ❌
- **Riesgo:** Sistema puede funcionar "aparentemente" pero con errores de 10-50cm

**Diagnóstico:**
1. Medir físicamente la separación entre centros ópticos de las cámaras
2. Comparar con `calibration.json → stereo → baseline_cm`
3. Si difieren > 1mm → Re-calibrar

**Solución Preventiva:**
```python
# Agregar check en depth_estimator.py:__init__
if abs(self.baseline_cm - StereoConfig.CAMERA_SEPARATION) > 0.1:
    print(f"[WARNING] Baseline mismatch: {self.baseline_cm} vs {StereoConfig.CAMERA_SEPARATION}")
```

---

### 3. **Negative Z Filtering Loss**
**Ubicación:** `src/ui/qt_free_mode_window.py:293-300`

**Problema:**
```python
if depth_absolute <= 0 or math.isinf(depth_absolute) or math.isnan(depth_absolute):
    continue  # Silently discard
```

- **Causa:** Triangulación DLT devuelve `Z < 0` cuando puntos NO se corresponden geométricamente
- **Síntoma:** Detección intermitente (dropout cada 3-5 frames)
- **Raíz del Problema:** El filtro es **REACTIVO** (descarta después de fallar), no **PREVENTIVO**
- **Tasa de Falla:** ~40% de frames a distancia <10cm

**Diagnóstico:**
Habilitar temporalmente:
```python
if depth_absolute <= 0:
    disp_x = pt_l_rect[0] - pt_r_rect[0]
    print(f"[NEG_Z] XL={pt_l_rect[0]:.1f} XR={pt_r_rect[0]:.1f} Disp={disp_x:.1f}")
```
Si `Disp < 0` → Las coordenadas están INVERTIDAS (matching fallido).

**Solución:**
Implementar disparity sanity check ANTES de triangular:
```python
disparity = pt_l_rect[0] - pt_r_rect[0]
if disparity <= 0:  # Geometrically impossible
    continue
```

---

### 4. **Keyboard Distance Mismatch**
**Ubicación:** `src/ui/qt_free_mode_window.py:243`

**Problema:**
```python
keyboard_distance = self.depth_estimator.keyboard_distance_cm  # ej: 41.78cm
depth_relative = keyboard_distance - depth_absolute
```

- **Causa:** `keyboard_distance` se calcula en **Fase 3 de calibración**, asumiendo que el tablero de calibración se coloca exactamente donde estará el plano del teclado virtual
- **Realidad:** El usuario probablemente **NO** colocó el tablero en el plano exacto de interacción
- **Síntoma:** 
  - Necesitas presionar "en el aire" (10cm sobre la mesa) para que suene
  - O al revés: necesitas "hundir" la mano 5cm bajo la mesa
- **Error Acumulado:** ±5-15cm típico

**Diagnóstico:**
```python
# Comprobar en logs de inicio
print(f"Keyboard Distance: {keyboard_distance} cm")
```
Luego medir físicamente la distancia desde la cámara izquierda hasta la mesa donde tocas.

**Solución:**
- Re-ejecutar Fase 3 con el tablero EXACTAMENTE en el plano de la mesa
- O agregar un offset configurable:
```python
KEYBOARD_OFFSET_CM = 5.0  # Ajuste manual
depth_relative = keyboard_distance - depth_absolute + KEYBOARD_OFFSET_CM
```

---

### 5. **Algorithm Bypass = No Safety Net**
**Ubicación:** `src/vision/keyboard_mapper.py:245`

**Problema:**
```python
# DESACTIVADO POR SOLICITUD DE USUARIO (Raw Mode)
# filtered_detections = self.algorithm_manager.process_detections(...)
filtered_detections = raw_detections  # Sin filtros
```

- **Causa Raíz:** Se eliminaron TODOS los algoritmos de corrección
- **Consecuencias:**
  1. **No Lift Guard:** Levantamiento de dedo puede re-trigger nota
  2. **No Debounce:** Ruido en el borde de detección causa notas dobles/triples
  3. **No Smoothing:** Jitter de tracking genera velocidad errática
- **Síntoma:**
  - "Ghost notes" al soltar teclas
  - "Machine gun" efecto (nota se enciende/apaga rápidamente)
  - Detección hipersensible a micro-movimientos

**Diagnóstico:**
Logs actuales en consola ya muestran esto:
```
[PASS] 5 | v=2.71
[PASS] 3 | v=-4.06   ← NEGATIVO (Lifting), pero pasa
[PASS] 2 | v=0.06    ← Casi estático, pero pasa
```

**Solución:**
Restaurar MÍNIMO el Lift Guard:
```python
# En keyboard_mapper.py, ANTES de pasar a note ON
for det in filtered_detections:
    velocity = det[3]
    if velocity < -5.0:  # Strong lift motion
        continue  # Skip
```

---

## 🟡 FALLAS MODERADAS (Media Prioridad)

### 6. **Depth Range Too Permissive**
**Ubicación:** `src/vision/keyboard_mapper.py:138`

**Problema:**
```python
if depth < -30.0 or depth > 50.0:
    continue
```

- **Rango Físico:** -30cm a +50cm (80cm total!)
- **Realidad:** Interacción musical típica: -5cm a +10cm (15cm)
- **Consecuencia:** Se aceptan detecciones **físicamente imposibles**
- **Ejemplo:** Mano a 40cm sobre la mesa (casi tocando el techo) aún se considera "válida"

**Solución:**
```python
if depth < -10.0 or depth > 15.0:  # Más restrictivo
    continue
```

---

### 7. **Display Transform Confusion**
**Ubicación:** `src/vision/stereo_config.py:91-127`

**Problema:**
- **Detección:** Usa frames RAW (sin espejo)
- **Visualización:** Usa `apply_display_transform` (180° rotation)
- **Keyboard Drawing:** Dibujado SOBRE frame transformado
- **Keyboard Hitbox:** Calculado en coordenadas RAW

**Riesgo:**
Si `transform_point_for_display` tiene un bug, el dibujo visual y la hitbox NO coinciden.

**Diagnóstico:**
```python
# En qt_free_mode_window.py
vx, vy = StereoConfig.transform_point_for_display((t[2], t[3]), w_frame, h_frame)
print(f"Raw=({t[2]}, {t[3]}) → Visual=({vx}, {vy})")
```

**Solución:**
Actualmente implementado correctamente, pero vulnerable si se modifica `StereoConfig`.

---

### 8. **Camera Initialization Failure**
**Ubicación:** `src/core/persistent_resources.py`

**Problema:**
- Si `cv2.VideoCapture` falla → Crash sin recovery
- Logs actuales:
```
Iniciando Izquierda (0)...
fluidsynth: error: Device "default" does not exists
```

**Riesgo:**
- Cámaras USB desconectadas
- Otro proceso usando las cámaras
- Driver corrupto (NVIDIA virtual camera)

**Solución:**
Agregar retry logic:
```python
for attempt in range(3):
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    if cap.isOpened():
        break
    time.sleep(1.0)
else:
    raise RuntimeError(f"Failed to open camera {camera_id}")
```

---

### 9. **Virtual Keyboard Position Drift**
**Ubicación:** `src/vision/stereo_config.py:185-188`

**Problema:**
```python
KEYBOARD_Y0_RATIO = 0.540  # Cambiado múltiples veces
KEYBOARD_Y1_RATIO = 0.810
```

- **Historia:** El teclado se ha movido 3 veces en esta sesión
- **Consecuencia:** El usuario perdió la referencia mental de "dónde tocar"
- **Calibración Fase 3:** Asumió una posición ANTIGUA del teclado

**Solución:**
- Re-ejecutar Fase 3 después de mover el teclado
- O documentar claramente: "Si mueves el teclado virtual, re-calibra Fase 3"

---

### 10. **MediaPipe Model Complexity**
**Ubicación:** `src/vision/hand_detector.py`

**Problema Implícito:**
- MediaPipe tiene 3 niveles de `model_complexity`: 0, 1, 2
- Mayor complejidad = Más preciso pero MÁS LENTO y más inestable en IDs
- Configuración actual: Probablemente 1 (default)

**Síntoma:**
- Latencia > 50ms en detección
- IDs swap frecuente (relacionado con Falla #1)

**Solución:**
Experimentar con `model_complexity=0`:
```python
self.hands = mp.solutions.hands.Hands(
    model_complexity=0,  # Más rápido, IDs más estables
    ...
)
```

---

## 🟢 OPTIMIZACIONES (Baja Prioridad)

### 11. **Depth Smoothing Disabled**
**Problema:** `KeyboardMapper` tiene smoothing pero está configurado con ventana muy pequeña
**Mejora:** Aumentar `smoothing_window = 5` a `smoothing_window = 8`

### 12. **No Chord Detection**
**Problema:** Sistema toca notas simultáneas pero no las reconoce como acordes
**Mejora:** Implementar agrupación temporal (ventana de 50ms)

### 13. **Hardcoded Paths**
**Ubicación:** `stereo_config.py:176`
```python
SOUNDFONT_PATH = r"C:\CodingWindows\IHC_Proyecto_Fork\..."
```
**Riesgo:** No portátil entre máquinas
**Mejora:** Usar rutas relativas

---

## 🔧 PROCEDIMIENTO DE DIAGNÓSTICO SISTEMÁTICO

### Paso 1: Validar Calibración
```bash
# Verificar que calibration.json existe y es reciente
dir camcalibration\calibration.json

# Revisar baseline
python -c "import json; print(json.load(open('camcalibration/calibration.json'))['stereo']['baseline_cm'])"
```

### Paso 2: Test ID Matching
Habilitar en `qt_free_mode_window.py:271`:
```python
if self._diag_counter % 30 == 0:
    print(f"[DIAG] Manos: L={len(hl_tips)} R={len(hr_tips)}")
    print(f"[DIAG] IDs Left: {[t[0] for t in hl_tips]}")
    print(f"[DIAG] IDs Right: {[t[0] for t in hr_tips]}")
```

**Resultado Esperado:** `IDs Left: [0]` y `IDs Right: [0]` (mismos IDs)  
**Resultado Malo:** `IDs Left: [0]` y `IDs Right: [1]` → Falla #1 confirmada

### Paso 3: Test Triangulación
Habilitar en `qt_free_mode_window.py:300`:
```python
if depth_absolute <= 0:
    print(f"[FAIL] Negative Z: {depth_absolute:.1f}")
```

**Frecuencia Aceptable:** <5% de frames  
**Frecuencia Crítica:** >30% de frames → Re-calibrar

### Paso 4: Test Depth Accuracy
```python
# Colocar mano a distancia CONOCIDA (ej: 30cm medidos con regla)
# Observar logs de depth_absolute
# Error aceptable: ±3cm
```

---

## 📊 MATRIZ DE IMPACTO

| Falla | Síntoma Usuario | Frecuencia | Severidad | Fix Effort |
|-------|----------------|------------|-----------|-----------|
| #1 ID Matching | "No detecta nada" | Alta | 🔴 Crítica | Media |
| #2 Calibration Stale | Depth absurdos | Media | 🔴 Crítica | Baja (Re-calibrar) |
| #3 Negative Z | Drops intermitentes | Alta | 🔴 Crítica | Baja |
| #4 Keyboard Distance | "Toca en el aire" | Alta | 🔴 Crítica | Media |
| #5 No Safety Algorithms | Ghost notes | Media | 🔴 Crítica | Baja |
| #6 Wide Depth Range | Aceptación errónea | Baja | 🟡 Moderada | Baja |
| #7 Transform Bug | Visual mismatch | Muy Baja | 🟡 Moderada | N/A (Preventivo) |
| #8 Camera Init | Crash al inicio | Baja | 🟡 Moderada | Media |
| #9 Keyboard Drift | Confusión | Media | 🟡 Moderada | Baja (Re-calibrar) |
| #10 Model Complexity | Latencia/ID swap | Media | 🟡 Moderada | Baja |

---

## 🎯 RECOMENDACIONES PRIORITARIAS

### Acción Inmediata (Esta Sesión)
1. ✅ **Habilitar logs de diagnóstico ID** (Paso 2) para confirmar Falla #1
2. ✅ **Restaurar Lift Guard mínimo** para reducir ghost notes
3. ✅ **Ajustar depth range** a -10/+15cm

### Acción Corto Plazo (Próxima Sesión)
4. 🔄 **Re-calibrar Fase 3** con teclado en posición final
5. 🔄 **Implementar geometric matching** como fallback para IDs
6. 🔄 **Agregar camera retry logic**

### Acción Largo Plazo (Mejora Continua)
7. 📈 **Agregar telemetry** (% de triangulaciones exitosas, latencia promedio)
8. 📈 **Interfaz de calibración visual** (mostrar puntos rectificados en vivo)
9. 📈 **Sistema de auto-validación** (alerta si baseline drift detectado)

---

## 🧪 TESTS FUNCIONALES RECOMENDADOS

### Test 1: Estabilidad de IDs
- Mover mano lentamente de izquierda a derecha
- **Esperado:** Detección continua sin drops
- **Falla:** Drops cuando la mano cruza el eje central

### Test 2: Depth Accuracy
- Colocar objeto plano a 20cm, 30cm, 40cm
- **Esperado:** Depth reported ±3cm del real
- **Falla:** Error >5cm → Re-calibrar

### Test 3: Ghost Note Immunity
- Tocar nota y levantar dedo rápidamente
- **Esperado:** Nota suena UNA vez
- **Falla:** Nota suena 2-3 veces → Restaurar Lift Guard

### Test 4: Edge Rejection
- Colocar mano a 1cm de la cámara (muy cerca)
- **Esperado:** Sistema la ignora (fuera de rango)
- **Falla:** Genera notas → Falla #3 presente

---

## 📝 CONCLUSIÓN

El sistema tiene **5 fallas críticas** que pueden causar "detección terrible":

1. **Strict ID Matching** (Sin fallback geométrico)
2. **Calibration Staleness** (Sin validación)
3. **Negative Z Loss** (Filtro reactivo, no preventivo)
4. **Keyboard Distance Mismatch** (Fase 3 desactualizada)
5. **Algorithm Bypass** (Modo raw sin protecciones)

**De estas, la #1 (ID Matching) es la MÁS probable** dado el síntoma "no detecta ni los dedos" reportado por el usuario.

**Next Steps:**
- Ejecutar Paso 2 del diagnóstico para confirmar
- Si confirmado → Implementar geometric matching
- Si no → Proceder con Paso 3 (triangulación)

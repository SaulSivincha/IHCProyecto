# Configuración de Calibración Óptima (Modo Velocidad)

Basado en pruebas de usuario, esta configuración permite una respuesta muy rápida para tocar notas repetidas ("metralla") y trinos.

```python
```python
'params': {
    'profundidad_activacion': 16.0,  # [Profundidad] Dispara la nota (Más alto = tocar más profundo)
    'profundidad_reset': 10.0,       # [Altura] Suelta la nota (Más bajo = soltar antes)
    'paciencia_frames': 5,           # [Estabilidad] Evita que la nota "parpadee" si la cámara pierde el dedo brevemente.
                                     # Si el dedo desaparece por 1-5 frames, la nota se MANTIENE.
    
    'frames_buffer': 3,              # [Anti-Rebote] Espera "X" frames antes de sonar una nota nueva.
                                     # 3 frames ≈ 0.1s. Elimina "falsos bajones" al temblar.
                                     
    'max_lateral_velocity': 20.0     # [Anti-Roce] Ignora movimientos bruscos hacia los lados.
                                     # Si te mueves rápido de izquierda a derecha mientras bajas, NO suena.
}
```

## ⚡ Guía: Cómo tocar notas repetidas ("Metralla") sin cansarse

Si quieres tocar la misma nota muy rápido repitiendo el dedo (metralla) sin tener que levantar mucho la mano:

**El truco está en acercar el "Reset" a la "Activación".**
*   Actualmente tienes **6.0cm** de diferencia (Activa en 16, Resetea en 10). Tienes que levantar 6cm para volver a tocar.
*   Para hacerlo más sensible, sube el valor de `profundidad_reset`.

**Configuración Recomendada para Metralla:**
*   `profundidad_activacion`: **16.0** (Igual)
*   `profundidad_reset`: **14.0** (Antes 10.0) -> ¡Solo necesitas levantar 2cm!

> **Nota**: Si los pones muy cerca (ej: 16.0 y 15.5), podrías tener "rebotes" accidentales. 14.0 es un buen balance.

## Diccionario de Parámetros

### `paciencia_frames` (Anti-Parpadeo)
*   **¿Qué hace?**: Es una "memoria de corto plazo". Si la cámara pierde de vista tu dedo por un instante (por sombras o movimiento rápido), el sistema "recuerda" que estaba ahí.
*   **Valor bajo (1-2)**: Riesgo de que la nota se corte si la cámara falla.
*   **Valor alto (5-8)**: Muy estable, pero la nota puede quedarse pegada un instante al sacar el dedo rápido.
*   **Recomendado**: `5`.

### `frames_buffer` (Estabilidad de Entrada)
*   **¿Qué hace?**: Es un "portero" en la entrada. Cuando detecta que has bajado el dedo, espera estos frames para confirmar que vas en serio y no fue un temblor.
*   **Valor bajo (0-1)**: Respuesta instantánea, pero riesgo de notas fantasma si tiemblas.
*   **Valor alto (4-6)**: Muy seguro, pero sentirás un pequeño retraso (lag).
*   **Recomendado**: `3` (Balance perfecto).

### `max_lateral_velocity` (Filtro Lateral)
*   **¿Qué hace?**: Distingue entre "Tocar" (bajar recto) y "Rozar" (pasar de lado).
*   **Valor**: Velocidad en píxeles por frame.
*   **Recomendado**: `20.0`. Si tocas muy agresivo lateralmente, auméntalo.

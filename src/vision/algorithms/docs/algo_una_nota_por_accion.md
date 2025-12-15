# Documentación: Una Nota Por Acción (Algoritmo Maestro)

Actualmente, este es el **único algoritmo activo** en el sistema, pero funciona como dos algoritmos en uno porque integra lógica de **Estado** y lógica de **Física**.

## 🧠 ¿Cómo funciona? (Lógica Híbrida)

Este algoritmo combina dos cerebros para tomar decisiones:

### 1. El Cerebro de Estado (Lógica Musical) 🎹
Se encarga de que el piano se sienta natural.
*   **Una Nota a la Vez**: Si mantienes el dedo en "Sol", no deja que repita (metralla) por error. Solo suena una vez.
*   **Sustain (Mantener)**: Si tu dedo tiembla un poco hacia arriba (hasta 2.5cm), la nota NO se corta. Esto permite notas largas naturales.
*   **Paciencia (Anti-Parpadeo)**: Si la cámara pierde tu dedo por un micro-segundo, el sistema "espera" 3 frames antes de cortar el sonido.

### 2. El Cerebro Físico (Detector de Movimiento) 🚀
Se encarga de la precisión y velocidad.
*   **Bloqueo de Subida (Anti-Roce)**:
    *   *Regla*: "Si la velocidad es negativa (subiendo), PROHIBIDO tocar".
    *   *Efecto*: Si tocas "Sol" y levantas el dedo hacia "La", el sistema ve que estás subiendo y **bloquea** el sonido de "La".
*   **Reset Rápido (Metralla)**:
    *   *Regla*: "Si la velocidad de subida es muy rápida, soltar de inmediato".
    *   *Efecto*: Permite tocar la misma nota repetidas veces muy rápido (trinos) sin tener que levantar mucho el dedo.

---

## 🚦 Los 4 Comportamientos Clave

Gracias a la unión de estos dos cerebros, el algoritmo maneja 4 situaciones:

| Situación | Tu Acción | Respuesta del Algoritmo | ¿Por qué? |
|-----------|-----------|-------------------------|-----------|
| **Tocar** | Bajas el dedo sobre una tecla | ✅ **SUENA** | Profundidad baja + Velocidad de bajada. |
| **Sustain** | Dejas el dedo quieto | ⏸️ **MANTIENE** | Está dentro del rango de "Sustain" (Hysteresis). |
| **Glissando** | Arrastras a otra tecla (pegado a la mesa) | ✅ **CAMBIA NOTA** | Profundidad baja + Movimiento lateral. |
| **Levantar** | Subes el dedo (rozando otras teclas) | 🔇 **SILENCIO** | El **Detector Físico** ve que subes y bloquea todo. |

## ⚙️ Resumen de Parámetros

```python
'params': {
    # 1. SENSIBILIDAD
    'profundidad_activacion': 1.0,   # Tocar fondo (mesa)

    # 2. SUSTAIN
    'profundidad_reset': 2.5,        # Margen para mantener la nota

    # 3. ESTABILIDAD
    'paciencia_frames': 3            # Protección contra parpadeo
}
# Nota: Los umbrales de velocidad (-2.0 y -3.0) son internos y automáticos.
```

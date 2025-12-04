# Módulo de Teoría Musical

Sistema de lecciones interactivas para aprender teoría musical usando el teclado virtual estereoscópico.

## Arquitectura

```
src/theory/
├── __init__.py              # Exports del módulo
├── lesson_base.py           # Clase base abstracta BaseLesson
├── lesson_manager.py        # LessonManager - carga y gestiona lecciones
├── theory_ui.py             # TheoryUI - menú de selección y navegación
└── lessons/                 # Directorio de lecciones individuales
    ├── __init__.py
    ├── lesson_intervals.py  # Lección 1: Intervalos
    ├── lesson_scales.py     # Lección 2: Escalas
    └── lesson_chords.py     # Lección 3: Acordes básicos
```

## Cómo usar

### Activar modo teoría
1. Ejecuta el programa: `python src/main.py`
2. Presiona `L` para entrar al modo teoría
3. Usa flechas ↑/↓ para navegar por las lecciones
4. Presiona `ENTER` para seleccionar una lección
5. Presiona `Q` para volver al modo libre

### Dentro de una lección
- `ESC`: Volver al menú de lecciones
- `Q`: Salir completamente del modo teoría
- Cada lección tiene sus propios controles específicos (se muestran en pantalla)

## Lecciones disponibles

### 1. Intervalos Musicales (Básico)
- Aprende la distancia entre dos notas
- Ejemplos: 2ª menor, 3ª mayor, 5ª justa, octava
- **Controles:**
  - `ESPACIO`: Escuchar el intervalo
  - `N`: Siguiente intervalo
  - `P`: Intervalo anterior

### 2. Escalas Musicales (Básico)
- Escalas mayores, menores, pentatónicas y cromática
- Muestra patrones de tonos/semitonos
- **Controles:**
  - `ESPACIO`: Tocar nota actual
  - `→`: Siguiente nota
  - `←`: Nota anterior
  - `A`: Auto-reproducir toda la escala
  - `N/P`: Cambiar de escala

### 3. Acordes Básicos (Intermedio)
- Acordes mayores y menores (tríadas)
- Construcción de acordes con intervalos
- **Controles:**
  - `ESPACIO`: Tocar acorde arpegiado
  - `C`: Tocar acorde completo (simultáneo)
  - `I`: Mostrar/ocultar construcción del acorde
  - `N/P`: Cambiar de acorde

### 4. Ritmo y Tempo (Básico)
- Duraciones de notas (redonda, blanca, negra, corchea, semicorchea)
- Conceptos de tempo (BPM) y velocidad musical
- Patrones rítmicos comunes
- **Controles:**
  - `1-5`: Seleccionar duración (1=Redonda, 5=Semicorchea)
  - `ESPACIO`: Tocar nota con duración actual
  - `M`: Activar/desactivar metrónomo visual
  - `P`: Reproducir patrón rítmico completo
  - `+/-`: Aumentar/disminuir tempo (BPM)
  - `N`: Siguiente patrón rítmico

## Crear una nueva lección

### 1. Crea un archivo `lesson_tu_leccion.py` en `src/theory/lessons/`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lección X: Tu Título
Descripción breve de tu lección
"""

import cv2
import numpy as np
from ..lesson_base import BaseLesson


class TuLeccion(BaseLesson):
    """Clase de tu lección"""
    
    def __init__(self):
        super().__init__()
        self.name = "Nombre de Tu Lección"
        self.description = "Descripción corta (1-2 líneas)"
        self.difficulty = "Básico"  # o "Intermedio" o "Avanzado"
        
        # Tus variables de estado
        self.current_step = 0
    
    def run(self, frame_left, frame_right, virtual_keyboard, synth, 
            hand_detector_left=None, hand_detector_right=None):
        """
        Ejecuta la lección en cada frame
        
        Returns:
            tuple: (frame_left, frame_right, continue_lesson)
        """
        # Dibujar header
        frame_left = self.draw_lesson_header(frame_left)
        
        # Tus instrucciones
        instructions = [
            "Instrucción 1",
            "Instrucción 2",
            "Presiona ESPACIO para..."
        ]
        frame_left = self.draw_instructions(frame_left, instructions)
        
        # Tu lógica aquí
        # ...
        
        return frame_left, frame_right, True  # True = continuar
    
    def handle_key(self, key, synth, octave_base=60):
        """
        Maneja teclas específicas de tu lección
        
        Returns:
            bool: True si se manejó la tecla
        """
        if key == ord(' '):  # ESPACIO
            # Tu código
            return True
        
        return False  # No se manejó
```

### 2. La lección se carga automáticamente

El `LessonManager` detecta automáticamente todos los archivos `lesson_*.py` y carga las clases que heredan de `BaseLesson`.

### 3. Métodos útiles de `BaseLesson`

- `draw_lesson_header(frame, title)`: Dibuja título y controles básicos
- `draw_instructions(frame, instructions, y_start)`: Lista de instrucciones
- `draw_progress_bar(frame, current, total, x, y, width, height)`: Barra de progreso
- `start()`: Se llama al entrar a la lección
- `stop()`: Se llama al salir de la lección

## Tips para lecciones efectivas

1. **Divide en pasos pequeños**: Cada concepto debe ser digestible
2. **Feedback visual**: Usa colores y gráficos para mostrar progreso
3. **Interactividad**: Pide al usuario tocar notas/acordes para practicar
4. **Audio claro**: Usa `synth.noteon()` / `synth.noteoff()` para ejemplos
5. **Progreso visible**: Usa `draw_progress_bar()` para mostrar avance

## Arquitectura técnica

### BaseLesson (clase abstracta)
- Define interfaz común para todas las lecciones
- Métodos de dibujo reutilizables
- Ciclo de vida: `start()` → `run()` (loop) → `stop()`

### LessonManager
- Carga automática de lecciones desde `lessons/`
- Registry centralizado
- Singleton pattern: `get_lesson_manager()`

### TheoryUI
- Menú de selección navegable
- Scroll automático
- Highlights y descripciones

### Integración en main.py
- Modo teoría activado con tecla `L`
- Estados: menú de lecciones → dentro de lección → vuelta al menú
- Teclas reservadas:
  - `L`: Activar modo teoría
  - `ESC`: Salir de lección (volver a menú)
  - `Q`: Salir del modo teoría

## Extensiones futuras

- Sistema de progreso/guardado por usuario
- Ejercicios con reconocimiento de notas tocadas
- Quiz interactivos con puntuación
- Certificados de finalización
- Lecciones de armonía avanzada
- Entrenamiento de oído
- Dictado melódico

## Troubleshooting

**Las lecciones no aparecen:**
- Verifica que el archivo esté en `src/theory/lessons/`
- Nombre debe empezar con `lesson_`
- La clase debe heredar de `BaseLesson`

**Errores al ejecutar:**
- Revisa la consola para mensajes de carga
- Asegúrate de que `run()` devuelve la tupla correcta
- Verifica que `handle_key()` existe (aunque sea vacío)

**La UI no se ve bien:**
- Usa los métodos helper de `BaseLesson`
- Respeta las dimensiones del frame
- Prueba en distintas resoluciones

---

**Autor:** Sistema de Piano Virtual Estereoscópico  
**Última actualización:** Diciembre 2025

# Resumen de Cambios y Lógica Implementada

Este documento resume todas las modificaciones realizadas para transformar la interfaz, mejorar el flujo de navegación y asegurar la estabilidad del sistema.

## 1. Diseño Visual y Experiencia (Kids UI)
**Objetivo:** Hacer la aplicación atractiva para niños y fácil de entender.

*   **Roadmap "Zig-Zag" Infinito:**
    *   **Lógica:** Se sustituyó el diseño estático por un `QGridLayout` dinámico que organiza las lecciones en dos filas alternas (Arriba/Abajo).
    *   **Conexiones Visuales:** Se creó una clase personalizada `RoadmapContainer` que sobreescribe `paintEvent`. Usa curvas Bézier (`QPainterPath.cubicTo`) para dibujar líneas punteadas suaves que conectan dinámicamente el botón 1 con el 2, el 2 con el 3, etc., sin importar cuántos haya.
    *   **Estilo:** Botones grandes, bordeados, colores vibrantes (Naranja, Verde, Azul, Amarillo) y fuente "Comic Sans MS".

*   **Ventanas de Lección:**
    *   Fondo gradiente azul cielo (Sky Blue).
    *   Controles simplificados y textos grandes.

## 2. Lógica de Navegación (Flow)
**Objetivo:** Evitar que el usuario se pierda o salga por accidente.

*   **Ciclo de Lección:**
    *   *Antes:* Al terminar una lección -> Volvía al Menú Principal.
    *   *Ahora (`src/main.py`):* Al terminar una lección -> **Vuelve al Roadmap**.
    *   **Implementación:** Se añadió un bucle interno en la sección de `theory_mode` que recarga las lecciones y muestra el menú de teoría nuevamente. Solo si el usuario pulsa "Volver a Casa" se rompe este bucle y regresa al menú principal.

## 3. Arquitectura y Escalabilidad
**Objetivo:** Permitir añadir contenido sin tocar código.

*   **Sistema de Archivos:**
    *   El `LessonManager` ahora detecta automáticamente cualquier archivo que siga el patrón `*lesson_*.py` en la carpeta `lessons/`.
    *   **Prueba de Estrés:** Se añadieron 6 lecciones "Dummy" (05-10) para verificar que el mapa crece y las líneas se dibujan solas.

*   **Progreso Universal:**
    *   El progreso se guarda por **Índice Numérico**. No importa el nombre del archivo. Si completas la lección #0, se desbloquea la #1. Esto hace que el sistema sea muy difícil de romper al cambiar nombres o contenidos.

## 4. Estabilidad y Corrección de Errores
**Objetivo:** Que el programa no se cierre inesperadamente.

*   **Crash "NoneType" en Modo Libre:**
    *   **Problema:** Si las cámaras fallaban al iniciar, `hand_detector` era `None` y el programa explotaba al intentar llamar a `.findHands()`.
    *   **Solución (`qt_free_mode_window.py`):** Se añadieron chequeos de seguridad (`if self.hand_detector:`). Si falla el hardware, la app sigue funcionando (muestra video sin esqueleto) en lugar de cerrarse.

*   **Renderizado Qt:**
    *   Se corrigió un error de tipos en `paintEvent` donde se pasaban objetos `QPoint` a una función que esperaba coordenadas `float`.

*   **Loop Principal (Sin Cámaras):**
    *   **Problema:** El bucle principal (`main.py`) intentaba leer frames de `cam_left` incluso si la inicialización fallaba (`None`), causando crash inmediato.
    *   **Solución:** Se añadió lógica de fallback. Si no hay cámaras, el sistema genera "frames negros" artificiales y duerme 30ms para simular 30FPS, permitiendo usar los menús y la teoría sin hardware conectado.

## Archivos Clave Modificados
- `src/ui/qt_theory_menu.py`: Nuevo Roadmap visual con líneas.
- `src/main.py`: Lógica de bucle para navegación Lección <-> Roadmap.
- `src/ui/qt_free_mode_window.py`: Parches de seguridad para cámaras.
- `src/ui/qt_lesson_window.py`: Estilizado visual.
- `src/theory/lesson_manager.py`: Recarga dinámica de lecciones.

# Documentación de Algoritmos de Visión

Esta carpeta contiene la documentación detallada de los algoritmos de procesamiento de gestos utilizados en el proyecto.

## Algoritmos Activos

### [Una Nota Por Acción (Sustain + Glissando)](./algo_una_nota_por_accion.md)
Es el algoritmo principal actual. Gestiona toda la lógica de interacción toque-sonido:
- **Anti-Rebote**: Evita notas múltiples falsas.
- **Sustain**: Mantiene notas largas.
- **Glissando**: Permite arrastrar el dedo.
- **Estabilidad**: Proteje contra parpadeos de la cámara.

## Estructura del Sistema

El sistema funciona como un pipeline:
1.  **Detección Cruda**: `keyboard_mapper.py` obtiene coordenadas y profundidad.
2.  **Filtrado (Algoritmos)**: `algorithm_manager.py` pasa los datos por los algoritmos activos.
3.  **Evento**: Si el algoritmo aprueba, se envía el evento MIDI/Sonido.

## Cómo agregar nuevos algoritmos

1.  Crear archivo en `src/vision/algorithms/`.
2.  Heredar de `BaseAlgorithm`.
3.  Implementar método `process`.
4.  Registrar en `__init__.py` y `algorithms_config.py`.
5.  Agregar documentación aquí.

## Guías de Configuración

### [Parámetros Óptimos (Velocidad)](./parametros_optimos.md)
Guía basada en pruebas de usuario para configuración de alta sensibilidad y velocidad.


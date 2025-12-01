# Piano Virtual Estereoscópico - Versión Final Integrada

## Inicio

```bash
python -m src.main
```

## Flujo en Pantalla

1. **Menú de Configuración** (visual)
   - Opción 1: Usar calibración guardada
   - Opción 2: Nueva calibración
   - Opción 3: Saltar (valores por defecto)

2. **Entrada de Medidas** (si selecciona opción 2)
   - Distancia entre cámaras (en cm)
   - Distancia del teclado (en cm)
   - Captura visual con teclado

3. **Juego**
   - Controles: G (juego), F (libre), D (dashboard), Q (salir)
   - Audio habilitado automáticamente si soundfont existe

## Características

✓ TODO integrado en interfaz visual
✓ Sin entrada desde consola
✓ Audio con manejo de errores
✓ Listo para empaquetar

## Requisitos

- Python 3.8+
- OpenCV, MediaPipe, FluidSynth, NumPy
- Cámaras USB (o webcams integradas)



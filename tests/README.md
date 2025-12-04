# 🧪 Tests y Herramientas de Diagnóstico

Esta carpeta contiene todos los scripts de prueba y herramientas de diagnóstico del proyecto.

## 📋 Scripts Disponibles

### Calibración
- **`check_calibration_status.py`** - Verifica el estado de la calibración estéreo
  ```bash
  python tests/check_calibration_status.py
  ```

- **`test_detection.py`** - Diagnóstico de detección de tablero de ajedrez
  ```bash
  python -m tests.test_detection
  ```

### Cámaras
- **`camtest.py`** - Detecta y prueba todas las cámaras disponibles
  ```bash
  python tests/camtest.py
  ```

### Visión Estéreo y Profundidad
- **`test_triangulation_dlt.py`** - Compara métodos de triangulación (DLT vs Q)
  ```bash
  python tests/test_triangulation_dlt.py
  ```

- **`test_stereo_depth.py`** - Test interactivo de visión estéreo y profundidad 3D
  ```bash
  python -m tests.test_stereo_depth
  ```

### Sistema
- **`test_imports.py`** - Verifica que todos los módulos se importan correctamente
  ```bash
  python -m tests.test_imports
  ```

## 🎯 Orden Recomendado de Ejecución

1. **Verificar cámaras**: `camtest.py`
2. **Verificar imports**: `test_imports.py`
3. **Calibrar**: Usar `src.main` → opción [S] o [R]
4. **Verificar calibración**: `check_calibration_status.py`
5. **Test de triangulación**: `test_triangulation_dlt.py`
6. **Test de profundidad**: `test_stereo_depth.py`

## 📝 Notas

- Todos los tests nuevos deben colocarse en esta carpeta
- Mantener nombres descriptivos con prefijo `test_`
- Incluir docstrings explicando qué prueba cada script

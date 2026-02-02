#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script standalone para ejecutar la calibración
Uso: python -m src.calibration.run_calibration
"""

from src.calibration.qt_calibration_manager import run_qt_calibration

if __name__ == '__main__':
    print("\n" + "="*70)
    print("CALIBRACIÓN ESTEREOSCÓPICA CON PYQT6")
    print("="*70)
    
    success = run_qt_calibration(cam_left_id=1, cam_right_id=2)
    
    if success:
        print("\nCalibración completa exitosa!")
    else:
        print("\nLa calibración no se completó.")

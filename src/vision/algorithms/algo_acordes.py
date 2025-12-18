#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO: Smart Chords (Acordes Inteligentes)

DESCRIPCIÓN:
Este algoritmo está optimizado para detectar y estabilizar ACORDES (múltiples notas simultáneas).
Cuando se tocan acordes, es común que:
1. Las notas no bajen con la misma velocidad (algunas más suaves).
2. Las notas no lleguen a la misma profundidad (dedos más cortos/largos).
3. Haya pequeñas diferencias de tiempo (arpegio involuntario).

SOLUCIÓN:
1. Detecta "Grupo de Dedos": Si hay >1 dedos activos.
2. Aplica "Tolerancia de Grupo": Si un dedo toca fuerte, ayuda a los otros a activarse (baja sus umbrales).
3. Estabilización: Reduce el riesgo de notas perdidas en acordes complejos.
"""

from typing import Any, Dict, List, Tuple, Set
from .base_algorithm import BaseAlgorithm


class SmartChordsAlgorithm(BaseAlgorithm):
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Smart Chords", enabled=enabled)
        
        # Umbrales
        self.umbral_individual = -2.0  # Para tocar una sola nota (Estándar)
        self.umbral_acorde = 0.0       # Para acordes (Permisivo, superficie)
        
        # Si detectamos un acorde, permitimos notas con velocidad casi nula
        # (para evitar que dedos "rezagados" no suenen)
        self.velocidad_minima_acorde = -0.5
        
        self.dedos_activos: Dict[Tuple, Any] = {}
        self._debug_count = 0
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        if not self.enabled:
            return detections
        
        filtered = []
        self._debug_count += 1
        
        # 1. ANÁLISIS DE GRUPO
        # ¿Cuántos dedos están intentando tocar?
        # Consideramos "intentando" si están cerca de la superficie (depth < 2.0)
        candidatos = [d for d in detections if d[2] < 2.0]
        num_candidatos = len(candidatos)
        
        ES_ACORDE = num_candidatos >= 2
        
        if ES_ACORDE and self._debug_count % 30 == 0:
            print(f"🎹 [CHORD DETECTED] {num_candidatos} dedos simultáneos")

        # 2. PROCESAMIENTO
        dedos_presentes = set()
        
        for detection in detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            dedos_presentes.add(finger_id)
            
            # --- LÓGICA DE ACTIVACIÓN ---
            
            should_activate = False
            
            if finger_id in self.dedos_activos:
                # YA ACTIVO (Sustain)
                # Mantenemos mientras no suba demasiado
                if depth < 1.0: # Reset en 1.0 (Superficie)
                    self.dedos_activos[finger_id] = key
                    filtered.append(detection)
                else:
                    del self.dedos_activos[finger_id] # Soltó
            else:
                # NUEVA NOTA
                
                if ES_ACORDE:
                    # MODO ACORDE (Tolerancia Alta)
                    # Si estamos en modo acorde, permitimos activar con un simple roce (0.0)
                    # y ignoramos velocidad (a menos que sea un lift muy obvio < -1.0)
                    if depth <= self.umbral_acorde and velocity > -1.0:
                        should_activate = True
                        if self._debug_count % 30 == 0:
                             print(f"✨ [CHORD NOTE] {key} | z={depth:.2f} (Boosted)")
                else:
                    # MODO SOLO (Estándar)
                    # Requiere un toque un poco más decidido (-2.0)
                    if depth <= self.umbral_individual:
                        should_activate = True

                if should_activate:
                    self.dedos_activos[finger_id] = key
                    filtered.append(detection)
        
        # Limpieza de dedos que desaparecieron
        for f_id in list(self.dedos_activos.keys()):
            if f_id not in dedos_presentes:
                del self.dedos_activos[f_id]

        return filtered
    
    def configure(self, **params):
        if 'umbral_individual' in params:
            self.umbral_individual = float(params['umbral_individual'])
        if 'umbral_acorde' in params:
            self.umbral_acorde = float(params['umbral_acorde'])

    def reset(self):
        self.dedos_activos.clear()
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'umbral_individual': self.umbral_individual,
            'umbral_acorde': self.umbral_acorde
        }

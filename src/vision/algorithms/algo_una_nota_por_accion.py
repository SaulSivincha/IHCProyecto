#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO: Lift Guard (Anteriormente Una Nota Por Acción)

FILOSOFÍA: "CERO LATENCIA"
- Este algoritmo se ha reducido a su mínima expresión.
- NO gestiona profundidad (delegado al Mapper).
- NO gestiona paciencia/buffer (eliminado para velocidad pura).
- ÚNICA FUNCIÓN: Bloquear frames si la velocidad es de "salida" (Lift).
"""

from typing import Any, Dict, List, Tuple, Set
from .base_algorithm import BaseAlgorithm


class UnaNotaPorAccionAlgorithm(BaseAlgorithm):
    
    def __init__(self, enabled: bool = True):
        super().__init__(name="Una Nota Por Acción", enabled=enabled)
        
        # Parámetros ÚTILES
        # Eliminamos: profundidad_activacion, paciencia_frames (causaban confusión/lag)
        self.profundidad_reset = -5.0 # Mantenemos solo para Reset por altura absurda
        
        # Estado Mínimo
        self.dedos_activos: Dict[Tuple, Any] = {}
        self.cooldown_por_dedo: Dict[Tuple, int] = {}
        
        self._debug_count = 0
    
    def process(self, detections: List[Tuple], context: Dict[str, Any]) -> List[Tuple]:
        if not self.enabled:
            return detections
        
        filtered = []
        self._debug_count += 1
        dedos_presentes = {det[0] for det in detections}
        
        # --- LIMPIEZA RÁPIDA (Sin bucles de paciencia) ---
        # Si el dedo no está en el frame actual, lo sacamos del estado inmediatamente.
        for f_id in list(self.dedos_activos.keys()):
            if f_id not in dedos_presentes:
                del self.dedos_activos[f_id]

        for f_id in list(self.cooldown_por_dedo.keys()):
            if self.cooldown_por_dedo[f_id] > 0: self.cooldown_por_dedo[f_id] -= 1
            else: del self.cooldown_por_dedo[f_id]

        # --- PROCESO DIRECTO ---
        for detection in detections:
            finger_id, key, depth, velocity, x_pos, y_pos = detection
            
            # --- 1. LIFT GUARD (Critical Safety) ---
            # Si vel < -2.0, BLOQUEAR.
            # Esta es la única razón por la que existe este algoritmo activado.
            
            IS_LIFTING = velocity < -2.0
            
            if IS_LIFTING:
                # Si detectamos lift, cortamos y ponemos cooldown.
                if finger_id in self.dedos_activos:
                    del self.dedos_activos[finger_id]
                
                self.cooldown_por_dedo[finger_id] = 6 
                
                if self._debug_count % 30 == 0:
                    print(f"🛑 [LIFT GUARD] {finger_id} | v={velocity:.2f} (Blocked)")
                continue

            # --- 2. PASO TRANSPARENTE (Zero Logic) ---
            # Si no hay lift, pasa directo.
            
            in_cooldown = self.cooldown_por_dedo.get(finger_id, 0) > 0
            
            if not in_cooldown:
                # Actualizar estado (simplemente para saber que sigue vivo)
                self.dedos_activos[finger_id] = key
                filtered.append(detection)
                
                # Debug ultrasimple
                if self._debug_count % 60 == 0: 
                    print(f"⚡ [PASS] {key} | v={velocity:.2f}")

        return filtered
    
    def configure(self, **params):
        # Permitimos configurar reset, pero ignoramos el resto para no confundir
        if 'profundidad_reset' in params:
            val = float(params['profundidad_reset'])
            if val > 0: self.profundidad_reset = -val
            else: self.profundidad_reset = val
            
    def reset(self):
        self.dedos_activos.clear()
        self.cooldown_por_dedo.clear()
    
    def get_config(self) -> Dict[str, Any]:
        # Solo retornamos lo que realmente usamos
        return {
            'profundidad_reset': self.profundidad_reset
        }

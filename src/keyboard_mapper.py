#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 30 00:43:58 2021

@author: mherrera
"""
import numpy as np


class KeyboardMap:
    def __init__(self):
        self.prev_map = np.empty(0, dtype=bool)

    def get_kayboard_map(self,
                         virtual_keyboard,
                         fingertips_pos,
                         contact_detector,
                         keyboard_n_key):

        curr_map = np.full((keyboard_n_key, 1), False, dtype=bool)
        on_map = np.full((keyboard_n_key, 1), False, dtype=bool)
        off_map = np.full((keyboard_n_key, 1), False, dtype=bool)

        contacts = contact_detector.is_touching
        
        for fingertip_pos in fingertips_pos:
            finger_id = fingertip_pos[1]
            
            # Verificar si intersecta con el teclado
            if virtual_keyboard.intersect((fingertip_pos[2], fingertip_pos[3])):
                key = virtual_keyboard.find_key(fingertip_pos[2], fingertip_pos[3])
                
                if key >= 0 and key < keyboard_n_key:
                    # CAMBIO CLAVE: Usar contacto en lugar de distancia
                    if finger_id in contacts and contacts[finger_id]:
                        curr_map[key] = True
                        print(f"Tecla {key} ACTIVADA por contacto!")
        
        # Lógica de on/off (igual que antes)
        if np.all(curr_map == False) and np.all(self.prev_map == False):
            pass
        else:
            on_map = np.logical_and(curr_map, np.logical_not(self.prev_map))
            off_map = np.logical_and(self.prev_map, np.logical_not(curr_map))
            
        self.prev_map = curr_map.copy()
        return on_map, off_map

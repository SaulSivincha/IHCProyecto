#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Side Contact Detector - Detecta contacto con mesa desde vista lateral
"""

import cv2
import numpy as np

class SideContactDetector:
    def __init__(self, canvas_height=480):
        self.canvas_height = canvas_height
        self.table_y_threshold = int(canvas_height * 0.70)  # Línea de la mesa (70% desde arriba)
        self.contact_tolerance = 15  # Píxeles de tolerancia
        self.is_touching = {}  # Estado de contacto por dedo
        
    def set_table_level(self, y_position):
        """Permite ajustar manualmente el nivel de la mesa"""
        self.table_y_threshold = y_position
        
    def detect_contact(self, fingertips_list):
        """
        Detecta si algún dedo está tocando la mesa
        fingertips_list: Lista de landmarks de dedos desde vista lateral
        Retorna: diccionario {finger_id: is_touching}
        """
        contacts = {}
        
        for finger_data in fingertips_list:
            finger_id = finger_data[1]  # ID del dedo
            finger_y = finger_data[3]   # Coordenada Y del dedo
            
            # Si el dedo está cerca o debajo del nivel de la mesa
            if finger_y >= (self.table_y_threshold - self.contact_tolerance):
                contacts[finger_id] = True
                self.is_touching[finger_id] = True
            else:
                contacts[finger_id] = False
                if finger_id in self.is_touching:
                    del self.is_touching[finger_id]
                    
        return contacts
    
    def draw_table_line(self, frame):
        """Dibuja la línea de referencia de la mesa"""
        cv2.line(frame, 
                (0, self.table_y_threshold), 
                (frame.shape[1], self.table_y_threshold),
                (0, 255, 0), 2)
        
        # Dibujar zona de tolerancia
        cv2.line(frame, 
                (0, self.table_y_threshold - self.contact_tolerance), 
                (frame.shape[1], self.table_y_threshold - self.contact_tolerance),
                (255, 255, 0), 1)
        
        cv2.putText(frame, "Mesa / Table Level", 
                   (10, self.table_y_threshold - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame
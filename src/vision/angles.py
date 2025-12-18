#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 00:25:35 2021

@author: mherrera
"""

import os
import math
import cv2

# Angulos del Frame y Distancia

class Frame_Angles:

    # Variables de Usuario

    pixel_width = 640
    pixel_height = 480

    angle_width = 60
    angle_height = None

    # Variables del Sistema
    x_origin = None
    y_origin = None

    x_adjacent = None
    x_adjacent = None

    # Funciones de Inicio

    def __init__(self,pixel_width=None,pixel_height=None,angle_width=None,angle_height=None):

        # dimensiones completas del frame en pixeles
        if type(pixel_width) in (int,float):
            self.pixel_width = int(pixel_width)
        if type(pixel_height) in (int,float):
            self.pixel_height = int(pixel_height)

        # dimensiones completas del frame en grados
        if type(angle_width) in (int,float):
            self.angle_width = float(angle_width)
        if type(angle_height) in (int,float):
            self.angle_height = float(angle_height)

        # configuracion inicial
        self.build_frame()

    def build_frame(self):

        # asume valores correctos para pixel_width, pixel_height, y angle_width

        # corregir altura angular
        if not self.angle_height:
            self.angle_height = self.angle_width*(self.pixel_height/self.pixel_width)

        # punto central (tambien distancia maxima en pixeles desde el origen)
        self.x_origin = int(self.pixel_width/2)
        self.y_origin = int(self.pixel_height/2)

        # distancia teorica en pixeles desde la camara al frame
        # esta es la longitud del lado adyacente en calculos de tangente
        # las entradas pixel x,y son las longitudes del lado opuesto
        self.x_adjacent = self.x_origin / math.tan(math.radians(self.angle_width/2))
        self.y_adjacent = self.y_origin / math.tan(math.radians(self.angle_height/2))

    # Funciones de Conversion Pixel-Angulo
    def angles(self, x, y):
        """Retorna los angulos (x, y) desde el centro para un pixel dado."""
        return self.angles_from_center(x, y)

    def angles_from_center(self, x, y, top_left=True, degrees=True):
        """
        Calcula el angulo de un pixel respecto al centro optico de la camara.

        Args:
            x: Posicion horizontal del pixel.
            y: Posicion vertical del pixel.
            top_left: Si True, asume (0,0) en la esquina superior izquierda (estandar OpenCV).
                     Si False, asume (0,0) en el centro de la imagen.
            degrees: Si True retorna grados, si False retorna radianes.
        
        Returns:
            (x_angle, y_angle): Angulos horizontal y vertical.
        """
        # Convertir coordenadas de imagen (top-left) a coordenadas centradas en el eje optico
        if top_left:
            x = x - self.x_origin
            y = self.y_origin - y # Invertir Y porque eje Y de imagen crece hacia abajo

        # Calcular tangente del angulo usando la distancia focal virtual (adyacente)
        xtan = x / self.x_adjacent
        ytan = y / self.y_adjacent

        xrad = math.atan(xtan)
        yrad = math.atan(ytan)

        if not degrees:
            return xrad, yrad

        return math.degrees(xrad), math.degrees(yrad)

    def pixels_from_center(self, x, y, degrees=True):
        """
        Operacion inversa a angles_from_center.
        Calcula la posicion en pixeles (desde el centro) para un angulo dado.
        """
        # x = angulo horizontal desde el centro
        # y = angulo vertical desde el centro

        if degrees:
            x = math.radians(x)
            y = math.radians(y)

        # return int(self.x_adjacent * math.tan(x)), int(self.y_adjacent * math.tan(y))
        return int(self.x_adjacent * math.tan(x)), int(self.y_adjacent * math.tan(y))

    # ------------------------------
    # Funciones 3D (Triangulacion)
    # ------------------------------

    def distance(self, *coordinates):
        return self.distance_from_origin(*coordinates)

    def distance_from_origin(self, *coordinates):
        """Calcula la distancia Euclidiana desde el origen (0,0,...)"""
        return math.sqrt(sum([x**2 for x in coordinates]))

    def intersection(self, pdistance, langle, rangle, degrees=False):
        """
        Calcula la posicion (X, Y) de un punto mediante triangulacion basica 2D.
        
        Args:
            pdistance: Distancia entre las dos camaras (baseline).
            langle: Angulo de la camara izquierda hacia el objeto.
            rangle: Angulo de la camara derecha hacia el objeto.
            degrees: Si los angulos estan en grados.
            
        Returns:
            (X, Y): Coordenadas del punto.
                    X: Distancia lateral desde el centro de la camara izquierda.
                    Y: Profundidad (distancia perpendicular al baseline).
        """
        # Normalizar a radianes
        if degrees:
            langle = math.radians(langle)
            rangle = math.radians(rangle)

        # Ajustar sistema de coordenadas de angulos
        # langle se mide desde el baseline derecho (90 grados - angulo)
        # rangle se mide desde el baseline izquierdo (90 grados + angulo)
        langle = math.pi/2 - langle
        rangle = math.pi/2 + rangle

        # Calculo usando ley de senos o tangentes para triangulacion
        ltan = math.tan(langle)
        rtan = math.tan(rangle)

        # Calcular profundidad (Y)
        # Formula derivada de: X = Y/tan(la)  y  (D-X) = Y/tan(ra)
        # Donde D = pdistance
        Y = pdistance / (1/ltan + 1/rtan)

        # Calcular posicion lateral (X) desde el centro de camara izquierda
        X = Y / ltan

        return X, Y

    def location(self, pdistance, lcamera, rcamera, center=False, degrees=True):
        """
        Calcula la posicion 3D (X, Y, Z) completa.
        
        Args:
            pdistance: Distancia entre camaras (baseline).
            lcamera: Tupla (x_angle, y_angle) camara izquierda.
            rcamera: Tupla (x_angle, y_angle) camara derecha.
            center: Si True, ajusta X para que (0,0,0) sea el centro del baseline (entre las camaras).
                   Si False, (0,0,0) es el centro de la camara izquierda.
        
        Returns:
            X, Y, Z, D: Coordenadas 3D y distancia total.
            NOTA: En este sistema de retorno:
              X: Lateral
              Y: Altura (calculada promedio de angulos verticales)
              Z: Profundidad (la Y de intersection)
        """
        # Separar angulos
        lxangle, lyangle = lcamera
        rxangle, ryangle = rcamera

        # Asumir que el objeto esta a la misma altura vertical para ambas camaras (promedio)
        yangle = (lyangle + ryangle) / 2

        if degrees:
            lxangle = math.radians(lxangle)
            rxangle = math.radians(rxangle)
            yangle  = math.radians(yangle)

        # Obtener X (Lateral) y Z (Profundidad) usando los angulos horizontales
        # Nota: intersection retorna (X, Y_depth), aqui lo asignamos a X, Z
        X, Z = self.intersection(pdistance, lxangle, rxangle, degrees=False)

        # Calcular Y (Altura) usando la profundidad Z y el angulo vertical
        Y = math.tan(yangle) * self.distance_from_origin(X, Z)

        # Centrar coordenada X al medio de las dos camaras
        if center:
            X -= pdistance / 2

        # Distancia total Euclidiana 3D
        D = self.distance_from_origin(X, Y, Z)

        return X, Y, Z, D

    # Tertiary Functions

    def frame_add_crosshairs(self,frame):
        """Agrega líneas de referencia al frame (si está habilitado en config)"""
        # Verificar si está habilitado
        try:
            from .stereo_config import StereoConfig
            if not StereoConfig.SHOW_CROSSHAIRS:
                return
        except:
            pass
        
        cv2.line(frame,(0,self.y_origin),(self.pixel_width,self.y_origin),(0,255,0),1)
        cv2.line(frame,(self.x_origin,0),(self.x_origin,self.pixel_height),(0,255,0),1)
        cv2.circle(frame,(self.x_origin,self.y_origin),int(round(self.y_origin/8,0)),(0,255,0),1)

    def frame_add_degrees(self,frame):

        # add lines to frame every 10 degrees (horizontally and vertically)
        # use this to test that your angle values are set up properly

        for angle in range(10,95,10):

            # calculate pixel offsets
            x,y = self.pixels_from_center(angle,angle)

            # draw verticals
            if x <= self.x_origin:
                cv2.line(frame,(self.x_origin-x,0),(self.x_origin-x,self.pixel_height),(255,0,255),1)
                cv2.line(frame,(self.x_origin+x,0),(self.x_origin+x,self.pixel_height),(255,0,255),1)

            # draw horizontals
            if y <= self.y_origin:
                cv2.line(frame,(0,self.y_origin-y),(self.pixel_width,self.y_origin-y),(255,0,255),1)
                cv2.line(frame,(0,self.y_origin+y),(self.pixel_width,self.y_origin+y),(255,0,255),1)

    def frame_make_target(self,outfilename='targeting_angles_frame_target.svg',openfile=False):

        # this will make a printable target that matches the frame_add_degrees output
        # use this to test that your angle values are set up properly

        # svg size
        ratio = self.pixel_height/self.pixel_width
        width = 1600
        height = 1600 * ratio

        #svg frame locations
        x_origin = width/2
        y_origin = height/2
        distance = width*0.5

        # start svg
        svg  = '<svg xmlns="http://www.w3.org/2000/svg"\n'
        svg += 'xmlns:xlink="http://www.w3.org/1999/xlink"\n'
        svg += 'width="{}px"\n'.format(width)
        svg += 'height="{}px">\n'.format(height)

        # crosshairs
        svg += '<line x1="{}" x2="{}" y1="{}" y2="{}" stroke-width="1" stroke="green"/>\n'.format(0,width,y_origin,y_origin)
        svg += '<line x1="{}" x2="{}" y1="{}" y2="{}" stroke-width="1" stroke="green"/>\n'.format(x_origin,x_origin,0,height)

        # center circle
        svg += '<circle cx="{}" cy="{}" r="{}" stroke="green" stroke-width="1" fill="none"/>'.format(x_origin,y_origin,y_origin/8)

        # distance from screen line
        svg += '<line x1="{0}" x2="{1}" y1="{2}" y2="{2}" stroke-width="1" stroke="red"/>\n'.format(x_origin-distance/2,x_origin+distance/2,y_origin-y_origin/8)
        svg += '<line x1="{0}" x2="{0}" y1="{1}" y2="{2}" stroke-width="1" stroke="red"/>\n'.format(x_origin-distance/2,y_origin-y_origin/16,y_origin-y_origin/8)
        svg += '<line x1="{0}" x2="{0}" y1="{1}" y2="{2}" stroke-width="1" stroke="red"/>\n'.format(x_origin+distance/2,y_origin-y_origin/16,y_origin-y_origin/8)

        # add degree lines
        for angle in range(10,95,10):
            pixels = distance * math.tan(math.radians(angle))

            # draw verticals
            if pixels <= x_origin:
                svg += '<line x1="{0}" x2="{0}" y1="0" y2="{1}" stroke-width="1" stroke="black"/>\n'.format(x_origin-pixels,height)
                svg += '<line x1="{0}" x2="{0}" y1="0" y2="{1}" stroke-width="1" stroke="black"/>\n'.format(x_origin+pixels,height)

            # draw horizontals
            if pixels <= y_origin:
                svg += '<line x1="0" x2="{0}" y1="{1}" y2="{1}" stroke-width="1" stroke="black"/>\n'.format(width,y_origin-pixels)
                svg += '<line x1="0" x2="{0}" y1="{1}" y2="{1}" stroke-width="1" stroke="black"/>\n'.format(width,y_origin+pixels)

        # end svg
        svg += '</svg>'

        # write file
        outfile = open(outfilename,'w')
        outfile.write(svg)
        outfile.close()

        # open file
        if openfile:
            import webbrowser
            webbrowser.open(os.path.abspath(outfilename))

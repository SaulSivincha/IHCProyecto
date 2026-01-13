from src.theory.lesson_base import BaseLesson
import cv2
import time

class MelodyLesson(BaseLesson):
    def __init__(self):
        super().__init__()
        self.name = "Melodias Simples"
        self.description = (
            "Aprende a tocar tu primera <a href='melodia'>Melodía</a>: 'Estrellita donde estás'. "
            "Sigue las <a href='nota'>Notas</a> en la pantalla."
        )
        self.difficulty = "Facil"
        
        self.glossary = {
            "melodia": "Una Melodía es como una línea de notas que cantas o tocas una tras otra.",
            "nota": "Una Nota es un sonido musical con un nombre (Do, Re, Mi...)."
        }
        
        # Notas de "Estrellita" (Semitonos desde Do: 0, 2, 4, 5, 7, 9, 11)
        # Do=0, Re=2, Mi=4, Fa=5, Sol=7, La=9
        self.melody = [
            (0, "Do"), (0, "Do"), (7, "Sol"), (7, "Sol"), (9, "La"), (9, "La"), (7, "Sol"), # Estrellita donde estas
            (5, "Fa"), (5, "Fa"), (4, "Mi"), (4, "Mi"), (2, "Re"), (2, "Re"), (0, "Do"),   # Me pregunto que seras
            (7, "Sol"), (7, "Sol"), (5, "Fa"), (5, "Fa"), (4, "Mi"), (4, "Mi"), (2, "Re"), # En el cielo o en el mar
            (7, "Sol"), (7, "Sol"), (5, "Fa"), (5, "Fa"), (4, "Mi"), (4, "Mi"), (2, "Re"), # Un diamante de verdad
            (0, "Do"), (0, "Do"), (7, "Sol"), (7, "Sol"), (9, "La"), (9, "La"), (7, "Sol"), # Estrellita donde estas
            (5, "Fa"), (5, "Fa"), (4, "Mi"), (4, "Mi"), (2, "Re"), (2, "Re"), (0, "Do")    # Me pregunto que seras
        ]
        
        self.current_note_idx = 0
        self.octave_base = 60 # Do central
        
        # Estado de reproducción
        self.play_state = None # None, 'auto_play'
        self.play_start_time = 0
        self.last_played_idx = -1
        self.active_midi_notes = []
        
        self._update_instructions()

    def _update_instructions(self):
        semitone, note_name = self.melody[self.current_note_idx]
        total = len(self.melody)
        
        text = "¡Presiona ESPACIO para tocar la nota actual de la canción!\n"
        text += "Presiona 'R' para escuchar la canción completa.\n\n"
        
        text += f"=== NOTA ACTUAL ({self.current_note_idx + 1}/{total}) ===\n"
        text += f"🎵 {note_name.upper()} 🎵\n\n"
        
        # Mostrar siguiente nota como pista
        if self.current_note_idx + 1 < total:
            _, next_name = self.melody[self.current_note_idx + 1]
            text += f"(Siguiente: {next_name})\n"
        else:
            text += "¡Fin de la canción!\n"
            
        text += "\n--- CONTROLES ---\n"
        text += "• ESPACIO: Tocar nota actual\n"
        text += "• N / FLECHA DER: Siguiente nota\n"
        text += "• P / FLECHA IZQ: Nota anterior\n"
        text += "• R: Reproducir Melodía Completa"
        
        self._instructions = text

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    def run(self, frame_left, frame_right, virtual_keyboard, synth, hand_detector_left=None, hand_detector_right=None):
        
        # Lógica de reproducción automática ('R')
        if self.play_state == 'auto_play':
            current_time = time.time()
            elapsed = current_time - self.play_start_time
            note_duration = 0.5
            
            idx = int(elapsed / note_duration)
            
            if idx < len(self.melody):
                if idx != self.last_played_idx:
                    # Apagar anterior
                    self._stop_all_notes(synth)
                    
                    # Tocar nueva
                    self.last_played_idx = idx
                    semitone, _ = self.melody[idx]
                    note = self.octave_base + semitone
                    synth.noteon(0, note, 100)
                    self.active_midi_notes = [note]
                    
                    # Actualizar UI para seguir la canción
                    if idx != self.current_note_idx:
                        self.current_note_idx = idx
                        self._update_instructions()
            else:
                # Fin
                self._stop_all_notes(synth)
                self.play_state = None
                self.current_note_idx = 0
                self._update_instructions()

        if self.play_state == 'manual_note':
            if time.time() - self.play_start_time > 1.0: # 1 segundo de duración
                self._stop_all_notes(synth)
                self.play_state = None

        # Visualización
        if virtual_keyboard:
            # Resaltar la nota que el usuario debe tocar (o la que suena)
            target_semitone, target_name = self.melody[self.current_note_idx]
            target_midi = self.octave_base + target_semitone
            
            # Dibujar en teclado virtual (si hay método helper o copy-paste logic)
            # Por simplicidad, usamos la logica simple si existe, o dibujamos texto
            
            # Dibujamos info en pantalla grande
            cv2.putText(frame_left, f"TOCA: {target_name}", (50, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

            # Si hay notas activas (sonando), resaltarlas
            if self.active_midi_notes:
                for midi_note in self.active_midi_notes:
                    key_props = self._get_key_visual_props(virtual_keyboard, midi_note)
                    if key_props:
                        (x, y, w, h), color = key_props
                        
                        # Overlay
                        overlay = frame_left.copy()
                        cv2.rectangle(overlay, (x, y), (x+w, y+h), color, -1)
                        cv2.addWeighted(overlay, 0.6, frame_left, 0.4, 0, frame_left)
                        
                        # Borde
                        cv2.rectangle(frame_left, (x, y), (x+w, y+h), (255, 255, 255), 2)

        return frame_left, frame_right, True

    def _get_key_visual_props(self, vk, midi_note):
        """Calcula coordenadas visuales de la tecla"""
        offset = midi_note - 60
        if offset < 0 or offset > 23: return None
        
        white_map = {0:0, 2:1, 4:2, 5:3, 7:4, 9:5, 11:6, 12:7, 14:8, 16:9, 17:10, 19:11, 21:12, 23:13}
        black_map = {1:0, 3:1, 6:3, 8:4, 10:5, 13:7, 15:8, 18:10, 20:11, 22:12}
        
        if offset in white_map:
            idx = white_map[offset]
            return (int(vk.kb_x0 + idx*vk.white_key_width), int(vk.kb_y0), 
                    int(vk.white_key_width), int(vk.kb_y1-vk.kb_y0)), (255, 255, 0)
        elif offset in black_map:
            idx = black_map[offset]
            x_center = vk.kb_x0 + vk.white_key_width * (idx + 1)
            idx_mod = idx % 7
            if idx_mod in (0, 3, 4): x = x_center - vk.black_key_width*(2/3)
            elif idx_mod in (1, 5): x = x_center - vk.black_key_width*(1/3)
            else: x = x_center - vk.black_key_width/2
            return (int(x), int(vk.kb_y0), int(vk.black_key_width), int(vk.black_key_heigth)), (255, 0, 255)
        return None

    def handle_key(self, key, synth, octave_base=60):
        self.octave_base = octave_base
        
        if key == ord(' '): # Espacio: Tocar nota actual y avanzar
            self._stop_all_notes(synth)
            semitone, _ = self.melody[self.current_note_idx]
            note = self.octave_base + semitone
            synth.noteon(0, note, 100)
            self.active_midi_notes = [note]
            
            # Estado manual con timeout
            self.play_state = 'manual_note'
            self.play_start_time = time.time()
            return True
            
        elif key == ord('n') or key == ord('N') or key == 83: # Next
            self._stop_all_notes(synth)
            self.current_note_idx = (self.current_note_idx + 1) % len(self.melody)
            self._update_instructions()
            return True
            
        elif key == ord('p') or key == ord('P') or key == 81: # Prev
            self._stop_all_notes(synth)
            self.current_note_idx = (self.current_note_idx - 1) % len(self.melody)
            self._update_instructions()
            return True
            
        elif key == ord('r') or key == ord('R'): # Reproducir todo
            self._stop_all_notes(synth)
            self.play_state = 'auto_play'
            self.play_start_time = time.time()
            self.last_played_idx = -1
            self.current_note_idx = 0 # Empezar desde el principio
            return True
            
        return False

    def _stop_all_notes(self, synth):
        if self.active_midi_notes:
            for n in self.active_midi_notes: synth.noteoff(0, n)
        self.active_midi_notes = []

    def get_lesson_state(self):
        return {
            "name": self.name,
            "progress": int((self.current_note_idx / len(self.melody)) * 100),
            "instructions": self._instructions
        }

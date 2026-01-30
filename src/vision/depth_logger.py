import json
import time
import os

class DepthLogger:
    def __init__(self, output_dir="logs"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.frame_data = [] 
        self.start_time = time.time()
        self.is_recording = False
        
        self.finger_names = {
            4: "Pulgar", 8: "Indice", 12: "Medio", 16: "Anular", 20: "Menique"
        }

    def start(self):
        self.frame_data = []
        self.start_time = time.time()
        self.is_recording = True
        print("[LOGGER] Grabación MODULAR iniciada (X, Y, Z, Nota por dedo)...")

    def log_frame(self, fingers_detailed_data, active_notes_global):
        """
        fingers_detailed_data: dict con {finger_name: {x, y, z, note_id}}
        active_notes_global: lista de notas sonando en el sistema
        """
        if not self.is_recording:
            return

        timestamp = round(time.time() - self.start_time, 3)
        
        # Guardamos el frame con granularidad total
        self.frame_data.append({
            "t": timestamp,
            "fingers": fingers_detailed_data,
            "global_notes": active_notes_global
        })

    def stop_and_save(self):
        self.is_recording = False
        if not self.frame_data:
            return None
            
        filename = f"research_log_{int(time.time())}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                # Usamos indent=2 para que sea legible por humanos en el paper
                json.dump(self.frame_data, f, indent=2) 
            print(f"[LOGGER] ✅ Datos de investigación guardados en {filepath}")
            return filepath
        except Exception as e:
            print(f"[LOGGER] Error: {e}")
            return None

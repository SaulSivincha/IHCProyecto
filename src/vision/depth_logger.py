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
        
        # Mapa de IDs a nombres legibles
        self.finger_names = {
            4: "Pulgar", 8: "Indice", 12: "Medio", 16: "Anular", 20: "Menique"
        }

    def start(self):
        self.frame_data = []
        self.start_time = time.time()
        self.is_recording = True
        print("[LOGGER] Grabación optimizada iniciada...")

    def log_frame(self, fingers_state):
        if not self.is_recording:
            return

        timestamp = round(time.time() - self.start_time, 3)
        relevant_data = {}
        has_activity = False

        for key, data in fingers_state.items():
            # FILTRO: Solo registrar dedos 'cerca' de la mesa (< 8cm)
            # Esto elimina todo el ruido cuando la mano está lejos/descansando
            z_rel = data.get('z_rel', 100)
            
            if z_rel < 8.0: 
                # Convertir clave tupla (0,8) a nombre legible
                tip_id = key[1]
                finger_name = self.finger_names.get(tip_id, str(tip_id))
                
                # Guardar solo lo esencial
                relevant_data[finger_name] = {
                    'z': round(z_rel, 2),      # Profundidad relativa
                    'abs': round(data.get('z_abs', 0), 1), # Profundidad absoluta
                    'y': data.get('yl', 0)     # Posición Y (útil para ver si está lejos/cerca)
                }
                has_activity = True

        # Solo guardar el frame si hubo actividad relevante
        if has_activity:
            self.frame_data.append({
                "t": timestamp,
                "f": relevant_data
            })

    def stop_and_save(self):
        self.is_recording = False
        if not self.frame_data:
            print("[LOGGER] No hubo actividad relevante para guardar.")
            return None
            
        filename = f"smart_log_{int(time.time())}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            # indent=None ahorra mucho espacio
            json.dump(self.frame_data, f, indent=None) 
            
        print(f"[LOGGER] Guardado LOG OPTIMIZADO en {filepath}")
        return filepath

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
        print("[LOGGER] Grabación optimizada iniciada (SIN FILTROS)...")

    def log_frame(self, fingers_state):
        if not self.is_recording:
            return

        timestamp = round(time.time() - self.start_time, 3)
        relevant_data = {}
        has_activity = False

        for key, data in fingers_state.items():
            # --- CORRECCIÓN ---
            # Antes: if z_rel < 8.0: (Muy estricto)
            # Ahora: if z_rel < 200.0: (Permite todo para depuración)
            z_rel = data.get('z_rel', 100)
            
            if z_rel < 200.0: 
                # Convertir clave tupla (0,8) a nombre legible
                tip_id = key[1]
                finger_name = self.finger_names.get(tip_id, str(tip_id))
                
                # Guardar datos
                relevant_data[finger_name] = {
                    'z': round(z_rel, 2),      # Profundidad relativa
                    'abs': round(data.get('z_abs', 0), 1), # Profundidad absoluta
                    'y': data.get('yl', 0)     # Posición Y
                }
                has_activity = True

        # Guardar frame si hubo ALGO de actividad
        if has_activity:
            self.frame_data.append({
                "t": timestamp,
                "f": relevant_data
            })

    def stop_and_save(self):
        self.is_recording = False
        if not self.frame_data:
            print("[LOGGER] ⚠️ El log está vacío (no se detectaron manos).")
            return None
            
        filename = f"smart_log_{int(time.time())}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.frame_data, f, indent=None) 
            print(f"[LOGGER] ✅ Guardado LOG en {filepath}")
            return filepath
        except Exception as e:
            print(f"[LOGGER] Error guardando archivo: {e}")
            return None

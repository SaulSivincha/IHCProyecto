
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.vision.algorithms.algo_una_nota_por_accion import UnaNotaPorAccionAlgorithm

def test_algo():
    print("--- TEST ALGORITMO ---")
    
    # 1. Instanciar
    algo = UnaNotaPorAccionAlgorithm(enabled=True)
    print(f"Algoritmo instanciado. Enabled: {algo.enabled}")
    
    # 2. Datos de prueba (Negativos, como el usuario)
    # (finger_id, key, depth, velocity, x, y)
    detections = [
        (0, 10, -14.0, 0.0, 100, 100) # Toque profundo
    ]
    
    # 3. Probar ENABLED (Debe activar con lógica negativa automática)
    print("\n--- TEST ENABLED ---")
    res = algo.process(detections, {})
    print(f"Input: {detections}")
    print(f"Output: {res}")
    
    if len(res) == 1:
        print("✅ Resultado ENABLED: Correcto (Detectó toque negativo)")
    else:
        print("❌ Resultado ENABLED: Fallo (Bloqueó toque válido)")

    # 4. Probar DISABLED (Debe pasar todo)
    print("\n--- TEST DISABLED ---")
    algo.enabled = False
    res_disabled = algo.process(detections, {})
    print(f"Output Disabled: {res_disabled}")
    
    if len(res_disabled) == 1:
        print("✅ Resultado DISABLED: Correcto (Passthrough)")
    else:
        print("❌ Resultado DISABLED: Fallo (Bloqueó estando apagado)")

if __name__ == "__main__":
    try:
        test_algo()
    except Exception as e:
        print(f"\n❌ CRASH: {e}")
        import traceback
        traceback.print_exc()

import json
import urllib.request
import time
import sys

def verify_direct_ollama_inference():
    url = "http://localhost:11434/api/generate"
    
    # Payload exacto basado en lo que el cliente capturó
    # Nota: El cliente NO usa 'options' en su payload crudo hacia nuestro servidor,
    # pero nuestro smart_image_server.py saca esos campos y los re-empaqueta para Ollama.
    # Aquí simulamos la llamada MÁS DIRECTA posible desde Python a Ollama.
    
    prompt = ("An animated character with aesthetic and detailed features, long dark hair, "
              "large light blue eyes, and a neutral facial expression. The character is "
              "wearing a fitted white suit that highlights their figure. The lighting is "
              "soft, creating a realistic and attractive effect.")
    
    payload = {
        "model": "x/z-image-turbo",
        "prompt": prompt,
        "stream": False,
        "width": 912,   # 912 es múltiplo de 16 (16 * 57)
        "height": 912,
        "options": {
            "width": 912,
            "height": 912,
            "steps": 4
        }
    }
    
    print(f"🚀 Iniciando inferencia DIRECTA a Ollama ({url})...")
    print(f"📦 Dimensiones solicitadas: 912x912 (Alineadas a 16px)")
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    start_t = time.perf_counter()
    try:
        # Aumentamos el timeout a 120s para dar tiempo a la GPU pero no esperar infinito
        with urllib.request.urlopen(req, timeout=120) as response:
            status_code = response.getcode()
            headers = dict(response.info())
            raw_res = response.read()
            duration = time.perf_counter() - start_t
            
            print(f"\n📡 --- RESPUESTA RECIBIDA en {duration:.2f}s ---")
            print(f"HTTP Status: {status_code}")
            print(f"Respuesta Raw (Bytes): {len(raw_res)}")
            
            if len(raw_res) == 0:
                print("❌ RESULTADO: CUERPO VACÍO (0 bytes). Ollama no entregó nada.")
            else:
                try:
                    res_json = json.loads(raw_res.decode('utf-8'))
                    print("✅ RESULTADO: JSON válido recibido.")
                    print(f"Keys presentes: {list(res_json.keys())}")
                    if 'image' in res_json or 'images' in res_json:
                        print("✨ ¡IMAGEN GENERADA EN EL PAYLOAD!")
                    else:
                        print("⚠️ El JSON no contiene datos de imagen.")
                except json.JSONDecodeError as e:
                    print(f"❌ RESULTADO: Error de parseo JSON: {e}")
                    print(f"Contenido crudo capturado: {raw_res[:100]}...")

    except Exception as e:
        duration = time.perf_counter() - start_t
        print(f"\n💥 ERROR CRÍTICO después de {duration:.2f}s: {e}")

if __name__ == "__main__":
    verify_direct_ollama_inference()

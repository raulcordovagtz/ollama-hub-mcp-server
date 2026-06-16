

Aquí tienes la implementación preliminar ( no Revisada ) del **"Dolphin-Local-Perception-Hub"**.

---

# 🐬 Dolphin-Local-Perception-Hub

**Filosofía:** El modelo es un recurso costoso y efímero. Solo vive mientras se le necesita.

## 1. Arquitectura del Sistema

### 🔴 Capa 1: El Núcleo (The Oracle) - `server_core.py`
*   **Comportamiento:**
    *   Se despierta, carga el modelo en MPS (Metal), emite sonido de "Listo".
    *   Tiene un **Watchdog (Perro guardián)**: Si pasan **5 minutos** (configurable) sin peticiones, emite sonido de "Apagado", libera VRAM y se suicida (`sys.exit`).
    *   Expone endpoints agnósticos: `/health` (estoy vivo) y `/infer` (procesa esto).

### 🟡 Capa 2: El Puente (The Bridge) - `bridge.py`
*   **Responsabilidad:** "Wake-on-Request".
*   El cliente nunca llama al servidor directamente. Llama al puente.
*   El puente verifica: ¿Está el puerto 8000 abierto?
    *   **NO:** Inicia el subproceso del servidor, espera el handshake "Ready", y luego pasa la petición.
    *   **SÍ:** Pasa la petición directamente y actualiza el "tiempo de última actividad" del servidor.

### 🟢 Capa 3: El Adaptador (The Client) - `dolphin_cli.py`
*   **Responsabilidad:** Formateo y UX.
*   Define los modos (`story`, `formula`, `table`).
*   Recibe el JSON crudo y lo convierte en archivos útiles (.md, .tex, .html).

---

## 2. Implementación de Código

### 🔴 1. El Núcleo: `server_core.py`

```python
import os
import time
import signal
import asyncio
import subprocess
import torch
from fastapi import FastAPI, UploadFile, Form, HTTPException
from contextlib import asynccontextmanager
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from PIL import Image
import io

# CONFIGURACIÓN
TIMEOUT_SECONDS = 300  # 5 minutos de inactividad = Autoapagado
PORT = 8000
MODEL_PATH = "ByteDance/Dolphin-v2"
DEVICE = "mps"

# ESTADO GLOBAL
last_activity = time.time()
model = None
processor = None

def play_sound(sound_name):
    """Feedback auditivo nativo de macOS"""
    sounds = {
        "loading": "/System/Library/Sounds/Blow.aiff",
        "ready": "/System/Library/Sounds/Glass.aiff",
        "processing": "/System/Library/Sounds/Tink.aiff",
        "shutdown": "/System/Library/Sounds/Bottle.aiff"
    }
    subprocess.run(["afplay", sounds.get(sound_name, sounds["ready"])])

async def watchdog_loop():
    """El Monitor de Vida: Se ejecuta en background"""
    global last_activity
    print(f"👁️ Watchdog activo. Timeout: {TIMEOUT_SECONDS}s")
    while True:
        await asyncio.sleep(10)
        idle_time = time.time() - last_activity
        if idle_time > TIMEOUT_SECONDS:
            print(f"💤 Inactividad ({int(idle_time)}s). Iniciando auto-destrucción...")
            play_sound("shutdown")
            os.kill(os.getpid(), signal.SIGTERM)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, processor
    print("⏳ Cargando Núcleo Dolphin...")
    play_sound("loading")
    
    # Carga del modelo
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_PATH, torch_dtype=torch.float16, device_map=DEVICE
    )
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    
    print("✅ Núcleo LISTO en puerto 8000")
    play_sound("ready")
    
    # Iniciar Watchdog
    asyncio.create_task(watchdog_loop())
    
    yield
    
    # Limpieza
    print("👋 Apagando Núcleo...")
    del model
    del processor
    torch.mps.empty_cache()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    global last_activity
    last_activity = time.time() # Reset timer
    return {"status": "alive", "device": DEVICE}

@app.post("/infer")
async def inference(
    file: UploadFile, 
    prompt: str = Form(...),
    max_tokens: int = Form(4096)
):
    global last_activity
    last_activity = time.time() # Reset timer (keep alive)
    play_sound("processing") # Feedback de "estoy pensando"

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Lógica Dolphin
        messages = [{
            "role": "user",
            "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]
        }]
        
        text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = processor(text=[text_input], images=image_inputs, padding=True, return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=max_tokens, temperature=0.01)
            
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        output_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]
        
        return {"result": output_text}
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
```

### 🟡 2. El Puente: `bridge.py`

```python
import requests
import subprocess
import time
import sys
import os

SERVER_URL = "http://localhost:8000"
SERVER_SCRIPT = "server_core.py" # Asegúrate que esté en la misma carpeta

def ensure_server_running():
    """
    Verifica si el oráculo está vivo. Si no, lo invoca.
    """
    try:
        requests.get(f"{SERVER_URL}/health", timeout=1)
        return True
    except (requests.ConnectionError, requests.Timeout):
        print("⚡ Despertando al Oráculo Dolphin...")
        # Lanzar servidor en background
        subprocess.Popen(["python", SERVER_SCRIPT], stdout=sys.stdout, stderr=sys.stderr)
        
        # Esperar handshake (polling)
        print("⏳ Esperando carga de modelo (esto puede tomar 10-20s)...")
        retries = 30
        while retries > 0:
            try:
                res = requests.get(f"{SERVER_URL}/health", timeout=1)
                if res.status_code == 200:
                    print("🔗 Conexión establecida.")
                    return True
            except:
                time.sleep(1)
                retries -= 1
        
        print("❌ Error: El servidor no respondió a tiempo.")
        sys.exit(1)

def send_request(filepath, prompt, max_tokens=4096):
    ensure_server_running()
    
    with open(filepath, "rb") as f:
        files = {"file": f}
        data = {"prompt": prompt, "max_tokens": max_tokens}
        try:
            resp = requests.post(f"{SERVER_URL}/infer", files=files, data=data)
            if resp.status_code == 200:
                return resp.json()["result"]
            else:
                return f"Error {resp.status_code}: {resp.text}"
        except Exception as e:
            return f"Error de transmisión: {str(e)}"
```

### 🟢 3. El Adaptador/Cliente: `dolphin_cli.py`

```python
import argparse
import bridge # Importamos nuestro puente
from pdf2image import convert_from_path
import os

# ESTRATEGIAS DE INGESTA (Prompts de Dolphin)
MODES = {
    "text": "Read text in the image.",
    "layout": "Analyze the layout of the document.",
    "table": "Parse the table in the image.",
    "formula": "Parse the formula in the image.",
    "code": "Read code in the image."
}

def main():
    parser = argparse.ArgumentParser(description="Cliente Dolphin Percepción Local")
    parser.add_argument("input", help="Archivo PDF o Imagen")
    parser.add_argument("-m", "--mode", choices=MODES.keys(), default="text", help="Modo de extracción")
    parser.add_argument("-o", "--output", help="Archivo de salida (opcional)")
    
    args = parser.parse_args()
    
    # 1. Preprocesamiento (Cliente -> Imágenes)
    images_to_process = []
    temp_files = []
    
    if args.input.lower().endswith(".pdf"):
        print(f"📑 Rasterizando PDF: {args.input}")
        pil_images = convert_from_path(args.input)
        # Guardar temporalmente como imágenes para enviar al server (que espera files)
        for i, img in enumerate(pil_images):
            path = f"temp_page_{i}.jpg"
            img.save(path)
            images_to_process.append(path)
            temp_files.append(path)
    else:
        images_to_process.append(args.input)

    # 2. Envío a través del Puente
    full_transcript = []
    prompt = MODES[args.mode]
    
    print(f"🚀 Enviando {len(images_to_process)} páginas al Núcleo...")
    
    for i, img_path in enumerate(images_to_process):
        print(f"   ↳ Procesando página {i+1}...")
        result = bridge.send_request(img_path, prompt)
        
        # Formateo inteligente según modo
        if args.mode == "formula":
            result = f"$$ \n{result}\n $$" # Envolver LaTeX
        elif args.mode == "table":
            result = f"<!-- Tabla Pág {i+1} -->\n{result}"
            
        full_transcript.append(result)

    # 3. Limpieza y Salida
    final_output = "\n\n".join(full_transcript)
    
    # Borrar temporales
    for f in temp_files:
        if os.path.exists(f): os.remove(f)

    if args.output:
        with open(args.output, "w") as f:
            f.write(final_output)
        print(f"💾 Guardado en: {args.output}")
    else:
        print("\n--- RESULTADO ---\n")
        print(final_output)

if __name__ == "__main__":
    main()
```

---

## 3. Flujo de Uso

1.  **Estado Inicial:** Tu MacBook está en silencio. No hay procesos de Python consumiendo RAM.
2.  **Comando:** Ejecutas en terminal:
    ```bash
    python dolphin_cli.py paper_fisica.pdf -m formula -o salida.tex
    ```
3.  **El Despertar:**
    *   El script detecta que el servidor está apagado.
    *   Lanza `server_core.py`.
    *   🔊 **Sonido "Blow":** (Cargando sistema).
    *   ... pasan unos segundos ...
    *   🔊 **Sonido "Glass":** (Modelo listo en VRAM).
4.  **La Inferencia:**
    *   Se procesan las páginas.
    *   🔊 **Sonido "Tink":** (Cada vez que procesa una página, confirmación auditiva).
5.  **El Resultado:**
    *   Obtienes tu archivo `.tex`.
6.  **El Reposo:**
    *   El servidor se queda esperando 5 minutos por si quieres procesar otro archivo.
    *   Si no haces nada...
    *   🔊 **Sonido "Bottle":** El servidor se apaga, libera los 7-8GB de RAM y tu Mac vuelve a estar 100% libre.

Esta arquitectura cumple con tu estándar de "Percepción Visual Local" y es extremadamente respetuosa con el hardware de Apple.
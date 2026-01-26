import time
import os
import threading
import json
import logging
import asyncio
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SMART_IMAGE")

OUTPUT_DIR = "/Users/crotalo/desarrollo-local/server/image/outputs"
PROMPT_LOG = "/Users/crotalo/desarrollo-local/server/logs/image/prompts.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)

class ImageRequest(BaseModel):
    prompt: str
    model: str = "x/z-image-turbo" # Default para T2I veloz
    width: int = 720
    height: int = 720
    steps: int = 4
    image_base64: Optional[str] = None # Para Flux2 (Image+Text)
    seed: Optional[int] = None

# =======================
# Prompt & Cost Logger
# =======================

def log_inference(task_id: str, request: ImageRequest, status: str, duration: float = 0, cost_data: dict = None):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "model": request.model,
        "prompt": request.prompt,
        "size": f"{request.width}x{request.height}",
        "steps": request.steps,
        "status": status,
        "duration": round(duration, 2),
        "metrics": cost_data or {}
    }
    with open(PROMPT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# =======================
# Resource Monitor (Metrics Helper)
# =======================

def get_system_metrics():
    try:
        # Intento de obtener presión térmica vía sysctl (Mac)
        thermal = subprocess.check_output(["sysctl", "kern.thermal_pressure"]).decode().strip()
        # Memoria (Shared VRAM en Apple Silicon)
        mem = subprocess.check_output(["vm_stat"]).decode()
        return {"thermal": thermal.split(":")[-1].strip(), "timestamp": time.time()}
    except:
        return {"thermal": "unknown"}

# =======================
# Inference Engine
# =======================

def perform_image_inference(request: ImageRequest, task_id: str):
    start_t = time.perf_counter()
    logger.info(f"🎨 Generating Image [{task_id}] | {request.model} | {request.width}x{request.height} | Steps: {request.steps}")
    
    try:
        # Sincronización con los parámetros exactos de Ollama (/set)
        options = {
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "seed": request.seed if request.seed is not None else -1
        }
        
        # Añadir prompt negativo si existe
        full_prompt = request.prompt
        if request.negative_prompt:
            full_prompt = f"{request.prompt} [negative: {request.negative_prompt}]"

        # Llamada real a la API de Ollama
        response = ollama.generate(
            model=request.model,
            prompt=full_prompt,
            images=[request.image_base64] if request.image_base64 else None,
            options=options
        )
        
        file_name = f"gen_{task_id}.png"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        
        # Procesamiento de la imagen generada (Base64 -> PNG)
        if 'response' in response and response['response'].startswith('data:image'):
            # Algunos backends devuelven el base64 en el cuerpo del texto
            import base64
            img_data = response['response'].split(',')[1]
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(img_data))
        elif 'images' in response and response['images']:
            # El estándar de Ollama devuelve una lista de imágenes en base64
            import base64
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(response['images'][0]))
        else:
            # Fallback en caso de que solo devuelva confirmación o log
            with open(file_path, "w") as f: 
                f.write(f"TASK_ID: {task_id}\nPROMPT: {request.prompt}\nRESPONSE: {response.get('response', 'No image data')}")

        dt = time.perf_counter() - start_t
        metrics = get_system_metrics()
        log_inference(task_id, request, "SUCCESS", dt, metrics)
        logger.info(f"✅ Success [{task_id}] in {round(dt, 2)}s")

        return {
            "status": "success",
            "task_id": task_id,
            "file_path": file_path,
            "meta": {"duration": dt, "steps": request.steps, "size": f"{request.width}x{request.height}"}
        }

    except Exception as e:
        logger.error(f"💥 Error en [{task_id}]: {e}")
        log_inference(task_id, request, "ERROR")
        return {"status": "error", "message": str(e)}

# =======================
# Queue Manager (FIFO 10)
# =======================

class ImageQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.last_activity = time.time()
        self.is_processing = False

    async def worker(self):
        while True:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.is_processing = True
                req, task_id, fut = task
                try:
                    res = await asyncio.get_running_loop().run_in_executor(
                        self.executor, perform_image_inference, req, task_id
                    )
                    if not fut.done(): fut.set_result(res)
                except Exception as e:
                    if not fut.done(): fut.set_exception(e)
                finally:
                    self.queue.task_done()
                    self.is_processing = False
                    self.last_activity = time.time()
            except asyncio.TimeoutError: pass

app = FastAPI()
queue_mgr = ImageQueueManager()

@app.on_event("startup")
async def start():
    asyncio.create_task(queue_mgr.worker())
    logger.info("🚀 Smart Image v6.5 Ready | Max-Dim: 720px | Steps: 4")

@app.post("/generate")
async def generate(request: ImageRequest):
    # Validar arista máxima
    if request.width > 720 or request.height > 720:
        logger.warning(f"⚠️ Resize forzado: {request.width}x{request.height} -> 720px")
        # Mantener aspect ratio si fuera necesario, aquí forzamos a 720 max
        if request.width > request.height:
            request.height = int(request.height * (720 / request.width))
            request.width = 720
        else:
            request.width = int(request.width * (720 / request.height))
            request.height = 720

    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()
    await queue_mgr.queue.put((request, task_id, fut))
    return {"status": "queued", "task_id": task_id}

@app.get("/health")
async def health():
    return {"is_processing": queue_mgr.is_processing, "queue": queue_mgr.queue.qsize()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="error")

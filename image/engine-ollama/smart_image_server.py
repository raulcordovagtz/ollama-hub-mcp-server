import time
import os
import json
import logging
import asyncio
import uuid
import base64
import urllib.request
import urllib.error
import signal
import sys
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from PIL import Image
import io

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SMART_IMAGE")

# =======================
# Constantes de Diseño
# =======================
MAX_EDGE = 1024
ALIGNMENT = 16

def normalize_dimension(val: int) -> int:
    """Ajusta al múltiplo de 16 más cercano."""
    return round(val / ALIGNMENT) * ALIGNMENT

def apply_geometric_firewall(width: int, height: int) -> tuple[int, int]:
    """
    Normaliza dimensiones:
    1. Limita la arista mayor a MAX_EDGE manteniendo el ratio.
    2. Ajusta ambas dimensiones al múltiplo de 16 más cercano.
    """
    if not width or not height:
        return 720, 720 

    if width > MAX_EDGE or height > MAX_EDGE:
        ratio = width / height
        if width > height:
            width = MAX_EDGE
            height = int(MAX_EDGE / ratio)
        else:
            height = MAX_EDGE
            width = int(MAX_EDGE * ratio)
    
    new_w = normalize_dimension(width)
    new_h = normalize_dimension(height)
    
    new_w = max(new_w, ALIGNMENT)
    new_h = max(new_h, ALIGNMENT)
    
    logger.info(f"🛡️ Firewall Geométrico: {width}x{height} -> {new_w}x{new_h}")
    return new_w, new_h

OUTPUT_DIR = "/Users/crotalo/desarrollo-local/server/image/outputs"
PROMPT_LOG = "/Users/crotalo/desarrollo-local/server/logs/image/prompts.log"
OLLAMA_URL = "http://localhost:11434/api/generate"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PROMPT_LOG), exist_ok=True)

class ImageRequest(BaseModel):
    prompt: str
    model: str = "x/z-image-turbo"
    width: Optional[int] = None
    height: Optional[int] = None
    steps: int = 4
    image_base64: Optional[str] = None
    images_base64: Optional[list[str]] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None

# =======================
# Prompt & Cost Logger
# =======================

def log_inference(task_id: str, request: ImageRequest, status: str, duration: float = 0, error_msg: str = ""):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "model": request.model,
        "prompt": request.prompt,
        "size": f"{request.width}x{request.height}",
        "steps": request.steps,
        "status": status,
        "duration": round(duration, 2),
        "error": error_msg
    }
    try:
        with open(PROMPT_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to prompt log: {e}")

# =======================
# Inference Engine (Raw API)
# =======================

def perform_image_inference(request: ImageRequest, task_id: str):
    start_t = time.perf_counter()
    logger.info(f"🎨 [RAW API] Task: {task_id} | {request.model} | {request.width}x{request.height}")
    
    try:
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "options": {
                "steps": request.steps,
                "seed": request.seed if request.seed is not None else -1
            }
        }
        
        if request.width:
            payload["width"] = request.width
            payload["options"]["width"] = request.width
        if request.height:
            payload["height"] = request.height
            payload["options"]["height"] = request.height
        
        if request.negative_prompt:
            payload["prompt"] = f"{request.prompt} [negative: {request.negative_prompt}]"

        imgs = request.images_base64 or []
        if request.image_base64:
            imgs.append(request.image_base64)
            
        if imgs:
            processed_imgs = []
            # Redimensionar si hay múltiples imágenes O si una sola es demasiado grande (>1024)
            for i, b64 in enumerate(imgs):
                if "," in b64: b64 = b64.split(",")[1]
                img_data = base64.b64decode(b64)
                img = Image.open(io.BytesIO(img_data))
                
                # Estrategia: 2+ imágenes -> 512px max. 1 imagen -> 1024px max.
                limit = 512 if len(imgs) > 1 else 1024
                if max(img.size) > limit:
                    img.thumbnail((limit, limit), Image.Resampling.LANCZOS)
                    logger.info(f"📏 Resized input image {i+1} to {img.size} (Limit: {limit}px)")
                
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                processed_imgs.append(base64.b64encode(buffered.getvalue()).decode('utf-8'))

            payload["images"] = processed_imgs
            logger.info(f"📸 Attached {len(processed_imgs)} images to payload.")

        # Añadir keep_alive para mantener el modelo cargado (suprimir arranque en frío)
        # pero permitir que Ollama lo libere si pasan 5 minutos de inactividad.
        payload["keep_alive"] = "5m"

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={'Content-Type': 'application/json'})
        
        # Timeout largo pero controlado
        with urllib.request.urlopen(req, timeout=300) as response:
            resp_body = json.loads(response.read().decode('utf-8'))
            
            img_b64 = resp_body.get('image')
            if not img_b64 and resp_body.get('images'):
                img_b64 = resp_body['images'][0]
            
            file_name = f"gen_{task_id}.png"
            file_path = os.path.join(OUTPUT_DIR, file_name)
            
            if img_b64:
                if "," in img_b64: img_b64 = img_b64.split(",")[1]
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(img_b64))
                status = "SUCCESS"
            else:
                logger.error(f"❌ No image data in Ollama response. Keys: {list(resp_body.keys())}")
                status = "ERROR_NO_IMAGE"

        dt = time.perf_counter() - start_t
        log_inference(task_id, request, status, dt)
        return {
            "status": "success" if status == "SUCCESS" else "error",
            "task_id": task_id,
            "file_path": file_path if status == "SUCCESS" else None,
            "meta": {"duration": dt}
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No body"
        logger.error(f"💥 Ollama HTTP Error {e.code} [{task_id}]: {error_body}")
        log_inference(task_id, request, "HTTP_ERROR", time.perf_counter() - start_t, f"{e.code}: {error_body}")
        return {"status": "error", "message": f"Ollama error {e.code}: {error_body}"}
    except Exception as e:
        logger.error(f"💥 Fatal error [{task_id}]: {e}")
        log_inference(task_id, request, "FATAL_ERROR", time.perf_counter() - start_t, str(e))
        return {"status": "error", "message": str(e)}

# =======================
# Queue Manager
# =======================

class ImageQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=15)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="InferenceWorker")
        self.is_processing = False
        self.current_task_id = None
        self._loop_task = None

    async def worker(self):
        logger.info("👷 Worker started.")
        while True:
            item = await self.queue.get()
            req, task_id, fut = item
            
            # Verificar si el cliente ya se desconectó
            if fut.cancelled():
                logger.info(f"⏭️ Task {task_id} cancelled before processing.")
                self.queue.task_done()
                continue

            self.is_processing = True
            self.current_task_id = task_id
            
            try:
                # Ejecutar inferencia en el executor
                res = await asyncio.get_running_loop().run_in_executor(
                    self.executor, perform_image_inference, req, task_id
                )
                if not fut.cancelled():
                    fut.set_result(res)
                else:
                    logger.info(f"🚮 Task {task_id} finished but client already disconnected.")
            except Exception as e:
                if not fut.cancelled():
                    fut.set_exception(e)
            finally:
                self.queue.task_done()
                self.is_processing = False
                self.current_task_id = None

    def start(self):
        self._loop_task = asyncio.create_task(self.worker())

    def stop(self):
        if self._loop_task:
            self._loop_task.cancel()
        self.executor.shutdown(wait=False)

queue_mgr = ImageQueueManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    queue_mgr.start()
    logger.info("🚀 Smart Image Server v7.0 (Robust Mode) Ready.")
    yield
    # Shutdown
    logger.info("🛑 Shutting down server...")
    queue_mgr.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "is_processing": queue_mgr.is_processing, 
        "current_task": queue_mgr.current_task_id,
        "queue_size": queue_mgr.queue.qsize()
    }

@app.post("/generate")
async def generate(request: ImageRequest):
    if "z-image" in request.model.lower():
        w = request.width or 720
        h = request.height or 720
        request.width, request.height = apply_geometric_firewall(w, h)
    
    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()
    
    try:
        await asyncio.wait_for(queue_mgr.queue.put((request, task_id, fut)), timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Server busy, queue is full.")

    try:
        return await fut
    except asyncio.CancelledError:
        logger.info(f"⚠️ Request {task_id} cancelled by client.")
        raise

if __name__ == "__main__":
    import uvicorn
    # Usar uvicorn con loop 'asyncio' y manejo de señales
    config = uvicorn.Config(
        app, 
        host="127.0.0.1", 
        port=8010, 
        log_level="info",
        timeout_keep_alive=30,
        limit_concurrency=20
    )
    server = uvicorn.Server(config)
    
    # Manejo explícito de señales para evitar procesos zombies
    def handle_exit(sig, frame):
        logger.info(f"Received signal {sig}, exiting...")
        queue_mgr.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    server.run()

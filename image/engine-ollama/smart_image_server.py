import time
import os
import json
import logging
import asyncio
import uuid
import base64
import urllib.request
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SMART_IMAGE")

OUTPUT_DIR = "/Users/crotalo/desarrollo-local/server/image/outputs"
PROMPT_LOG = "/Users/crotalo/desarrollo-local/server/logs/image/prompts.log"
OLLAMA_URL = "http://localhost:11434/api/generate"

os.makedirs(OUTPUT_DIR, exist_ok=True)

class ImageRequest(BaseModel):
    prompt: str
    model: str = "x/z-image-turbo"
    width: int = 720
    height: int = 720
    steps: int = 4
    image_base64: Optional[str] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None

# =======================
# Prompt & Cost Logger
# =======================

def log_inference(task_id: str, request: ImageRequest, status: str, duration: float = 0):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "model": request.model,
        "prompt": request.prompt,
        "size": f"{request.width}x{request.height}",
        "steps": request.steps,
        "status": status,
        "duration": round(duration, 2)
    }
    with open(PROMPT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# =======================
# Inference Engine (Raw API)
# =======================

def perform_image_inference(request: ImageRequest, task_id: str):
    start_t = time.perf_counter()
    logger.info(f"🎨 [RAW API] Task: {task_id} | {request.model} | {request.width}x{request.height}")
    
    try:
        # Preparamos el payload crudo para evitar que la libreria ollama-python filtre campos
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
            # Probamos inyectar parametros en raiz Y en options para maxima compatibilidad
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "options": {
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "seed": request.seed if request.seed is not None else -1
            }
        }
        
        if request.negative_prompt:
            payload["prompt"] = f"{request.prompt} [negative: {request.negative_prompt}]"

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={'Content-Type': 'application/json'})
        
        # Timeout largo para modelos de 12GB
        with urllib.request.urlopen(req, timeout=600) as response:
            resp_body = json.loads(response.read().decode('utf-8'))
            
            # Buscamos la imagen en 'image' (singular) o 'images' (lista)
            img_b64 = resp_body.get('image')
            if not img_b64 and resp_body.get('images'):
                img_b64 = resp_body['images'][0]
            
            file_name = f"gen_{task_id}.png"
            file_path = os.path.join(OUTPUT_DIR, file_name)
            
            if img_b64:
                # Limpiar prefijo si existe
                if "," in img_b64: img_b64 = img_b64.split(",")[1]
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(img_b64))
                status = "SUCCESS"
            else:
                with open(file_path, "w") as f:
                    f.write(f"NO_IMAGE_DATA\nKEYS: {list(resp_body.keys())}\nRAW: {str(resp_body)[:1000]}")
                status = "ERROR_NO_IMAGE"

        dt = time.perf_counter() - start_t
        log_inference(task_id, request, status, dt)
        logger.info(f"✅ Finished [{task_id}] in {round(dt, 2)}s | Status: {status}")

        return {
            "status": "success" if status == "SUCCESS" else "error",
            "task_id": task_id,
            "file_path": file_path,
            "meta": {"duration": dt}
        }

    except Exception as e:
        logger.error(f"💥 Fatal error [{task_id}]: {e}")
        return {"status": "error", "message": str(e)}

# =======================
# Queue Manager
# =======================

class ImageQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.is_processing = False

    async def worker(self):
        while True:
            item = await self.queue.get()
            self.is_processing = True
            req, task_id, fut = item
            try:
                res = await asyncio.get_running_loop().run_in_executor(self.executor, perform_image_inference, req, task_id)
                fut.set_result(res)
            except Exception as e:
                fut.set_exception(e)
            finally:
                self.queue.task_done()
                self.is_processing = False

app = FastAPI()
queue_mgr = ImageQueueManager()

@app.on_event("startup")
async def start_worker():
    asyncio.create_task(queue_mgr.worker())
    logger.info("🚀 Smart Image Server v6.7 (RAW API Mode) Ready.")

@app.get("/health")
async def health():
    return {"status": "ok", "is_processing": queue_mgr.is_processing, "queue_size": queue_mgr.queue.qsize()}

@app.post("/generate")
async def generate(request: ImageRequest):
    # Auto-limitador industrial
    request.width = min(request.width, 720)
    request.height = min(request.height, 720)
    
    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()
    await queue_mgr.queue.put((request, task_id, fut))
    return await fut

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="error")

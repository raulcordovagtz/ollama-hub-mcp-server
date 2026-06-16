import time
import os
import threading
import json
import logging
import asyncio
import uuid
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SMART_DIFFUSION")

DIFFUSION_LOG = "/Users/crotalo/desarrollo-local/server/logs/diffusion/inference.log"
os.makedirs(os.path.dirname(DIFFUSION_LOG), exist_ok=True)

# Ruta local del modelo (ya descargado via LM Studio)
MODEL_PATH = "/Users/crotalo/.lmstudio/models/mlx-community/diffusiongemma-26B-A4B-it-4bit"

class DiffusionRequest(BaseModel):
    prompt: Optional[str] = None
    system_prompt: Optional[str] = "Eres un asistente experto, conciso y creativo."
    messages: Optional[List[Any]] = None
    temperature: float = 0.5
    max_tokens: int = 3000

# =======================
# Model Manager (Lazy Loading)
# =======================

class DiffusionModelManager:
    def __init__(self):
        self.model = None
        self.processor = None
        self.lock = threading.Lock()

    def load(self):
        with self.lock:
            if self.model is None:
                import subprocess
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"🧬 Cargando DiffusionGemma desde {MODEL_PATH}...")

                from mlx_vlm import load
                self.model, self.processor = load(MODEL_PATH)

                logger.info("✨ DiffusionGemma Listo.")

    def get_model(self):
        if self.model is None:
            self.load()
        return self.model, self.processor

    def is_loaded(self):
        return self.model is not None

# =======================
# Inference Engine (Diffusion Text)
# =======================

def perform_diffusion_inference(request: DiffusionRequest, task_id: str):
    start_t = time.perf_counter()
    logger.info(f"🧬 [DIFFUSION] Task: {task_id} | Tokens: {request.max_tokens}")

    try:
        model, processor = model_manager.get_model()

        from mlx_vlm import generate

        if request.messages:
            # Si nos pasan mensajes estructurados (como de OpenAI)
            messages = []
            for msg in request.messages:
                if isinstance(msg, dict):
                    messages.append(msg)
                else:
                    messages.append({"role": msg.role, "content": msg.content})
        else:
            # Construir mensajes con chat template tradicional de un turno
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        # Aplicar chat template del procesador
        prompt_text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Generar respuesta con ventana de contexto de 256K tokens (262144)
        output = generate(
            model,
            processor,
            prompt=prompt_text,
            max_tokens=request.max_tokens,
            temp=request.temperature,
            verbose=False,
            max_kv_size=262144,
        )

        dt = time.perf_counter() - start_t

        # Log accounting
        with open(DIFFUSION_LOG, "a") as f:
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "task_id": task_id,
                "model": "diffusiongemma-26B-A4B-it-4bit",
                "mode": "DIFFUSION",
                "duration": round(dt, 2),
                "max_tokens": request.max_tokens
            }
            f.write(json.dumps(log_entry) + "\n")

        logger.info(f"✅ Success [{task_id}] in {round(dt, 2)}s")
        return {
            "status": "success",
            "task_id": task_id,
            "response": output,
            "meta": {
                "duration": round(dt, 2),
                "model": "diffusiongemma-26B-A4B-it-4bit",
                "engine": "mlx-vlm"
            }
        }

    except Exception as e:
        logger.error(f"💥 Diffusion error [{task_id}]: {e}")
        return {"status": "error", "task_id": task_id, "message": str(e)}

# =======================
# API & Queue Manager
# =======================

class DiffusionQueueManager:
    def __init__(self, idle_timeout=1200):
        self.queue = asyncio.Queue(maxsize=5)
        self.executor = ThreadPoolExecutor(max_workers=1)  # Serializado para protección térmica
        self.is_processing = False
        self.last_activity = time.time()
        self.idle_timeout = idle_timeout
        self.boot_time = time.time()

    async def inactivity_monitor(self):
        logger.info(f"⏳ Monitor de inactividad iniciado (Timeout: {self.idle_timeout}s)")
        while True:
            await asyncio.sleep(10)
            elapsed = time.time() - self.last_activity
            if elapsed > self.idle_timeout:
                logger.warning(f"😴 Inactividad detectada ({round(elapsed, 1)}s). Apagando servidor...")
                os._exit(0)

    async def worker(self):
        while True:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.is_processing = True
                req, task_id, fut = task
                try:
                    res = await asyncio.get_running_loop().run_in_executor(
                        self.executor, perform_diffusion_inference, req, task_id
                    )
                    if not fut.done():
                        fut.set_result(res)
                except Exception as e:
                    if not fut.done():
                        fut.set_exception(e)
                finally:
                    self.queue.task_done()
                    self.is_processing = False
                    self.last_activity = time.time()
            except asyncio.TimeoutError:
                pass

app = FastAPI()
model_manager = DiffusionModelManager()
queue_mgr = DiffusionQueueManager(idle_timeout=1200)

@app.on_event("startup")
async def start():
    asyncio.create_task(queue_mgr.worker())
    asyncio.create_task(queue_mgr.inactivity_monitor())
    logger.info("🧬 Smart Diffusion Server Ready (Port 8011)")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ready": model_manager.is_loaded(),
        "model": "diffusiongemma-26B-A4B-it-4bit",
        "engine": "mlx-vlm"
    }

@app.post("/chat")
async def chat(request: DiffusionRequest):
    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()
    try:
        await asyncio.wait_for(
            queue_mgr.queue.put((request, task_id, fut)),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Cola llena. Intente más tarde.")
    result = await fut
    return result

# Modelos para compatibilidad con API de OpenAI /v1/chat/completions
class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAICompletionRequest(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False

@app.post("/v1/chat/completions")
async def openai_chat_completions(req: OpenAICompletionRequest):
    # Traducir la petición de OpenAI a nuestro formato DiffusionRequest
    diffusion_req = DiffusionRequest(
        messages=req.messages,
        temperature=req.temperature if req.temperature is not None else 0.7,
        max_tokens=req.max_tokens if req.max_tokens is not None else 1000
    )
    
    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()
    
    try:
        await asyncio.wait_for(
            queue_mgr.queue.put((diffusion_req, task_id, fut)),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Cola llena. Intente más tarde.")
        
    result = await fut
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
        
    response_text = result["response"]
    if hasattr(response_text, "text"):
        response_text = response_text.text
    elif isinstance(response_text, dict):
        response_text = response_text.get("text", "")
    else:
        response_text = str(response_text)
        
    if req.stream:
        # Si pide streaming, simulamos una respuesta SSE
        async def sse_generator():
            created_time = int(time.time())
            # Chunk 1: El texto generado
            chunk_data_1 = {
                "id": f"chatcmpl-{task_id}",
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data_1)}\n\n"
            
            # Chunk 2: Finalización de la generación (finish_reason = stop)
            chunk_data_2 = {
                "id": f"chatcmpl-{task_id}",
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data_2)}\n\n"
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(sse_generator(), media_type="text/event-stream")
    else:
        return {
            "id": f"chatcmpl-{task_id}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": -1,
                "completion_tokens": -1,
                "total_tokens": -1
            }
        }

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "diffusiongemma-26B-A4B-it-4bit",
                "object": "model",
                "created": 1700000000,
                "owned_by": "custom"
            }
        ]
    }

@app.get("/v1/health")
async def v1_health():
    return {
        "status": "ok",
        "ready": model_manager.is_loaded(),
        "model": "diffusiongemma-26B-A4B-it-4bit",
        "engine": "mlx-vlm"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8011, log_level="error")

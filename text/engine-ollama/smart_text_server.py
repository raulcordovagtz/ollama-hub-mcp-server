import time
import os
import threading
import json
import logging
import asyncio
import uuid
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SMART_TEXT")

TEXT_LOG = "/Users/crotalo/desarrollo-local/server/logs/text/inference.log"
os.makedirs(os.path.dirname(TEXT_LOG), exist_ok=True)

class TextRequest(BaseModel):
    prompt: str
    model: str = "qwen3:8b" # Default mediano balanceado
    system_prompt: Optional[str] = "Eres un asistente experto, conciso y creativo."
    images_base64: Optional[List[str]] = None # Soporte para Vision (Qwen3-VL / Granite-Vision)
    temperature: float = 0.7
    max_tokens: int = 1000

# =======================
# Inference Engine (Text & Vision)
# =======================

def perform_text_inference(request: TextRequest, task_id: str):
    start_t = time.perf_counter()
    mode = "VISION" if request.images_base64 else "TEXT"
    logger.info(f"📝 [{mode}] Task: {task_id} | Model: {request.model}")
    
    try:
        # Llamada a Ollama (Soporta Chat API para System Prompts y Vision)
        messages = []
        if request.system_prompt:
            messages.append({'role': 'system', 'content': request.system_prompt})
        
        user_message = {'role': 'user', 'content': request.prompt}
        if request.images_base64:
            user_message['images'] = request.images_base64
            
        messages.append(user_message)

        response = ollama.chat(
            model=request.model,
            messages=messages,
            options={
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        )

        content = response['message']['content']
        dt = time.perf_counter() - start_t
        
        # Log accounting
        with open(TEXT_LOG, "a") as f:
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "task_id": task_id,
                "model": request.model,
                "mode": mode,
                "duration": round(dt, 2),
                "tokens": response.get('eval_count', 0)
            }
            f.write(json.dumps(log_entry) + "\n")

        logger.info(f"✅ Success [{task_id}] in {round(dt, 2)}s")
        return {
            "status": "success",
            "task_id": task_id,
            "response": content,
            "meta": {"duration": dt, "model": request.model}
        }

    except Exception as e:
        logger.error(f"💥 Text error [{task_id}]: {e}")
        return {"status": "error", "message": str(e)}

# =======================
# API & Queue Manager
# =======================

class TextQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=1) # Serializado para calma térmica
        self.is_processing = False

    async def worker(self):
        while True:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.is_processing = True
                req, task_id, fut = task
                try:
                    res = await asyncio.get_running_loop().run_in_executor(
                        self.executor, perform_text_inference, req, task_id
                    )
                    if not fut.done(): fut.set_result(res)
                except Exception as e:
                    if not fut.done(): fut.set_exception(e)
                finally:
                    self.queue.task_done()
                    self.is_processing = False
            except asyncio.TimeoutError: pass

app = FastAPI()
queue_mgr = TextQueueManager()

@app.on_event("startup")
async def start():
    asyncio.create_task(queue_mgr.worker())
    logger.info("🚀 Smart Text & Vision Server Ready (Port 8009)")

@app.post("/chat")
async def chat(request: TextRequest):
    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()
    await queue_mgr.queue.put((request, task_id, fut))
    result = await fut
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8009, log_level="error")

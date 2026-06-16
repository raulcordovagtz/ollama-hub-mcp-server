import os
import io
import base64
import yaml
import time
import asyncio
import logging
import uvicorn
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from PIL import Image

# Import our modules
# from .config import load_config # Removed incorrect import
from .queue_manager import RequestQueue
from .session_manager import SessionManager
from .inference import InferenceEngine
from .shutdown_manager import ShutdownManager
from .model_loader import ModelLoader

# --- Configuration Loading ---
def load_config(path="server/config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

# Allow env var override for config path
CONFIG_PATH = os.getenv("SERVER_CONFIG_PATH", os.path.join(os.path.dirname(__file__), "config.yaml"))
config = load_config(CONFIG_PATH)

# --- Global Components ---
queue_manager = RequestQueue()
session_manager = SessionManager()
# Strict shutdown manager
shutdown_manager = ShutdownManager(
    idle_timeout_minutes=config["server"]["idle_timeout_minutes"],
    vram_threshold_mb=config["server"]["vram_threshold_mb"]
)
inference_engine = InferenceEngine(config)
model_loader = ModelLoader(config)

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Server starting up...")
    
    # Start shutdown monitor (background thread)
    shutdown_manager.start_monitor()
    
    yield
    
    # Shutdown
    logging.info("Server shutting down...")
    shutdown_manager.stop()
    model_loader.unload()

app = FastAPI(lifespan=lifespan)

# --- Pydantic Models ---
class InteractionRequest(BaseModel):
    session_id: Optional[str] = None
    image_base64: str
    prompt: str
    generation_config: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    vram_usage_mb: float
    queue_depth: int

class InteractionResponse(BaseModel):
    raw_text_output: str
    metadata: Dict[str, Any]

# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health_check():
    # Update activity for shutdown manager
    shutdown_manager.update_activity()
    
    status = "READY" if model_loader.is_loaded() else "WARMING" # Or DEAD if process not running, but if we are here...
    # WARMING usually means "loading", but here we load on demand or keep loaded. 
    # Let's say READY if loaded, WARMING if we are alive but model not loaded (will load on request).
    # Client expects "DEAD" if can't connect (handled by client exception), "WARMING" maybe if loading?
    # For now: READY = responsive.
    
    return HealthResponse(
        status="READY",
        model_loaded=model_loader.is_loaded(),
        vram_usage_mb=model_loader.get_vram_usage(),
        queue_depth=queue_manager.get_status()["queue_depth"]
    )

@app.post("/api/shutdown")
async def shutdown_server():
    shutdown_manager.shutdown(reason="user request")
    return {"status": "shutting down"}

@app.post("/api/interact", response_model=InteractionResponse)
async def interact(request: InteractionRequest):
    shutdown_manager.update_activity()
    
    # 1. Decode Image
    try:
        image_data = base64.b64decode(request.image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    # 2. Prepare Session/History
    if request.session_id:
        history = session_manager.get_session_history(request.session_id)
        # Append user message for inference context (but not yet to history, we do that after success?)
        # Actually inference engine applies template. 
        # We need to construct the messages list.
        # History has system prompt + previous.
        messages = history + [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": request.prompt}]}]
    else:
        # Stateless
        messages = [
            {"role": "system", "content": session_manager.system_instruction},
            {"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": request.prompt}]}
        ]

    # 3. Enqueue and Execute Inference
    start_time = time.time()
    try:
        response_text = await queue_manager.execute(
            inference_engine.run_inference,
            messages=messages,
            image=image, # Config overrides extraction inside inference? 
            # Wait, inference_engine.run_inference takes (messages, image). 
            # But the 'image' arg in run_inference might be redundant if it's in messages?
            # Let's check inference.py... Yes, it takes image arg.
            # processor(images=image, ...) is needed for the vision model.
            generation_config=request.generation_config
        )
    except Exception as e:
        logging.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    end_time = time.time()

    # 4. Update Session (if exists)
    if request.session_id:
        session_manager.update_session(
            request.session_id,
            [{"type": "text", "text": request.prompt}],
            response_text
        )

    return InteractionResponse(
        raw_text_output=response_text,
        metadata={
            "duration_seconds": end_time - start_time,
            "inference_id": str(uuid.uuid4()),
            "model_loaded": True,
            "vram_usage_mb": model_loader.get_vram_usage(),
            "queued_requests": queue_manager.get_status()["queue_depth"]
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host=config["server"]["host"], port=config["server"]["port"])

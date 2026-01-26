import time
import os
import threading
import json
import gc
import argparse
import subprocess
import logging
import asyncio
import re
import wave
import librosa
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

import mlx.core as mx
import numpy as np
import langid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mlx_audio.tts.utils import load_model

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TTS_FINAL")

CONFIG_PATH = "/Users/crotalo/desarrollo-local/server/tts/engine-mlx/server_config.json"
with open(CONFIG_PATH, "r") as f:
    GLOBAL_CONFIG = json.load(f)

class InferenceRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    lang: Optional[str] = None

# =======================
# Model Manager (Pre-Caching)
# =======================

class ModelManager:
    def __init__(self, model_type: str):
        self.model_type = model_type
        self.model_id = GLOBAL_CONFIG[model_type]["model_id"]
        self.model = None
        self.lock = threading.Lock()
        self.active_task_id = 0  # 🧠 ID de la tarea activa para interrupción radical

    def load(self):
        with self.lock:
            if self.model is None:
                logger.info(f"🚀 Cargando {self.model_id} (Kokoro)...")
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.model = load_model(self.model_id)
                logger.info("✨ Sistema Kokoro Listo.")

    def get_model(self):
        if self.model is None: self.load()
        return self.model

# =======================
# Audio Handler (Atomic)
# =======================

class AudioHandler:
    def __init__(self):
        self.current_process = None
        self.lock = threading.Lock()

    def play(self, audio_data: np.ndarray, sample_rate: int):
        threading.Thread(target=self._play_sync, args=(audio_data, sample_rate), daemon=True).start()

    def _play_sync(self, audio_data: np.ndarray, sample_rate: int):
        with self.lock:
            try:
                if self.current_process and self.current_process.poll() is None:
                    self.current_process.terminate()
                path = f"/tmp/tts_master_{time.time_ns()}.wav"
                data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
                with wave.open(path, 'wb') as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
                    wf.writeframes(data.tobytes())
                self.current_process = subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e: logger.error(f"Audio Error: {e}")

# =======================
# Inference Logic (Kokoro Only)
# =======================

def perform_inference(request: InferenceRequest, task_id: int):
    start_t = time.perf_counter()
    text = request.text.strip()
    
    # 🕵️ Detección de Idioma
    if request.lang:
        lang = request.lang
    else:
        lang, _ = langid.classify(text)
    
    logger.info(f"🎙️ Task: KOKORO | TaskID: {task_id} | Language: {lang.upper()}")

    mappings = GLOBAL_CONFIG.get("kokoro", {}).get("language_mapping", {})
    cfg = mappings.get(lang) or mappings.get("en", {})
    
    model = manager.get_model()
    audio_chunks = []

    try:
        v = request.voice or cfg.get("voice", "af_heart")
        l = cfg.get("lang_code", "a")
        results = model.generate(text=text, voice=v, lang_code=l)
        
        for res in results:
            # INTERRUPCIÓN RADICAL: Si el ID activo cambió, salimos ya.
            if manager.active_task_id != task_id:
                logger.info(f"🛑 Tarea {task_id} interrumpida por una más nueva.")
                return None
            audio_chunks.append(np.array(res.audio))
            mx.eval(mx.array(audio_chunks[-1])) # Periodic GPU pulse

        if not audio_chunks: return None

        final_audio = np.concatenate(audio_chunks)
        dt = time.perf_counter() - start_t
        rtf = round((len(final_audio)/model.sample_rate)/dt, 2)
        logger.info(f"✅ Success (T{task_id}): {round(dt, 2)}s | RTF: {rtf}")

        return {
            "status": "success", 
            "audio": final_audio, 
            "sr": model.sample_rate,
            "detected_lang": lang,
            "voice": v,
            "rtf": rtf
        }

    except Exception as e:
        logger.error(f"💥 Inference Fault (T{task_id}): {e}")
        return {"status": "error", "message": str(e)}
    finally:
        mx.clear_cache()

# =======================
# API (Queue Managed)
# =======================

# =======================
# API (Queue Managed)
# =======================

class QueueManager:
    def __init__(self, idle_timeout=1200):
        self.queue = asyncio.Queue(maxsize=1)
        self.executor = ThreadPoolExecutor(max_workers=1)
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
                req, task_id, fut = task
                try:
                    res = await asyncio.get_running_loop().run_in_executor(
                        self.executor, perform_inference, req, task_id
                    )
                    if not fut.done(): fut.set_result(res)
                except Exception as e:
                    if not fut.done(): fut.set_exception(e)
                finally: 
                    self.queue.task_done()
                    self.last_activity = time.time()
            except asyncio.TimeoutError: pass

    async def add_task(self, req: InferenceRequest):
        self.last_activity = time.time()
        new_id = time.time_ns()
        manager.active_task_id = new_id
        
        while not self.queue.empty():
            try:
                _, _, f = self.queue.get_nowait()
                if not f.done(): f.set_result(None)
                self.queue.task_done()
            except: break
        
        fut = asyncio.get_running_loop().create_future()
        await self.queue.put((req, new_id, fut))
        return await fut

app = FastAPI()
manager = None
audio_handler = AudioHandler()

# ⚙️ Configuración Dinámica
IDLE_TIMEOUT = GLOBAL_CONFIG.get("global_settings", {}).get("idle_timeout_seconds", 1200)
queue_mgr = QueueManager(idle_timeout=IDLE_TIMEOUT)

@app.on_event("startup")
async def start():
    logger.info(f"⏱️ Servidor FastAPI listo en {round(time.time() - queue_mgr.boot_time, 3)}s")
    asyncio.create_task(queue_mgr.worker())
    asyncio.create_task(queue_mgr.inactivity_monitor())

@app.get("/health")
async def health(): return {"status": "ok", "ready": manager.model is not None}

@app.post("/generate")
async def generate(request: InferenceRequest):
    try:
        res = await queue_mgr.add_task(request)
        if res is None: return {"status": "interrupted"}
        audio = res.pop("audio")
        sr = res.pop("sr")
        audio_handler.play(audio, sr)
        return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    start_time = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--port", type=int, default=8007)
    args = parser.parse_args()
    
    manager = ModelManager(args.model)
    
    import uvicorn
    logger.info("⚡️ Iniciando motor de servidor...")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="error")

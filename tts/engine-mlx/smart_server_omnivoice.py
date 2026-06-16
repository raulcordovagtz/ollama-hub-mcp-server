import time
import os
import threading
import json
import argparse
import subprocess
import logging
import asyncio
import wave
from typing import Optional
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
logger = logging.getLogger("OMNIVOICE_TTS")

PROJECT_DIR = "/Users/crotalo/desarrollo-local/server/tts/engine-mlx"
CONFIG_PATH = os.path.join(PROJECT_DIR, "server_config_omnivoice.json")
with open(CONFIG_PATH, "r") as f:
    GLOBAL_CONFIG = json.load(f)

class InferenceRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    language: Optional[str] = None
    ref_audio: Optional[str] = None
    num_steps: Optional[int] = 32
    guidance_scale: Optional[float] = 2.0

# =======================
# Model Manager (OmniVoice)
# =======================

class ModelManager:
    def __init__(self):
        self.model_path = GLOBAL_CONFIG["omnivoice"]["model_path"]
        self.model = None
        self.lock = threading.Lock()
        self.active_task_id = 0

    def load(self):
        with self.lock:
            if self.model is None:
                logger.info(f"🚀 Cargando OmniVoice desde {self.model_path}...")
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.model = load_model(self.model_path)
                logger.info(f"✨ OmniVoice MLX Listo. Sample Rate: {self.model.sample_rate}Hz")

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
                path = f"/tmp/omnivoice_tts_{time.time_ns()}.wav"
                data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
                with wave.open(path, 'wb') as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
                    wf.writeframes(data.tobytes())
                speed = str(GLOBAL_CONFIG.get("global_settings", {}).get("speed", 1.0))
                self.current_process = subprocess.Popen(["afplay", "-r", speed, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e: logger.error(f"Audio Error: {e}")

# =======================
# Reference Audio Resolver
# =======================

def resolve_ref_audio(request: InferenceRequest, lang: str) -> Optional[str]:
    """Resuelve el audio de referencia para voice cloning.
    Prioridad: request.ref_audio > voice_preset > language_mapping > None
    """
    ref_path = None

    # 1. Ruta explícita del request
    if request.ref_audio:
        ref_path = request.ref_audio

    # 2. Voice preset
    elif request.voice and request.voice in GLOBAL_CONFIG["omnivoice"].get("voice_presets", {}):
        preset = GLOBAL_CONFIG["omnivoice"]["voice_presets"][request.voice]
        ref_path = preset.get("ref_audio")

    # 3. Language mapping
    elif lang in GLOBAL_CONFIG["omnivoice"].get("language_mapping", {}):
        mapping = GLOBAL_CONFIG["omnivoice"]["language_mapping"][lang]
        ref_path = mapping.get("ref_audio")

    # Resolver rutas relativas contra PROJECT_DIR
    if ref_path and not ref_path.startswith("/"):
        ref_path = os.path.join(PROJECT_DIR, ref_path)

    # Verificar existencia
    if ref_path and os.path.isfile(ref_path):
        return ref_path
    elif ref_path:
        logger.warning(f"⚠️ Audio de referencia no encontrado: {ref_path}")

    return None

# =======================
# Inference Logic (OmniVoice)
# =======================

def perform_inference(request: InferenceRequest, task_id: int):
    start_t = time.perf_counter()
    text = request.text.strip()

    # Detección de Idioma
    if request.language:
        lang = request.language
    elif request.voice and request.voice in GLOBAL_CONFIG["omnivoice"].get("voice_presets", {}):
        lang = GLOBAL_CONFIG["omnivoice"]["voice_presets"][request.voice].get("language", "en")
    else:
        lang, _ = langid.classify(text)

    logger.info(f"🎙️ Task: OMNIVOICE | TaskID: {task_id} | Language: {lang.upper()}")

    model = manager.get_model()
    audio_chunks = []

    # Resolver audio de referencia para voice cloning
    ref_audio_path = resolve_ref_audio(request, lang)
    if ref_audio_path:
        logger.info(f"🎨 Voice Cloning activo: {ref_audio_path}")
    else:
        logger.info("🔊 Modo TTS estándar (sin clonación)")

    try:
        # OmniVoice generate API (from model inspection):
        # generate(text, duration_s, language, lang_code, instruct, ref_audio,
        #          ref_text, ref_audio_max_duration_s, num_steps, guidance_scale, ...)
        gen_kwargs = {
            "text": text,
            "language": lang,
            "num_steps": request.num_steps or 32,
            "guidance_scale": request.guidance_scale or 2.0,
        }
        if ref_audio_path:
            gen_kwargs["ref_audio"] = ref_audio_path

        results = model.generate(**gen_kwargs)

        for res in results:
            # INTERRUPCIÓN RADICAL: Si el ID activo cambió, salimos ya.
            if manager.active_task_id != task_id:
                logger.info(f"🛑 Tarea {task_id} interrumpida por una más nueva.")
                return None
            audio_chunks.append(np.array(res.audio))

        if not audio_chunks: return None

        final_audio = np.concatenate(audio_chunks)
        dt = time.perf_counter() - start_t
        rtf = round((len(final_audio) / model.sample_rate) / dt, 2)
        logger.info(f"✅ Success (T{task_id}): {round(dt, 2)}s | RTF: {rtf}")

        return {
            "status": "success",
            "audio": final_audio,
            "sr": model.sample_rate,
            "detected_lang": lang,
            "voice": request.voice or "default",
            "cloned": ref_audio_path is not None,
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

IDLE_TIMEOUT = GLOBAL_CONFIG.get("global_settings", {}).get("idle_timeout_seconds", 1200)
queue_mgr = QueueManager(idle_timeout=IDLE_TIMEOUT)

@app.on_event("startup")
async def start():
    logger.info(f"⏱️ Servidor OmniVoice listo en {round(time.time() - queue_mgr.boot_time, 3)}s")
    asyncio.create_task(queue_mgr.worker())
    asyncio.create_task(queue_mgr.inactivity_monitor())

@app.get("/health")
async def health(): return {"status": "ok", "engine": "omnivoice", "ready": manager.model is not None}

@app.get("/config")
async def get_config():
    """Devuelve la configuración de voice presets y language mappings."""
    return {
        "voice_presets": list(GLOBAL_CONFIG["omnivoice"].get("voice_presets", {}).keys()),
        "language_mapping": list(GLOBAL_CONFIG["omnivoice"].get("language_mapping", {}).keys()),
        "supported_languages": GLOBAL_CONFIG["omnivoice"].get("supported_languages", [])
    }

@app.post("/generate")
async def generate(request: InferenceRequest):
    try:
        res = await queue_mgr.add_task(request)
        if res is None: return {"status": "interrupted"}
        if res.get("status") == "error": return res
        audio = res.pop("audio")
        sr = res.pop("sr")
        audio_handler.play(audio, sr)
        return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniVoice MLX TTS Server")
    parser.add_argument("--port", type=int, default=8009)
    args = parser.parse_args()

    manager = ModelManager()

    import uvicorn
    logger.info("⚡️ Iniciando motor OmniVoice MLX...")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="error")

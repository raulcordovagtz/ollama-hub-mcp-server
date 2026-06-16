import time
import os
import threading
import json
import argparse
import subprocess
import logging
import asyncio
import wave
import io
import unicodedata
import re
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from supertonic import TTS

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SUPERTONIC_SERVER")

# We simulate the config reading logic
GLOBAL_CONFIG = {
    "global_settings": {
        "speed": 1.0,
        "idle_timeout_seconds": 1200
    }
}

class InferenceRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    prompt_audio_path: Optional[str] = None
    max_new_frames: Optional[int] = 375 # Ignored in Supertonic

class OpenAISpeechRequest(BaseModel):
    model: str
    input: str
    voice: Optional[str] = "alloy"
    response_format: Optional[str] = "wav"
    speed: Optional[float] = 1.0

# =======================
# Model Manager
# =======================

class ModelManager:
    def __init__(self):
        self.tts = None
        self.lock = threading.Lock()
        self.active_task_id = 0
        self.assets_dir = os.path.join(os.path.dirname(__file__), "assets")

    def load(self):
        with self.lock:
            if self.tts is None:
                logger.info("🚀 Cargando Supertonic 3 (Local)...")
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.tts = TTS(auto_download=False)
                logger.info("✨ Sistema Supertonic TTS Listo.")

    def get_service(self):
        if self.tts is None: self.load()
        return self.tts

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
                path = f"/tmp/supertonic_{time.time_ns()}.wav"
                
                # audio_data from supertonic is (1, num_samples), float32
                data = (np.clip(audio_data.squeeze(), -1.0, 1.0) * 32767).astype(np.int16)
                
                with wave.open(path, 'wb') as wf:
                    wf.setnchannels(1) # mono output from supertonic
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(data.tobytes())
                
                speed = str(GLOBAL_CONFIG.get("global_settings", {}).get("speed", 1.0))
                # Bloquear hasta que termine para poder borrar el archivo (residuo)
                subprocess.run(["afplay", "-r", speed, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    os.remove(path)
                except: pass
            except Exception as e: logger.error(f"Audio Error: {e}")

# =======================
# Inference Logic
# =======================

def get_voice_and_lang(text: str, voice_str: str):
    v_name = "F1"
    lang = "na"
    
    v_lower = voice_str.lower() if voice_str else ""
    
    if v_lower == "auto":
        try:
            import langdetect
            # Attempt to detect language
            det = langdetect.detect(text)
            if det == "en": return "F1", "en"
            elif det == "es": return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "preset_voice_f.json"), "es"
            elif det == "fr": return "F5", "fr"
            elif det == "it": return "F2", "it" # Italian uses F2
            else: return "F1", "na"
        except:
            return "F1", "na"
            
    if "en" in v_lower or "english" in v_lower:
        v_name = "F1"
        lang = "en"
    elif "es" in v_lower or "spanish" in v_lower or "español" in v_lower:
        v_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "preset_voice_f.json")
        lang = "es"
    elif "fr" in v_lower or "french" in v_lower or "frances" in v_lower or "français" in v_lower:
        v_name = "F5"
        lang = "fr"
    elif "it" in v_lower or "italian" in v_lower or "italiano" in v_lower:
        v_name = "F2"
        lang = "it"
    
    return v_name, lang

def strip_format_chars(text):
    return "".join(
        ch for ch in text
        if unicodedata.category(ch) != "Cf"
    )

def math_to_speech(expr):
    replacements = {
        r"\log_2": "logaritmo en base dos",
        "=": " igual a ",
        "^2": " al cuadrado",
    }
    for k, v in replacements.items():
        expr = expr.replace(k, v)
    return expr

def markdown_math_to_tts(text):
    return re.sub(
        r"\$(.*?)\$",
        lambda m: math_to_speech(m.group(1)),
        text
    )

def perform_inference(request: InferenceRequest, task_id: int):
    start_t = time.perf_counter()
    
    text = request.text.strip()
    text = markdown_math_to_tts(text)
    text = strip_format_chars(text)
    
    v_name, lang = get_voice_and_lang(text, request.voice)
    
    # Allow overriding with an explicit custom path
    if request.voice and request.voice.endswith(".json") and os.path.isfile(request.voice):
        v_name = request.voice
        lang = "es"
        
    is_custom = v_name.endswith(".json") and os.path.isfile(v_name)
        
    logger.info(f"🎙️ Task: Supertonic | TaskID: {task_id} | ReqVoice: {request.voice} -> Preset: {v_name} | Lang: {lang}")

    tts_engine = manager.get_service()
    
    try:
        if is_custom:
            style = tts_engine.get_voice_style_from_path(v_name)
        else:
            style = tts_engine.get_voice_style(voice_name=v_name)
        
        # Supertonic synthesis
        speed_factor = 1.2 if lang == "es" else 1.0
        
        wav, duration = tts_engine.synthesize(
            text=text,
            lang=lang,
            voice_style=style,
            total_steps=8,
            speed=speed_factor
        )
        
        if manager.active_task_id != task_id:
            logger.info(f"🛑 Tarea {task_id} interrumpida.")
            return None

        dt = time.perf_counter() - start_t
        rtf = round(float(duration[0])/dt, 2)
        logger.info(f"✅ Success (T{task_id}): {round(dt, 2)}s | Gen duration: {float(duration[0]):.2f}s | RTF: {rtf}")

        return {
            "status": "success", 
            "audio": wav, 
            "sr": 44100, # Supertonic default
            "voice": v_name,
            "rtf": rtf
        }

    except Exception as e:
        logger.error(f"💥 Inference Fault (T{task_id}): {e}")
        return {"status": "error", "message": str(e)}

# =======================
# API (Queue Managed)
# =======================

class QueueManager:
    def __init__(self, idle_timeout=1200):
        self.queue = asyncio.Queue(maxsize=1)
        # Supertonic is single-threaded CPU inference primarily
        self.last_activity = time.time()
        self.idle_timeout = idle_timeout
        self.boot_time = time.time()

    async def inactivity_monitor(self):
        logger.info(f"⏳ Monitor de inactividad iniciado (Timeout: {self.idle_timeout}s)")
        while True:
            await asyncio.sleep(10)
            elapsed = time.time() - self.last_activity
            if elapsed > self.idle_timeout:
                logger.warning(f"😴 Inactividad detectada ({round(elapsed, 1)}s). Apagando servidor completamente...")
                import os
                os._exit(0)

    async def worker(self):
        while True:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                req, task_id, fut = task
                try:
                    res = await asyncio.to_thread(perform_inference, req, task_id)
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

IDLE_TIMEOUT = GLOBAL_CONFIG["global_settings"]["idle_timeout_seconds"]
queue_mgr = QueueManager(idle_timeout=IDLE_TIMEOUT)

@app.on_event("startup")
async def start():
    logger.info(f"⏱️ Servidor Supertonic listo en {round(time.time() - queue_mgr.boot_time, 3)}s")
    asyncio.create_task(queue_mgr.worker())
    asyncio.create_task(queue_mgr.inactivity_monitor())

@app.get("/health")
async def health(): return {"status": "ok", "ready": manager.tts is not None}

@app.post("/generate")
async def generate(request: InferenceRequest):
    try:
        res = await queue_mgr.add_task(request)
        if res is None: return {"status": "interrupted"}
        if res["status"] == "error": return res
        audio = res.pop("audio")
        sr = res.pop("sr")
        audio_handler.play(audio, sr)
        return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/audio/speech")
async def openai_speech(request: OpenAISpeechRequest):
    try:
        req = InferenceRequest(text=request.input, voice=request.voice)
        res = await queue_mgr.add_task(req)
        if res is None: return Response(status_code=499, content="Interrupted")
        if res["status"] == "error": raise HTTPException(status_code=500, detail=res.get("message", "Error"))
        
        audio_data = res.pop("audio")
        sr = res.pop("sr")
        
        # Reproducción automática en el servidor (como lo hacía MOSS), 
        # para que el usuario no tenga que reproducirlo en Hermes manualmente
        audio_handler.play(audio_data, sr)
        
        data = (np.clip(audio_data.squeeze(), -1.0, 1.0) * 32767).astype(np.int16)
        
        # Usar ffmpeg para convertir al vuelo a MP3, ya que Hermes lo exige para el proveedor OpenAI
        import subprocess
        process = subprocess.Popen(
            ['/opt/homebrew/bin/ffmpeg', '-y', '-f', 's16le', '-ar', str(sr), '-ac', '1', '-i', 'pipe:0', '-f', 'mp3', '-b:a', '128k', 'pipe:1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        mp3_bytes, _ = process.communicate(input=data.tobytes())
            
        return Response(content=mp3_bytes, media_type="audio/mpeg")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()
    
    manager = ModelManager()
    
    import uvicorn
    logger.info(f"⚡️ Iniciando motor de servidor Supertonic en puerto {args.port}...")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="error")

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

import numpy as np
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from pocket_tts import TTSModel

# =======================
# Logging & Configuration
# =======================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("POCKET_TTS_SERVER")

IDLE_TIMEOUT = 1200 # 20 minutos

class InferenceRequest(BaseModel):
    text: str
    voice: Optional[str] = None

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
        self.models = {}
        self.lock = threading.Lock()
        self.active_task_id = 0
        self.assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self.config_path = os.path.join(self.assets_dir, "voices_config.json")
        self.voices_config = {}
        self.voice_states = {}
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.voices_config = json.load(f)
        except Exception as e:
            logger.error(f"No se pudo cargar voices_config.json: {e}")
            self.voices_config = {}

    def load(self, language: str):
        lang_str_map = {"en": "english", "es": "spanish_24l", "fr": "french_24l", "it": "italian_24l"}
        lang_arg = lang_str_map.get(language, "english")
        
        with self.lock:
            if lang_arg not in self.models:
                logger.info(f"🚀 Cargando Pocket TTS ({lang_arg})...")
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.models[lang_arg] = TTSModel.load_model(language=lang_arg)
                logger.info(f"✨ Sistema Pocket TTS ({lang_arg}) Listo.")
            return self.models[lang_arg]

    def get_service(self, language: str):
        lang_str_map = {"en": "english", "es": "spanish_24l", "fr": "french_24l", "it": "italian_24l"}
        lang_arg = lang_str_map.get(language, "english")
        
        if lang_arg not in self.models:
            self.load(language)
        return self.models[lang_arg]

    def get_voice_state(self, voice_name_or_path: str, language: str):
        cache_key = f"{language}_{voice_name_or_path}"
        if cache_key in self.voice_states:
            return self.voice_states[cache_key]
        
        tts = self.get_service(language)
        state = tts.get_state_for_audio_prompt(voice_name_or_path)
        self.voice_states[cache_key] = state
        return state

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
                path = f"/tmp/pockettts_{time.time_ns()}.wav"
                
                # audio_data is a numpy array from torch tensor PCM data (float32, -1 to 1).
                # Convert to int16 before saving to wav.
                data = (np.clip(audio_data.squeeze(), -1.0, 1.0) * 32767).astype(np.int16) if audio_data.dtype != np.int16 else audio_data
                
                with wave.open(path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(data.tobytes())
                
                # Play audio locally
                subprocess.run(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    os.remove(path)
                except: pass
            except Exception as e: logger.error(f"Audio Error: {e}")

# =======================
# Inference Logic
# =======================

def get_voice_and_lang(text: str, voice_str: str, config: dict):
    # Detect language basic
    lang = "en"
    try:
        import langdetect
        det = langdetect.detect(text)
        if det in ["en", "es", "fr", "it"]:
            lang = det
    except:
        pass
        
    v_lower = voice_str.lower() if voice_str else ""
    
    # Check if voice maps explicitly to alloy
    if v_lower == "alloy":
        target = config.get(lang, {}).get("alloy", config.get(lang, {}).get("default", "alba"))
        return target, lang
        
    # Check if a custom file was requested or default for language
    target = config.get(lang, {}).get("default", "alba")
    
    if v_lower == "custom":
        target = config.get(lang, {}).get("custom", target)

    return target, lang

def perform_inference(request: InferenceRequest, task_id: int):
    start_t = time.perf_counter()
    text = request.text.strip()
    
    v_target, lang = get_voice_and_lang(text, request.voice, manager.voices_config)
    
    logger.info(f"🎙️ Task: Pocket TTS | TaskID: {task_id} | ReqVoice: {request.voice} -> Target: {v_target} | Lang: {lang}")

    tts_engine = manager.get_service(lang)
    
    try:
        voice_state = manager.get_voice_state(v_target, lang)
        
        # Generar audio con Pocket TTS
        audio = tts_engine.generate_audio(voice_state, text)
        audio_np = audio.numpy()
        
        if manager.active_task_id != task_id:
            logger.info(f"🛑 Tarea {task_id} interrumpida.")
            return None

        dt = time.perf_counter() - start_t
        # Estimación de RTF
        duration = len(audio_np) / tts_engine.sample_rate
        rtf = round(duration/dt, 2)
        logger.info(f"✅ Success (T{task_id}): {round(dt, 2)}s | Gen duration: {duration:.2f}s | Speedup: {rtf}x")

        return {
            "status": "success", 
            "audio": audio_np, 
            "sr": tts_engine.sample_rate, 
            "voice": v_target,
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
        self.last_activity = time.time()
        self.idle_timeout = idle_timeout
        self.boot_time = time.time()

    async def inactivity_monitor(self):
        logger.info(f"⏳ Monitor de inactividad iniciado (Timeout: {self.idle_timeout}s)")
        while True:
            await asyncio.sleep(10)
            elapsed = time.time() - self.last_activity
            if elapsed > self.idle_timeout:
                logger.warning(f"😴 Inactividad detectada ({round(elapsed, 1)}s). Apagando servidor completamente (Zero-Residues)...")
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
queue_mgr = QueueManager(idle_timeout=IDLE_TIMEOUT)

@app.on_event("startup")
async def start():
    logger.info(f"⏱️ Servidor Pocket TTS listo en {round(time.time() - queue_mgr.boot_time, 3)}s")
    asyncio.create_task(queue_mgr.worker())
    asyncio.create_task(queue_mgr.inactivity_monitor())

@app.get("/health")
async def health(): return {"status": "ok", "ready": True}

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
        
        # Reproducción local automática
        audio_handler.play(audio_data, sr)
        
        # Escalar Float32 a Int16 para ffmpeg
        data = (np.clip(audio_data.squeeze(), -1.0, 1.0) * 32767).astype(np.int16) if audio_data.dtype != np.int16 else audio_data
        
        # FFmpeg para mp3 (compatible con OpenAI)
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
    parser.add_argument("--port", type=int, default=8013)
    args = parser.parse_args()
    
    manager = ModelManager()
    
    import uvicorn
    logger.info(f"⚡️ Iniciando servidor Pocket TTS en puerto {args.port}...")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="error")

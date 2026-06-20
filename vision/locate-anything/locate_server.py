#!/usr/bin/env python3
"""
LocateAnything Smart Server — v1.0
FastAPI HTTP server (Puerto 8014) que sirve nvidia/LocateAnything-3B
sobre Apple Silicon (MPS). Muerto por defecto, vive bajo demanda.

Protocolo:
  POST /locate  — {image_path, prompt, task, categories}
  GET  /health  — estado del servidor y del worker
  POST /shutdown — apagado limpio (usado por idle timer)

Arquitectura de desactivación:
  El servidor se apaga automáticamente tras IDLE_TIMEOUT_SECONDS de
  inactividad. El proxy STDIO (locate_smart_client.py) lo re-despierta
  si es necesario en la siguiente llamada.

Hardware objetivo: Apple Silicon MPS (M1/M2/M3/M4).
NO se provee fallback a CPU — un modelo 3B en CPU no es operable.
"""

import os
# Fix macOS OpenMP conflict between PyTorch and OpenCV (libomp.dylib duplicated)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import time
import os
import sys
import json
import logging
import asyncio
import uuid
import base64
import signal
import threading
import re
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import torch
from PIL import Image, ImageDraw, ImageFont
import io

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import uvicorn

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("LOCATE_SERVER")

# =============================================================================
# Constantes
# =============================================================================

MODEL_ID = "nvidia/LocateAnything-3B"
PORT = 8014
IDLE_TIMEOUT_SECONDS = 20 * 60  # 20 minutos
LOG_PATH = "/Users/crotalo/desarrollo-local/server/logs/locate/inferences.log"
OUTPUT_DIR = "/Users/crotalo/desarrollo-local/server/vision/locate-anything/outputs"

# Colores para recuadros (ciclo de colores distinguibles)
BOX_COLORS = [
    "#FF4444", "#44AAFF", "#44FF88", "#FFB344", "#CC44FF",
    "#FF44CC", "#44FFFF", "#FFFF44", "#FF8844", "#88FF44",
]

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# Validación MPS estricta
# =============================================================================

def get_mps_device() -> torch.device:
    """
    Retorna el dispositivo MPS. Falla explícitamente si MPS no está disponible.
    Este servidor está diseñado exclusivamente para Apple Silicon.
    """
    if not torch.backends.mps.is_available():
        if not torch.backends.mps.is_built():
            raise RuntimeError(
                "❌ PyTorch no fue compilado con soporte MPS. "
                "Instala PyTorch >= 2.0 para macOS desde https://pytorch.org/get-started/locally/"
            )
        raise RuntimeError(
            "❌ MPS no está disponible en este sistema. "
            "Este servidor requiere Apple Silicon (M1/M2/M3/M4)."
        )
    return torch.device("mps")

# =============================================================================
# Worker LocateAnything (adaptado para MPS)
# =============================================================================

class LocateAnythingWorkerMPS:
    """
    Worker que carga el modelo LocateAnything-3B una sola vez en MPS
    y sirve consultas de localización visual.

    Diferencias vs código original de NVIDIA:
      - device: "mps" (no "cuda")
      - dtype: torch.float16 (bfloat16 no estable en MPS para todos los ops)
      - Carga modelo en CPU primero, luego .to(device) (evita OOM en MPS)
      - Sin la_flash backend (CUDA-only) — usa sdpa de PyTorch
    """

    def __init__(self, model_path: str = MODEL_ID):
        from transformers import AutoModel, AutoTokenizer, AutoProcessor

        self.device = get_mps_device()
        # float16: estable en MPS. bfloat16 puede causar NaN en algunas ops de VLM.
        self.dtype = torch.float16

        logger.info(f"🔋 Dispositivo: {self.device} (Apple Silicon MPS)")
        logger.info(f"📦 Cargando modelo {model_path}...")
        logger.info("⏳ Primera carga ~20-40s. Cargando en CPU primero, luego pasando a MPS...")

        # Carga en CPU primero, luego movemos a MPS de una vez
        # (evita fragmentación de memoria en MPS con modelos grandes)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(
            model_path,
            torch_dtype=self.dtype,
            trust_remote_code=True,
        )
        self.model = self.model.to(self.device).eval()

        logger.info(f"✅ Modelo listo en {self.device}")

    @torch.no_grad()
    def predict(
        self,
        image: Image.Image,
        question: str,
        generation_mode: str = "hybrid",
        max_new_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": question},
                ],
            }
        ]

        text = self.processor.py_apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        images, videos = self.processor.process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=images, videos=videos, return_tensors="pt"
        ).to(self.device)

        # Convertir pixel_values explícitamente a float16
        pixel_values = inputs["pixel_values"].to(self.dtype)
        input_ids = inputs["input_ids"]
        image_grid_hws = inputs.get("image_grid_hws", None)

        response = self.model.generate(
            pixel_values=pixel_values,
            input_ids=input_ids,
            attention_mask=inputs["attention_mask"],
            image_grid_hws=image_grid_hws,
            tokenizer=self.tokenizer,
            max_new_tokens=max_new_tokens,
            use_cache=True,
            generation_mode=generation_mode,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
            verbose=False,
        )

        answer = response[0] if isinstance(response, tuple) else response
        return {"answer": answer}

    # ---- Métodos de conveniencia ----

    def detect(self, image: Image.Image, categories: list[str], **kwargs) -> dict:
        cats = "</c>".join(categories)
        prompt = f"Locate all the instances that matches the following description: {cats}."
        return self.predict(image, prompt, **kwargs)

    def ground_multi(self, image: Image.Image, phrase: str, **kwargs) -> dict:
        prompt = f"Locate all the instances that match the following description: {phrase}."
        return self.predict(image, prompt, **kwargs)

    def ground_single(self, image: Image.Image, phrase: str, **kwargs) -> dict:
        prompt = f"Locate a single instance that matches the following description: {phrase}."
        return self.predict(image, prompt, **kwargs)

    def detect_text(self, image: Image.Image, **kwargs) -> dict:
        return self.predict(image, "Detect all the text in box format.", **kwargs)

    def ground_gui(self, image: Image.Image, phrase: str, **kwargs) -> dict:
        prompt = f"Locate the region that matches the following description: {phrase}."
        return self.predict(image, prompt, **kwargs)

    def point(self, image: Image.Image, phrase: str, **kwargs) -> dict:
        return self.predict(image, f"Point to: {phrase}.", **kwargs)

    # ---- Parsers de salida ----

    @staticmethod
    def parse_boxes(answer: str, image_width: int, image_height: int) -> list[dict]:
        """
        Convierte los tokens de coordenadas normalizadas [0, 1000] a píxeles.
        Formato del modelo: <box><x1><y1><x2><y2></box>
        """
        boxes = []
        for m in re.finditer(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>", answer):
            x1, y1, x2, y2 = [int(g) for g in m.groups()]
            boxes.append(
                {
                    "x1": round(x1 / 1000 * image_width),
                    "y1": round(y1 / 1000 * image_height),
                    "x2": round(x2 / 1000 * image_width),
                    "y2": round(y2 / 1000 * image_height),
                }
            )
        return boxes

    @staticmethod
    def parse_points(answer: str, image_width: int, image_height: int) -> list[dict]:
        points = []
        for m in re.finditer(r"<box><(\d+)><(\d+)></box>", answer):
            x, y = int(m.group(1)), int(m.group(2))
            points.append(
                {
                    "x": round(x / 1000 * image_width),
                    "y": round(y / 1000 * image_height),
                }
            )
        return points


# =============================================================================
# Estado global del Worker (lazy init)
# =============================================================================

_worker: Optional[LocateAnythingWorkerMPS] = None
_worker_lock = threading.Lock()


def get_worker() -> LocateAnythingWorkerMPS:
    global _worker
    if _worker is None:
        with _worker_lock:
            if _worker is None:
                _worker = LocateAnythingWorkerMPS()
    return _worker


# =============================================================================
# Idle Shutdown Timer
# =============================================================================

class IdleShutdownTimer:
    """
    Reinicia el countdown de inactividad en cada inferencia.
    Al expirar, apaga el proceso limpiamente (os._exit, igual que TTS).
    """

    def __init__(self, timeout: int = IDLE_TIMEOUT_SECONDS):
        self.timeout = timeout
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def reset(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.timeout, self._shutdown)
            self._timer.daemon = True
            self._timer.start()
        logger.info(f"⏱️  Idle timer reiniciado. Apagado automático en {self.timeout // 60} min de inactividad.")

    def _shutdown(self):
        logger.info("💤 Timeout de inactividad alcanzado. Cerrando servidor...")
        os._exit(0)

    def cancel(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()


idle_timer = IdleShutdownTimer()

# =============================================================================
# Pydantic Models
# =============================================================================

SUPPORTED_TASKS = {"detect", "ground", "ground_single", "text", "gui", "point"}


class LocateRequest(BaseModel):
    image_path: str
    prompt: str
    task: str = "ground"
    categories: Optional[list[str]] = None  # solo para task="detect"
    generation_mode: str = "hybrid"


class LocateResponse(BaseModel):
    status: str
    task_id: str
    task: str
    prompt_translated: str
    boxes: list[dict] = []
    points: list[dict] = []
    raw_answer: str = ""
    annotated_image_path: Optional[str] = None
    summary: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None


# =============================================================================
# Traducción automática de prompts
# =============================================================================

def translate_to_english(text: str) -> str:
    """
    Traduce el prompt al inglés si no está ya en inglés.
    Usa deep-translator (GoogleTranslator, sin API key).
    Si falla, retorna el texto original para no bloquear la inferencia.
    """
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        if translated and translated != text:
            logger.info(f"🌐 Prompt traducido: '{text}' → '{translated}'")
        return translated or text
    except Exception as e:
        logger.warning(f"⚠️  Traducción falló ({e}), usando prompt original: '{text}'")
        return text


# =============================================================================
# Dibujado de recuadros sobre imagen
# =============================================================================

def annotate_image(
    image: Image.Image,
    boxes: list[dict],
    points: list[dict],
    prompt: str,
    task_id: str,
) -> str:
    """
    Dibuja recuadros numerados y puntos sobre la imagen.
    Guarda la imagen en disco y retorna la ruta absoluta.
    """
    # Usar una copia para no modificar el original
    annotated = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw = ImageDraw.Draw(annotated)

    # Intentar cargar fuente del sistema, fallback a default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    for i, box in enumerate(boxes):
        color_hex = BOX_COLORS[i % len(BOX_COLORS)]
        # Convertir hex a RGBA
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        color_rgba = (r, g, b, 200)
        color_solid = (r, g, b, 255)

        x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]

        # Recuadro semi-transparente
        draw_overlay.rectangle([x1, y1, x2, y2], outline=color_solid, width=3)
        draw_overlay.rectangle(
            [x1, y1, x2, min(y1 + 28, y2)],
            fill=(r, g, b, 160),
        )

        # Etiqueta numérica
        label = f" #{i + 1}"
        draw_overlay.text((x1 + 4, y1 + 4), label, fill=(255, 255, 255, 255), font=font)

    # Merge overlay
    annotated = Image.alpha_composite(annotated, overlay)

    # Dibujar puntos (si los hay)
    draw_final = ImageDraw.Draw(annotated)
    for i, pt in enumerate(points):
        color_hex = BOX_COLORS[i % len(BOX_COLORS)]
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        x, y = pt["x"], pt["y"]
        radius = 8
        draw_final.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(r, g, b, 220),
            outline=(255, 255, 255, 255),
            width=2,
        )
        draw_final.text((x + radius + 2, y - 8), f"#{i + 1}", fill=(255, 255, 255, 255), font=font_small)

    # Guardar en disco
    annotated_rgb = annotated.convert("RGB")
    file_name = f"{task_id}.jpg"
    out_path = os.path.join(OUTPUT_DIR, file_name)
    annotated_rgb.save(out_path, format="JPEG", quality=85)
    return out_path


# =============================================================================
# Lógica de inferencia
# =============================================================================

def run_locate(req: LocateRequest, task_id: str) -> LocateResponse:
    start_t = time.perf_counter()

    # Traducción automática
    prompt_en = translate_to_english(req.prompt)

    try:
        # Cargar imagen
        if not os.path.isabs(req.image_path):
            raise ValueError(f"image_path debe ser una ruta absoluta: '{req.image_path}'")
        if not os.path.exists(req.image_path):
            raise FileNotFoundError(f"Imagen no encontrada: '{req.image_path}'")

        image = Image.open(req.image_path).convert("RGB")
        w, h = image.size
        logger.info(f"🖼️  [{task_id}] Imagen: {req.image_path} ({w}x{h}) | Task: {req.task} | Prompt: '{prompt_en}'")

        worker = get_worker()
        task = req.task

        if task not in SUPPORTED_TASKS:
            raise ValueError(f"Task desconocida: '{task}'. Soportadas: {SUPPORTED_TASKS}")

        # Dispatch por tarea
        if task == "detect":
            cats = req.categories or [prompt_en]
            result = worker.detect(image, cats, generation_mode=req.generation_mode)
        elif task == "ground":
            result = worker.ground_multi(image, prompt_en, generation_mode=req.generation_mode)
        elif task == "ground_single":
            result = worker.ground_single(image, prompt_en, generation_mode=req.generation_mode)
        elif task == "text":
            result = worker.detect_text(image, generation_mode=req.generation_mode)
        elif task == "gui":
            result = worker.ground_gui(image, prompt_en, generation_mode=req.generation_mode)
        elif task == "point":
            result = worker.point(image, prompt_en, generation_mode=req.generation_mode)

        raw_answer = result.get("answer", "")
        logger.info(f"🔍 [{task_id}] Respuesta raw: {raw_answer[:200]}...")

        # Parsear coordenadas
        boxes = LocateAnythingWorkerMPS.parse_boxes(raw_answer, w, h)
        points = LocateAnythingWorkerMPS.parse_points(raw_answer, w, h)

        # Anotar imagen y guardarla
        annotated_path = annotate_image(image, boxes, points, prompt_en, task_id)

        # Resumen legible
        if boxes:
            lines = [f"#{i+1}: ({b['x1']}, {b['y1']}) → ({b['x2']}, {b['y2']})" for i, b in enumerate(boxes)]
            summary = f"Encontrados {len(boxes)} recuadro(s) para '{req.prompt}':\n" + "\n".join(lines)
        elif points:
            lines = [f"#{i+1}: ({p['x']}, {p['y']})" for i, p in enumerate(points)]
            summary = f"Encontrados {len(points)} punto(s) para '{req.prompt}':\n" + "\n".join(lines)
        else:
            summary = f"No se encontraron elementos para '{req.prompt}' en la imagen."

        duration = time.perf_counter() - start_t
        logger.info(f"✅ [{task_id}] {len(boxes)} boxes, {len(points)} points — {duration:.1f}s")

        _log_inference(task_id, req, prompt_en, "SUCCESS", duration, boxes, points)

        return LocateResponse(
            status="success",
            task_id=task_id,
            task=task,
            prompt_translated=prompt_en,
            boxes=boxes,
            points=points,
            raw_answer=raw_answer,
            annotated_image_path=annotated_path,
            summary=summary,
            duration_seconds=round(duration, 2),
        )

    except Exception as e:
        duration = time.perf_counter() - start_t
        logger.error(f"💥 [{task_id}] Error: {e}")
        _log_inference(task_id, req, prompt_en, "ERROR", duration, [], [], str(e))
        return LocateResponse(
            status="error",
            task_id=task_id,
            task=req.task,
            prompt_translated=prompt_en,
            summary=f"Error al procesar imagen: {e}",
            duration_seconds=round(duration, 2),
            error=str(e),
        )


def _log_inference(task_id, req, prompt_en, status, duration, boxes, points, error=""):
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "task": req.task,
        "prompt_original": req.prompt,
        "prompt_en": prompt_en,
        "image_path": req.image_path,
        "status": status,
        "boxes_found": len(boxes),
        "points_found": len(points),
        "duration_s": round(duration, 2),
        "error": error,
    }
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"No se pudo escribir log: {e}")


# =============================================================================
# Queue Manager (serialización de tareas — protección de hardware)
# =============================================================================

class LocateQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="LocateWorker")
        self._loop_task = None
        self.is_processing = False
        self.current_task_id = None

    async def worker(self):
        logger.info("👷 Queue worker iniciado.")
        while True:
            req, task_id, fut = await self.queue.get()
            if fut.cancelled():
                self.queue.task_done()
                continue
            self.is_processing = True
            self.current_task_id = task_id
            try:
                res = await asyncio.get_running_loop().run_in_executor(
                    self.executor, run_locate, req, task_id
                )
                if not fut.cancelled():
                    fut.set_result(res)
            except Exception as e:
                if not fut.cancelled():
                    fut.set_exception(e)
            finally:
                self.queue.task_done()
                self.is_processing = False
                self.current_task_id = None
                idle_timer.reset()

    def start(self):
        self._loop_task = asyncio.create_task(self.worker())

    def stop(self):
        if self._loop_task:
            self._loop_task.cancel()
        self.executor.shutdown(wait=False)


queue_mgr = LocateQueueManager()

# =============================================================================
# FastAPI App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    queue_mgr.start()
    idle_timer.reset()  # Iniciar countdown desde el arranque
    logger.info(f"🚀 LocateAnything Server v1.0 — Puerto {PORT} — MPS ready.")
    yield
    idle_timer.cancel()
    queue_mgr.stop()
    logger.info("🛑 Servidor detenido.")


app = FastAPI(
    title="LocateAnything MCP Server",
    description="Visual grounding server powered by nvidia/LocateAnything-3B on Apple Silicon MPS",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": "mps",
        "is_processing": queue_mgr.is_processing,
        "current_task": queue_mgr.current_task_id,
        "queue_size": queue_mgr.queue.qsize(),
        "idle_timeout_min": IDLE_TIMEOUT_SECONDS // 60,
    }


@app.post("/locate", response_model=LocateResponse)
async def locate(req: LocateRequest):
    if req.task not in SUPPORTED_TASKS:
        raise HTTPException(status_code=400, detail=f"Task inválida: '{req.task}'. Soportadas: {list(SUPPORTED_TASKS)}")

    task_id = str(uuid.uuid4())[:8]
    fut = asyncio.get_running_loop().create_future()

    try:
        await asyncio.wait_for(queue_mgr.queue.put((req, task_id, fut)), timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Servidor ocupado, cola llena. Intenta más tarde.")

    try:
        return await fut
    except asyncio.CancelledError:
        logger.info(f"⚠️ Request {task_id} cancelado por cliente.")
        raise


@app.post("/shutdown")
async def shutdown():
    """Apagado limpio para uso del idle timer o scripts externos."""
    logger.info("🛑 Apagado solicitado via /shutdown")
    asyncio.create_task(_delayed_exit())
    return {"status": "shutting_down"}


async def _delayed_exit():
    await asyncio.sleep(0.5)
    os._exit(0)


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    def handle_signal(sig, frame):
        logger.info(f"Señal {sig} recibida. Cerrando...")
        idle_timer.cancel()
        queue_mgr.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=PORT,
        log_level="warning",  # uvicorn silencioso, logging propio activo
        timeout_keep_alive=30,
        limit_concurrency=20,
    )
    server = uvicorn.Server(config)
    server.run()

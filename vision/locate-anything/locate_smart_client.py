#!/usr/bin/env python3
"""
LocateAnything Smart Client — v1.0
Proxy STDIO → HTTP que actúa como servidor MCP para clientes como
LM Studio, Antigravity IDE, Claude Desktop, etc.

Protocolo:
  - Entrada:  JSON-RPC 2.0 por STDIN (protocolo MCP estándar)
  - Salida:   JSON-RPC 2.0 por STDOUT
  - Backend:  HTTP POST a http://localhost:8014/locate

Filosofía Cold Start:
  1. Verifica si el servidor HTTP está vivo (GET /health, timeout 1s)
  2. Si está muerto → lanza locate_server.py en background con nohup
  3. Espera hasta 90s a que el servidor esté listo (carga del modelo ~20-40s)
  4. Redirige las peticiones JSON-RPC al servidor HTTP

Herramienta MCP expuesta:
  - locate_objects: Localiza elementos en imágenes con bounding boxes

Cero dependencias externas — solo stdlib de Python.
"""

import sys
import os
import time
import json
import threading
import urllib.request
import urllib.error

# =============================================================================
# Configuración
# =============================================================================

PORT = 8014
BASE_URL = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BASE_URL}/health"
LOCATE_URL = f"{BASE_URL}/locate"

# Ruta al servidor (relativa al directorio de este script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, "locate_server.py")
# Entorno conda
VENV_PYTHON = "/opt/miniconda3/envs/locate-anything/bin/python3"
LOG_FILE = os.path.expanduser("~/locate_server_boot.log")

# =============================================================================
# Herramientas MCP disponibles
# =============================================================================

MCP_TOOLS = [
    {
        "name": "locate_objects",
        "description": (
            "Identifies and localizes objects or elements in an image using natural language "
            "via nvidia/LocateAnything-3B running locally on Apple Silicon MPS. "
            "Accepts prompts in any language (auto-translated to English). "
            "Returns numbered bounding boxes, pixel coordinates, and an annotated image with drawn rectangles. "
            "Supports: object detection, phrase grounding, GUI element grounding, text detection, pointing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Absolute path to the image file on disk (e.g. /Users/you/photo.jpg)",
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "What to locate. Examples: 'person', 'botón de enviar', 'red car', "
                        "'el texto que dice hola', 'submit button', 'all cats'. "
                        "Prompts in any language are accepted."
                    ),
                },
                "task": {
                    "type": "string",
                    "enum": ["detect", "ground", "ground_single", "text", "gui", "point"],
                    "default": "ground",
                    "description": (
                        "Detection mode: "
                        "'detect' = multi-category object detection (use with categories field), "
                        "'ground' = phrase grounding multiple instances (default), "
                        "'ground_single' = phrase grounding single instance, "
                        "'text' = scene text detection (ignores prompt), "
                        "'gui' = GUI element grounding (for screenshots), "
                        "'point' = point-based localization"
                    ),
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of categories for task='detect'. Example: ['person', 'car', 'bicycle']",
                },
                "generation_mode": {
                    "type": "string",
                    "enum": ["fast", "slow", "hybrid"],
                    "default": "hybrid",
                    "description": "Inference mode: 'hybrid' (default, best overall), 'fast' (MTP parallel), 'slow' (autoregressive, most robust)",
                },
            },
            "required": ["image_path", "prompt"],
        },
    }
]

# =============================================================================
# Utilidades de servidor
# =============================================================================

def is_server_up() -> bool:
    """Verifica si el servidor HTTP está respondiendo."""
    import socket
    try:
        urllib.request.urlopen(HEALTH_URL, timeout=1)
        return True
    except urllib.error.URLError as e:
        # e.reason is usually an OSError or socket.error
        if isinstance(e.reason, (ConnectionRefusedError, socket.error)) or "Connection refused" in str(e.reason):
            return False
        return True  # Otro tipo de error (timeout, etc.) = probablemente vivo
    except Exception:
        return True


def boot_server() -> bool:
    """
    Arranca el servidor HTTP en background.
    Usa el Python del venv local si existe, sino el Python del sistema.
    Espera hasta 90s a que el modelo cargue en MPS.
    """
    python = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

    sys.stderr.write(
        f"[locate-client] Servidor inactivo. Iniciando locate_server.py (MPS)...\n"
        f"[locate-client] Cargando modelo nvidia/LocateAnything-3B (~20-40s en Apple Silicon)\n"
    )
    sys.stderr.flush()

    cmd = f'nohup "{python}" "{SERVER_SCRIPT}" >> "{LOG_FILE}" 2>&1 &'
    os.system(cmd)

    # Esperar hasta 90s (el modelo tarda ~30s en cargar en MPS la primera vez)
    for attempt in range(180):
        time.sleep(0.5)
        if is_server_up():
            sys.stderr.write("[locate-client] ✅ Servidor listo.\n")
            sys.stderr.flush()
            return True
        if attempt % 20 == 19:
            elapsed = (attempt + 1) * 0.5
            sys.stderr.write(f"[locate-client] Esperando... {elapsed:.0f}s / 90s\n")
            sys.stderr.flush()

    sys.stderr.write("[locate-client] ❌ Timeout: el servidor no respondió en 90s.\n")
    sys.stderr.flush()
    return False


# =============================================================================
# MCP Protocol Handlers
# =============================================================================

def handle_initialize(req_id, params):
    """Responde al handshake inicial de MCP."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "locate-anything",
                "version": "1.0.0",
            },
        },
    }


def handle_tools_list(req_id):
    """Retorna el catálogo de herramientas disponibles."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": MCP_TOOLS},
    }


def handle_tools_call(req_id, params):
    """
    Ejecuta una herramienta MCP: redirige la llamada al servidor HTTP.
    Retorna la respuesta como contenido MCP (texto + imagen).
    """
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name != "locate_objects":
        return _mcp_error(req_id, -32601, f"Herramienta desconocida: '{tool_name}'")

    # Construir petición al servidor HTTP
    payload = json.dumps(arguments).encode("utf-8")
    req_http = urllib.request.Request(
        LOCATE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req_http, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else "Sin cuerpo de respuesta"
        return _mcp_error(req_id, -32000, f"Error HTTP {e.code}: {err_body}")
    except Exception as e:
        return _mcp_error(req_id, -32000, f"Error de conexión al servidor: {e}")

    # Construir contenido MCP desde la respuesta del servidor
    content = []

    if body.get("status") == "error":
        content.append({
            "type": "text",
            "text": f"❌ Error: {body.get('error', 'Desconocido')}\n{body.get('summary', '')}",
        })
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": content, "isError": True},
        }

    # Texto descriptivo con resumen y coordenadas
    summary_text = body.get("summary", "Procesado sin resultados.")
    prompt_en = body.get("prompt_translated", "")
    duration = body.get("duration_seconds", 0)
    boxes = body.get("boxes", [])
    points = body.get("points", [])

    text_lines = [summary_text, ""]

    if boxes:
        text_lines.append("📦 Bounding Boxes (píxeles):")
        for i, b in enumerate(boxes):
            text_lines.append(
                f"  #{i+1}: x1={b['x1']}, y1={b['y1']}, x2={b['x2']}, y2={b['y2']} "
                f"(tamaño: {b['x2']-b['x1']}x{b['y2']-b['y1']}px)"
            )

    if points:
        text_lines.append("📍 Puntos:")
        for i, p in enumerate(points):
            text_lines.append(f"  #{i+1}: x={p['x']}, y={p['y']}")

    if prompt_en and prompt_en != arguments.get("prompt", ""):
        text_lines.append(f"\n🌐 Prompt traducido: '{prompt_en}'")

    text_lines.append(f"⏱️  Tiempo de inferencia: {duration}s")
    text_lines.append(f"🤖 Modelo: nvidia/LocateAnything-3B (MPS)")

    # Ruta a la imagen anotada
    annotated_path = body.get("annotated_image_path")
    if annotated_path:
        text_lines.append(f"\n📁 Imagen anotada guardada en: {annotated_path}")

    content.append({"type": "text", "text": "\n".join(text_lines)})

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": content},
    }


def _mcp_error(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _mcp_notification_ok() -> None:
    """Las notificaciones no tienen respuesta en MCP."""
    pass


# =============================================================================
# Loop principal STDIO
# =============================================================================

def proxy():
    server_ready = False

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError as e:
            # Ignorar líneas malformadas
            sys.stderr.write(f"[locate-client] JSON inválido ignorado: {e}\n")
            sys.stderr.flush()
            continue

        method = msg.get("method", "")
        req_id = msg.get("id")
        params = msg.get("params", {})

        # Notificaciones (sin id) — no requieren respuesta
        if req_id is None:
            if method == "notifications/initialized":
                sys.stderr.write("[locate-client] Cliente MCP inicializado.\n")
                sys.stderr.flush()
            continue

        # Manejar initialize sin arrancar el servidor (el servidor solo se
        # necesita cuando hay un tools/call real)
        if method == "initialize":
            response = handle_initialize(req_id, params)
            _send(response)
            continue

        if method == "tools/list":
            response = handle_tools_list(req_id)
            _send(response)
            continue

        # Para tools/call — asegurarse de que el servidor está vivo
        if method == "tools/call":
            if not server_ready:
                if not is_server_up():
                    if not boot_server():
                        _send(_mcp_error(req_id, -32000, "No se pudo arrancar el servidor LocateAnything en el puerto 8014."))
                        continue
                server_ready = True

            response = handle_tools_call(req_id, params)
            _send(response)
            continue

        # Ping
        if method == "ping":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {}})
            continue

        # Método desconocido
        _send(_mcp_error(req_id, -32601, f"Método no soportado: '{method}'"))


def _send(obj: dict) -> None:
    """Escribe un mensaje JSON-RPC en STDOUT con flush inmediato."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    try:
        proxy()
    except KeyboardInterrupt:
        sys.exit(0)
    except BrokenPipeError:
        sys.exit(0)

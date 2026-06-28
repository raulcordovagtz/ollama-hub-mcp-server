#!/usr/bin/env python3
"""
FastContext Smart Client — v1.0
Proxy STDIO → HTTP que actúa como servidor MCP para clientes de IA.

Protocolo:
  - Entrada:  JSON-RPC 2.0 por STDIN (protocolo MCP estándar)
  - Salida:   JSON-RPC 2.0 por STDOUT
  - Backend:  HTTP POST a http://localhost:8015/

Filosofía Cold Start:
  1. Verifica si el servidor HTTP está vivo (GET /health, timeout 1s)
  2. Si está muerto → lanza start_fastcontext_server.sh en background
  3. Espera hasta 15s a que el servidor esté listo
  4. Redirige las peticiones JSON-RPC al servidor HTTP

Cancelación Activa:
  - Genera un `task_id` único por consulta de exploración.
  - Si la entrada se interrumpe (pipe roto o Ctrl+C), envía una petición a /cancel/{task_id}
    para detener la inferencia del modelo en Python de inmediato.
"""

import sys
import os
import time
import json
import uuid
import signal
import urllib.request
import urllib.error

# =============================================================================
# Configuración
# =============================================================================
PORT = 8015
BASE_URL = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BASE_URL}/health"
EXPLORE_URL = f"{BASE_URL}/explore"
ONTOLOGY_URL = f"{BASE_URL}/ontology"
CANCEL_URL_TEMPLATE = f"{BASE_URL}/cancel/{{task_id}}"

# Ruta al script de arranque
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
START_SCRIPT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../scripts/start_fastcontext_server.sh"))

# Variable global para rastrear la tarea en ejecución en esta sesión de cliente
current_task_id = None

# =============================================================================
# Catálogo de Herramientas MCP
# =============================================================================
MCP_TOOLS = [
    {
        "name": "get_project_ontology",
        "description": (
            "Returns a structured ontology report (Bird's Eye View) of the repository. "
            "Analyzes code manifests, identifies core libraries and hardware integration "
            "(e.g., Apple Silicon MLX, PyTorch), and extracts main class and function "
            "definitions using AST and regex parser in < 2 seconds."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository directory (e.g. /Users/you/project)",
                },
                "architecture": {
                    "type": "string",
                    "description": "Optional architectural description or notes to guide structure extraction.",
                }
            },
            "required": ["repo_path"],
        },
    },
    {
        "name": "fastcontext_explore",
        "description": (
            "Spawns the local FastContext-4B sub-agent to search for specific code "
            "references. The sub-agent issues recursive search operations (READ, GLOB, GREP) "
            "under the hood and returns a clean, structured report containing exact file paths "
            "and line number citations. Recommended for debugging or finding specific logic."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository directory (e.g. /Users/you/project)",
                },
                "query": {
                    "type": "string",
                    "description": "Specific search query (e.g. 'where is the authorization token validated?')",
                },
                "architecture": {
                    "type": "string",
                    "description": "Optional architectural description or notes to guide exploration.",
                },
                "file_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of glob patterns to restrict the search (e.g. ['*.py', '*.ts']).",
                }
            },
            "required": ["repo_path", "query"],
        },
    }
]

# =============================================================================
# Control del Servidor
# =============================================================================
def is_server_up() -> bool:
    """Verifica si el servidor FastContext está activo."""
    import socket
    try:
        urllib.request.urlopen(HEALTH_URL, timeout=1)
        return True
    except urllib.error.URLError as e:
        if isinstance(e.reason, (ConnectionRefusedError, socket.error)) or "Connection refused" in str(e.reason):
            return False
        return True  # Otro error (ej. 500) indica que el servidor está levantado
    except Exception:
        return False

def boot_server() -> bool:
    """Arranca el servidor de FastContext en background usando el script de control."""
    sys.stderr.write("[fastcontext-client] Servidor inactivo. Iniciando FastContext Server...\n")
    sys.stderr.flush()

    if not os.path.exists(START_SCRIPT):
        # Fallback si no está el script central (ejecutar python directamente)
        sys.stderr.write(f"[fastcontext-client] Script {START_SCRIPT} no encontrado, usando python fallback...\n")
        sys.stderr.flush()
        python = sys.executable
        server_py = os.path.join(SCRIPT_DIR, "fastcontext_server.py")
        cmd = f'nohup "{python}" "{server_py}" > /dev/null 2>&1 &'
        os.system(cmd)
    else:
        # Ejecutar script de control centralizado
        os.system(f'bash "{START_SCRIPT}" > /dev/null 2>&1 &')

    # Esperar hasta 15 segundos a que responda
    for attempt in range(30):
        time.sleep(0.5)
        if is_server_up():
            sys.stderr.write("[fastcontext-client] ✅ Servidor listo.\n")
            sys.stderr.flush()
            return True
        if attempt % 10 == 9:
            elapsed = (attempt + 1) * 0.5
            sys.stderr.write(f"[fastcontext-client] Esperando servidor... {elapsed:.1f}s / 15s\n")
            sys.stderr.flush()

    sys.stderr.write("[fastcontext-client] ❌ Timeout: El servidor no inició en 15s.\n")
    sys.stderr.flush()
    return False

# =============================================================================
# Cancelación Activa de Tarea
# =============================================================================
def trigger_cancel():
    """Envía la petición de cancelación al servidor HTTP de FastContext."""
    global current_task_id
    if current_task_id:
        sys.stderr.write(f"[fastcontext-client] 🛑 Enviando cancelación para tarea: {current_task_id}\n")
        sys.stderr.flush()
        try:
            cancel_url = CANCEL_URL_TEMPLATE.format(task_id=current_task_id)
            req = urllib.request.Request(cancel_url, method="POST")
            with urllib.request.urlopen(req, timeout=3) as resp:
                pass
        except Exception as e:
            sys.stderr.write(f"[fastcontext-client] Falló envío de cancelación: {e}\n")
            sys.stderr.flush()
        current_task_id = None

def signal_handler(sig, frame):
    """Manejador de señales del sistema para abortar."""
    trigger_cancel()
    sys.exit(0)

# Registrar manejadores de señales
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# =============================================================================
# Protocolo MCP Handlers
# =============================================================================
def handle_initialize(req_id, params):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "fastcontext",
                "version": "1.0.0",
            },
        },
    }

def handle_tools_list(req_id):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": MCP_TOOLS},
    }

def handle_tools_call(req_id, params):
    global current_task_id
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name not in ["get_project_ontology", "fastcontext_explore"]:
        return _mcp_error(req_id, -32601, f"Herramienta desconocida: '{tool_name}'")

    # Ejecutar get_project_ontology
    if tool_name == "get_project_ontology":
        url = ONTOLOGY_URL
        payload = {
            "repo_path": arguments.get("repo_path"),
            "architecture": arguments.get("architecture")
        }
    else:
        # Exploración profunda con sub-agente
        url = EXPLORE_URL
        task_id = uuid.uuid4().hex[:8]
        current_task_id = task_id  # Guardar para cancelación activa
        payload = {
            "repo_path": arguments.get("repo_path"),
            "query": arguments.get("query"),
            "architecture": arguments.get("architecture"),
            "file_patterns": arguments.get("file_patterns"),
            "task_id": task_id
        }

    # Serializar request
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        # Esperar respuesta del servidor (límite de 5 minutos para búsquedas pesadas)
        with urllib.request.urlopen(req, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else "Sin cuerpo"
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("detail", str(e))
        except Exception:
            msg = f"HTTP Error {e.code}: {err_body}"
        return _mcp_error(req_id, -32000, msg)
    except Exception as e:
        return _mcp_error(req_id, -32000, f"Error conectando al servidor local: {e}")
    finally:
        current_task_id = None  # Limpiar task_id una vez terminado

    # Procesar respuesta para formato MCP
    content = []
    if tool_name == "get_project_ontology":
        report_text = body.get("report", "No se pudo generar la ontología.")
        content.append({"type": "text", "text": report_text})
    else:
        report_text = body.get("report", "")
        content.append({"type": "text", "text": report_text})

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

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

# =============================================================================
# Loop Principal STDIO
# =============================================================================
def main():
    server_ready = False

    try:
        for raw_line in sys.stdin:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                msg = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            method = msg.get("method", "")
            req_id = msg.get("id")
            params = msg.get("params", {})

            # Notificaciones (sin id)
            if req_id is None:
                continue

            if method == "initialize":
                _send(handle_initialize(req_id, params))
                continue

            if method == "tools/list":
                _send(handle_tools_list(req_id))
                continue

            if method == "tools/call":
                # Asegurar que el servidor está levantado
                if not server_ready:
                    if not is_server_up():
                        if not boot_server():
                            _send(_mcp_error(req_id, -32000, "No se pudo arrancar el servidor FastContext."))
                            continue
                    server_ready = True

                _send(handle_tools_call(req_id, params))
                continue

            if method == "ping":
                _send({"jsonrpc": "2.0", "id": req_id, "result": {}})
                continue

            _send(_mcp_error(req_id, -32601, f"Método no soportado: '{method}'"))

    except (KeyboardInterrupt, SystemExit, BrokenPipeError):
        pass
    finally:
        # Asegurar cancelación activa si el pipe se cierra
        trigger_cancel()

if __name__ == "__main__":
    main()

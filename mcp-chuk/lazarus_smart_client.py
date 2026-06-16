#!/usr/bin/env python3
"""
Proxy Inteligente para Lazarus Interpretability Server.
Actúa como un cliente STDIO para Antigravity que redirige el tráfico
JSON-RPC hacia chuk-mcp-lazarus en el puerto 8010.

Incluye lógica de Auto-Start: Si el servidor está apagado (por idle timeout),
este script lo enciende en background antes de enviar la primera petición.
Cero dependencias externas (usa librería estándar de Python).
"""

import sys
import os
import time
import json
import threading
import urllib.request
import urllib.error

PORT = 8010
BASE_URL = f"http://localhost:{PORT}"

def is_server_up():
    try:
        # Comprobamos conectividad. Un 404 significa que el servidor está vivo.
        urllib.request.urlopen(BASE_URL, timeout=1)
        return True
    except urllib.error.URLError as e:
        if isinstance(e.reason, ConnectionRefusedError):
            return False
        return True
    except Exception:
        return True

def boot_server():
    log_file = os.path.expanduser("~/lazarus_server.log")
    sys.stderr.write(f"Servidor inactivo. Iniciando chuk-mcp-lazarus en el puerto {PORT}...\n")
    # Arrancar el servidor Lazarus en background usando la ruta directa (mucho más rápido que conda run)
    python_bin = "/opt/miniconda3/envs/MarketGraph-AI/bin/python"
    lazarus_bin = "/opt/miniconda3/envs/MarketGraph-AI/bin/chuk-mcp-lazarus"
    cmd = f"nohup {python_bin} {lazarus_bin} http --port {PORT} > {log_file} 2>&1 &"
    os.system(cmd)
    
    # Esperar hasta 25 segundos a que la interfaz HTTP despierte
    for _ in range(50):
        if is_server_up():
            sys.stderr.write("Servidor iniciado correctamente.\n")
            return True
        time.sleep(0.5)
    return False

def proxy():
    # 1. AUTO-START
    if not is_server_up():
        if not boot_server():
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": "Falló el auto-arranque del servidor Lazarus en el puerto 8010."}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            sys.exit(1)

    # 2. TUNEL DE PETICIONES (STDIN -> POST)
    # chuk_mcp_server procesa el JSON-RPC directamente a través de POST en /mcp
    post_url = f"{BASE_URL}/mcp"
    session_id = None
    
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            headers = {'Content-Type': 'application/json'}
            if session_id:
                headers['mcp-session-id'] = session_id
                
            req = urllib.request.Request(
                post_url, 
                data=line.encode('utf-8'), 
                headers=headers
            )
            with urllib.request.urlopen(req) as response:
                # Extraer session_id si no lo tenemos
                if not session_id:
                    sid = response.getheader('mcp-session-id')
                    if sid:
                        session_id = sid
                        
                resp_body = response.read().decode('utf-8').strip()
                if resp_body:
                    sys.stdout.write(resp_body + "\n")
                    sys.stdout.flush()
        except urllib.error.HTTPError as e:
            # Si el servidor responde con error HTTP pero manda cuerpo (ej: 400 Bad Request)
            try:
                err_body = e.read().decode('utf-8').strip()
                if err_body:
                    sys.stdout.write(err_body + "\n")
                    sys.stdout.flush()
            except Exception:
                sys.stderr.write(f"HTTP POST Error: {e}\n")
        except Exception as e:
            sys.stderr.write(f"HTTP POST Error: {e}\n")

if __name__ == "__main__":
    proxy()

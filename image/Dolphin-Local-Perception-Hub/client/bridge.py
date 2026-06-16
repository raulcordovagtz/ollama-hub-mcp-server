import requests
import subprocess
import time
import sys
import os

SERVER_URL = "http://localhost:8000"
# Path to project root (parent of client/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def ensure_server_running():
    """
    Verifies if the Dolphin Oracle is alive. If not, wakes it.
    """
    try:
        requests.get(f"{SERVER_URL}/health", timeout=1)
        return True
    except (requests.ConnectionError, requests.Timeout):
        print("⚡ Despertando al Oráculo Dolphin...")
        
        # Check if server module exists via path check (rough)
        server_dir = os.path.join(PROJECT_ROOT, "server")
        if not os.path.exists(server_dir):
            print(f"❌ Error: Cannot find server directory at {server_dir}")
            sys.exit(1)
            
        # Launch server in background as module
        # We need to run from project root for -m server.server to work
        subprocess.Popen(
            [sys.executable, "-m", "server.server"], 
            cwd=PROJECT_ROOT,
            stdout=sys.stdout, 
            stderr=sys.stderr
        )
        
        # Wait for handshake (polling)
        print("⏳ Esperando carga de modelo (esto puede tomar 10-20s)...")
        retries = 30
        while retries > 0:
            try:
                res = requests.get(f"{SERVER_URL}/health", timeout=1)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "READY":
                         print("🔗 Conexión establecida (Modelo LISTO).")
                         return True
                    else:
                        print(f"⏳ Servidor vivo, cargando modelo... ({data.get('status')})")
            except:
                pass
            time.sleep(1)
            retries -= 1
        
        print("❌ Error: El servidor no respondió a tiempo.")
        sys.exit(1)

def send_request(filepath, prompt, max_tokens=2048):
    ensure_server_running()
    
    import base64
    
    with open(filepath, "rb") as f:
        image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
    payload = {
        "image_base64": image_base64,
        "prompt": prompt,
        "generation_config": {
            "max_new_tokens": max_tokens
        }
    }
    
    try:
        resp = requests.post(f"{SERVER_URL}/api/interact", json=payload)
        if resp.status_code == 200:
            return resp.json()["raw_text_output"]
        else:
            return f"Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Error de transmisión: {str(e)}"

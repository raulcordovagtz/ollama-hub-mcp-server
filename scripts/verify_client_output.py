import json
import subprocess
import time

def test_mcp_client_delivery():
    print("🚦 Iniciando prueba de entrega del cliente MCP...")
    
    # Payload que el usuario reportó como problemático
    prompt = "An animated character with aesthetic and detailed features, long dark hair, large light blue eyes, and a neutral facial expression. The character is wearing a fitted white suit that highlights their figure. The lighting is soft, creating a realistic and attractive effect."
    args = {
        "prompt": prompt,
        "width": 920,
        "height": 920
    }
    
    # Simulamos el mensaje que LM Studio enviaría al bridge (JSON-RPC)
    mcp_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "generate_image",
            "arguments": args
        }
    }
    
    # Lanzamos el bridge directamente
    bridge_path = "/Users/crotalo/.lmstudio/extensions/plugins/mcp/ollama-hub/ollama_hub_mcp.py"
    python_path = "/opt/miniconda3/envs/kokoro_env/bin/python"
    
    process = subprocess.Popen(
        [python_path, bridge_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"📡 Enviando comando al bridge: tools/call (generate_image)")
    process.stdin.write(json.dumps(mcp_message) + "\n")
    process.stdin.flush()
    
    # Esperamos un poco para que el bridge procese y envíe al servidor de debug
    time.sleep(2)
    
    # Terminamos el bridge
    process.terminate()
    print("✅ Prueba completada. Verificando logs del servidor de debug...")

if __name__ == "__main__":
    test_mcp_client_delivery()

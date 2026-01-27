from fastapi import FastAPI, Request
import uvicorn
import json
import logging

# Configuración de logging para ver todo el tráfico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG_SERVER")

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def debug_generate(request: Request):
    # Capturamos el cuerpo crudo antes de cualquier parseo automático
    raw_body = await request.body()
    headers = dict(request.headers)
    
    logger.info("--- NUEVA PETICIÓN CAPTURADA ---")
    
    try:
        parsed_body = json.loads(raw_body)
        logger.info(f"Cuerpo (JSON): {json.dumps(parsed_body, indent=2)}")
        
        # Guardamos en un archivo para inspección forense física
        with open("/Users/crotalo/desarrollo-local/server/logs/image/last_client_payload.json", "w") as f:
            json.dump({"headers": headers, "body": parsed_body}, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error parseando cuerpo: {e}")
        logger.error(f"Contenido crudo: {raw_body}")

    # Devolvemos un éxito ficticio para que el cliente no explote
    return {"status": "success", "task_id": "debug-test", "file_path": "/tmp/dummy.png"}

if __name__ == "__main__":
    print("🎯 Servidor de Depuración (v2) escuchando en el puerto 8010...")
    uvicorn.run(app, host="127.0.0.1", port=8010)

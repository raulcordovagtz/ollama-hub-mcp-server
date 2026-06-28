#!/usr/bin/env bash
# =============================================================================
# start_fastcontext_server.sh — Arranque en frío del servidor FastContext
# =============================================================================
# Usado por el bridge MCP (fastcontext_smart_client.py) y scripts de admin.
# Sigue la misma filosofía de start_locate_server.sh / start_text_server.sh.
# Puerto: 8015 | Entorno: locate-anything conda env
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../text/fastcontext"
if command -v conda &> /dev/null; then
    CONDA_BASE=$(conda info --base)
    VENV_PYTHON="$CONDA_BASE/envs/locate-anything/bin/python3"
else
    VENV_PYTHON="/opt/miniconda3/envs/locate-anything/bin/python3"
fi
SERVER_SCRIPT="$SERVER_DIR/fastcontext_server.py"
LOG_FILE="$SCRIPT_DIR/../logs/fastcontext/server.log"
PORT=8015

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[start-fastcontext]${NC} $*"; }
ok()   { echo -e "${GREEN}[start-fastcontext] ✅${NC} $*"; }
warn() { echo -e "${YELLOW}[start-fastcontext] ⚠️${NC}  $*"; }
err()  { echo -e "${RED}[start-fastcontext] ❌${NC} $*"; }

mkdir -p "$(dirname "$LOG_FILE")"

# ---- Verificar si ya está corriendo ----
if curl -s --connect-timeout 1 "http://127.0.0.1:$PORT/health" &> /dev/null; then
    ok "Servidor FastContext ya activo en el puerto $PORT."
    exit 0
fi

# ---- Verificar venv ----
if [ ! -f "$VENV_PYTHON" ]; then
    err "Venv no encontrado en $VENV_PYTHON"
    err "Ejecuta: conda activate locate-anything && pip install fastapi uvicorn pydantic"
    exit 1
fi

# ---- Verificar script del servidor ----
if [ ! -f "$SERVER_SCRIPT" ]; then
    err "Script del servidor no encontrado en $SERVER_SCRIPT"
    exit 1
fi

# ---- Arrancar ----
log "Iniciando FastContext Server (puerto $PORT)..."
log "Modelo: FastContext-1.0-4B-SFT (via SGLang en puerto 8080)"
log "Dispositivo: Apple Silicon MPS"
log "Log: $LOG_FILE"
log ""
warn "Primera carga ~10-20s (esperando FastAPI + SGLang)..."

FASTCONTEXT_API_BASE="http://localhost:8080/v1" \
FASTCONTEXT_MODEL="FastContext-1.0-4B-SFT" \
nohup "$VENV_PYTHON" -m uvicorn fastcontext_server:app --host 127.0.0.1 --port "$PORT" --log-level warning \
    >> "$LOG_FILE" 2>&1 &

# Esperar hasta 30s
for i in $(seq 1 60); do
    sleep 0.5
    if curl -s --connect-timeout 1 "http://127.0.0.1:$PORT/health" &> /dev/null; then
        ok "Servidor FastContext listo en http://127.0.0.1:$PORT"
        ok "Idle timeout: 20 minutos de inactividad"
        exit 0
    fi
    if [ $((i % 20)) -eq 0 ]; then
        elapsed=$((i / 2))
        log "Esperando... ${elapsed}s / 30s"
    fi
done

err "Timeout: el servidor FastContext no respondió en 30s."
err "Revisa el log: $LOG_FILE"
exit 1

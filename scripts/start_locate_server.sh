#!/usr/bin/env bash
# =============================================================================
# start_locate_server.sh — Arranque en frío del servidor LocateAnything
# =============================================================================
# Usado por el bridge MCP y scripts de administración.
# Sigue la misma filosofía de start_image_server.sh / start_text_server.sh.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../vision/locate-anything"
if command -v conda &> /dev/null; then
    CONDA_BASE=$(conda info --base)
    VENV_PYTHON="$CONDA_BASE/envs/locate-anything/bin/python3"
else
    VENV_PYTHON="/opt/miniconda3/envs/locate-anything/bin/python3"
fi
SERVER_SCRIPT="$SERVER_DIR/locate_server.py"
LOG_FILE="$SCRIPT_DIR/../logs/locate/server.log"
PORT=8014

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[start-locate]${NC} $*"; }
ok()   { echo -e "${GREEN}[start-locate] ✅${NC} $*"; }
warn() { echo -e "${YELLOW}[start-locate] ⚠️${NC}  $*"; }
err()  { echo -e "${RED}[start-locate] ❌${NC} $*"; }

mkdir -p "$(dirname "$LOG_FILE")"

# ---- Verificar si ya está corriendo ----
if curl -s --connect-timeout 1 "http://127.0.0.1:$PORT/health" &>/dev/null; then
    ok "Servidor ya activo en el puerto $PORT."
    exit 0
fi

# ---- Verificar venv ----
if [ ! -f "$VENV_PYTHON" ]; then
    err "Venv no encontrado en $VENV_PYTHON"
    err "Ejecuta primero: $SERVER_DIR/install_deps.sh"
    exit 1
fi

# ---- Arrancar ----
log "Iniciando LocateAnything Server (puerto $PORT)..."
log "Modelo: nvidia/LocateAnything-3B"
log "Dispositivo: Apple Silicon MPS"
log "Log: $LOG_FILE"
log ""
warn "Primera carga ~20-40s (cargando modelo en MPS)..."

nohup "$VENV_PYTHON" "$SERVER_SCRIPT" >> "$LOG_FILE" 2>&1 &

# Esperar hasta 90s
for i in $(seq 1 180); do
    sleep 0.5
    if curl -s --connect-timeout 1 "http://127.0.0.1:$PORT/health" &>/dev/null; then
        ok "Servidor listo en http://127.0.0.1:$PORT"
        ok "Idle timeout: 20 minutos de inactividad"
        exit 0
    fi
    if [ $((i % 20)) -eq 0 ]; then
        elapsed=$((i / 2))
        log "Esperando... ${elapsed}s / 90s"
    fi
done

err "Timeout: el servidor no respondió en 90s."
err "Revisa el log: $LOG_FILE"
exit 1

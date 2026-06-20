#!/usr/bin/env bash
# =============================================================================
# download_model.sh — Descarga nvidia/LocateAnything-3B desde HuggingFace
# =============================================================================
# Descarga el modelo al caché estándar de HuggingFace (~/.cache/huggingface/).
# Usa el entorno conda locate-anything.
#
# Uso:
#   ./download_model.sh           # Descarga normal
#   ./download_model.sh --check   # Solo verifica si ya está descargado
# =============================================================================

set -euo pipefail

ENV_NAME="locate-anything"
MODEL_ID="nvidia/LocateAnything-3B"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}/hub"
MODEL_CACHE_DIR="$HF_CACHE/models--nvidia--LocateAnything-3B"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[locate-dl]${NC} $*"; }
ok()   { echo -e "${GREEN}[locate-dl] ✅${NC} $*"; }
warn() { echo -e "${YELLOW}[locate-dl] ⚠️${NC}  $*"; }
err()  { echo -e "${RED}[locate-dl] ❌${NC} $*"; }

# ---- Verificar caché existente ----
check_cached() {
    if [ -d "$MODEL_CACHE_DIR" ] && [ -n "$(ls -A "$MODEL_CACHE_DIR" 2>/dev/null)" ]; then
        return 0  # ya descargado
    fi
    return 1
}

if [ "${1:-}" == "--check" ]; then
    if check_cached; then
        ok "Modelo ya descargado en: $MODEL_CACHE_DIR"
        exit 0
    else
        warn "Modelo NO encontrado en caché. Ejecuta sin --check para descargar."
        exit 1
    fi
fi

# ---- Verificar caché antes de descargar ----
if check_cached; then
    ok "Modelo ya está en caché: $MODEL_CACHE_DIR"
    ok "No es necesario volver a descargar."
    exit 0
fi

if ! conda env list | grep -q "$ENV_NAME"; then
    err "El entorno conda '$ENV_NAME' no existe."
    err "Ejecuta primero: ./install_deps.sh"
    exit 1
fi

# ---- Descarga ----
log "Iniciando descarga de ${MODEL_ID}..."
log "Destino: $HF_CACHE"
log "Tamaño estimado: ~6-7 GB"
log ""
warn "La descarga puede tomar 10-30 min según tu conexión."
log ""

# Descarga con huggingface-cli via conda
conda run -n "$ENV_NAME" huggingface-cli download "$MODEL_ID" \
    --repo-type model \
    --local-dir-use-symlinks False \
    2>&1 | tee /tmp/locate_download.log

if check_cached; then
    ok "Descarga completa: $MODEL_CACHE_DIR"
    log ""
    log "Próximos pasos:"
    log "  1. Inicia el servidor: python3 locate_server.py (o usa el cliente MCP)"
else
    err "La descarga falló o el caché está incompleto."
    err "Revisa /tmp/locate_download.log para detalles."
    exit 1
fi

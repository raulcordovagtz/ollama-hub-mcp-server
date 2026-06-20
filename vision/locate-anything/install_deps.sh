#!/usr/bin/env bash
# =============================================================================
# install_deps.sh — Crea el entorno conda e instala dependencias
# =============================================================================
# Uso: ./install_deps.sh
# =============================================================================

set -euo pipefail

ENV_NAME="locate-anything"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[install]${NC} $*"; }
ok()  { echo -e "${GREEN}[install] ✅${NC} $*"; }

# Detectar conda
if ! command -v conda &> /dev/null; then
    echo "❌ Conda no está instalado o no está en el PATH."
    exit 1
fi

log "Creando entorno conda '$ENV_NAME' con Python 3.11..."
conda create -n "$ENV_NAME" python=3.11 -y

# Función helper para ejecutar en conda
crun() {
    conda run -n "$ENV_NAME" "$@"
}

log "Instalando dependencias en el entorno '$ENV_NAME'..."
crun pip install --upgrade pip --quiet

# PyTorch con soporte MPS
crun pip install torch torchvision --quiet

# Modelo y transformers
crun pip install \
    "transformers==4.57.1" \
    Pillow \
    numpy \
    peft \
    opencv-python-headless \
    --quiet

# Servidor HTTP
crun pip install fastapi uvicorn --quiet

# Traducción automática de prompts
crun pip install deep-translator --quiet

# HuggingFace Hub (para descarga del modelo)
crun pip install huggingface_hub --quiet

ok "Instalación completa."
log ""
log "Próximo paso: descargar el modelo"
log "  ./download_model.sh"

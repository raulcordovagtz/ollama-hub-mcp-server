#!/bin/bash
ENV_PATH="/opt/miniconda3/envs/mlx_unified"
PYTHON="$ENV_PATH/bin/python"
SERVER_SCRIPT="/Users/crotalo/desarrollo-local/server/diffusion/engine-mlx/smart_diffusion_server.py"
LOG_DIR="/Users/crotalo/desarrollo-local/server/logs/diffusion"

mkdir -p "$LOG_DIR"
nohup "$PYTHON" "$SERVER_SCRIPT" > "$LOG_DIR/server.log" 2>&1 &
echo "🧬 Servidor de Diffusion iniciado (PID $!)"

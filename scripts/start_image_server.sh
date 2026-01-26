#!/bin/bash
ENV_PATH="/opt/miniconda3/envs/mlx-audio"
PYTHON="$ENV_PATH/bin/python"
SERVER_SCRIPT="/Users/crotalo/desarrollo-local/server/image/engine-ollama/smart_image_server.py"
LOG_DIR="/Users/crotalo/desarrollo-local/server/logs/image"

mkdir -p "$LOG_DIR"
nohup "$PYTHON" "$SERVER_SCRIPT" > "$LOG_DIR/server.log" 2>&1 &
echo "🚀 Servidor de Imagen iniciado (PID $!)"

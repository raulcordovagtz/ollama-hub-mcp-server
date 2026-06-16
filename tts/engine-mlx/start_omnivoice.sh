#!/bin/bash

# Configuración del Servidor OmniVoice MLX
PROJECT_DIR="/Users/crotalo/desarrollo-local/server/tts/engine-mlx"
CONDA_ENV="mlx-audio"
CONDA_PYTHON="/opt/miniconda3/envs/${CONDA_ENV}/bin/python"
SERVER_SCRIPT="$PROJECT_DIR/smart_server_omnivoice.py"
LOG_DIR="/Users/crotalo/desarrollo-local/server/logs/tts"
PORT=8009

mkdir -p "$LOG_DIR"

# Verificar entorno
if [ ! -f "$CONDA_PYTHON" ]; then
    echo "❌ Error: No se encuentra el entorno conda '$CONDA_ENV' en $CONDA_PYTHON"
    exit 1
fi

# Matar procesos anteriores del servidor OmniVoice
echo "🧹 Limpiando procesos anteriores de OmniVoice en puerto $PORT..."
pkill -f "smart_server_omnivoice.py --port $PORT" 2>/dev/null

# Iniciar servicio en segundo plano
LOG_FILE="$LOG_DIR/omnivoice_server.log"
echo "🚀 Iniciando OmniVoice MLX en puerto $PORT..."
cd "$PROJECT_DIR"
nohup "$CONDA_PYTHON" "$SERVER_SCRIPT" --port "$PORT" > "$LOG_FILE" 2>&1 &
PID=$!

echo "✅ Servicio OmniVoice iniciado con PID: $PID. Logs en: $LOG_FILE"

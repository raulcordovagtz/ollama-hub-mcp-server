#!/bin/bash

# Configuración del Servidor Supertonic TTS
PROJECT_DIR="/Users/crotalo/desarrollo-local/server/tts/supertonic-tts"
CONDA_PYTHON="/opt/miniconda3/bin/python" # Usando base environment
SERVER_SCRIPT="$PROJECT_DIR/smart_server.py"
LOG_DIR="/Users/crotalo/desarrollo-local/server/logs/tts"
PORT=8013

mkdir -p "$LOG_DIR"

# Verificar entorno
if [ ! -f "$CONDA_PYTHON" ]; then
    echo "❌ Error: No se encuentra Python en $CONDA_PYTHON"
    exit 1
fi

# Matar procesos anteriores del servidor TTS
echo "🧹 Limpiando procesos anteriores de TTS en puerto $PORT..."
pkill -f "smart_server.py --port $PORT" 2>/dev/null

# Iniciar servicio en segundo plano
echo "🚀 Iniciando Supertonic TTS en puerto $PORT (Logs silenciados para no dejar residuos)..."
cd "$PROJECT_DIR"
nohup "$CONDA_PYTHON" "$SERVER_SCRIPT" --port "$PORT" > /dev/null 2>&1 &
PID=$!

echo "✅ Servicio Supertonic iniciado con PID: $PID en modo silencioso (Zero-Residues)."

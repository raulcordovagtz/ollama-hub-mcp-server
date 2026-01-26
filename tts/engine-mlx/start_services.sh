#!/bin/bash

# Configuración
ENV_PATH="/opt/miniconda3/envs/mlx-audio"
PYTHON="$ENV_PATH/bin/python"
SERVER_SCRIPT="/Users/crotalo/desarrollo-local/server/tts/engine-mlx/smart_server.py"
LOG_DIR="/Users/crotalo/desarrollo-local/server/logs/tts"

mkdir -p "$LOG_DIR"

# Función para iniciar un servicio
start_service() {
    MODEL=$1
    PORT=$2
    LOG_FILE="$LOG_DIR/${MODEL}.log"
    
    echo "🚀 Iniciando $MODEL en puerto $PORT..."
    nohup "$PYTHON" "$SERVER_SCRIPT" --model "$MODEL" --port "$PORT" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo "$MODEL iniciado con PID: $PID. Logs en: $LOG_FILE"
}

# Verificar entorno
if [ ! -f "$PYTHON" ]; then
    echo "❌ Error: No se encuentra el entorno Python en $PYTHON"
    exit 1
fi

# Matar procesos anteriores (opcional, para reiniciar limpio)
echo "🧹 Limpiando procesos anteriores..."
pkill -f "smart_server.py"

# Iniciar servicios
start_service "kokoro" 8007

echo "✅ Servicio Kokoro iniciado."
echo "Monitoriza los logs con: tail -f $LOG_DIR/*.log"

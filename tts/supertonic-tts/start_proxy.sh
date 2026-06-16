#!/bin/bash
PROJECT_DIR="/Users/crotalo/desarrollo-local/server/tts/supertonic-tts"
LOG_DIR="/Users/crotalo/desarrollo-local/server/logs/tts"
PORT=8008

mkdir -p "$LOG_DIR"

echo "🧹 Limpiando proxy anterior..."
pkill -f "proxy.py" 2>/dev/null

echo "🚀 Iniciando Proxy Interceptor en puerto $PORT (Logs silenciados para no dejar residuos)..."
cd "$PROJECT_DIR"
nohup /opt/miniconda3/bin/python proxy.py > /dev/null 2>&1 &
PID=$!

echo "✅ Proxy iniciado con PID: $PID en modo silencioso (Zero-Residues)."

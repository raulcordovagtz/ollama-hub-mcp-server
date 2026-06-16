#!/bin/bash

# 🚨 BOTON ROJO: MODO EMERGENCIA 🚨
# Proposito: Detener todos los procesos de IA, vaciar puertos y liberar VRAM de Ollama.

echo "🔴 DETENIENDO TODOS LOS SERVICIOS DE IA..."

# 1. Matar servidores inteligentes (Python)
echo "🧹 Terminando servidores locales (FastAPI)..."
pkill -9 -f "smart_server.py"
pkill -9 -f "smart_image_server.py"
pkill -9 -f "smart_diffusion_server.py"

# 2. Instruccion Radical a Ollama: Vaciar VRAM
# Esto le dice a Ollama que reduzca el keep_alive de todos los modelos a 0 para que se descarguen ya.
echo "❄️ Vaciando modelos de Ollama (Keep-alive: 0)..."

# Lista de modelos comunes para asegurar que no se queden colgando (o podemos iterar sobre 'ollama ls')
models=$(ollama ls | awk 'NR>1 {print $1}')
for model in $models; do
    echo "  - Descargando: $model"
    curl -s http://localhost:11434/api/generate -d "{\"model\": \"$model\", \"keep_alive\": 0}" > /dev/null &
done

# 3. Limpiar puertos (si algo se quedo colgado)
echo "🔌 Liberando puertos (8007-8011)..."
for port in {8007..8011}; do
    pid=$(lsof -ti :$port)
    if [ ! -z "$pid" ]; then
        kill -9 $pid
    fi
done

# 4. Alerta Auditiva
afplay /System/Library/Sounds/Sosumi.aiff
echo "✅ SISTEMA LIMPIEZA COMPLETADO. VRAM LIBERADA."

#!/bin/zsh
# OmniVoice MLX CLI Client — Para Automator
# Uso: ./tts_client_omnivoice.sh "Texto a sintetizar"
# Uso con voz: ./tts_client_omnivoice.sh "Texto" --voice "Sally"
# Uso con pipe: echo "Texto" | ./tts_client_omnivoice.sh
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

PROJECT_DIR="/Users/crotalo/desarrollo-local/server/tts/engine-mlx"
PORT=8009

VOICE=""
TEXT_INPUT=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --voice) VOICE="$2"; shift ;;
        *) [ -z "$TEXT_INPUT" ] && TEXT_INPUT="$1" || TEXT_INPUT="$TEXT_INPUT $1" ;;
    esac
    shift
done

# Handle pipe if no text input
if [[ -z "$TEXT_INPUT" ]]; then
    if [[ ! -t 0 ]]; then
        TEXT_INPUT=$(cat)
    fi
fi

[[ -z "$TEXT_INPUT" ]] && exit 0

cd "$PROJECT_DIR" || exit

# 1. Health Check — Si no responde, arranca el servidor
CHECK=$(curl -s --max-time 1 -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health)

if [[ "$CHECK" != "200" ]]; then
    echo "🚀 Iniciando OmniVoice..."
    ./start_omnivoice.sh >/dev/null 2>&1
    sleep 6
fi

# 2. Construir JSON payload
# Si hay voice, incluirlo para resolver el preset (con ref_audio automático)
if [[ -n "$VOICE" ]]; then
    JSON_PAYLOAD=$(python3 -c "import json, sys; print(json.dumps({'text': sys.argv[1], 'voice': sys.argv[2]}))" "$TEXT_INPUT" "$VOICE")
else
    JSON_PAYLOAD=$(python3 -c "import json, sys; print(json.dumps({'text': sys.argv[1]}))" "$TEXT_INPUT")
fi

# 3. Inference
curl -X POST "http://127.0.0.1:$PORT/generate" \
     -H "Content-Type: application/json" \
     -d "$JSON_PAYLOAD" \
     --max-time 120 \
     --silent >/dev/null

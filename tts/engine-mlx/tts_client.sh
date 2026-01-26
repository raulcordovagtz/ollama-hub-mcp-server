#!/bin/zsh
# MLX Smart Server CLI Client v4.3
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

PROJECT_DIR="/Users/crotalo/desarrollo-local/server/tts/engine-mlx"
PORT=8007 # Default to Kokoro.

# Handle arguments or pipe
if [[ -z "$1" ]]; then
    TEXT_INPUT=$(cat)
else
    TEXT_INPUT="$*"
fi

[[ -z "$TEXT_INPUT" ]] && exit 0

cd "$PROJECT_DIR" || exit

# 1. Health Check
CHECK=$(curl -s --max-time 1 -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health)

if [[ "$CHECK" != "200" ]]; then
    echo "🚀 Starting services..."
    ./start_services.sh >/dev/null 2>&1
    sleep 4
fi

# 2. Secure JSON payload
TMP_FILE="/tmp/tts_cli_input_$(date +%s).txt"
echo "$TEXT_INPUT" > "$TMP_FILE"
JSON_PAYLOAD=$(python3 -c "import json; print(json.dumps({'text': open('$TMP_FILE').read()}))")
rm "$TMP_FILE"

# 3. Inference
curl -X POST "http://127.0.0.1:$PORT/generate" \
     -H "Content-Type: application/json" \
     -d "$JSON_PAYLOAD" \
     --max-time 90 \
     --silent >/dev/null

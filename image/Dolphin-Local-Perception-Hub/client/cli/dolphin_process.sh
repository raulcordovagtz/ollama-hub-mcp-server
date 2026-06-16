#!/bin/bash

# Configuration
SERVER_URL="http://localhost:8000"
INPUT_FILE="$1"
MODE="$2"
CUSTOM_OUTPUT_DIR="$3"

# Usage check
if [ -z "$INPUT_FILE" ] || [ -z "$MODE" ]; then
  echo "Usage: ./dolphin_process.sh <file_path> <mode> [output_dir]"
  echo "Modes: text, layout, table, formula, code, general"
  exit 1
fi

# Determine Prompt based on Mode
case $MODE in
  text)
    PROMPT="Extract all text from this image."
    ;;
  layout)
    PROMPT="Describe the layout and structure of this document."
    ;;
  table)
    PROMPT="Extract this table in Markdown format."
    ;;
  formula)
    PROMPT="Extract this math formula in LaTeX format."
    ;;
  code)
    PROMPT="Extract this code block."
    ;;
  general)
    PROMPT="Describe this image in detail."
    ;;
  *)
    echo "Unknown mode: $MODE"
    exit 1
    ;;
esac

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ORIGINAL_DIR=$(pwd)

# --- 1. PDF Handling (Simple Pre-process) ---
# If input is PDF, we warn user or try to convert. 
# For strict adherence to the requested architecture (shell orchestrator), 
# we will rely on the user providing images or add a python helper later.
# For now, we proceed assuming image-compatible input for base64.
EXTENSION="${INPUT_FILE##*.}"
if [[ "$EXTENSION" == "pdf" || "$EXTENSION" == "PDF" ]]; then
    echo "Processing PDF..."
    # We will let the post-processor handle multi-page logic or fail? 
    # Actually, the Server expects Base64 Image. 
    # We must convert PDF to Image here if we want to support it.
    # To keep this script simple and robust like wake_and_send.sh, strictly for images for now.
    echo "Error: This shell orchestrator currently supports Images only (jpg, png)."
    echo "Please convert PDF to image first or use the python client for advanced batching."
    exit 1
fi

# --- 2. Server Wake-on-LAN ---
echo "Checking server status..."
STATUS=$(curl -s --max-time 2 "$SERVER_URL/health" | jq -r '.status' 2>/dev/null)

if [ "$STATUS" != "READY" ]; then
  echo "Server is down/sleeping. Waking up..."
  
  # Launch Server from Root
  cd "$PROJECT_ROOT" || exit 1
  nohup python3 -m server.server > server.log 2>&1 &
  SERVER_PID=$!
  echo "Server launching (PID: $SERVER_PID)..."
  
  # Wait loop
  RETRIES=30
  while [ $RETRIES -gt 0 ]; do
    sleep 2
    STATUS=$(curl -s --max-time 2 "$SERVER_URL/health" | jq -r '.status' 2>/dev/null)
    if [ "$STATUS" == "READY" ]; then
      echo "Server is READY!"
      break
    fi
    echo "Waiting for model load... ($RETRIES)"
    ((RETRIES--))
  done
  
  if [ "$STATUS" != "READY" ]; then
    echo "Failed to start server. Check logs."
    exit 1
  fi
fi

# --- 3. Prepare Request ---
echo "Encoding image..."
IMAGE_BASE64=$(base64 < "$INPUT_FILE" | tr -d '\n')
SAFE_PROMPT=$(echo "$PROMPT" | sed 's/"/\\"/g')

# --- 4. Send Request ---
echo "Sending request (Mode: $MODE)..."
RESPONSE=$(curl -s -X POST "$SERVER_URL/api/interact" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": null,
    \"image_base64\": \"$IMAGE_BASE64\",
    \"prompt\": \"$SAFE_PROMPT\",
    \"generation_config\": {}
  }")

# Check curl success (basic)
if [ -z "$RESPONSE" ]; then
    echo "Error: Empty response from server."
    exit 1
fi

# Save raw response
# Generate ID based on timestamp
INF_ID=$(date +%Y%m%d_%H%M%S)

# Define Output Dir
if [ -z "$CUSTOM_OUTPUT_DIR" ]; then
    OUTPUT_BASE="$PROJECT_ROOT/server/image/outputs/Dolphin-Perception"
    OUTPUT_DIR="$OUTPUT_BASE/$INF_ID"
else
    OUTPUT_DIR="$CUSTOM_OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"
RAW_JSON_PATH="$OUTPUT_DIR/raw_response.json"
echo "$RESPONSE" > "$RAW_JSON_PATH"
echo "Raw response saved to: $RAW_JSON_PATH"

# --- 5. Post-Processing ---
echo "Running Post-Processing..."
python3 "$SCRIPT_DIR/postprocess_cli.py" "$RAW_JSON_PATH" "$INPUT_FILE" "$OUTPUT_DIR" "$MODE"

echo "Done."

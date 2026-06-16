#!/bin/bash

TEXT="$1"
VOICE="en"

shift

while [[ $# -gt 0 ]]; do
  case $1 in
    --voice|-v)
      VOICE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [ -z "$TEXT" ]; then
    echo "Uso: $0 \"texto a procesar\" [--voice nombre]"
    exit 1
fi

/opt/miniconda3/bin/python -c '
import urllib.request
import json
import sys

text = sys.argv[1]
voice = sys.argv[2]

data = json.dumps({
    "text": text,
    "voice": voice
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8008/generate",
    data=data,
    headers={"Content-Type": "application/json"}
)

try:
    urllib.request.urlopen(req)
except Exception as e:
    print(f"Error enviando a Supertonic: {e}")
' "$TEXT" "$VOICE"

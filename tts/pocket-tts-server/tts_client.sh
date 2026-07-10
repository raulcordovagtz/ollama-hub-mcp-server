#!/bin/bash
# Cliente por línea de comandos para Pocket TTS

TEXT="$1"
VOICE="alloy"

shift
while [[ $# -gt 0 ]]; do
  case $1 in
    --voice)
      VOICE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# Usamos Python para asegurar que los caracteres especiales se escapen correctamente en el JSON
/opt/miniconda3/bin/python -c '
import sys, json, urllib.request
text = sys.argv[1]
voice = sys.argv[2]
url = "http://127.0.0.1:8008/generate"
data = json.dumps({"text": text, "voice": voice}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    urllib.request.urlopen(req)
except Exception as e:
    print(f"Error al conectar con Pocket TTS: {e}")
' "$TEXT" "$VOICE"

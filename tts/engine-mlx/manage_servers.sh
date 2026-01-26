#!/bin/bash
# Bridge script for Automator compatibility

PROJECT_DIR="/Users/crotalo/desarrollo-local/server/tts/engine-mlx"
cd "$PROJECT_DIR" || exit 1

case "$1" in
    start)
        ./start_services.sh
        ;;
    stop)
        pkill -v -f "smart_server.py"
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac

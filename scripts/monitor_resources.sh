#!/bin/bash

# 🌡️ MONITOR DE COSTOS IA (Apple Silicon)
# Este script mide temperatura, presion termica y consumo de memoria.

echo "📊 Monitor de Recursos IA iniciado..."
echo "Presiona Ctrl+C para detener."
echo "------------------------------------------------"
echo "TIMESTAMP | THERMAL PRESSURE | MEMORY USED | ACTIVE SERVERS"
echo "------------------------------------------------"

while true; do
    TS=$(date +"%H:%M:%S")
    
    # Kernel Thermal Pressure (0=Normal, 1=Moderate, 2=Heavy)
    THERMAL=$(sysctl -n kern.thermal_pressure)
    case $THERMAL in
        0) T_LABEL="NORMAL" ;;
        1) T_LABEL="MODERATE" ;;
        2) T_LABEL="HEAVY/THROTTLING" ;;
        *) T_LABEL="UNKNOWN" ;;
    esac

    # Memoria Activa (Aproximada vía vm_stat)
    MEM_PAGES=$(vm_stat | grep "Pages active" | awk '{print $3}' | sed 's/\.//')
    MEM_GB=$(echo "scale=2; $MEM_PAGES * 4096 / 1024 / 1024 / 1024" | bc)

    # Contar servidores activos
    AUDIO=$(pgrep -f smart_server.py | wc -l | xargs)
    IMAGE=$(pgrep -f smart_image_server.py | wc -l | xargs)
    
    printf "%s | %-16s | %-10s | Audio:%s Image:%s\n" "$TS" "$T_LABEL" "${MEM_GB}GB" "$AUDIO" "$IMAGE"

    # Alarma si la presion termica es Heavy
    if [ "$THERMAL" -eq 2 ]; then
        echo "🚨 ALERTA: PRESION TERMICA ALTA. CONSIDERAR BOTON ROJO."
        afplay /System/Library/Sounds/Basso.aiff
    fi

    sleep 5
done

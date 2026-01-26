# MLX Audio Smart Server (v5.1 Productions) 🎙️⚡️

Este proyecto implementa un servidor de síntesis de voz (TTS) de ultra-alto rendimiento optimizado para Apple Silicon (M-Series) utilizando la librería `mlx-audio`.

## 🚀 Arquitectura Optimizada

Tras la evaluación de estabilidad, el sistema se ha consolidado en un único motor de alto rendimiento para garantizar latencia mínima e interferencia cero:

1. **Motor Kokoro (Puerto 8007)**:
    * **Propósito**: Producción principal, velocidad extrema y consumo eficiente.
    * **Idiomas**: Soporte nativo para Inglés, Español, Francés, Hindi, Italiano, Portugués, Japonés y Chino.
    * **Lógica**: Manejo de atributos `.audio` nativos optimizado para GPU MLX.

> **Nota sobre Qwen3/VibeVoice**: El motor de clonación de voz ha sido retirado del flujo de producción local debido a la inestabilidad en servidores compartidos. Sin embargo, el código y la configuración permanecen preservados en el historial de Git para futuros despliegues artísticos o procesamiento por lotes (Batch).

## 🛠️ Archivos Operativos

* `smart_server.py`: Servidor de inferencia unificado (v5.1).
* `server_config.json`: Configuración de voces y mapeo de idiomas.
* `start_services.sh`: Script de arranque (ahora exclusivamente Kokoro).
* `manage_servers.sh`: Puente de compatibilidad para flujos heredados (Automator).

## ⚙️ Uso desde Automator

El sistema es ideal para integración con MacOS Automator. Se recomienda usar `tts_client.sh` o realizar peticiones POST directas al puerto `8007`.

## 🔋 Características Master

* **Interrupción Instantánea**: Al enviar una nueva frase, la GPU corta el proceso anterior inmediatamente.
* **Higiene de GPU**: Ejecuta `mx.clear_cache()` tras cada inferencia para evitar degradación.
* **Detección Automática**: Identifica el idioma del texto y aplica el código de idioma (lang_code) y voz adecuados.

---
**Estado**: Producción Estable (Only Kokoro). 🏆
**Backup**: Qwen3 preservado en commit `1eb0f63`.

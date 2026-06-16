# MLX Audio Smart Server (v5.1 Productions) 🎙️⚡️

Este proyecto implementa un servidor de síntesis de voz (TTS) de ultra-alto rendimiento optimizado para Apple Silicon (M-Series) utilizando la librería `mlx-audio`.

## 🚀 Arquitectura Optimizada

Tras la evaluación de estabilidad y capacidades, el sistema utiliza múltiples motores de alto rendimiento para diferentes propósitos:

1. **Motor Kokoro (Puerto 8007)**:
    * **Propósito**: Producción principal, velocidad extrema y consumo eficiente.
    * **Idiomas**: Soporte nativo multilingüe.
    * **Lógica**: Manejo de atributos `.audio` nativos optimizado para GPU MLX.

2. **Motor OmniVoice (Puerto 8009)**:
    * **Propósito**: Capacidades avanzadas de **Clonación de Voz (Voice Cloning)** usando audio de referencia.
    * **Idiomas**: Soporte multilingüe expansivo.
    * **Lógica**: Utiliza un servidor dedicado para manejar la memoria adicional requerida.

> **Nota sobre Qwen3/VibeVoice**: El motor de clonación de voz (Qwen3) ha sido retirado del flujo de producción local debido a la inestabilidad en servidores compartidos. Sin embargo, el código y la configuración permanecen preservados en el historial de Git para futuros despliegues artísticos o procesamiento por lotes (Batch). OmniVoice ha tomado su lugar para las tareas de clonación.

## 🛠️ Archivos Operativos

### Motores y Servidores
* `smart_server.py`: Servidor de inferencia Kokoro (v5.1, Puerto 8007).
* `smart_server_omnivoice.py`: Servidor de inferencia OmniVoice (Puerto 8009).

### Configuraciones
* `server_config.json`: Configuración de voces para Kokoro.
* `server_config_omnivoice.json`: Configuración de mapeo de idiomas y audios de referencia (Clonación) para OmniVoice.

### Scripts de Gestión
* `start_services.sh`: Script de arranque (exclusivamente Kokoro).
* `start_omnivoice.sh`: Script de arranque (exclusivamente OmniVoice).
* `manage_servers.sh`: Puente de compatibilidad para flujos heredados (Automator).

## ⚙️ Uso desde Automator

El sistema es ideal para integración con MacOS Automator. Se recomiendan los siguientes clientes CLI:
* Para **Kokoro** (Velocidad): Usar `tts_client.sh`
* Para **OmniVoice** (Clonación): Usar `tts_client_omnivoice.sh`

## 🔋 Características Master

## 🔋 Características Master

* **Interrupción Instantánea**: Al enviar una nueva frase, la GPU corta el proceso anterior inmediatamente.
* **Higiene de GPU**: Ejecuta `mx.clear_cache()` tras cada inferencia para evitar degradación.
* **Detección Automática**: Identifica el idioma del texto y aplica el código de idioma (lang_code) y voz adecuados.
* **Auto-Arranque Inteligente**: Los scripts clientes (`tts_client.sh`, `tts_client_omnivoice.sh`) detectan automáticamente si el servidor está caído y lo reinician.

---
**Estado**: Producción Estable (Kokoro + OmniVoice). 🏆
**Backup**: Qwen3 preservado en commit `1eb0f63`.

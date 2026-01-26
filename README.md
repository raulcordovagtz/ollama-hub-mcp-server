# 🌐 Infraestructura de Servidores Inteligentes (v7.0)

Repositorio unificado para la gestión de servicios de IA local de grado industrial sobre Apple Silicon.

## 📁 Estructura del Proyecto

```text
server/
├── tts/              # Oído/Voz: Motor Kokoro (MLX) - Puerto 8007
├── image/            # Creación Visual: Z-Image / Flux2 - Puerto 8010
├── text/             # Pensamiento/Visión: Qwen3 / Granite - Puerto 8009
├── scripts/          # Motor de Control y Arranque
└── logs/             # Auditoría y Accounting centralizado
```

## 🛠️ Herramientas de Control (`scripts/`)

* **`emergency_stop.sh` (Botón Rojo):** Detención inmediata de procesos y vaciado de VRAM en Ollama.
* **`monitor_resources.sh`:** Vigilancia de presión térmica y memoria activa con alertas acústicas.
* **`start_image_server.sh` / `start_text_server.sh`:** Scripts de levantamiento en frío (Cold Start) usados por el bridge MCP.

## 🔌 Integración con Clientes

### 1. LM Studio (MCP)

El sistema expone 4 herramientas mediante el bridge `ollama-hub` (v1.0.5):

* `generate_image`: T2I optimizado (720px).
* `edit_image`: I2I + Edición tipográfica.
* `ollama_chat`: Inferencia LLM avanzada.
* `ollama_vision`: Análisis visual (VLM).

## 🚀 Estrategia de Ingeniería Industrial

1. **Protección de Hardware:** Uso de `max_workers=1` para serializar tareas pesadas.
2. **Límites de Inventario:** Cola FIFO de 10 posiciones para evitar saturación de memoria.
3. **Eficiencia Energética:** Estándar de 4 steps en imágenes y 720px de arista máxima.
4. **Auto-Arranque:** Las herramientas MCP despiertan los servicios solo cuando son necesarios, liberando recursos en reposo.

---
**Estado:** Producción Unificada y Estabilizada. 🏆

# 🌐 Infraestructura de Servidores Inteligentes (v7.1)

Repositario unificado para la gestión de servicios de IA local de grado industrial sobre Apple Silicon.

## 📁 Estructura del Proyecto

```text
server/
├── tts/              # Oído/Voz: Supertonic (Puerto 8008 Proxy / 8013 Interno) & Kokoro (Puerto 8007)
├── image/            # Creación Visual: Z-Image / Flux2 - Puerto 8012
├── text/             # Pensamiento/Visión: Qwen3 / Granite - Puerto 8009
├── diffusion/        # Generación por Difusión Discreta: DiffusionGemma - Puerto 8011
├── gemini-proxy/     # Proxy Traductor de APIs: Claude Code -> Gemini API - Puerto 1235
├── mcp-chuk/         # Smart Client STDIO -> HTTP para Lazarus MCP - Puerto 8010
├── skills/           # Skills Hub: Directorio central de skills MCP (symlinks + skills propios)
├── Skills_Hub/       # Reservado: Fork local de local-skills-mcp (uso futuro)
├── sync-skills.sh    # Sincronizador de symlinks desde plugins de Antigravity IDE → skills/
├── scripts/          # Motor de Control y Arranque
└── logs/             # Auditoría y Accounting centralizado
```

## 🛠️ Herramientas de Control (`scripts/`)

* **`emergency_stop.sh` (Botón Rojo):** Detención inmediata de procesos y vaciado de VRAM en Ollama.
* **`monitor_resources.sh`:** Vigilancia de presión térmica y memoria activa con alertas acústicas.
* **`start_image_server.sh` / `start_text_server.sh` / `start_diffusion_server.sh`:** Scripts de levantamiento en frío (Cold Start) usados por el bridge MCP.

## 🔌 Integración con Clientes

### 1. LM Studio (MCP)

El sistema expone 4 herramientas mediante el bridge `ollama-hub` (v1.0.5):

* `generate_image`: T2I optimizado (720px).
* `edit_image`: I2I + Edición tipográfica.
* `ollama_chat`: Inferencia LLM avanzada.
* `ollama_vision`: Análisis visual (VLM).

### 2. Claude Code CLI (vía gemini-proxy)

Puente Node.js que expone el puerto `1235` para traducir las llamadas nativas de Anthropic hacia Google Gemini API.
* **Inteligencia:** Inicia automáticamente al invocar los alias (`claud-gemini`, `claud-3flash`) y se apaga al cerrar la sesión de código para no gastar recursos.

### 3. Skills Hub (vía `local-skills-mcp`)

Servidor MCP universal (`local-skills-mcp` v1.x — npm global) que expone todos los skills del directorio `/skills/` a cualquier agente MCP compatible.
* **Protocolo:** STDIO puro (sin puerto ni proceso residente).
* **Cold Start Nativo:** No requiere proxy ni arranque manual. El cliente MCP lanza el proceso al invocar la primera herramienta y lo destruye al desconectar.
* **Single Source of Truth:** `SKILLS_DIR=/Users/crotalo/desarrollo-local/server/skills` es la raíz unificada. Los skills de Antigravity IDE se enlazan via symlinks con `sync-skills.sh`.
* **Herramienta expuesta:** `get_skill` — carga el contenido de cualquier skill bajo demanda (~50 tokens por nombre/descripción en idle).
* **Clientes activos:** LM Studio (`~/.lmstudio/mcp.json`) — Hermes harness y agentes locales (futuros).

---

### 4. Lazarus Interpretability Server (vía mcp-chuk)

Proxy inteligente (`lazarus_smart_client.py`) que actúa como puente bidireccional entre el protocolo STDIO estándar de MCP (Machine Context Protocol) y el servidor HTTP de Lazarus (`chuk-mcp-lazarus`) corriendo en el puerto `8010`.
* **Entorno Objetivo:** Apunta a la instalación aislada del entorno conda en `/opt/miniconda3/envs/MarketGraph-AI/`.
* **Inteligencia:** Implementa Cold Start. Despierta en segundo plano el servidor en el entorno objetivo antes de rutear el primer comando si detecta que está dormido.

## 🚀 Estrategia de Ingeniería Industrial

1. **Protección de Hardware:** Uso de `max_workers=1` para serializar tareas pesadas.
2. **Límites de Inventario:** Cola FIFO de 10 posiciones para evitar saturación de memoria.
3. **Eficiencia Energética:** Estándar de 4 steps en imágenes y 720px de arista máxima.
4. **Auto-Arranque (Cold Start):** Las herramientas MCP despiertan los servicios solo cuando son necesarios, liberando recursos en reposo.
5. **Arquitectura Zero-Residues (TTS):** Uso de Proxy Interceptor ultra-ligero (~10MB RAM) en puerto `8008`. Intercepta peticiones, enciende el modelo pesado de IA en el puerto interno `8013`, reproduce el audio directamente, y apaga el servidor interno (`os._exit`) tras 20 min de inactividad, sin dejar rastros en disco duro ni logs (silenciados hacia `/dev/null`).

---
**Estado:** Producción Unificada y Estabilizada. 🏆

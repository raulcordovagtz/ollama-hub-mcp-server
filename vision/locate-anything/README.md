# 👁️ vision/locate-anything

Servidor MCP local para localización visual de objetos con **bounding boxes** usando `nvidia/LocateAnything-3B` sobre **Apple Silicon MPS**.

## Filosofía

Servidor **muerto por defecto, vive bajo demanda** — se despierta automáticamente cuando un cliente MCP invoca la herramienta `locate_objects`, y se apaga solo tras **20 minutos de inactividad**.

## Arquitectura

```text
Cliente MCP (LM Studio / Antigravity IDE)
    ↓ STDIN — JSON-RPC 2.0 (protocolo MCP estándar)
locate_smart_client.py      ← Proxy STDIO (Cold Start)
    ↓ HTTP POST /locate
locate_server.py            ← FastAPI HTTP (Puerto 8014)
    ↓ PyTorch MPS
nvidia/LocateAnything-3B    ← Modelo VLM en Apple Silicon
    ↓
Respuesta MCP: texto + imagen anotada con recuadros numerados
```

## Hardware

| Requisito | Valor |
|---|---|
| Hardware | Apple Silicon (M1 / M2 / M3 / M4) |
| Backend | PyTorch MPS |
| Precisión | float16 (bfloat16 no estable en MPS) |
| RAM Unificada | Mínimo 16 GB (recomendado 32 GB+) |
| CPU Fallback | ❌ No disponible (modelo no operable en CPU) |

## Instalación

### 1. Crear entorno Conda e instalar dependencias

```bash
cd /Users/crotalo/desarrollo-local/server/vision/locate-anything
./install_deps.sh
```

Esto crea el entorno `locate-anything` con Python 3.11 e instala: `torch`, `transformers==4.57.1`, `fastapi`, `uvicorn`, `Pillow`, `deep-translator`, `huggingface_hub`.

### 2. Descargar el modelo (~6-7 GB)

```bash
./download_model.sh
```

El modelo se descarga al caché estándar de HuggingFace (`~/.cache/huggingface/`). El servidor lo carga desde ahí automáticamente.

Para verificar si ya está descargado:
```bash
./download_model.sh --check
```

## Herramienta MCP: `locate_objects`

### Parámetros

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `image_path` | string | ✅ | Ruta absoluta a la imagen (JPG, PNG, WebP, etc.) |
| `prompt` | string | ✅ | Descripción en cualquier idioma. Se auto-traduce al inglés. |
| `task` | string | — | Modo de detección (ver tabla abajo). Default: `ground` |
| `categories` | array | — | Lista de categorías para `task=detect` |
| `generation_mode` | string | — | `hybrid` (default), `fast`, `slow` |

### Modos de tarea (`task`)

| task | Descripción | Ejemplo de prompt |
|---|---|---|
| `ground` | Grounding multi-instancia (default) | `"person"`, `"red car"`, `"gato naranja"` |
| `ground_single` | Grounding una sola instancia | `"the person on the left"` |
| `detect` | Detección multi-categoría | `categories: ["person", "car", "bike"]` |
| `text` | Detectar texto en la imagen | (el prompt se ignora) |
| `gui` | Elementos de UI en screenshots | `"submit button"`, `"botón de búsqueda"` |
| `point` | Localización por punto | `"the traffic light"` |

### Modos de generación

| Modo | Descripción |
|---|---|
| `hybrid` | MTP paralelo con fallback AR. Mejor relación velocidad/precisión. |
| `fast` | Solo MTP paralelo. Más rápido, mejor para escenas simples. |
| `slow` | Solo autoregresivo. Más robusto para escenas complejas. |

## Configuración en LM Studio

Añade al archivo `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "locate-anything": {
      "command": "/opt/miniconda3/envs/locate-anything/bin/python3",
      "args": [
        "/Users/crotalo/desarrollo-local/server/vision/locate-anything/locate_smart_client.py"
      ]
    }
  }
}
```

## Configuración en Antigravity IDE

En la configuración MCP de Antigravity IDE:

```json
{
  "name": "locate-anything",
  "command": "/opt/miniconda3/envs/locate-anything/bin/python3",
  "args": [
    "/Users/crotalo/desarrollo-local/server/vision/locate-anything/locate_smart_client.py"
  ]
}
```

## Pruebas con `curl`

### Verificar estado del servidor

```bash
curl http://127.0.0.1:8014/health
```

### Detectar personas en una imagen

```bash
curl -X POST http://127.0.0.1:8014/locate \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/Users/crotalo/Pictures/test.jpg",
    "prompt": "person",
    "task": "ground"
  }'
```

### Grounding con prompt en español (auto-traducción)

```bash
curl -X POST http://127.0.0.1:8014/locate \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/Users/crotalo/Pictures/screenshot.png",
    "prompt": "botón de enviar formulario",
    "task": "gui"
  }'
```

### Detección multi-categoría

```bash
curl -X POST http://127.0.0.1:8014/locate \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/Users/crotalo/Pictures/street.jpg",
    "prompt": "vehicles",
    "task": "detect",
    "categories": ["car", "bus", "bicycle", "motorcycle"]
  }'
```

## Respuesta del servidor

```json
{
  "status": "success",
  "task_id": "b193a4c3",
  "task": "ground",
  "prompt_translated": "the falcon's claws",
  "boxes": [
    { "x1": 210, "y1": 807, "x2": 271, "y2": 909 },
    { "x1": 277, "y1": 802, "x2": 351, "y2": 884 }
  ],
  "points": [],
  "raw_answer": "<box><210>...<box>",
  "annotated_image_path": "/Users/crotalo/desarrollo-local/server/vision/locate-anything/outputs/b193a4c3.jpg",
  "summary": "Encontrados 2 recuadro(s) para 'las garras del halcon':\n#1: (210, 807) → (271, 909)\n#2: (277, 802) → (351, 884)",
  "duration_seconds": 20.97,
  "error": null
}
```

La imagen `annotated_image_base64` contiene la imagen original con:
- Recuadros de colores diferentes por elemento
- Etiqueta `#N` en cada recuadro
- Transparencia semi-opaca en el encabezado del recuadro

## Archivos del módulo

```text
vision/locate-anything/
├── locate_server.py        # Servidor FastAPI HTTP (Puerto 8014)
├── locate_smart_client.py  # Proxy STDIO MCP (Cold Start)
├── install_deps.sh         # Instala venv y dependencias
├── download_model.sh       # Descarga el modelo de HuggingFace
├── requirements.txt        # Lista de dependencias Python
├── outputs/                # Imágenes anotadas (opcional)
```

## Logs

- Inferencias: `/Users/crotalo/desarrollo-local/server/logs/locate/inferences.log`
- Arranque del servidor: `~/locate_server_boot.log`
- Servidor principal: `/Users/crotalo/desarrollo-local/server/logs/locate/server.log`

## Notas sobre el modelo

- **Licencia:** NVIDIA License — solo para investigación y uso no-comercial.
- **Idioma:** Entrenado principalmente en inglés. Los prompts se auto-traducen.
- **Resolución:** Soporta hasta 2.5K. Imágenes de alta resolución tardan más.
- **Precisión de coordenadas:** Los bounding boxes se retornan normalizados en [0, 1000] y se convierten a píxeles automáticamente.
- **Backends no soportados:** `la_flash` (FlashAttention sparse) es CUDA-only. En MPS se usa `sdpa` de PyTorch (totalmente funcional, sin CUDA extensions).

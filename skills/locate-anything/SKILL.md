---
name: locate-anything
description: >
  Mejores prácticas y tutoría de operación para el servidor local MCP locate-anything.
  Usa este skill cuando el usuario pida ayuda para usar la herramienta locate_objects,
  quiera entender cómo funciona el grounding visual, cómo detectar elementos de UI,
  o cómo estructurar prompts para maximizar la precisión del modelo nvidia/LocateAnything-3B.
---

# locate-anything — Guía de Operación y Mejores Prácticas

Este documento contiene las reglas y mejores prácticas para operar el servidor MCP `locate-anything` (basado en `nvidia/LocateAnything-3B`) a través de la herramienta `locate_objects`.

## 1. Modos de Operación (`task`)

El modelo soporta múltiples modos según lo que se necesite localizar. Elige el `task` correcto:

*   **`ground` (Default)**: Busca **múltiples instancias** que coincidan con la frase. Ideal para descripciones generales.
    *   *Ejemplo:* `prompt: "person"`, `prompt: "red car"`
*   **`ground_single`**: Obliga al modelo a buscar **solo la mejor coincidencia única**. Útil cuando sabes que solo hay un elemento específico que te interesa.
    *   *Ejemplo:* `prompt: "the largest person"`, `prompt: "the submit button at the bottom"`
*   **`detect`**: Detección clásica de clases. Requiere enviar el array `categories`.
    *   *Ejemplo:* `prompt: "vehicles"`, `categories: ["car", "bus", "truck"]`
*   **`gui`**: Optimizado para interfaces de usuario y capturas de pantalla. El modelo ha sido fine-tuneado para entender botones, campos, iconos, etc.
    *   *Ejemplo:* `prompt: "search icon"`, `prompt: "email input field"`
*   **`text`**: Detección de texto genérico (OCR de cajas). El prompt descriptivo se ignora.
*   **`point`**: Devuelve una sola coordenada `(x, y)` en lugar de un bounding box. Útil para emular clicks.

## 2. Idioma de los Prompts

El modelo `LocateAnything-3B` fue entrenado **estrictamente en inglés**. Sin embargo, el servidor incluye traducción automática (`deep-translator`).

**Mejor práctica:**
Puedes enviar el prompt en español o cualquier otro idioma y el servidor lo traducirá al vuelo antes de la inferencia. Si notas imprecisiones o pérdida de contexto en descripciones complejas, envía el prompt **directamente en inglés**.

*   *Evitar:* `"el botón azul cuadrado con el ícono de una casita en la esquina superior derecha"`
*   *Preferir (si falla lo anterior):* `"blue square home button at top right"`

## 3. Coordenadas y Tamaño de Imagen

*   El servidor acepta imágenes de alta resolución (hasta 2.5K). Imágenes más grandes tardarán más en procesarse y ocuparán más RAM.
*   El modelo internamente usa coordenadas normalizadas (0 a 1000). El servidor automáticamente hace la matemática para devolver las coordenadas en **píxeles reales** relativos al tamaño original de la imagen que enviaste.
*   Puedes usar los bounding boxes devueltos `(x1, y1, x2, y2)` para recortar imágenes (`PIL.Image.crop`) o como entrada para otros modelos locales (ej: editar solo esa parte con Flux I2I).

## 4. Filosofía "Cold Start"

Es importante saber (y transmitir al usuario si pregunta por latencia) que el servidor vive **bajo demanda**.

1.  **Primer uso:** Al enviar la primera imagen, la petición puede tardar entre **20 y 40 segundos** extra, ya que el modelo de 3B parámetros se debe cargar desde el disco a la memoria unificada de Apple Silicon (MPS).
2.  **Usos subsecuentes:** Serán mucho más rápidos (3-8 segundos dependiendo de la imagen).
3.  **Apagado:** Tras 20 minutos de inactividad, el servidor se "suicida" (`os._exit`) para liberar RAM. No deja procesos fantasma consumiendo recursos.

## 5. Modos de Inferencia (`generation_mode`)

*   `hybrid` (Por defecto): Recomendado. Intenta decodificación paralela rápida (MTP) y cae a autoregresivo clásico si la caja es ambigua.
*   `fast`: Fuerza la decodificación paralela completa. Mucho más rápido, pero puede perder algo de precisión en escenas muy desordenadas o pequeñas. Útil si procesas video frame a frame o necesitas latencia baja extrema.
*   `slow`: Autoregresivo completo. Lento pero la mayor precisión posible.

## 6. Integración con Agentes

Cuando uses `locate_objects` como agente para resolver una tarea:

1.  **Revisa la imagen anotada:** El servidor guardará la imagen en la carpeta `outputs/` y te devolverá la ruta absoluta en `annotated_image_path`. Puedes abrir esa imagen para verificar visualmente los recuadros dibujados y numerados (`#1`, `#2`, etc.).
2.  **Referencia por ID:** En la respuesta de texto, tendrás el resumen con las coordenadas. Usa el número (ej: `"Encontré el botón en el recuadro #2"`) para mantener el contexto con el usuario.
3.  **Encadenamiento de Herramientas:** Si el usuario pide "encuentra el botón y descríbelo", primero usas `locate_objects` para obtener las coordenadas, luego usas un script Python local (`execute_python`) para recortar la imagen original usando esas coordenadas, y finalmente envías ese recorte a `ollama_vision` para describirlo.

## 7. Uso Directo desde Terminal (MCP Proxy)

Dado que la arquitectura establece que el servidor está **muerto por defecto** (se apaga a los 20 minutos de inactividad para liberar RAM), hacer un `curl` directo por HTTP puede fallar si el servidor ya durmió. 

La forma correcta de usarlo en terminal es canalizando un JSON-RPC por STDIN al proxy (`locate_smart_client.py`), que se encarga de encender el servidor si es necesario:

```bash
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "locate_objects", "arguments": {"image_path": "/Users/crotalo/Documents/ComfyUI/input/9fd137579cbb3b01cbf7d981908d0740.jpg", "prompt": "face", "task": "ground_single"}}}' | /opt/miniconda3/envs/locate-anything/bin/python3 /Users/crotalo/desarrollo-local/server/vision/locate-anything/locate_smart_client.py
```

**Respuesta del Proxy:**
El proxy devolverá la salida de la herramienta MCP, que incluye el resumen, las coordenadas, y una ruta **absoluta al archivo** `annotated_image_path` guardado en el directorio `outputs`. (No devolvemos base64 para no saturar el contexto de los modelos).

```json
{
  "status": "success",
  "task_id": "8f3a9b1c",
  "task": "ground_single",
  "prompt_translated": "face",
  "boxes": [
    { "x1": 420, "y1": 150, "x2": 580, "y2": 320 }
  ],
  "points": [],
  "raw_answer": "<box><420><150><580><320></box>",
  "annotated_image_path": "/Users/crotalo/desarrollo-local/server/vision/locate-anything/outputs/8f3a9b1c.jpg",
  "summary": "Encontrados 1 recuadro(s) para 'face':\n#1: (420, 150) → (580, 320)",
  "duration_seconds": 4.52,
  "error": null
}
```

> **Nota:** La clave utilizada para mandar la imagen es `image_path` y debe ser una **ruta absoluta**. No se puede enviar la imagen codificada en la petición para mantener el tamaño del payload bajo.

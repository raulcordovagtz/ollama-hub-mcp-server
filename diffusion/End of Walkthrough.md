# 🧬 Integración de DiffusionGemma - Walkthrough

Hemos completado la integración del modelo de difusión de texto `diffusiongemma-26B-A4B-it-4bit` bajo la nueva categoría `diffusion`. El sistema ahora corre exitosamente sobre Apple Silicon utilizando `mlx-vlm==0.6.3`.

---

## 🛠️ Cambios Realizados

1. **Entorno de Python (`mlx_unified`):**
   - Actualización exitosa de `mlx-vlm` de `0.4.3` a `0.6.3` para dar soporte a la arquitectura de difusión discreta de Google DeepMind.

2. **Servidor Inteligente:**
   - [smart_diffusion_server.py](file:///Users/crotalo/desarrollo-local/server/diffusion/engine-mlx/smart_diffusion_server.py): Servidor FastAPI dedicado en el puerto `8011` con carga diferida (lazy loading), cola de ejecución serializada (`ThreadPoolExecutor(max_workers=1)`) para protección térmica, monitor de auto-inactividad de 1200 segundos (20 min) y logs centralizados.

3. **Documentación:**
   - [MODEL_GUIDE.md](file:///Users/crotalo/desarrollo-local/server/diffusion/MODEL_GUIDE.md): Guía de arquitectura, muestreo y particularidades operativas del modelo DiffusionGemma.
   - [README.md](file:///Users/crotalo/desarrollo-local/server/README.md): Actualización de la infraestructura a la versión **v7.1**, listando la nueva categoría en el puerto `8011` y los scripts de arranque correspondientes.

4. **Scripts de Control:**
   - [start_diffusion_server.sh](file:///Users/crotalo/desarrollo-local/server/scripts/start_diffusion_server.sh): Script de arranque en segundo plano (`nohup`) para el bridge MCP o carga manual.
   - [emergency_stop.sh](file:///Users/crotalo/desarrollo-local/server/scripts/emergency_stop.sh): Botón rojo actualizado para incluir el proceso `smart_diffusion_server.py` y liberar los puertos en el rango ampliado `8007-8011`.

---

## 🧪 Pruebas y Resultados de Verificación

### 1. Inferencia Directa por CLI

Ejecutamos una prueba directa en terminal usando el módulo nativo de generación de `mlx-vlm` con la versión 0.6.3:

```bash
/opt/miniconda3/envs/mlx_unified/bin/python -m mlx_vlm.generate \
  --model /Users/crotalo/.lmstudio/models/mlx-community/diffusiongemma-26B-A4B-it-4bit \
  --max-tokens 50 \
  --prompt "¿Por qué el cielo es azul?"
```

- **Resultado:** Éxito. Generación limpia de 50 tokens a **13.9 tokens/s** (prompt process: 50.7 tokens/s).
- **Consumo de Memoria:** Peak Memory de **17.47 GB**.

### 2. Levantamiento y Health Check del Servidor

Iniciamos el servidor con el script de control y validamos el estado inicial:

```bash
/Users/crotalo/desarrollo-local/server/scripts/start_diffusion_server.sh
curl http://127.0.0.1:8011/health
```

- **Respuesta:**

  ```json
  {"status":"ok","ready":false,"model":"diffusiongemma-26B-A4B-it-4bit","engine":"mlx-vlm"}
  ```

  *(El estado `ready: false` confirma que el modelo se mantendrá descargado hasta recibir la primera llamada para optimizar el uso de VRAM)*

### 3. Prueba Endpoint `/chat` (Carga diferida + Inferencia)

Realizamos una petición POST simulando a un cliente inteligente:

```bash
curl -X POST http://127.0.0.1:8011/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "¿Por qué el cielo es azul?", "max_tokens": 100}'
```

- **Logs del servidor (`logs/diffusion/server.log`):**
  - Carga el modelo en 5.4 segundos (haciendo sonar el sonido local del sistema `afplay Ping`).
  - Inferencia completada en **12.06s** (generando a **26.08 tokens/s**).
- **Respuesta API:**

  ```json
  {
    "status": "success",
    "task_id": "16c5b66e",
    "response": {
      "text": "El cielo es azul debido a un fenómeno llamado **dispersión de Rayleigh**...\n...",
      "prompt_tokens": 37,
      "generation_tokens": 100,
      "total_tokens": 137,
      "generation_tps": 26.07901687863504,
      "peak_memory": 17.657328317,
      "diffusion_denoising_steps": 11
    },
    "meta": {
      "duration": 12.06,
      "model": "diffusiongemma-26B-A4B-it-4bit",
      "engine": "mlx-vlm"
    }
  }
  ```

- **Accounting logs (`logs/diffusion/inference.log`):**
  Se registra correctamente el entry correspondiente:

  ```json
  {"timestamp": "2026-06-11 09:02:44", "task_id": "16c5b66e", "model": "diffusiongemma-26B-A4B-it-4bit", "mode": "DIFFUSION", "duration": 12.06, "max_tokens": 100}
  ```

### 4. Botón Rojo / Parada de Emergencia

Ejecutamos el script de limpieza para liberar memoria y recursos:

```bash
/Users/crotalo/desarrollo-local/server/scripts/emergency_stop.sh
```

- **Resultado:** El servidor es detenido exitosamente, los procesos finalizan y el puerto `8011` queda libre (validado mediante re-intento de curl con error de conexión).

# 🧠 Guía Maestra de Texto y Visión (Ollama Infrastructure)

Este documento detalla la operación del servidor de inferencia lingüística y visual (VLM).

---

## 🚀 Perfiles de Modelos

### 1. `qwen3:8b` (5.2 GB)

**Especialidad:** Razonamiento balanceado y Creatividad.

* **Perfil:** El "Intelectual Ágil".
* **Fortalezas:** Excelente en español, responde rápido y consume pocos recursos. Ideal para resúmenes, chats generales y poesía.
* **Contexto:** Cargado por defecto para herramientas de chat MCP.

### 2. `qwen3-vl:32b` (20 GB)

**Especialidad:** Análisis Visual Profundo (VLM).

* **Perfil:** El "Ojo Crítico".
* **Fortalezas:** Capaz de describir detalles minúsculos en imágenes, realizar OCR de alta precisión y entender diagramas complejos.
* **Costo de Hardware:** Muy Alto. Durante su uso, la VRAM estará al límite. Se recomienda no realizar tareas de imagen simultáneas.

---

## ⚙️ Arquitectura del Servidor (v6.8)

El servidor en el puerto **8009** gestiona la inteligencia lingüística:

1. **Dualidad Chat/Vision:** Detecta automáticamente si el request incluye imágenes para invocar el motor VLM.
2. **Accounting:** Registra cada inferencia en `/logs/text/inference.log` con duración y conteo de tokens.
3. **Serialización:** Al igual que el de imagen, procesa 1 a 1 para proteger la CPU del MacBook.

---

## ✍️ Prompt Engineering Lingüístico

1. **System Prompts:** El servidor soporta prompts de sistema para definir personalidad.
2. **Visión:** Para mejores resultados en VLM, indicar siempre la ruta absoluta del archivo y una pregunta específica (ej: "¿Qué texto hay en el cartel?").

---
**Nota:** El uso del modelo de 32B puede disparar alertas en el `monitor_resources.sh`. Monitorear la presión térmica es obligatorio en sesiones largas.

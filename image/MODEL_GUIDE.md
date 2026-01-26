# 🎨 Guía Maestra de Generación de Imagen (Ollama Infrastructure)

Este documento sirve como base técnica y estratégica para la operación de los modelos de imagen en el servidor inteligente de producción local.

---

## 🚀 Perfiles de Modelos

### 1. `x/z-image-turbo` (12 GB)
**Especialidad:** Realismo Fotográfico y Escenas Generales.
*   **Perfil:** El "Fotógrafo Maestro".
*   **Fortalezas:** Texturas de piel realistas, iluminación de estudio, paisajes naturales y renderizado de texto bilingüe (EN/ZH). 
*   **Recomendación de Uso:** Úsalo como modelo principal para **Text-to-Image** cuando necesites una imagen desde cero que se sienta "real" o cinematográfica.
*   **Costo de Hardware:** Alto (12 GB VRAM). Mantener monitorizado el sistema si se envían ráfagas.

### 2. `x/flux2-klein` (5.7 GB)
**Especialidad:** Edición Estructural y Tipografía.
*   **Perfil:** El "Arquitecto y Editor".
*   **Fortalezas:** Excelente seguimiento de instrucciones complejas, renderizado de texto estilizado y alta consistencia en flujos de **Image-to-Image**.
*   **Recomendación de Uso:** Ideal para **Edición (Image+Text)**. Si ya tienes una base y quieres añadir elementos o texto específico sin que la composición se rompa, este es el vehículo adecuado.
*   **Costo de Hardware:** Moderado (5.7 GB VRAM). Muy ágil para previsualizaciones rápidas.

---

## ✍️ Compendio de Prompt Engineering (Criterio Local)

Para maximizar el rendimiento de la GPU de Apple y evitar el estrangulamiento térmico, se sugieren los siguientes lineamientos:

1.  **Regla de Oro de Resolución:** 
    *   Mantener una arista máxima de **720px**. 
    *   Para borradores ultra-veloces, solicitar tamaños inferiores a **450px**.
2.  **Economía de Pasos (Steps):**
    *   Ambos modelos rinden de forma excepcional con **4 steps**. 
    *   Subir a 8 steps solo si se detectan artefactos en texturas muy finas. Más de 10 steps suele ser un desperdicio de energía en estos modelos "Turbo/Klein".
3.  **Encapsulamiento del Prompt:**
    *   Ser descriptivo pero conciso.
    *   Para `flux2`, usar un lenguaje directo de "acción" para ediciones (ej: "Add a neon sign saying 'Edison'").
4.  **Uso del Prompt Negativo:**
    *   Utilizar para limpiar el "ruido" visual: `distorted, blurry, low quality, deformed`.

---

## 🌡️ Gestión de Costos y Recursos

*   **Límite de Seguridad (80%):** Siempre dejar un margen de VRAM para el sistema. Evitar cargar ambos modelos simultáneamente si no se cuenta con +32GB de memoria unificada.
*   **Boton Rojo:** Si la presión térmica sube a nivel "Heavy" según el `monitor_resources.sh`, detener la cola inmediatamente.
*   **FIFO (Cola de 10):** El servidor procesará por orden de llegada. No enviar más de 10 trabajos si el tiempo de respuesta sube mas allá de los 60 segundos por imagen.

---

**Nota:** Estos criterios son recomendaciones técnicas basadas en la estabilidad del sistema, no leyes absolutas. El usuario/agente es libre de experimentar con los límites del hardware bajo supervisión del monitor de recursos.

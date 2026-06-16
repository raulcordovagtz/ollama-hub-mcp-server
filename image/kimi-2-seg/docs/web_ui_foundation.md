# Documento Técnico Fundacional: Interfaz de Percepción Visual

## Proyecto: SimpleSeg-Kimi-VL Web Interaction Layer

**Versión:** 1.0  
**Estado:** Requerimientos de Diseño y Conectividad

---

## 1. Visión del Producto

Desarrollar una interfaz web de alta fidelidad que actúe como un **Estudio de Segmentación Inteligente**. La UI debe combinar la flexibilidad de un chat de lenguaje natural con las capacidades de edición vectorial de una herramienta profesional (estilo Adobe Illustrator/Photoshop), permitiendo el refinamiento humano sobre las predicciones de la IA.

## 2. Capas de Conectividad (The Bridge)

### A. Capa de Activación (Wake-up Layer)

La UI no debe asumir que el servidor está encendido. Debe implementar un middleware (posiblemente en Node.js o Python) que replique la lógica de `wake_and_send.sh`:

- **Protocolo de Salud:** Consulta frecuente a `/health`.
- **Trigger de Inicio:** Si el servidor está apagado, ejecutar el comando de fondo `python -m server.server`.
- **Visual Feedback:** Mostrar un "Spinner de Calentamiento" mientras el modelo se carga en VRAM.

### B. Comunicación con el Núcleo (API Bridge)

- **Endpoint Cliente -> Servidor:** `POST /api/interact`.
- **Payload:**
  - `image_base64`: Captura del canvas actual.
  - `prompt`: Texto del chat.
  - `session_id`: Para mantener el hilo de la conversación.
  - `generation_config`: Parámetros dinámicos (temperatura, etc.).

### C. Capa de Post-procesamiento Web (Web Post-process)

En lugar de recibir archivos estáticos, la UI consumirá el JSON crudo del servidor y lo procesará en el cliente:

- **Traductor de Coordenadas:** Función JS que mapea los puntos normalizados `[0,1]` al tamaño real del elemento `canvas` en pantalla.
- **Layering System:** Cada nueva inferencia que contenga polígonos debe instanciarse como una nueva "Capa Vectorial" independiente.

---

## 3. Especificaciones de la Interfaz (UI/UX)

### A. Panel de Chat (Natural Language Hub)

- **Visual:** Estilo burbujas de conversación modernas.
- **Funcionalidad:** Renderizado de Markdown para las respuestas del modelo.
- **Historial:** Persistencia de la sesión mediante el `session_id` del servidor.

### B. Canvas de Percepción (Smart Illustrator)

El componente central debe ser un canvas híbrido (Vectores sobre Raster):

- **Motor Vectorial:** Uso de librerías como **Fabric.js** o **Paper.js** para permitir:
  - **Edición de Nodos:** Arrastrar puntos generados por el modelo para ajustar el borde.
  - **Curvas de Bézier/Splines:** Conversión automática de nubes de puntos a trazados suaves con manejadores de tangencias.
  - **Herramientas Manuales:** Pluma (Pen tool), Borrador de puntos y Añadir puntos.
- **Layer Stack:** Lista de capas a la derecha, permitiendo ocultar, bloquear o cambiar la opacidad de los polígonos detectados.

### C. Tab de Configuración (Model Control)

Panel deslizable para ajustar el comportamiento del "Cerebro":

- **System Prompt:** Editor de texto para redefinir el rol del modelo.
- **Parámetros Técnicos:**
  - `Temperature` (Slider 0.0 - 1.0)
  - `Repetition Penalty` (Slider 1.0 - 2.0)
  - `Max New Tokens` (Input numérico)

---

## 4. Contrato de Datos (Data Contract)

La UI debe estar preparada para interpretar la siguiente estructura extendida de metadata:

```json
{
  "raw_text_output": "Texto conversacional + [[[...coords...]]]",
  "metadata": {
    "inference_id": "uuid-v4",
    "duration_seconds": 12.5,
    "vram_usage_mb": 31500,
    "session_id": "user-unique-session"
  }
}
```

---

## 5. Requerimientos de Stitch (Diseño Visual)

Se recomienda utilizar el sistema de generación de pantallas de **Stitch** para prototipar los siguientes estados:

1. **Vista de Inicio:** Dropzone para imágenes y prompt inicial.
2. **Dashboard Principal:** Canvas central, chat a la izquierda, herramientas manuales arriba y capas a la derecha.
3. **Estado de Inferencia:** Overlay sutil indicando que el "Oracle" está procesando puntos.
4. **Modo Edición:** Visualización de nodos y manejadores de tangencia sobre el polígono seleccionado.

---

## 6. Conclusión Técnico-Operativa

Esta interfaz no es solo un visor de resultados, sino un **editor colaborativo Humano-IA**. La clave del éxito reside en la latencia mínima de la capa de activación y en la capacidad de "re-inyectar" las correcciones manuales del usuario en futuras iteraciones del prompt si fuera necesario.

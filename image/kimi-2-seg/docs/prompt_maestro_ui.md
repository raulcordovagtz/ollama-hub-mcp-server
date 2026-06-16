# Prompt Maestro: Desarrollo de la Web UI "SimpleSeg Studio"

Copia y pega este prompt en tu agente de desarrollo frontend preferido (v0.dev, Cursor, Claude 3.5 Sonnet, etc.) para generar la interfaz avanzada.

---

### 📋 PROMPT MAESTRO

**Rol:** Eres un **Senior Frontend Engineer & UX Designer** especializado en herramientas creativas (estilo Figma/Canva) y visualización de datos de IA.

**Objetivo:** Crear una Web App ("SimpleSeg Studio") que sirva como interfaz gráfica para un modelo de segmentación local profesional.

**Stack Tecnológico Obligatorio:**

* **Framework:** React + Vite (o Next.js).
* **Estilos:** Tailwind CSS (Diseño Profesional / Dark Mode).
* **Canvas/Vectores:** **Fabric.js** (CRÍTICO: Para la manipulación de polígonos y capas).
* **Estado:** Zustand o React Context.
* **Conectividad:** Axios/Fetch para hablar con el API local.

---

### 1. ARQUITECTURA DEL SISTEMA

La UI habla con un **Núcleo de Inferencia Local** en `http://localhost:8000`.

**Debes gestionar 3 estados críticos:**

1. **DORMIDO (Server Off):** Mostrar botón "Iniciar Motor". (Llama a un endpoint de activación).
2. **CALENTANDO (Warming):** Mostrar spinner/loader mientras haces polling a `/health`.
3. **LISTO (Ready):** Dashboard completo (Chat + Canvas).

---

### 2. ESTRUCTURA DE LA INTERFAZ (Layout Split)

* **Izquierda (30%): Panel de Chat.** Burbujas de chat, soporte Markdown, input de texto.
* **Centro (50%): Canvas Interactivo (Fabric.js).**
  * Imagen de fondo bloqueada.
  * Polígonos vectoriales editables encima.
  * Soporte para edición de nodos y tangencias (Splines).
* **Derecha (20%): Panel de Capas.** Lista de polígonos (ocultar/mostrar) y parámetros del modelo (Temperatura, Penalty, etc.).

---

### 3. CONTRATO DE DATOS (API Bridge)

**A. Envío de Petición:**
POST a `/api/interact`

```json
{
  "session_id": "uuid-v4",
  "prompt": "Texto del usuario",
  "image_base64": "...",
  "generation_config": { "temperature": 0.7 }
}
```

**B. Recepción y Parseo:**
El servidor devuelve texto crudo que contiene coordenadas. Ejemplo: `Aquí está el área: [[[0.1, 0.2]...]]`.

1. Extrae el texto para el chat.
2. Extrae los puntos `[[[x,y],...]]`.
3. Convierte coordenadas normalizadas (0-1) a píxeles del canvas.
4. Dibuja un `fabric.Polygon` editable.

---

### 4. PRIORIDADES DE IMPLEMENTACIÓN

1. Configura el Store para los estados de conexión global.
2. Crea la lógica de Polling a `/health`.
3. Implementa el Canvas de Fabric.js con soporte para "Nuevas Capas" por cada respuesta.
4. Crea la función `parseModelResponse` (Regex es recomendada).

**Nota de Diseño:** Usa una estética tipo "Adobe Creative Cloud" o "VS Code Dark". Mantén los polígonos con un fill semitransparente (rgba 255,0,0,0.3) y outline sólido.

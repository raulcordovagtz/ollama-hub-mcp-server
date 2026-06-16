# Claude-Gemini Proxy Server

Este servidor actúa como puente entre **Claude Code** (Anthropic API format) y **Google Gemini API**. Permite usar modelos de Gemini directamente en la CLI de Claude.

## 🚀 Instalación y Configuración

El servidor está ubicado en: `/Users/crotalo/desarrollo-local/server/gemini-proxy`

### Requisitos

- Node.js
- PM2 (instalado globalmente para gestión persistente)
- `@google/generative-ai` y `express` (instalados en la carpeta del proxy)

### Variables de Entorno

El proxy utiliza las siguientes variables (configuradas en tu `.zshrc`):

- `GEMINI_API_KEY`: Tu clave de Google AI Studio.
- `PORT`: Por defecto `1235`.

## 🛠️ Comandos de Gestión (Alias en .zshrc)

He creado comandos simplificados para gestionar el servidor:

- `claude-gemini-proxy-start`: Inicia el proxy manualmente usando PM2.
- `claude-gemini-proxy-stop`: Detiene el servidor manualmente.
- `claude-gemini-proxy-status`: Muestra el estado del proceso en PM2.
- `claude-gemini-proxy-logs`: Muestra los logs en tiempo real.

## 🧠 Modo Inteligente (On-Demand)

El sistema está configurado para ser **inteligente**. No necesitas iniciar el proxy manualmente:

- Al ejecutar cualquier alias (`claud-gemini`, `claud-3flash`, etc.), el script verificará si el proxy está corriendo.
- Si no lo está, lo iniciará automáticamente.
- Al cerrar la sesión de Claude Code, el proxy se detendrá solo para liberar recursos.

## 💻 Uso con Claude Code

Puedes usar los siguientes alias directamente en tu terminal:

- `claud-gemini`: Inicia Claude Code con el modelo **Gemini 3 Flash Preview** (automático).
- `claud-3flash`: Alias directo al modelo Flash.
- `claud-31`: Usa **Gemini 3.1 Pro Preview**.
- `claud-25`: Usa **Gemini 2.5 Pro**.
- `claud-flash`: Usa el modelo Flash más reciente.

## 📝 Notas de Depuración

- Si recibes un error `PayloadTooLarge`, el proxy maneja hasta **50MB**.
- Si recibes un error `429 (Too Many Requests)`, cambia a un modelo "Flash".

---
*Configurado por Antigravity - 2026*

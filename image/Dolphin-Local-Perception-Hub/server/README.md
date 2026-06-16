# 🐬 Dolphin-Local-Perception-Hub: Server

**Version:** 2.0 (Dolphin-v2 Edition)
**Model:** ByteDance/Dolphin-v2 (Qwen2.5-VL Architecture)

## Overview

The server acts as an efficient, on-demand inference engine for multimodal document parsing. It hosts the 8B parameter model locally on Apple Silicon (MPS) or CUDA devices.

## Key Features

- **Ephemeral Existence:**
  - Starts automatically when a client requests it.
  - **Auto-Shutdown:** Terminates after 5 minutes of inactivity to free up system RAM/VRAM.
  - **VRAM Guard:** Monitors memory usage to prevent system freezes.
- **API Endpoints:**
  - `GET /health`: Checks status. Returns `READY` if model is loaded.
  - `POST /api/interact`: Main inference endpoint. Accepting images (Base64) and prompts.
  - `POST /api/shutdown`: Manually stops the server.
- **Protocol:**
  - Standard REST API (FastAPI).
  - Clients communicate via HTTP.

## Configuration

Settings are defined in `config.yaml`:

```yaml
model:
  path: "path/to/dolphin-v2-snapshot"
  device_map: "mps" # Apple Silicon
server:
  port: 8000
  idle_timeout_minutes: 5
```

## Manual Usage

While typically managed by the client, you can run the server manually for debugging:

```bash
# From project root
python -m server.server
```

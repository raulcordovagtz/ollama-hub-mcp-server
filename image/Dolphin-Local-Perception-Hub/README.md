# 🐬 Dolphin-Local-Perception-Hub

A unified, local AI perception engine for parsing documents, images, and diagrams using the **ByteDance/Dolphin-v2** (Qwen2.5-VL) model.

## 🌟 Philosophy

**"The AI model is a heavy resource. usage should be ephemeral."**
This project treats the VLM (Visual Language Model) as a system service that starts when needed and shuts down when idle, keeping your machine resources free for other tasks.

## 📂 Project Structure

- **`/server`**: The inference engine.
  - Hosts the 8B parameter model.
  - Manages VRAM and auto-shutdown.
  - [Read Server Documentation](server/README.md)

- **`/client`**: The interface.
  - `dolphin_cli.py`: Command line tool for processing files.
  - `bridge.py`: Handles server orchestration (Start/Stop/Check).
  - [Read Client Documentation](client/README.md)

- **`requirements.txt`**: Minimal dependency list for the entire system.

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- `poppler` (for PDF processing):

  ```bash
  brew install poppler
  ```

### 2. Installation

```bash
pip install -r requirements.txt
```

### 3. Usage

You don't need to manually start the server. Just run the client:

```bash
# Process an image
python client/dolphin_cli.py path/to/image.jpg -m text

# Process a PDF
python client/dolphin_cli.py path/to/doc.pdf -m table
```

## ⚙️ Configuration

Server settings (model path, timeouts) can be found in `server/config.yaml`.
Default outputs are saved to `server/image/outputs/Dolphin-Perception`.

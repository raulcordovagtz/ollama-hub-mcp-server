# 🐬 Dolphin-Local-Perception-Hub: Client

**Tool:** `dolphin_process.sh` (Standard) & `process_book_batch.py` (Advanced)

## Overview

The client strictly follows the "Agnostic Server" philosophy. It uses a Shell script to handle the lifecycle (Wake-on-LAN) and transport (Curl), and a Python script (`postprocess_cli.py`) to format the output.

For complex documents like books, a specialized Python batch processor is provided.

## Usage

### 1. Standard Single File Processing

```bash
./client/cli/dolphin_process.sh <INPUT_FILE> <MODE> [OUTPUT_DIR]
```

### 2. Batch Book Processing (Optimized)

Processes entire PDF books using a 2x2 grid strategy to maximize throughput and minimize VRAM usage.

```bash
python3 client/cli/process_book_batch.py <PDF_PATH>
```

- **Strategy:** Converts 4 pages -> 1 Grid Image -> 1 Inference.
- **Output:** A single Markdown file containing the full book analysis.

### Standard Arguments

- `INPUT_FILE`: Path to an image (`.jpg`, `.png`).
- `MODE`: The processing mode (determines the prompt).
- `OUTPUT_DIR`: (Optional) Custom path to save the output.

### Standard Modes

| Mode | Description |
|------|-------------|
| `text` | Extracts standard text from the image. |
| `layout` | Describes the visual layout and structure. |
| `table` | Parses tables into Markdown/HTML-friendly formats. |
| `formula` | Extracts math formulas in LaTeX format. |
| `code` | Extracts code blocks maintaining syntax. |
| `general` | Detailed image description. |

## Examples

**1. Extract text from an image:**

```bash
./client/cli/dolphin_process.sh image.jpg text
```

**2. Parse a generic table:**

```bash
./client/cli/dolphin_process.sh data.png table
```

**3. Process a full book:**

```bash
python3 client/cli/process_book_batch.py my_book.pdf
```

## Architecture

- **`dolphin_process.sh`**: The Orchestrator (Single File).
- **`postprocess_cli.py`**: The Formatter (JSON -> Markdown).
- **`process_book_batch.py`**: The Bulk Processor (PDF -> Grid -> Markdown).

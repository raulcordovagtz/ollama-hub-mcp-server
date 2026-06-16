# 🎵 Music MCP Hub — macOS

Hub de herramientas MCP para controlar **Apple Music** desde cualquier LLM:
Claude Desktop, Gemini CLI, Antigravity, Claude Code, Cursor, Windsurf, Ollama, etc.

## Requisitos

- **macOS** con Apple Music
- **Python 3.10+**
- **FastMCP** (`pip install "fastmcp>=2.0,<3"`)

## Inicio rápido

```bash
# Probar con el MCP Inspector (interfaz web interactiva)
fastmcp dev server.py

# Ejecutar directamente (stdio — para clientes MCP)
python3 server.py
```

## 🛠 Tools disponibles

| Tool | Descripción |
|------|------------|
| `get_player_status` | Estado actual (track, artista, volumen, etc.) |
| `play_pause` | Toggle play/pause |
| `next_track` | Siguiente canción |
| `previous_track` | Canción anterior |
| `set_volume` | Ajustar volumen (0–100) |
| `play_playlist` | Reproducir playlist por nombre |
| `play_track` | Buscar y reproducir canción |
| `set_shuffle` | Activar/desactivar aleatorio |
| `search_library` | Buscar canciones en la biblioteca |
| `get_playlists` | Listar playlists |
| `get_library_summary` | Resumen de biblioteca (géneros, artistas, playlists) |
| `get_airplay_devices` | Listar dispositivos AirPlay |

## ⚙️ Configuración por cliente

### Claude Desktop

Agrega a `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "music": {
      "command": "python3",
      "args": ["/Users/crotalo/desarrollo-local/server/musica/server.py"]
    }
  }
}
```

### Gemini CLI / Antigravity

Agrega a `~/.gemini/settings.json` (sección `mcpServers`):

```json
{
  "mcpServers": {
    "music": {
      "command": "python3",
      "args": ["/Users/crotalo/desarrollo-local/server/musica/server.py"],
      "cwd": "/Users/crotalo/desarrollo-local/server/musica"
    }
  }
}
```

### Cursor / Windsurf / Otros

Usa el formato estándar MCP. Snippet en `configs/generic_mcp_client.json`.

### Ollama (vía script wrapper)

Ollama no tiene soporte nativo MCP, pero puedes usar el servidor HTTP:

```bash
# Levantar como servidor HTTP (StreamableHTTP)
fastmcp run server.py --transport streamable-http --port 8000

# Luego desde Ollama u otro script:
curl http://127.0.0.1:8000/mcp/tools
```

## 🚀 launchd (opcional)

Para activación automática del servicio en macOS:

```bash
cp com.music-mcp.server.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.music-mcp.server.plist
```

## Arquitectura

```
musica/
├── server.py               ← Servidor MCP (FastMCP) — punto de entrada
├── applescript_engine.py    ← Motor AppleScript — bridge a Music.app
├── pyproject.toml           ← Metadata y dependencias
├── configs/                 ← Snippets de configuración por cliente
│   ├── claude_desktop.json
│   ├── gemini_cli.json
│   └── generic_mcp_client.json
└── com.music-mcp.server.plist  ← launchd (opcional)
```

## Uso típico con un LLM

> **Tú:** "Pon algo de jazz para trabajar"
>
> **LLM:** *(llama get_library_summary → busca playlists de jazz → play_playlist "Jazz Focus" → set_volume 40)*
>
> "Listo, estoy reproduciendo tu playlist 'Jazz Focus' al 40% de volumen. 🎷"

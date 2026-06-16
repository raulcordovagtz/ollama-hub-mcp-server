#!/usr/bin/env python3
"""
Music MCP Hub — macOS Apple Music Controller

A Model Context Protocol (MCP) server that exposes Apple Music controls
as tools for any LLM client (Claude Desktop, Gemini CLI, Antigravity,
Ollama, Claude Code, etc.).

Usage:
    python3 server.py                    # stdio transport (default for MCP clients)
    fastmcp run server.py                # same, via fastmcp CLI
    fastmcp dev server.py                # interactive MCP Inspector

Configuration (Claude Desktop — claude_desktop_config.json):
    {
        "mcpServers": {
            "music": {
                "command": "python3",
                "args": ["/Users/crotalo/desarrollo-local/server/musica/server.py"]
            }
        }
    }
"""

import sys
import os

# Ensure the project root is in the path so applescript_engine is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP
import applescript_engine as music

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Music Hub",
    instructions=(
        "You are a DJ assistant for macOS. You control Apple Music via AppleScript. "
        "Always call get_player_status first to understand what's playing. "
        "Use get_library_summary to learn the user's music collection before making suggestions. "
        "When the user asks for music by mood, genre, or activity, search their library "
        "and pick appropriate playlists or tracks."
    ),
)


# ---------------------------------------------------------------------------
# Tools — Player Controls
# ---------------------------------------------------------------------------

@mcp.tool()
def get_player_status() -> dict:
    """Get the current player status: track name, artist, album, volume,
    player state (playing/paused/stopped), position, genre, and shuffle mode."""
    return music.get_player_state()


@mcp.tool()
def play_pause() -> str:
    """Toggle play/pause on Apple Music."""
    return music.play_pause()


@mcp.tool()
def next_track() -> str:
    """Skip to the next track."""
    return music.next_track()


@mcp.tool()
def previous_track() -> str:
    """Go back to the previous track."""
    return music.previous_track()


@mcp.tool()
def set_volume(level: int) -> str:
    """Set the playback volume.

    Args:
        level: Volume level from 0 (mute) to 100 (max).
    """
    return music.set_volume(level)


@mcp.tool()
def set_shuffle(enabled: bool) -> str:
    """Enable or disable shuffle mode.

    Args:
        enabled: True to enable shuffle, False to disable.
    """
    return music.set_shuffle(enabled)


# ---------------------------------------------------------------------------
# Tools — Playback
# ---------------------------------------------------------------------------

@mcp.tool()
def play_playlist(name: str) -> str:
    """Play a playlist by its exact name.
    Use get_playlists() first to see available playlist names.

    Args:
        name: The exact name of the playlist to play.
    """
    return music.play_playlist(name)


@mcp.tool()
def play_track(name: str) -> str:
    """Search for a track by name and play the first match.

    Args:
        name: The song name (or part of it) to search and play.
    """
    return music.play_track(name)


# ---------------------------------------------------------------------------
# Tools — Library Discovery
# ---------------------------------------------------------------------------

@mcp.tool()
def get_playlists() -> list[str]:
    """Get a list of all user playlist names in Apple Music."""
    return music.get_playlists()


@mcp.tool()
def get_playlist_tracks(name: str, limit: int = 30) -> list[dict]:
    """Get the tracks in a specific playlist.

    Args:
        name: The exact name of the playlist.
        limit: Maximum number of tracks to return (default 30).
    """
    return music.get_playlist_tracks(name, limit=limit)


@mcp.tool()
def search_library(query: str, limit: int = 15) -> list[dict]:
    """Search the user's music library for tracks matching a query.
    Returns track name, artist, and album for each match.

    Args:
        query: Search term (song name, artist, album, etc.).
        limit: Maximum results to return (default 15).
    """
    return music.search_library(query, limit=limit)


@mcp.tool()
def get_library_summary() -> dict:
    """Get a compact summary of the user's music library.
    Returns: track count, playlist names, genres, and top artists.
    Call this to understand what music the user has before making suggestions."""
    return music.get_library_summary()


@mcp.tool()
def get_airplay_devices() -> list[dict]:
    """List available AirPlay output devices and their active status.
    Each device has a 'name' and 'active' boolean."""
    return music.get_airplay_devices()


@mcp.tool()
def organize_library() -> str:
    """Re-scan the music library and create/update playlists automatically.
    Creates genre playlists (🎵 Jazz, 🎵 Rock, etc.), mood playlists
    (🧘 Chill & Focus, 🎉 Fiesta, etc.), and an uncataloged playlist.
    Call this after adding new music to keep playlists up to date."""
    import subprocess as sp
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "organize_library.py")
    result = sp.run(
        [sys.executable, script_path],
        capture_output=True, text=True, timeout=600,
    )
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"


# ---------------------------------------------------------------------------
# Resource — Library context for the LLM
# ---------------------------------------------------------------------------

@mcp.resource("music://library/summary")
def library_summary_resource() -> str:
    """A summary of the user's Apple Music library — useful as LLM context."""
    import json
    summary = music.get_library_summary()
    return json.dumps(summary, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()

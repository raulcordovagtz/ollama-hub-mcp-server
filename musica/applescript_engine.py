"""
AppleScript Engine — Low-level bridge to Apple Music on macOS.

Every function calls `osascript` via subprocess and returns parsed Python data.
This module has ZERO MCP dependencies — it's a pure AppleScript wrapper.
"""

import subprocess
import json
from typing import Optional


# ---------------------------------------------------------------------------
# Core executor
# ---------------------------------------------------------------------------

def run_script(script: str) -> str:
    """Execute an AppleScript snippet and return its stdout (stripped)."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0 and result.stderr.strip():
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def run_script_lines(script: str) -> list[str]:
    """Execute an AppleScript and return output split by newlines, filtering blanks."""
    raw = run_script(script)
    if not raw:
        return []
    return [line.strip() for line in raw.split(",") if line.strip()]


# ---------------------------------------------------------------------------
# Player controls
# ---------------------------------------------------------------------------

def play_pause() -> str:
    """Toggle play/pause."""
    run_script('tell application "Music" to playpause')
    return "Toggled play/pause"


def next_track() -> str:
    """Skip to next track."""
    run_script('tell application "Music" to next track')
    return "Skipped to next track"


def previous_track() -> str:
    """Go to previous track."""
    run_script('tell application "Music" to previous track')
    return "Went to previous track"


def set_volume(level: int) -> str:
    """Set volume (0–100)."""
    level = max(0, min(100, level))
    run_script(f'tell application "Music" to set sound volume to {level}')
    return f"Volume set to {level}"


def set_shuffle(enabled: bool) -> str:
    """Enable or disable shuffle mode."""
    val = "true" if enabled else "false"
    run_script(f'tell application "Music" to set shuffle enabled to {val}')
    return f"Shuffle {'enabled' if enabled else 'disabled'}"


# ---------------------------------------------------------------------------
# Player state
# ---------------------------------------------------------------------------

def get_player_state() -> dict:
    """Return current player state as a dictionary."""
    script = '''
    tell application "Music"
        set playerInfo to ""
        set playerInfo to playerInfo & "state:" & (player state as string) & "\\n"
        set playerInfo to playerInfo & "volume:" & (sound volume as string) & "\\n"
        set playerInfo to playerInfo & "shuffle:" & (shuffle enabled as string) & "\\n"
        try
            set playerInfo to playerInfo & "track:" & (name of current track as string) & "\\n"
            set playerInfo to playerInfo & "artist:" & (artist of current track as string) & "\\n"
            set playerInfo to playerInfo & "album:" & (album of current track as string) & "\\n"
            set playerInfo to playerInfo & "duration:" & (duration of current track as string) & "\\n"
            set playerInfo to playerInfo & "position:" & (player position as string) & "\\n"
            set playerInfo to playerInfo & "genre:" & (genre of current track as string) & "\\n"
        end try
        return playerInfo
    end tell
    '''
    raw = run_script(script)
    state = {}
    for line in raw.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            state[key.strip()] = value.strip()
    return state


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------

def get_playlists() -> list[str]:
    """Return names of all user playlists."""
    script = '''
    tell application "Music"
        set playlistNames to name of every user playlist
        set output to ""
        repeat with pName in playlistNames
            set output to output & pName & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = run_script(script)
    if not raw:
        return []
    return [p.strip() for p in raw.split("\n") if p.strip()]


def play_playlist(name: str) -> str:
    """Play a playlist by name."""
    escaped = name.replace('"', '\\"')
    run_script(f'tell application "Music" to play playlist "{escaped}"')
    return f"Playing playlist: {name}"


def get_playlist_tracks(name: str, limit: int = 50) -> list[dict]:
    """Return tracks from a playlist (capped at `limit`)."""
    escaped = name.replace('"', '\\"')
    script = f'''
    tell application "Music"
        set theTracks to every track of playlist "{escaped}"
        set maxCount to {limit}
        if (count of theTracks) < maxCount then set maxCount to (count of theTracks)
        set output to ""
        repeat with i from 1 to maxCount
            set t to item i of theTracks
            set output to output & (name of t) & " — " & (artist of t) & " — " & (album of t) & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = run_script(script)
    tracks = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(" — ")
        track = {"name": parts[0] if len(parts) > 0 else ""}
        track["artist"] = parts[1] if len(parts) > 1 else ""
        track["album"] = parts[2] if len(parts) > 2 else ""
        tracks.append(track)
    return tracks


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_library(query: str, limit: int = 20) -> list[dict]:
    """Search the music library for tracks matching `query`."""
    escaped = query.replace('"', '\\"')
    script = f'''
    tell application "Music"
        set results to (search playlist "Library" for "{escaped}")
        set maxCount to {limit}
        if (count of results) < maxCount then set maxCount to (count of results)
        set output to ""
        repeat with i from 1 to maxCount
            set t to item i of results
            set output to output & (name of t) & " — " & (artist of t) & " — " & (album of t) & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = run_script(script)
    tracks = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(" — ")
        track = {"name": parts[0] if len(parts) > 0 else ""}
        track["artist"] = parts[1] if len(parts) > 1 else ""
        track["album"] = parts[2] if len(parts) > 2 else ""
        tracks.append(track)
    return tracks


def play_track(name: str) -> str:
    """Search for a track by name and play the first result."""
    escaped = name.replace('"', '\\"')
    script = f'''
    tell application "Music"
        set results to (search playlist "Library" for "{escaped}")
        if (count of results) > 0 then
            play item 1 of results
            return "Playing: " & (name of item 1 of results) & " by " & (artist of item 1 of results)
        else
            return "No track found for: {escaped}"
        end if
    end tell
    '''
    return run_script(script)


# ---------------------------------------------------------------------------
# Library summary (token-efficient for LLMs)
# ---------------------------------------------------------------------------

def get_library_summary() -> dict:
    """
    Return a compact summary of the library:
    - playlist names
    - top artists (by track count, approx)
    - genres found
    """
    playlists = get_playlists()

    # Get genres
    genre_script = '''
    tell application "Music"
        set allGenres to genre of every track of playlist "Library"
        set uniqueGenres to {}
        repeat with g in allGenres
            if g is not in uniqueGenres and g is not "" then
                set end of uniqueGenres to (g as string)
            end if
            if (count of uniqueGenres) ≥ 30 then exit repeat
        end repeat
        set output to ""
        repeat with g in uniqueGenres
            set output to output & g & "\\n"
        end repeat
        return output
    end tell
    '''
    try:
        genres_raw = run_script(genre_script)
        genres = [g.strip() for g in genres_raw.split("\n") if g.strip()]
    except Exception:
        genres = []

    # Get top artists
    artist_script = '''
    tell application "Music"
        set allArtists to artist of every track of playlist "Library"
        set artistCounts to {}
        set artistNames to {}
        repeat with a in allArtists
            set aStr to (a as string)
            if aStr is not "" then
                if aStr is not in artistNames then
                    set end of artistNames to aStr
                end if
            end if
            if (count of artistNames) ≥ 20 then exit repeat
        end repeat
        set output to ""
        repeat with a in artistNames
            set output to output & a & "\\n"
        end repeat
        return output
    end tell
    '''
    try:
        artists_raw = run_script(artist_script)
        artists = [a.strip() for a in artists_raw.split("\n") if a.strip()]
    except Exception:
        artists = []

    # Track count
    try:
        count_str = run_script('tell application "Music" to get count of tracks of playlist "Library"')
        track_count = int(count_str)
    except Exception:
        track_count = -1

    return {
        "track_count": track_count,
        "playlists": playlists,
        "genres": genres[:20],
        "top_artists": artists[:15],
    }


# ---------------------------------------------------------------------------
# AirPlay
# ---------------------------------------------------------------------------

def get_airplay_devices() -> list[dict]:
    """Return available AirPlay devices and their active status."""
    script = '''
    tell application "Music"
        set deviceInfo to ""
        repeat with d in (every AirPlay device)
            set deviceInfo to deviceInfo & (name of d) & "|" & (selected of d) & "\\n"
        end repeat
        return deviceInfo
    end tell
    '''
    raw = run_script(script)
    devices = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        devices.append({
            "name": parts[0].strip() if len(parts) > 0 else "",
            "active": parts[1].strip().lower() == "true" if len(parts) > 1 else False,
        })
    return devices

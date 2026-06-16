#!/usr/bin/env python3
"""
organize_library.py — Auto-create playlists in Apple Music.

Creates:
  1. Genre playlists    (🎵 Classical, 🎵 Jazz, etc.)
  2. Mood playlists     (🧘 Chill & Focus, 🎉 Fiesta, etc.)
  3. Uncataloged list   (⚠️ Sin Catalogar — tracks missing metadata)

Usage:
    python3 organize_library.py          # full run
    python3 organize_library.py --dry    # preview only, no changes
"""

import subprocess
import sys
import json

DRY_RUN = "--dry" in sys.argv

# ---------------------------------------------------------------------------
# Mood mappings: mood name → list of genres that belong
# ---------------------------------------------------------------------------
MOOD_PLAYLISTS = {
    "🧘 Chill & Focus": [
        "Classical", "New Age", "Soundtrack", "Vocal", "France",
    ],
    "🎉 Fiesta": [
        "Dance", "Latin Urban", "Salsa and Tropical", "Reggae",
    ],
    "🇲🇽 México": [
        "Regional Mexican", "Baladas and Boleros", "Pop in Spanish",
        "Contemporary Latin",
    ],
    "🇧🇷 Brasil": [
        "Brazilian",
    ],
    "🎸 Rock & Alt": [
        "Rock", "Alternative", "Hard Rock", "Alternative and Latin Rock",
    ],
    "❤️ Romance": [
        "Baladas and Boleros", "Adult Contemporary", "Singer/Songwriter",
        "R&B/Soul",
    ],
    "🌎 World & Latin": [
        "Latin", "Worldwide", "Tribute",
    ],
    "🎭 Stage & Screen": [
        "Soundtrack", "Musicals",
    ],
}

# Minimum tracks to create a genre playlist (skip tiny genres)
MIN_TRACKS_FOR_GENRE = 3


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0 and result.stderr.strip():
        print(f"  ⚠️  AppleScript warning: {result.stderr.strip()}")
    return result.stdout.strip()


def get_genre_distribution() -> dict[str, int]:
    """Return {genre: track_count} for all genres in the library."""
    script = '''
    tell application "Music"
        set allGenres to genre of every track of playlist "Library"
        set gNames to {}
        set gCounts to {}
        repeat with g in allGenres
            set gStr to (g as string)
            if gStr is "" then set gStr to "__EMPTY__"
            set found to false
            repeat with i from 1 to (count of gNames)
                if item i of gNames is gStr then
                    set item i of gCounts to (item i of gCounts) + 1
                    set found to true
                    exit repeat
                end if
            end repeat
            if not found then
                set end of gNames to gStr
                set end of gCounts to 1
            end if
        end repeat
        set output to ""
        repeat with i from 1 to (count of gNames)
            set output to output & item i of gNames & "|" & (item i of gCounts as string) & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = run_applescript(script)
    dist = {}
    for line in raw.split("\n"):
        line = line.strip()
        if "|" in line:
            parts = line.split("|")
            dist[parts[0]] = int(parts[1])
    return dist


def get_existing_playlists() -> set[str]:
    raw = run_applescript('''
    tell application "Music"
        set pNames to name of every user playlist
        set output to ""
        repeat with p in pNames
            set output to output & p & "\\n"
        end repeat
        return output
    end tell
    ''')
    return {p.strip() for p in raw.split("\n") if p.strip()}


def create_playlist_from_genre(playlist_name: str, genre: str):
    """Create a playlist and populate it with tracks of that genre."""
    escaped_name = playlist_name.replace('"', '\\"')
    escaped_genre = genre.replace('"', '\\"')
    script = f'''
    tell application "Music"
        -- Create or find playlist
        set pExists to false
        try
            set p to user playlist "{escaped_name}"
            set pExists to true
        end try
        if not pExists then
            set p to (make new user playlist with properties {{name:"{escaped_name}"}})
        end if
        -- Add tracks
        set matchingTracks to (every track of playlist "Library" whose genre is "{escaped_genre}")
        repeat with t in matchingTracks
            duplicate t to p
        end repeat
        return (count of matchingTracks) as string
    end tell
    '''
    count = run_applescript(script)
    return int(count) if count.isdigit() else 0


def create_mood_playlist(playlist_name: str, genres: list[str]):
    """Create a mood playlist from multiple genres."""
    escaped_name = playlist_name.replace('"', '\\"')

    # Build the AppleScript to collect tracks from all matching genres
    genre_conditions = " or ".join(
        f'genre of t is "{g.replace(chr(34), chr(92) + chr(34))}"' for g in genres
    )

    script = f'''
    tell application "Music"
        set pExists to false
        try
            set p to user playlist "{escaped_name}"
            set pExists to true
        end try
        if not pExists then
            set p to (make new user playlist with properties {{name:"{escaped_name}"}})
        end if
        set allTracks to every track of playlist "Library"
        set addedCount to 0
        repeat with t in allTracks
            if ({genre_conditions}) then
                duplicate t to p
                set addedCount to addedCount + 1
            end if
        end repeat
        return addedCount as string
    end tell
    '''
    count = run_applescript(script)
    return int(count) if count.isdigit() else 0


def create_uncataloged_playlist():
    """Create a playlist of tracks missing genre, artist, or album."""
    script = '''
    tell application "Music"
        set pExists to false
        try
            set p to user playlist "⚠️ Sin Catalogar"
            set pExists to true
        end try
        if not pExists then
            set p to (make new user playlist with properties {name:"⚠️ Sin Catalogar"})
        end if
        set allTracks to every track of playlist "Library"
        set addedCount to 0
        repeat with t in allTracks
            if (genre of t is "") or (artist of t is "") or (album of t is "") then
                duplicate t to p
                set addedCount to addedCount + 1
            end if
        end repeat
        return addedCount as string
    end tell
    '''
    count = run_applescript(script)
    return int(count) if count.isdigit() else 0


def main():
    print("🎵 Music Library Organizer")
    print("=" * 50)

    # Step 1: Analyze
    print("\n📊 Analyzing library...")
    genres = get_genre_distribution()
    existing = get_existing_playlists()

    total = sum(genres.values())
    print(f"   {total} tracks, {len(genres)} genres, {len(existing)} existing playlists")

    # Step 2: Genre playlists
    print("\n📁 Fase 1: Genre Playlists")
    genre_plan = {}
    for genre, count in sorted(genres.items(), key=lambda x: -x[1]):
        if genre == "__EMPTY__":
            continue
        if count < MIN_TRACKS_FOR_GENRE:
            continue
        pname = f"🎵 {genre}"
        genre_plan[pname] = (genre, count)

    for pname, (genre, count) in genre_plan.items():
        status = "SKIP (exists)" if pname in existing else "CREATE"
        print(f"   {status}: {pname} ({count} tracks)")

    if not DRY_RUN:
        for pname, (genre, count) in genre_plan.items():
            if pname not in existing:
                actual = create_playlist_from_genre(pname, genre)
                print(f"   ✅ Created: {pname} → {actual} tracks")
            else:
                print(f"   ⏭  Skipped: {pname} (already exists)")

    # Step 3: Mood playlists
    print("\n🎭 Fase 2: Mood Playlists")
    for mood_name, mood_genres in MOOD_PLAYLISTS.items():
        matching = [g for g in mood_genres if g in genres]
        track_sum = sum(genres.get(g, 0) for g in matching)
        if track_sum == 0:
            continue
        status = "SKIP (exists)" if mood_name in existing else "CREATE"
        print(f"   {status}: {mood_name} ({track_sum} tracks from {len(matching)} genres)")

    if not DRY_RUN:
        for mood_name, mood_genres in MOOD_PLAYLISTS.items():
            matching = [g for g in mood_genres if g in genres]
            if not matching:
                continue
            if mood_name not in existing:
                actual = create_mood_playlist(mood_name, matching)
                print(f"   ✅ Created: {mood_name} → {actual} tracks")
            else:
                print(f"   ⏭  Skipped: {mood_name} (already exists)")

    # Step 4: Uncataloged
    print("\n⚠️  Fase 3: Sin Catalogar")
    empty_count = genres.get("__EMPTY__", 0)
    print(f"   ~{empty_count}+ tracks with missing metadata")

    if not DRY_RUN:
        if "⚠️ Sin Catalogar" not in existing:
            actual = create_uncataloged_playlist()
            print(f"   ✅ Created: ⚠️ Sin Catalogar → {actual} tracks")
        else:
            print("   ⏭  Skipped: already exists")

    # Summary
    if DRY_RUN:
        print("\n🔍 DRY RUN — no changes made. Run without --dry to apply.")
    else:
        print("\n🎉 Done! Open Apple Music to see your new playlists.")


if __name__ == "__main__":
    main()

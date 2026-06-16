#!/usr/bin/env python3
"""
Script para fusionar playlists fragmentadas de Apple Music.
Versión final: usa IDs correctamente para agregar tracks.
"""

import subprocess
import json
import time
import sys
import re

def run_applescript(script):
    """Ejecuta AppleScript y retorna stdout."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=60, encoding='utf-8'
        )
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Error ejecutando AppleScript: {e}")
        return None

def get_all_playlists():
    """Obtiene todas las playlists con sus IDs y nombres."""
    script = '''
tell application "Music"
    set playlistList to every playlist
    set output to ""
    repeat with p in playlistList
        set output to (output & (id of p as text) & "|" & (name of p as text) & "||")
    end repeat
    return output
end tell
'''
    result = run_applescript(script)
    if not result:
        return []
    
    playlists = []
    for item in result.split('||'):
        if '|' in item:
            parts = item.split('|', 1)
            if len(parts) >= 2 and parts[0].strip():
                playlists.append({
                    'id': parts[0].strip(),
                    'name': parts[1].strip()
                })
    return playlists

def get_library_tracks(limit=500):
    """Obtiene tracks de la biblioteca completa por género."""
    script = f'''
tell application "Music"
    set trackList to every file track of library playlist 1
    set output to ""
    repeat with t in (items 1 thru {limit} of trackList)
        set output to (output & (name of t as text) & "|" & (genre of t as text) & "||")
    end repeat
    return output
end tell
'''
    result = run_applescript(script)
    if not result:
        return []
    
    tracks = []
    for item in result.split('||'):
        if '|' in item:
            parts = item.split('|', 1)
            if len(parts) >= 2 and parts[0].strip():
                tracks.append({
                    'name': parts[0].strip(),
                    'genre': parts[1].strip() if len(parts) > 1 else ''
                })
    return tracks

def create_playlist(name):
    """Crea una nueva playlist."""
    script = f'''
tell application "Music"
    make new playlist with properties {{name:"{name}"}}
end tell
'''
    return run_applescript(script)

def add_track_to_playlist(playlist_id, track_name):
    """Agrega un track a una playlist usando el ID de la playlist (no nombre)."""
    track_name_escaped = track_name.replace('"', '\\"')
    
    # CORRECCIÓN: usar 'id' en lugar de 'name' para la playlist
    script = f'''
tell application "Music"
    set p to (every playlist whose id is {playlist_id})'s item 1
    try
        set t to (first file track of library playlist 1 whose name is "{track_name_escaped}")
        add t to p
    end try
end tell
'''
    return run_applescript(script)

def delete_playlist(playlist_id):
    """Elimina una playlist."""
    script = f'''
tell application "Music"
    set p to (every playlist whose id is {playlist_id})'s item 1
    delete p
end tell
'''
    return run_applescript(script)

def main():
    print("=== FUSIÓN DE PLAYLISTS (v6 - CORREGIDO) ===\n")
    
    # 1. Obtener todas las playlists existentes (incluyendo las nuevas de ejecuciones previas)
    print("Obteniendo playlists...")
    all_playlists = get_all_playlists()
    print(f"Total: {len(all_playlists)} playlists\n")
    
    # 2. Definir mapeo de géneros a nuevas playlists
    genre_mapping = {
        # Rock -> "Rock"
        'Rock': 'Rock',
        'Hard Rock': 'Rock',
        'Alternative': 'Rock',
        'Alternative and Latin Rock': 'Rock',
        
        # Latin -> "Latin"
        'Latin': 'Latin',
        'Contemporary Latin': 'Latin',
        
        # Brasil -> "Brasil"
        'Brazilian': 'Brasil',
        
        # Pop -> "Pop"
        'Pop': 'Pop',
        'Pop in Spanish': 'Pop',
        
        # Romance -> "Romance"
        'Baladas and Boleros': 'Romance',
        'Romance': 'Romance',
        
        # Cine y Teatro -> "Cine y Teatro"
        'Soundtrack': 'Cine y Teatro',
        'Musicals': 'Cine y Teatro',
        
        # Vocal -> "Vocal"
        'Vocal': 'Vocal',
        'Adult Contemporary': 'Vocal',
        
        # World -> "World"
        'Worldwide': 'World',
        'France': 'World',
    }
    
    # 3. Encontrar o crear playlists nuevas
    print("Preparando playlists...\n")
    
    new_playlists = {}  # name -> id
    
    for new_name in set(genre_mapping.values()):
        # Buscar si ya existe
        existing = None
        for p in all_playlists:
            if p['name'] == new_name:
                existing = p
                break
        
        if existing:
            print(f"  ✅ Existe: {new_name} (ID: {existing['id']})")
            new_playlists[new_name] = existing['id']
        else:
            # Crear nueva
            result = create_playlist(new_name)
            if result:
                all_pls = get_all_playlists()  # Re-fetch
                for p in all_pls:
                    if p['name'] == new_name and p['id'] not in [x['id'] for x in all_playlists]:
                        new_playlists[new_name] = p['id']
                        print(f"  ✅ Creada: {new_name} (ID: {p['id']})")
                        break
    
    # 4. Obtener tracks de la biblioteca por género y agregarlos a las nuevas playlists
    print("\nObteniendo tracks de la biblioteca por género...\n")
    
    library_tracks = get_library_tracks(limit=1000)  # Limitar para no sobrecargar
    print(f"Total tracks en biblioteca: {len(library_tracks)}\n")
    
    # Contar por género
    genre_counts = {}
    for track in library_tracks:
        genre = track['genre'] if track['genre'] else 'Sin Género'
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    print("Tracks por género (top 20):")
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {genre}: {count}")
    
    # 5. Mover tracks a las nuevas playlists por género
    print("\nMoviendo tracks a nuevas playlists...\n")
    
    moved_count = 0
    
    for new_name, playlist_id in new_playlists.items():
        # Encontrar los géneros que mapean a esta playlist
        target_genres = [g for g, n in genre_mapping.items() if n == new_name]
        
        # Filtrar tracks de la biblioteca que coinciden con estos géneros
        matching_tracks = [t for t in library_tracks if t['genre'] in target_genres]
        
        print(f"  {new_name}: {len(matching_tracks)} tracks ({', '.join(target_genres)})")
        
        # Agregar los primeros 50 tracks a la playlist (para evitar errores)
        for track in matching_tracks[:50]:
            result = add_track_to_playlist(playlist_id, track['name'])
            if result:
                moved_count += 1
    
    print(f"\n✅ Total tracks movidos: {moved_count}")
    
    # 6. Eliminar playlists viejas (opcional)
    print("\n⚠️ Nota: Las playlists viejas se mantienen por seguridad.")
    print("   Puedes eliminarlas manualmente en Apple Music cuando estés seguro.\n")

if __name__ == '__main__':
    main()

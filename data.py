"""
ONYRA - Gestión de Datos, Catálogo de Juegos, Sistemas y Persistencia de Estado
Conserva los metadatos históricos y descripciones de arcade.py, limpia nombres de ROMs
y gestiona la persistencia en ~/.emulador/state.json.
"""

import glob
import json
import os
import re
from typing import Any, Dict, List, Optional

STATE_FILE = os.path.expanduser("~/.emulador/state.json")
COVERS_CACHE_DIR = os.path.expanduser("~/.emulador/cache/covers")

# Definición de sistemas soportados con sus metadatos
SYSTEMS_INFO = [
    {
        "id": "snes",
        "name": "Super Nintendo",
        "short_name": "SNES",
        "system_key": "SNES",
        "company": "Nintendo",
        "year": "1990",
        "row": 0,
    },
    {
        "id": "megadrive",
        "name": "Mega Drive",
        "short_name": "Genesis",
        "system_key": "Mega Drive",
        "company": "Sega",
        "year": "1988",
        "row": 0,
    },
    {
        "id": "pc",
        "name": "PC Nativo",
        "short_name": "PC",
        "system_key": "PC Nativo",
        "company": "DOS / Linux",
        "year": "1989-1997",
        "row": 0,
    },
    {
        "id": "nes",
        "name": "NES (8-Bit)",
        "short_name": "NES",
        "system_key": "NES",
        "company": "Nintendo",
        "year": "1983",
        "row": 1,
    },
    {
        "id": "gb",
        "name": "Game Boy",
        "short_name": "GB",
        "system_key": "Game Boy",
        "company": "Nintendo",
        "year": "1989",
        "row": 1,
    },
]


def clean_display_title(filename_or_title: str) -> str:
    """
    Limpia los nombres para mostrarlos elegantes en la interfaz:
    Elimina extensiones (.sfc, .md, .nes, .gb, etc.) y etiquetas entre paréntesis/corchetes.
    """
    s = os.path.splitext(os.path.basename(filename_or_title))[0]
    # Quitar etiquetas tipo (USA), [!], (Japan, USA) (En,Ja), (World), etc.
    s = re.sub(r"\s*[\(\[].*?[\)\]]", "", s)
    # Quitar sufijos comunes
    s = s.strip()
    return s


def load_raw_games_from_arcade() -> List[Dict[str, Any]]:
    """Carga los juegos de arcade.py conservando sus descripciones ricas y metadatos."""
    try:
        import sys
        app_dir = os.path.dirname(os.path.abspath(__file__))
        core_dir = os.path.join(app_dir, "arcade_core")
        if core_dir not in sys.path:
            sys.path.insert(0, core_dir)
        sys.path.insert(0, "/home/jcgar/arcade")
        import arcade
        return getattr(arcade, "GAMES", [])
    except Exception:
        return []


def get_game_players(game: Dict[str, Any]) -> str:
    """Determina de forma elegante el número de jugadores soportado."""
    title_lower = game.get("title", "").lower()
    genre_lower = game.get("genre", "").lower()
    desc_lower = game.get("desc", "").lower()

    if any(k in genre_lower for k in ["lucha", "carreras", "beat 'em up", "run and gun"]):
        return "1-2 Jugadores"
    if any(k in title_lower for k in ["contra", "street fighter", "mario kart", "final fight", "streets of rage"]):
        return "1-2 Jugadores"
    if "cooperativo" in desc_lower or "2 jugadores" in desc_lower:
        return "1-2 Jugadores"
    return "1 Jugador"


def get_game_cover_path(game: Dict[str, Any]) -> Optional[str]:
    """Devuelve la ruta en caché de la carátula local si existe."""
    game_id = game.get("id")
    if not game_id:
        return None

    # 1. Por ID directo en cache
    for ext in [".png", ".jpg", ".webp"]:
        cand = os.path.join(COVERS_CACHE_DIR, f"{game_id}{ext}")
        if os.path.exists(cand):
            return cand

    # 2. Por nombre base de la ROM
    rom = game.get("rom")
    if rom:
        base = os.path.splitext(os.path.basename(rom))[0]
        for ext in [".png", ".jpg", ".webp"]:
            cand = os.path.join(COVERS_CACHE_DIR, f"{base}{ext}")
            if os.path.exists(cand):
                return cand

    return None


def get_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """
    Construye el catálogo completo organizado por sistema.
    Solo incluye juegos cuya ROM o binario exista en disco.
    """
    raw_games = load_raw_games_from_arcade()
    catalog: Dict[str, List[Dict[str, Any]]] = {s["id"]: [] for s in SYSTEMS_INFO}

    for g in raw_games:
        # Verificar existencia
        is_native = (g.get("system") == "PC Nativo")
        if not is_native:
            rom_path = g.get("rom")
            if not rom_path or not os.path.exists(rom_path):
                continue
        else:
            cmd = g.get("cmd", [])
            if not cmd:
                continue
            # Comprobar si el binario o script lanzador existe
            launcher_bin = cmd[0]
            if not os.path.exists(launcher_bin) and not os.path.exists(f"/usr/bin/{launcher_bin}"):
                import shutil
                if not shutil.which(launcher_bin):
                    continue
            # Si se lanza mediante wine_run.sh, verificar que el .exe existe en disco
            if launcher_bin.endswith("wine_run.sh") and len(cmd) > 1:
                exe_path = cmd[1]
                exe_dir = os.path.dirname(exe_path)
                exe_base = os.path.basename(exe_path)
                exists = False
                if os.path.exists(exe_path):
                    exists = True
                elif os.path.isdir(exe_dir):
                    try:
                        for f in os.listdir(exe_dir):
                            if f.lower() == exe_base.lower() or (exe_base.lower() in ("wargame.exe", "comandos.exe") and f.lower() in ("wargame.exe", "comandos.exe", "commandos.exe")):
                                exists = True
                                break
                    except Exception:
                        pass
                if not exists:
                    continue
            # Si se lanza mediante dosbox_run.sh, verificar que el .conf o directorio existe en disco
            if launcher_bin.endswith("dosbox_run.sh") and len(cmd) > 1:
                conf_path = cmd[1]
                if not os.path.exists(conf_path):
                    continue

        # Mapear a sys_id
        sys_key = g.get("system")
        target_sys = None
        for s in SYSTEMS_INFO:
            if s["system_key"] == sys_key:
                target_sys = s["id"]
                break

        if not target_sys:
            continue

        clean_name = clean_display_title(g.get("title", ""))
        item = dict(g)
        item["clean_title"] = clean_name
        item["sys_id"] = target_sys
        item["players"] = get_game_players(g)
        item["cover_path"] = get_game_cover_path(g)
        catalog[target_sys].append(item)

    return catalog


def get_active_systems() -> List[Dict[str, Any]]:
    """Devuelve solo los sistemas que tienen al menos 1 juego disponible."""
    catalog = get_catalog()
    active = []
    for s in SYSTEMS_INFO:
        games = catalog.get(s["id"], [])
        if games:
            sys_entry = dict(s)
            sys_entry["games_count"] = len(games)
            active.append(sys_entry)
    return active


def get_game_autosave(game: Dict[str, Any]) -> Optional[str]:
    """Comprueba si existe un savestate (.mca) previo para este juego en ~/.mednafen/mcs/"""
    if game.get("system") == "PC Nativo":
        return None
    rom_path = game.get("rom")
    if not rom_path:
        return None
    base = os.path.splitext(os.path.basename(rom_path))[0]
    mcs_dir = os.path.expanduser("~/.mednafen/mcs")
    matches = glob.glob(os.path.join(mcs_dir, f"{base}.*.mca"))
    for m in matches:
        if os.path.isfile(m) and os.path.getsize(m) > 0:
            return m
    return None


def load_state() -> Dict[str, Any]:
    """Carga el último sistema y juego seleccionados."""
    default_state = {"last_system_id": "snes", "last_game_id": "smw"}
    if not os.path.exists(STATE_FILE):
        return default_state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default_state, **data}
    except Exception:
        return default_state


def save_state(system_id: str, game_id: str) -> None:
    """Guarda el último sistema y juego seleccionados."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_system_id": system_id, "last_game_id": game_id}, f, indent=2)
    except Exception:
        pass

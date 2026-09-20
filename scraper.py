"""
ONYRA - Scraper y Gestor de Caché de Carátulas y Logos
Descarga una sola vez los logos de sistemas y carátulas desde libretro-thumbnails a ~/.emulador/cache/.
En uso normal no accede a la red.
"""

import os
import urllib.parse
import requests
from typing import Dict, List, Optional

CACHE_DIR = os.path.expanduser("~/.emulador/cache")
LOGOS_DIR = os.path.join(CACHE_DIR, "logos")
COVERS_DIR = os.path.join(CACHE_DIR, "covers")

# Logos oficiales de sistemas (monocromos, fondo transparente)
SYSTEM_LOGOS = {
    "snes": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Nintendo%20-%20Super%20Nintendo%20Entertainment%20System.png",
    "megadrive": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Sega%20-%20Mega%20Drive%20-%20Genesis.png",
    "nes": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Nintendo%20-%20Nintendo%20Entertainment%20System.png",
    "gb": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Nintendo%20-%20Game%20Boy.png",
    "pc": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/DOS.png",
}

# URLs directas de carátulas para cada juego de la colección
BASE_THUMB = "https://raw.githubusercontent.com/libretro-thumbnails"

GAME_BOXARTS = {
    # SNES
    "smw": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Super%20Mario%20World%20(USA).png",
    "super_metroid": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Super%20Metroid%20(Japan%2C%20USA)%20(En%2CJa).png",
    "chrono_trigger": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Chrono%20Trigger%20(USA).png",
    "final_fight": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Final%20Fight%20(USA).png",
    "captain_commando": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Captain%20Commando%20(USA).png",
    "super_ghouls": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Super%20Ghouls%20'N%20Ghosts%20(USA).png",
    "super_castlevania_4": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Super%20Castlevania%20IV%20(USA).png",
    "mega_man_x": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Mega%20Man%20X%20(USA).png",
    "earthbound": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/EarthBound%20(USA).png",
    "ff3": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Final%20Fantasy%20III%20(USA)%20(Rev%201).png",
    "contra_3": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Contra%20III%20-%20The%20Alien%20Wars%20(USA).png",
    "zelda_alttp": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Legend%20of%20Zelda%2C%20The%20-%20A%20Link%20to%20the%20Past%20(USA).png",
    "fzero": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/F-Zero%20(USA).png",
    "sf2_turbo": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Street%20Fighter%20II%20Turbo%20-%20Hyper%20Fighting%20(USA).png",
    "dkc": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Donkey%20Kong%20Country%20(USA).png",
    "mario_kart": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Super%20Mario%20Kart%20(USA).png",
    "tetris_drmario": f"{BASE_THUMB}/Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/Tetris%20%26%20Dr.%20Mario%20(USA).png",

    # Mega Drive
    "sor2": f"{BASE_THUMB}/Sega_-_Mega_Drive_-_Genesis/master/Named_Boxarts/Streets%20of%20Rage%202%20(USA).png",
    "mercs": f"{BASE_THUMB}/Sega_-_Mega_Drive_-_Genesis/master/Named_Boxarts/Mercs%20(World).png",
    "gunstar_heroes": f"{BASE_THUMB}/Sega_-_Mega_Drive_-_Genesis/master/Named_Boxarts/Gunstar%20Heroes%20(USA).png",
    "shinobi_3": f"{BASE_THUMB}/Sega_-_Mega_Drive_-_Genesis/master/Named_Boxarts/Shinobi%20III%20-%20Return%20of%20the%20Ninja%20Master%20(USA).png",
    "castlevania_bloodlines": f"{BASE_THUMB}/Sega_-_Mega_Drive_-_Genesis/master/Named_Boxarts/Castlevania%20-%20Bloodlines%20(USA).png",
    "sonic": f"{BASE_THUMB}/Sega_-_Mega_Drive_-_Genesis/master/Named_Boxarts/Sonic%20The%20Hedgehog%20(USA%2C%20Europe).png",

    # NES
    "commando": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Commando%20(USA).png",
    "ninja_gaiden": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Ninja%20Gaiden%20(USA).png",
    "castlevania_3": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Castlevania%20III%20-%20Dracula's%20Curse%20(USA).png",
    "metal_gear": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Metal%20Gear%20(USA).png",
    "contra": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Contra%20(USA).png",
    "smb": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Super%20Mario%20Bros.%20(World).png",
    "pacman": f"{BASE_THUMB}/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/Pac-Man%20(USA)%20(Namco).png",

    # Game Boy
    "links_awakening": f"{BASE_THUMB}/Nintendo_-_Game_Boy/master/Named_Boxarts/Legend%20of%20Zelda%2C%20The%20-%20Link's%20Awakening%20(USA%2C%20Europe)%20(Rev%202).png",
    "metroid_2": f"{BASE_THUMB}/Nintendo_-_Game_Boy/master/Named_Boxarts/Metroid%20II%20-%20Return%20of%20Samus%20(World).png",
    "pokemon_red": f"{BASE_THUMB}/Nintendo_-_Game_Boy/master/Named_Boxarts/Pokemon%20-%20Red%20Version%20(USA%2C%20Europe)%20(SGB%20Enhanced).png",
    "wario_land": f"{BASE_THUMB}/Nintendo_-_Game_Boy/master/Named_Boxarts/Super%20Mario%20Land%203%20-%20Wario%20Land%20(World).png",

    # PC Nativo
    "doom": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Doom%20(1993).png",
    "doom2": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Doom%20II%20-%20Hell%20on%20Earth%20(1994).png",
    "quake": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Quake%20(1996).png",
    "quake2": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Quake%20II%20(1997).png",
    "prince_of_persia": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Prince%20of%20Persia%20(1989).png",
    "monkey1": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Secret%20of%20Monkey%20Island%2C%20The%20(1990).png",
    "monkey2": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Monkey%20Island%202%20-%20LeChuck's%20Revenge%20(1991).png",
    "tentacle": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Maniac%20Mansion%20-%20Day%20of%20the%20Tentacle%20(1993).png",
    "atlantis": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Indiana%20Jones%20and%20the%20Fate%20of%20Atlantis%20(1992).png",
    "samnmax": f"{BASE_THUMB}/DOS/master/Named_Boxarts/Sam%20%26%20Max%20Hit%20the%20Road%20(1993).png",
    "angrybirds_sw2": "https://upload.wikimedia.org/wikipedia/en/d/d4/Angry_Birds_Star_Wars_II.png",
}


def download_file(url: str, dest_path: str) -> bool:
    """Descarga un archivo con timeout y validación básica."""
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200 and len(r.content) > 500:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


def update_all_cache(force: bool = False):
    """Descarga todos los logos y carátulas que no existan en caché."""
    os.makedirs(LOGOS_DIR, exist_ok=True)
    os.makedirs(COVERS_DIR, exist_ok=True)

    # 1. Logos de sistemas
    print("Sincronizando logos de sistemas...")
    for sys_id, url in SYSTEM_LOGOS.items():
        dest = os.path.join(LOGOS_DIR, f"{sys_id}.png")
        if force or not os.path.exists(dest):
            ok = download_file(url, dest)
            print(f"  [{'OK' if ok else 'FALLO'}] Logo: {sys_id}")

    # 2. Carátulas de juegos
    print("Sincronizando carátulas de juegos...")
    for game_id, url in GAME_BOXARTS.items():
        dest = os.path.join(COVERS_DIR, f"{game_id}.png")
        if force or not os.path.exists(dest):
            ok = download_file(url, dest)
            print(f"  [{'OK' if ok else 'FALLO'}] Carátula: {game_id}")


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    update_all_cache(force=force_flag)

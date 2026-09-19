"""
ONYRA - Motor de Lanzamiento y Traspaso de DRM a Mednafen / PC Nativo
Cierra por completo la pantalla y subsistemas de Pygame para liberar el DRM Master,
ejecuta el juego con la configuración exacta existente, y al volver restaura la pantalla
y los periféricos al 100%.
"""

import os
import subprocess
import sys
import time
from typing import Any, Dict
import pygame

from input_manager import input_mgr

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(APP_DIR, "arcade_core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
sys.path.insert(0, "/home/jcgar/arcade")

try:
    import volume
except Exception:
    volume = None

try:
    import sound
except Exception:
    sound = None


def launch_game(game: Dict[str, Any], restart_clean: bool = False) -> pygame.Surface:
    """
    Traspaso limpio de DRM:
    1. Pausa entrada del menú.
    2. Cierra display de Pygame.
    3. Ejecuta Mednafen / juego nativo con la configuración idéntica.
    4. Restaura modo de teclado y terminal.
    5. Reabre Pygame en pantalla completa y devuelve la nueva Surface.
    """
    is_native = (game.get("system") == "PC Nativo")
    if not is_native:
        rom_path = game.get("rom")
        if not rom_path or not os.path.exists(rom_path):
            return pygame.display.get_surface()

    # Si se solicitó empezar de nuevo, eliminar la instantánea previa
    if restart_clean and not is_native:
        from data import get_game_autosave
        save_file = get_game_autosave(game)
        if save_file and os.path.exists(save_file):
            try:
                os.remove(save_file)
            except Exception:
                pass

    if volume:
        volume.set_emulator_active(True)

    if sound:
        sound.play("coin")
        time.sleep(0.3)

    subprocess.run(["killall", "-9", "aplay"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 1. Pausar listener de entrada física
    input_mgr.pause()

    # 2. Cierre total de Pygame y liberación de DRM Master
    pygame.display.quit()
    pygame.quit()

    env = os.environ.copy()
    if not env.get("DISPLAY"):
        env["SDL_VIDEODRIVER"] = "kmsdrm"
    env.pop("SDL_AUDIODRIVER", None)

    try:
        if is_native:
            cmd = game["cmd"]
            cwd = game.get("cwd", None)
            subprocess.run(cmd, env=env, cwd=cwd)
        else:
            # Reconfigurar controles y lanzar Mednafen
            apply_script = "/home/jcgar/arcade/apply_input_config.py"
            if not os.path.exists(apply_script):
                apply_script = os.path.join(CORE_DIR, "apply_input_config.py")
            cfg_file = "/home/jcgar/arcade/mednafen_arcade.cfg"
            if not os.path.exists(cfg_file):
                cfg_file = os.path.join(CORE_DIR, "mednafen_arcade.cfg")

            if os.path.exists(apply_script):
                subprocess.run(
                    [sys.executable, apply_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            cmd = [
                "mednafen",
                "-ovconfig",
                cfg_file,
                "-video.driver",
                "softfb",
                "-sound.driver",
                "sdl",
                "-autosave",
                "1",
                game["rom"],
            ]
            subprocess.run(cmd, env=env)
    except Exception as e:
        pass
    finally:
        # Reconfigurar controles para el frontend
        if os.path.exists(apply_script):
            subprocess.run(
                [sys.executable, apply_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if volume:
            volume.set_emulator_active(False)

        # Restaurar teclado y modo de consola del kernel
        os.system("sudo kbd_mode -u -f 2>/dev/null; stty sane 2>/dev/null")

    # 3. Reapertura limpia de Pygame en KMSDRM
    pygame.init()
    pygame.display.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)

    import theme
    theme.reset_theme_cache()

    # Obtener el modo óptimo
    modes = pygame.display.list_modes()
    res = modes[0] if modes else (1920, 1080)
    new_screen = pygame.display.set_mode(res, pygame.FULLSCREEN | pygame.DOUBLEBUF)

    # 4. Pausa de estabilización y purga de eventos
    time.sleep(0.3)
    pygame.event.clear()
    input_mgr.resume()

    return new_screen

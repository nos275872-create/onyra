"""
ONYRA - Motor de Lanzamiento, Traspaso de DRM, Watcher de Tecla Q y Configuración de Mando
Cierra por completo la pantalla y subsistemas de Pygame para liberar el DRM Master,
ejecuta el juego con la configuración exacta existente, vigila la pulsación de Q durante
1 segundo en hilo paralelo evdev para matar el proceso de forma homogénea, y al volver
restaura la pantalla y los periféricos al 100%.
"""

import os
import select
import signal
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

# Mapeo universal SDL2 GameController para ShanWan Gamepad en Linux
SHANWAN_MAPPING = (
    "03008dbf632500007505000011010000,ShanWan Gamepad,"
    "platform:Linux,"
    "a:b0,b:b1,x:b3,y:b4,"
    "back:b10,start:b11,guide:b12,"
    "leftshoulder:b6,rightshoulder:b7,"
    "lefttrigger:b8,righttrigger:b9,"
    "leftx:a0,lefty:a1,rightx:a2,righty:a3,"
    "dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
)


def _force_kill(proc: subprocess.Popen, is_wine: bool) -> None:
    """Garantiza que el proceso del juego (y su grupo) muere pase lo que pase."""
    if proc.poll() is not None:
        return
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=2.0)
        except Exception:
            pass
    if is_wine:
        subprocess.run(["wineserver", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _watch_process_and_q_key(proc: subprocess.Popen, is_wine: bool = False) -> None:
    keyboards = []
    try:
        import evdev
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                if evdev.ecodes.EV_KEY in caps and evdev.ecodes.KEY_Q in caps[evdev.ecodes.EV_KEY]:
                    keyboards.append(dev)
            except Exception:
                pass
    except Exception:
        pass

    q_press_start = None

    try:
        while proc.poll() is None:
            if keyboards:
                try:
                    r, _, _ = select.select(keyboards, [], [], 0.05)
                    for dev in r:
                        for ev in dev.read():
                            if ev.type == evdev.ecodes.EV_KEY and ev.code == evdev.ecodes.KEY_Q:
                                if ev.value == 1 and q_press_start is None:
                                    q_press_start = time.monotonic()
                                elif ev.value == 0:
                                    q_press_start = None
                except OSError:
                    # Dispositivo reenumerado/perdido: recargar lista y seguir vigilando,
                    # NUNCA salir del bucle dejando el proceso vivo sin matar.
                    for dev in keyboards:
                        try:
                            dev.close()
                        except Exception:
                            pass
                    keyboards = []
                    try:
                        import evdev
                        for path in evdev.list_devices():
                            try:
                                dev = evdev.InputDevice(path)
                                caps = dev.capabilities()
                                if evdev.ecodes.EV_KEY in caps and evdev.ecodes.KEY_Q in caps[evdev.ecodes.EV_KEY]:
                                    keyboards.append(dev)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    time.sleep(0.2)
                    continue

                if q_press_start is not None and (time.monotonic() - q_press_start) >= 1.0:
                    _force_kill(proc, is_wine)
                    break
            else:
                time.sleep(0.05)
    except Exception:
        # CUALQUIER fallo inesperado: garantizar que el juego no queda huérfano.
        _force_kill(proc, is_wine)
    finally:
        for dev in keyboards:
            try:
                dev.close()
            except Exception:
                pass


def launch_game(game: Dict[str, Any], restart_clean: bool = False) -> pygame.Surface:
    """
    Traspaso limpio de DRM con vigilancia paralela de Q:
    1. Pausa entrada de ONYRA.
    2. Cierra display de Pygame para liberar DRM Master.
    3. Aplica configuración de controles de mando para el juego actual.
    4. Ejecuta el juego mediante subprocess.Popen con start_new_session=True.
    5. Vigila la tecla Q con _watch_process_and_q_key en hilo evdev paralelo.
    6. Restaura modo de teclado y terminal del kernel.
    7. Reabre Pygame en pantalla completa y devuelve la nueva Surface.
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

    # 1. Pausar listener de entrada física de ONYRA
    input_mgr.pause()

    # 2. Cierre total de Pygame y liberación de DRM Master
    pygame.display.quit()
    pygame.quit()

    env = os.environ.copy()
    if not env.get("DISPLAY"):
        env["SDL_VIDEODRIVER"] = "kmsdrm"
    env.pop("SDL_AUDIODRIVER", None)

    # Inyectar mapeo estándar de mando ShanWan para todos los motores SDL2
    env["SDL_GAMECONTROLLERCONFIG"] = SHANWAN_MAPPING

    is_wine = (game.get("id") == "commandos" or "wine" in str(game.get("cmd", [])))
    apply_script = None

    try:
        if is_native:
            # Configurar mando ShanWan para el motor nativo correspondiente
            native_script = "/home/jcgar/arcade/apply_native_gamepad_config.py"
            if not os.path.exists(native_script):
                native_script = os.path.join(CORE_DIR, "apply_native_gamepad_config.py")
            if os.path.exists(native_script):
                subprocess.run(
                    [sys.executable, native_script, game.get("id", "")],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            cmd = game["cmd"]
            cwd = game.get("cwd", None)
            proc = subprocess.Popen(cmd, env=env, cwd=cwd, start_new_session=True)
            _watch_process_and_q_key(proc, is_wine=is_wine)
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
            proc = subprocess.Popen(cmd, env=env, start_new_session=True)
            _watch_process_and_q_key(proc, is_wine=False)
    except Exception as e:
        pass
    finally:
        # Reconfigurar controles para el frontend si procede
        if apply_script and os.path.exists(apply_script):
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

"""
ONYRA - Motor de Lanzamiento, Traspaso de DRM, Watcher de Tecla Q y Configuración de Mando
Cierra por completo la pantalla y subsistemas de Pygame para liberar el DRM Master,
ejecuta el juego con la configuración exacta existente, vigila la pulsación de Q durante
1 segundo en hilo paralelo evdev para matar el proceso de forma homogénea, y al volver
restaura la pantalla y los periféricos al 100%.
"""

import json
import os
import select
import signal
import subprocess
import sys
import time
from typing import Any, Dict

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

try:
    import evdev
except ImportError:
    evdev = None

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


def _release_drm_master() -> None:
    """
    Libera explícitamente DRM Master y cierra los descriptores de /dev/dri/card*
    que SDL2 KMSDRM no cierra al llamar a pygame.display.quit(), evitando el error
    'drmSetMaster failed: Device or resource busy' al lanzar Xorg / Wine.
    """
    try:
        import ctypes
        libdrm = None
        try:
            libdrm = ctypes.CDLL("libdrm.so.2")
        except Exception:
            pass

        fd_dir = "/proc/self/fd"
        if os.path.exists(fd_dir):
            for fd_name in os.listdir(fd_dir):
                try:
                    fd = int(fd_name)
                    if fd <= 2:
                        continue
                    target = os.readlink(os.path.join(fd_dir, fd_name))
                    if "/dev/dri/card" in target:
                        if libdrm and hasattr(libdrm, "drmDropMaster"):
                            try:
                                libdrm.drmDropMaster(fd)
                            except Exception:
                                pass
                        try:
                            os.close(fd)
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        pass


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
        subprocess.run(["killall", "-9", "dosbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "killall", "-9", "Xorg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "pkill", "-9", "-f", "Xorg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "rm", "-f", "/tmp/.X1-lock", "/tmp/.X2-lock", "/tmp/.X11-unix/X1", "/tmp/.X11-unix/X2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _find_input_devices():
    if not evdev:
        return []
    devices = []
    try:
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                # Solo teclados físicos: NUNCA interceptar mandos de juego
                name_lower = dev.name.lower()
                if "shanwan" in name_lower or "gamepad" in name_lower or "joystick" in name_lower:
                    continue
                caps = dev.capabilities()
                if evdev.ecodes.EV_KEY in caps:
                    keys = caps[evdev.ecodes.EV_KEY]
                    if (evdev.ecodes.KEY_Q in keys or
                        evdev.ecodes.KEY_VOLUMEUP in keys or
                        evdev.ecodes.KEY_VOLUMEDOWN in keys or
                        evdev.ecodes.KEY_MUTE in keys):
                        devices.append(dev)
            except Exception:
                pass
    except Exception:
        pass
    return devices


def _watch_process_and_q_key(proc: subprocess.Popen, is_wine: bool = False) -> None:
    if not evdev:
        proc.wait()
        return

    devices = _find_input_devices()
    q_press_start = None
    last_vol_time = 0.0

    while proc.poll() is None:
        if devices:
            try:
                r, _, _ = select.select(devices, [], [], 0.05)
                for dev in r:
                    try:
                        for ev in dev.read():
                            if ev.type == evdev.ecodes.EV_KEY:
                                # 1. Pulsación de Q mantenida durante 1s para forzar salida limpia
                                if ev.code == evdev.ecodes.KEY_Q:
                                    if ev.value == 1 and q_press_start is None:
                                        q_press_start = time.monotonic()
                                    elif ev.value == 0:
                                        q_press_start = None

                                # 2. Teclas multimedia específicas de volumen del teclado
                                elif ev.code == evdev.ecodes.KEY_VOLUMEUP and ev.value in (1, 2):
                                    now = time.monotonic()
                                    if now - last_vol_time >= 0.08:
                                        if volume:
                                            volume.set_volume_delta(+5)
                                        else:
                                            subprocess.run(["amixer", "set", "Master", "5%+", "unmute"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                        last_vol_time = now

                                elif ev.code == evdev.ecodes.KEY_VOLUMEDOWN and ev.value in (1, 2):
                                    now = time.monotonic()
                                    if now - last_vol_time >= 0.08:
                                        if volume:
                                            volume.set_volume_delta(-5)
                                        else:
                                            subprocess.run(["amixer", "set", "Master", "5%-", "unmute"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                        last_vol_time = now

                                elif ev.code == evdev.ecodes.KEY_MUTE and ev.value == 1:
                                    if volume:
                                        volume.toggle_mute()
                                    else:
                                        subprocess.run(["amixer", "set", "Master", "toggle"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except (OSError, BlockingIOError):
                        pass

            except Exception:
                # Si falla select o lectura, recargar dispositivos y continuar
                time.sleep(0.1)
                devices = _find_input_devices()
                continue

            # ÚNICA condición que cierra el juego: tecla Q pulsada durante 1 segundo entero
            if q_press_start is not None and (time.monotonic() - q_press_start) >= 1.0:
                _force_kill(proc, is_wine)
                break
        else:
            time.sleep(0.1)
            devices = _find_input_devices()

    for dev in devices:
        try:
            dev.close()
        except Exception:
            pass


def _update_cfg_dict(file_path: str, key_values: Dict[str, Any]) -> None:
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            for k, v in key_values.items():
                val_str = f'"{v}"' if isinstance(v, str) else str(v)
                f.write(f"{k.ljust(30)}{val_str}\n")
        return

    # Backup <cfg>.onyra.bak la primera vez
    bak_file = f"{file_path}.onyra.bak"
    if not os.path.exists(bak_file):
        try:
            import shutil
            shutil.copy2(file_path, bak_file)
        except Exception:
            pass

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    keys_found = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for k, v in key_values.items():
            if stripped.startswith(k) and (len(stripped) == len(k) or stripped[len(k)].isspace()):
                val_str = f'"{v}"' if isinstance(v, str) else str(v)
                new_lines.append(f"{k.ljust(30)}{val_str}\n")
                keys_found.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in key_values.items():
        if k not in keys_found:
            val_str = f'"{v}"' if isinstance(v, str) else str(v)
            new_lines.append(f"{k.ljust(30)}{val_str}\n")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def _ensure_doom_joystick_cfg(cmd: list) -> None:
    """Asegura de forma idempotente que el motor Doom tiene activado y configurado el mando ShanWan."""
    try:
        bin_name = os.path.basename(cmd[0]) if cmd else "crispy-doom"
        cfg_dir = os.path.expanduser(f"~/.local/share/{bin_name}")
        if not os.path.exists(cfg_dir):
            cfg_dir = os.path.expanduser("~/.local/share/crispy-doom")
        os.makedirs(cfg_dir, exist_ok=True)

        cfg_path = os.path.join(cfg_dir, f"{bin_name}.cfg")
        if not os.path.exists(cfg_path) and os.path.exists(os.path.join(cfg_dir, "crispy-doom.cfg")):
            cfg_path = os.path.join(cfg_dir, "crispy-doom.cfg")

        keys_doom = {
            "use_joystick": 1,
            "use_analog": 1,
            "use_gamepad": 0,
            "joystick_index": 0,
            "joystick_guid": "",
            "joystick_y_axis": 1,              # Stick Izq Vertical -> Mover adelante/atrás
            "joystick_y_invert": 0,
            "joystick_strafe_axis": 0,         # Stick Izq Horizontal -> Strafe izquierda/derecha
            "joystick_strafe_invert": 0,
            "joystick_x_axis": 2,              # Stick Der Horizontal -> Girar izquierda/derecha
            "joystick_x_invert": 0,
            "joystick_look_axis": -1,
            "joystick_turn_sensitivity": 16,
            "joystick_move_sensitivity": 12,
            "joystick_strafe_dead_zone": 20,
            "joystick_x_dead_zone": 20,
            "joystick_y_dead_zone": 20,
            "joyb_fire": 9,                    # RT (Gatillo Derecho) -> Disparar
            "joyb_use": 0,                     # Botón A (Sur) -> Abrir puertas / Usar
            "joyb_speed": 1,                   # Botón B (Este) -> Correr / Sprint
            "joyb_prevweapon": 6,              # LB -> Arma anterior
            "joyb_nextweapon": 7,              # RB -> Arma siguiente
            "joyb_menu_activate": 11,          # Start -> Menú
            "joyb_toggle_automap": 10,         # Select / Back -> Ver mapa
            "joyb_strafe": -1,
            "joyb_strafeleft": -1,
            "joyb_straferight": -1,
            "joyb_jump": -1,
        }
        _update_cfg_dict(cfg_path, keys_doom)

        # Crispy/Chocolate Doom también lee/guarda use_joystick y botones base en default.cfg
        default_cfg = os.path.join(cfg_dir, "default.cfg")
        default_keys = {
            "use_joystick": 1,
            "joyb_fire": 9,
            "joyb_use": 0,
            "joyb_speed": 1,
            "joyb_strafe": -1,
        }
        _update_cfg_dict(default_cfg, default_keys)
    except Exception:
        pass


def prepare_launch(game: Dict[str, Any], restart_clean: bool = False) -> None:
    """Prepara el lanzamiento desacoplado: guarda los datos del juego para el ejecutor exterior."""
    launch_path = os.path.expanduser("~/.emulador/next_launch.json")
    payload = {
        "game": game,
        "restart_clean": restart_clean,
    }
    try:
        with open(launch_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def run_game(game: Dict[str, Any], restart_clean: bool = False) -> None:
    """
    Ejecuta el juego en un proceso 100% independiente y limpio (sin Pygame ni DRM de ONYRA activo).
    Monitorea la pulsación de la tecla Q durante 1 segundo mediante evdev para forzar el cierre.
    """
    orig_vt = subprocess.getoutput("fgconsole 2>/dev/null || echo 1").strip()
    if not orig_vt or not orig_vt.isdigit():
        orig_vt = "1"

    is_native = (game.get("system") == "PC Nativo")
    if not is_native:
        rom_path = game.get("rom")
        if not rom_path or not os.path.exists(rom_path):
            return

    # Si se solicitó empezar de nuevo, eliminar la instantánea previa
    if restart_clean and not is_native:
        try:
            from data import get_game_autosave
            save_file = get_game_autosave(game)
            if save_file and os.path.exists(save_file):
                os.remove(save_file)
        except Exception:
            pass

    if volume:
        volume.set_emulator_active(True)

    if sound:
        sound.play("coin")
        time.sleep(0.3)

    subprocess.run(["killall", "-9", "aplay"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    env = os.environ.copy()
    if not env.get("DISPLAY"):
        env["SDL_VIDEODRIVER"] = "kmsdrm"
    env.pop("SDL_AUDIODRIVER", None)

    # Inyectar mapeo estándar de mando ShanWan para todos los motores SDL2
    env["SDL_GAMECONTROLLERCONFIG"] = SHANWAN_MAPPING

    is_wine = (game.get("id") == "commandos" or "wine" in str(game.get("cmd", [])) or "dosbox" in str(game.get("cmd", [])))

    apply_script = "/home/jcgar/arcade/apply_input_config.py"
    if not os.path.exists(apply_script):
        apply_script = os.path.join(CORE_DIR, "apply_input_config.py")
    cfg_file = "/home/jcgar/arcade/mednafen_arcade.cfg"
    if not os.path.exists(cfg_file):
        cfg_file = os.path.join(CORE_DIR, "mednafen_arcade.cfg")

    try:
        if is_native:
            cmd = game["cmd"]
            cwd = game.get("cwd", None)

            # Activar joystick en motor Doom si corresponde
            bin_name = os.path.basename(cmd[0]) if cmd else ""
            if bin_name in ("crispy-doom", "chocolate-doom"):
                _ensure_doom_joystick_cfg(cmd)

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

            proc = subprocess.Popen(cmd, env=env, cwd=cwd, start_new_session=True, close_fds=True)
            _watch_process_and_q_key(proc, is_wine=is_wine)
        else:
            # Reconfigurar controles y lanzar Mednafen
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
            proc = subprocess.Popen(cmd, env=env, start_new_session=True, close_fds=True)
            _watch_process_and_q_key(proc, is_wine=False)
    except Exception:
        pass
    finally:
        if is_wine:
            subprocess.run(["wineserver", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["killall", "-9", "dosbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "killall", "-9", "Xorg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "pkill", "-9", "-f", "Xorg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "rm", "-f", "/tmp/.X1-lock", "/tmp/.X2-lock", "/tmp/.X11-unix/X1", "/tmp/.X11-unix/X2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Reconfigurar controles para el frontend si procede
        if apply_script and os.path.exists(apply_script):
            try:
                subprocess.run(
                    [sys.executable, apply_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3.0,
                )
            except Exception:
                pass
        if volume:
            try:
                volume.set_emulator_active(False)
            except Exception:
                pass

        # Forzar vuelta al VT de origen para evitar pantalla negra en tty2
        subprocess.run(["sudo", "chvt", orig_vt], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Restaurar teclado, pantalla activa (unblank) y modo de consola del kernel
        os.system("sudo sh -c 'echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null || true; kbd_mode -u -f 2>/dev/null || true; stty sane 2>/dev/null || true'")


def launch_game(game: Dict[str, Any], restart_clean: bool = False) -> None:
    """Prepara el lanzamiento desacoplado."""
    prepare_launch(game, restart_clean=restart_clean)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        target = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.emulador/next_launch.json")
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data_obj = json.load(f)
                run_game(data_obj["game"], restart_clean=data_obj.get("restart_clean", False))
            except Exception:
                pass

"""
Control de volumen por hardware ALSA y escucha de teclas multimedia (Logitech K400 y Mando ShanWan).
NO guarda el volumen en ningún archivo.
Al salir de la app, SIEMPRE fuerza el volumen del chip ALSA al 100% (y desmutea).
"""

import os
import re
import subprocess
import threading
import time

try:
    import evdev
except ImportError:
    evdev = None


def get_volume():
    """Obtiene el volumen actual en porcentaje (0-100)."""
    try:
        out = subprocess.check_output(["amixer", "get", "Master"], text=True)
        m = re.search(r"\[(\d+)%\]", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 100


def is_muted():
    """Comprueba si el audio está silenciado."""
    try:
        out = subprocess.check_output(["amixer", "get", "Master"], text=True)
        return "[off]" in out
    except Exception:
        return False


def reset_to_100():
    """Restaura el chip de sonido de hardware al 100% y desmutea."""
    try:
        subprocess.run(
            ["amixer", "set", "Master", "100%", "unmute"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def set_volume_percent(percent: int):
    """Ajusta el volumen a un porcentaje exacto y desmutea."""
    val = max(0, min(100, int(percent)))
    try:
        subprocess.run(
            ["amixer", "set", "Master", f"{val}%", "unmute"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    return get_volume()


def init_arcade_volume():
    """Fuerza el volumen siempre al 65% al arrancar el Arcade (sin guardar en disco)."""
    return set_volume_percent(65)


def set_volume_delta(delta):
    """Sube o baja el volumen en tiempo real (NUNCA guarda en disco)."""
    op = f"{abs(delta)}%+" if delta > 0 else f"{abs(delta)}%-"
    try:
        subprocess.run(
            ["amixer", "set", "Master", op, "unmute"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    return get_volume()


def toggle_mute():
    """Alterna el mute de hardware."""
    try:
        subprocess.run(
            ["amixer", "set", "Master", "toggle"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    return is_muted()


def format_volume_bar(width=10):
    """Devuelve una barra visual retro estilo [██████░░░░] 60%."""
    vol = get_volume()
    muted = is_muted()
    if muted:
        return f"[ SILENCIADO ]   0%"
    filled = int(round((vol / 100.0) * width))
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {vol:3d}%"


import queue

_gamepad_queue = queue.Queue()
_in_emulator = False


def set_emulator_active(active: bool):
    global _in_emulator
    _in_emulator = active


def get_gamepad_key():
    try:
        return _gamepad_queue.get_nowait()
    except Exception:
        return None


# ── Escucha de fondo de teclas multimedia y mando ────────────────────────────

class VolumeKeyListener:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._select_pressed = False

    def start(self):
        if not evdev or self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread = None

    def _worker(self):
        try:
            devices = []
            for path in evdev.list_devices():
                try:
                    d = evdev.InputDevice(path)
                    caps = d.capabilities()
                    key_caps = caps.get(evdev.ecodes.EV_KEY, [])
                    if evdev.ecodes.KEY_VOLUMEUP in key_caps or "ShanWan" in d.name:
                        devices.append(d)
                except Exception:
                    pass

            if not devices:
                return

            import select
            while not self._stop_event.is_set():
                r, _, _ = select.select(devices, [], [], 0.3)
                for dev in r:
                    for ev in dev.read():
                        # 1. Teclas multimedia de teclado (Logitech K400)
                        if "ShanWan" not in dev.name and ev.type == evdev.ecodes.EV_KEY:
                            if ev.value in (1, 2):
                                if ev.code == evdev.ecodes.KEY_VOLUMEUP:
                                    set_volume_delta(+5)
                                elif ev.code == evdev.ecodes.KEY_VOLUMEDOWN:
                                    set_volume_delta(-5)
                                elif ev.code == evdev.ecodes.KEY_MUTE and ev.value == 1:
                                    toggle_mute()
                            continue

                        # 2. Mando ShanWan
                        if _in_emulator:
                            # Dentro del juego: solo atajos de salida y volumen
                            if ev.type == evdev.ecodes.EV_KEY:
                                if ev.code == evdev.ecodes.BTN_MODE and ev.value == 1:
                                    subprocess.run(["pkill", "-TERM", "mednafen"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                elif ev.code == evdev.ecodes.BTN_SELECT:
                                    self._select_pressed = (ev.value == 1)
                                elif self._select_pressed and ev.value == 1:
                                    if ev.code == evdev.ecodes.BTN_START:
                                        subprocess.run(["pkill", "-TERM", "mednafen"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    elif ev.code == evdev.ecodes.BTN_TR:
                                        set_volume_delta(+5)
                                    elif ev.code == evdev.ecodes.BTN_TL:
                                        set_volume_delta(-5)
                        else:
                            # En el menú del arcade: navegar con el mando
                            if ev.type == evdev.ecodes.EV_KEY and ev.value == 1:
                                if ev.code in (evdev.ecodes.BTN_A, evdev.ecodes.BTN_SOUTH, evdev.ecodes.BTN_START):
                                    _gamepad_queue.put(10)  # Enter
                                elif ev.code in (evdev.ecodes.BTN_B, evdev.ecodes.BTN_EAST, evdev.ecodes.BTN_MODE):
                                    _gamepad_queue.put(ord("q"))  # Q / Volver
                            elif ev.type == evdev.ecodes.EV_ABS:
                                if ev.code == evdev.ecodes.ABS_HAT0Y:
                                    if ev.value == -1:
                                        _gamepad_queue.put(259)  # KEY_UP
                                    elif ev.value == 1:
                                        _gamepad_queue.put(258)  # KEY_DOWN
                                elif ev.code == evdev.ecodes.ABS_HAT0X:
                                    if ev.value == -1:
                                        _gamepad_queue.put(260)  # KEY_LEFT
                                    elif ev.value == 1:
                                        _gamepad_queue.put(261)  # KEY_RIGHT
                                elif ev.code == evdev.ecodes.ABS_Y:
                                    now = time.monotonic()
                                    if now - getattr(self, "_last_stick_y", 0.0) > 0.22:
                                        if ev.value < -16000:
                                            _gamepad_queue.put(259)  # KEY_UP
                                            self._last_stick_y = now
                                        elif ev.value > 16000:
                                            _gamepad_queue.put(258)  # KEY_DOWN
                                            self._last_stick_y = now
                                elif ev.code == evdev.ecodes.ABS_X:
                                    now = time.monotonic()
                                    if now - getattr(self, "_last_stick_x", 0.0) > 0.28:
                                        if ev.value < -16000:
                                            _gamepad_queue.put(260)  # KEY_LEFT
                                            self._last_stick_x = now
                                        elif ev.value > 16000:
                                            _gamepad_queue.put(261)  # KEY_RIGHT
                                            self._last_stick_x = now
        except Exception:
            pass


# Instancia global del listener de volumen
_listener = VolumeKeyListener()


def start_listener():
    _listener.start()


def stop_listener():
    _listener.stop()

"""
ONYRA - Soporte de Mando Gamepad ShanWan y Teclado Multimedia
Reutiliza evdev para capturar eventos del mando físico en segundo plano
y transmitirlos a la interfaz de Textual de forma asíncrona y segura.
"""

import select
import threading
from typing import Callable, Optional

try:
    import evdev
except ImportError:
    evdev = None

try:
    import sys
    sys.path.insert(0, "/home/jcgar/arcade")
    import volume
except Exception:
    volume = None


class GamepadListener:
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if not evdev or self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread = None

    def _run(self):
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

            while not self._stop_event.is_set():
                r, _, _ = select.select(devices, [], [], 0.2)
                for dev in r:
                    for ev in dev.read():
                        # Teclas multimedia K400
                        if "ShanWan" not in dev.name and ev.type == evdev.ecodes.EV_KEY:
                            if ev.value in (1, 2) and volume:
                                if ev.code == evdev.ecodes.KEY_VOLUMEUP:
                                    volume.set_volume_delta(+5)
                                elif ev.code == evdev.ecodes.KEY_VOLUMEDOWN:
                                    volume.set_volume_delta(-5)
                                elif ev.code == evdev.ecodes.KEY_MUTE and ev.value == 1:
                                    volume.toggle_mute()
                            continue

                        # Mando ShanWan en Menú
                        if ev.type == evdev.ecodes.EV_KEY and ev.value == 1:
                            if ev.code in (evdev.ecodes.BTN_A, evdev.ecodes.BTN_SOUTH, evdev.ecodes.BTN_START):
                                self.callback("enter")
                            elif ev.code in (evdev.ecodes.BTN_B, evdev.ecodes.BTN_EAST, evdev.ecodes.BTN_MODE):
                                self.callback("escape")
                        elif ev.type == evdev.ecodes.EV_ABS:
                            if ev.code == evdev.ecodes.ABS_HAT0Y:
                                if ev.value == -1:
                                    self.callback("up")
                                elif ev.value == 1:
                                    self.callback("down")
                            elif ev.code == evdev.ecodes.ABS_HAT0X:
                                if ev.value == -1:
                                    self.callback("left")
                                elif ev.value == 1:
                                    self.callback("right")
        except Exception:
            pass

"""
ONYRA - Gestor Unificado de Entrada Física (KMSDRM)
Lee teclado y mando ShanWan directamente por evdev para garantizar latencia cero
y evitar pérdidas de foco en Linux KMSDRM, inyectando eventos únicos en Pygame.
"""

import os
import queue
import select
import threading
import time
from typing import Optional, Set

try:
    import evdev
except ImportError:
    evdev = None

import pygame

try:
    import sys
    sys.path.insert(0, "/home/jcgar/arcade")
    import volume
except Exception:
    volume = None

# Eventos personalizados para Pygame
EVENT_ONYRA_INPUT = pygame.USEREVENT + 1

# Tipos de acciones normalizadas
ACTION_UP = "UP"
ACTION_DOWN = "DOWN"
ACTION_LEFT = "LEFT"
ACTION_RIGHT = "RIGHT"
ACTION_ENTER = "ENTER"
ACTION_BACK = "BACK"
ACTION_CHAR = "CHAR"
ACTION_BACKSPACE = "BACKSPACE"

KEY_CHAR_MAP = {
    evdev.ecodes.KEY_A: "a", evdev.ecodes.KEY_B: "b", evdev.ecodes.KEY_C: "c",
    evdev.ecodes.KEY_D: "d", evdev.ecodes.KEY_E: "e", evdev.ecodes.KEY_F: "f",
    evdev.ecodes.KEY_G: "g", evdev.ecodes.KEY_H: "h", evdev.ecodes.KEY_I: "i",
    evdev.ecodes.KEY_J: "j", evdev.ecodes.KEY_K: "k", evdev.ecodes.KEY_L: "l",
    evdev.ecodes.KEY_M: "m", evdev.ecodes.KEY_N: "n", evdev.ecodes.KEY_O: "o",
    evdev.ecodes.KEY_P: "p", evdev.ecodes.KEY_Q: "q", evdev.ecodes.KEY_R: "r",
    evdev.ecodes.KEY_S: "s", evdev.ecodes.KEY_T: "t", evdev.ecodes.KEY_U: "u",
    evdev.ecodes.KEY_V: "v", evdev.ecodes.KEY_W: "w", evdev.ecodes.KEY_X: "x",
    evdev.ecodes.KEY_Y: "y", evdev.ecodes.KEY_Z: "z",
    evdev.ecodes.KEY_0: "0", evdev.ecodes.KEY_1: "1", evdev.ecodes.KEY_2: "2",
    evdev.ecodes.KEY_3: "3", evdev.ecodes.KEY_4: "4", evdev.ecodes.KEY_5: "5",
    evdev.ecodes.KEY_6: "6", evdev.ecodes.KEY_7: "7", evdev.ecodes.KEY_8: "8",
    evdev.ecodes.KEY_9: "9", evdev.ecodes.KEY_SPACE: " ",
} if evdev else {}


class InputManager:
    def __init__(self):
        self._stop_event = threading.Event()
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._select_pressed = False
        self._last_event_time = 0.0
        self._last_action = ""

    def start(self):
        if not evdev or self._thread is not None:
            return
        self._stop_event.clear()
        self._paused = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def pause(self):
        self._paused = True

    def resume(self):
        # Drenar eventos residuales de los dispositivos antes de escuchar
        try:
            if evdev:
                for path in evdev.list_devices():
                    try:
                        d = evdev.InputDevice(path)
                        while d.read_one() is not None:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass
        self._paused = False
        self.flush()
        # Cooldown de 0.4s tras volver para no registrar pulsaciones de salida del emulador
        self._last_event_time = time.monotonic() + 0.4

    def flush(self):
        """Descarta cualquier evento pendiente en la cola de pygame y resetea debounce."""
        self._last_action = ""
        self._last_event_time = time.monotonic()
        try:
            pygame.event.clear(EVENT_ONYRA_INPUT)
            pygame.event.clear()
        except Exception:
            pass

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread = None

    def post_action(self, action: str, char_val: str = ""):
        if self._paused:
            return

        now = time.monotonic()
        # Debounce rápido (60ms) para evitar rebotes de contactos
        if action == self._last_action and (now - self._last_event_time) < 0.06:
            return

        self._last_action = action
        self._last_event_time = now

        try:
            evt = pygame.event.Event(EVENT_ONYRA_INPUT, action=action, char=char_val)
            pygame.event.post(evt)
        except Exception:
            pass

    def _worker(self):
        while not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.1)
                continue

            devices = []
            try:
                for path in evdev.list_devices():
                    try:
                        d = evdev.InputDevice(path)
                        caps = d.capabilities()
                        key_caps = caps.get(evdev.ecodes.EV_KEY, [])
                        if (evdev.ecodes.KEY_ENTER in key_caps or
                            evdev.ecodes.KEY_VOLUMEUP in key_caps or
                            "ShanWan" in d.name or
                            "Gamepad" in d.name or
                            "Keyboard" in d.name):
                            devices.append(d)
                    except Exception:
                        pass
            except Exception:
                time.sleep(0.5)
                continue

            if not devices:
                time.sleep(0.5)
                continue

            try:
                while not self._stop_event.is_set() and not self._paused:
                    r, _, _ = select.select(devices, [], [], 0.2)
                    for dev in r:
                        for ev in dev.read():
                            if self._paused:
                                break

                            # 1. Gamepad ShanWan
                            if "ShanWan" in dev.name or "Gamepad" in dev.name:
                                if ev.type == evdev.ecodes.EV_KEY:
                                    if ev.code == evdev.ecodes.BTN_SELECT:
                                        self._select_pressed = (ev.value == 1)
                                    elif self._select_pressed and ev.value == 1:
                                        if ev.code == evdev.ecodes.BTN_TR and volume:
                                            volume.set_volume_delta(+5)
                                        elif ev.code == evdev.ecodes.BTN_TL and volume:
                                            volume.set_volume_delta(-5)
                                    elif ev.value == 1: # Pulsación
                                        if ev.code in (evdev.ecodes.BTN_A, evdev.ecodes.BTN_SOUTH, evdev.ecodes.BTN_START):
                                            self.post_action(ACTION_ENTER)
                                        elif ev.code in (evdev.ecodes.BTN_B, evdev.ecodes.BTN_EAST, evdev.ecodes.BTN_MODE):
                                            self.post_action(ACTION_BACK)
                                elif ev.type == evdev.ecodes.EV_ABS:
                                    if ev.code == evdev.ecodes.ABS_HAT0Y:
                                        if ev.value == -1:
                                            self.post_action(ACTION_UP)
                                        elif ev.value == 1:
                                            self.post_action(ACTION_DOWN)
                                    elif ev.code == evdev.ecodes.ABS_HAT0X:
                                        if ev.value == -1:
                                            self.post_action(ACTION_LEFT)
                                        elif ev.value == 1:
                                            self.post_action(ACTION_RIGHT)
                                continue

                            # 2. Teclado Físico
                            if ev.type == evdev.ecodes.EV_KEY:
                                if ev.value in (1, 2) and volume: # Pulsación o repetición de volumen
                                    if ev.code == evdev.ecodes.KEY_VOLUMEUP:
                                        volume.set_volume_delta(+5)
                                        continue
                                    elif ev.code == evdev.ecodes.KEY_VOLUMEDOWN:
                                        volume.set_volume_delta(-5)
                                        continue
                                    elif ev.code == evdev.ecodes.KEY_MUTE and ev.value == 1:
                                        volume.toggle_mute()
                                        continue

                                if ev.value == 1: # Key down
                                    if ev.code in (evdev.ecodes.KEY_UP, evdev.ecodes.KEY_W):
                                        self.post_action(ACTION_UP)
                                    elif ev.code in (evdev.ecodes.KEY_DOWN, evdev.ecodes.KEY_S):
                                        self.post_action(ACTION_DOWN)
                                    elif ev.code in (evdev.ecodes.KEY_LEFT, evdev.ecodes.KEY_A):
                                        self.post_action(ACTION_LEFT)
                                    elif ev.code in (evdev.ecodes.KEY_RIGHT, evdev.ecodes.KEY_D):
                                        self.post_action(ACTION_RIGHT)
                                    elif ev.code in (evdev.ecodes.KEY_ENTER, evdev.ecodes.KEY_KPENTER, evdev.ecodes.KEY_SPACE):
                                        self.post_action(ACTION_ENTER)
                                    elif ev.code in (evdev.ecodes.KEY_ESC, evdev.ecodes.KEY_Q):
                                        self.post_action(ACTION_BACK)
                                    elif ev.code == evdev.ecodes.KEY_BACKSPACE:
                                        self.post_action(ACTION_BACKSPACE)
                                    elif ev.code in KEY_CHAR_MAP:
                                        self.post_action(ACTION_CHAR, KEY_CHAR_MAP[ev.code])
            except Exception:
                time.sleep(0.5)


input_mgr = InputManager()

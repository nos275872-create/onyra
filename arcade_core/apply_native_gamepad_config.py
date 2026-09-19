#!/usr/bin/env python3
"""
ONYRA - Autoconfigurador de Mando ShanWan (Layout Xbox) para Motores Nativos de PC
Configura los archivos de configuración de crispy-doom, quakespasm, yamagi-quake2,
scummvm y sdlpop antes de lanzar el juego.
"""

import os
import re
import sys
from typing import Dict, Optional


def update_crispy_config(path: str, settings: Dict[str, Any]) -> None:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lines = []
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

    keys_found = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for k, v in settings.items():
            if stripped.startswith(k) and (len(stripped) == len(k) or stripped[len(k)].isspace()):
                new_lines.append(f"{k.ljust(30)}{v}\n")
                keys_found.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in settings.items():
        if k not in keys_found:
            new_lines.append(f"{k.ljust(30)}{v}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def configure_crispy_doom():
    """Configura DOOM / DOOM II para mando ShanWan."""
    base_dir = os.path.expanduser("~/.local/share/crispy-doom")
    os.makedirs(base_dir, exist_ok=True)

    # También asegurar enlace simbólico en ~/.crispy-doom si es necesario
    compat_dir = os.path.expanduser("~/.crispy-doom")
    if not os.path.exists(compat_dir):
        try:
            os.symlink(base_dir, compat_dir)
        except Exception:
            pass

    default_cfg = os.path.join(base_dir, "default.cfg")
    crispy_cfg = os.path.join(base_dir, "crispy-doom.cfg")

    # default.cfg: activación de joystick y acciones base
    default_settings = {
        "use_joystick": 1,
        "joyb_fire": 0,       # Botón A (Sur) -> Disparar
        "joyb_strafe": -1,    # Strafe en botones dedicados (LB/RB)
        "joyb_use": 3,        # Botón X (Oeste) -> Abrir puertas / Usar
        "joyb_speed": 1,      # Botón B -> Correr turbo (mantener)
        "joyb_jump": -1,
    }
    update_crispy_config(default_cfg, default_settings)

    # crispy-doom.cfg: ejes analógicos y asignación de botones extendidos
    crispy_settings = {
        "joystick_index": 0,
        "joystick_x_axis": 0,              # Stick izq X -> Girar izq/der
        "joystick_x_invert": 0,
        "joystick_y_axis": 1,              # Stick izq Y -> Mover adelante/atrás
        "joystick_y_invert": 0,
        "joystick_turn_sensitivity": 12,
        "joystick_move_sensitivity": 10,
        "joyb_strafeleft": 6,              # LB -> Strafe izquierda
        "joyb_straferight": 7,             # RB -> Strafe derecha
        "joyb_nextweapon": 9,              # RT -> Cambiar arma siguiente
        "joyb_prevweapon": 8,              # LT -> Cambiar arma anterior
        "joyb_toggle_automap": 10,         # Select/Back -> Ver mapa
        "joyb_menu_activate": 11,          # Start -> Menú
        "use_analog": 1,
        "use_gamepad": 0,
    }
    update_crispy_config(crispy_cfg, crispy_settings)


def configure_quakespasm():
    """Configura Quake (quakespasm) para mando ShanWan."""
    cfg_path = os.path.expanduser("~/.quakespasm/id1/config.cfg")
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)

    binds = {
        "RTRIGGER": "+attack",             # RT -> Disparar
        "JOY1": "+jump",                   # Botón A -> Saltar
        "RSHOULDER": "impulse 10",         # RB -> Cambiar arma siguiente
        "LSHOULDER": "impulse 12",         # LB -> Cambiar arma anterior
        "JOY3": "impulse 10",              # Botón X -> Usar / Impulso
        "LTHUMB": "+speed",                # Stick izq pulsado (L3) -> Correr
        "JOY2": "+speed",                  # Botón B -> Correr (fallback)
        "START": "togglemenu",             # Start -> Menú
        "BACK": "+showscores",             # Select -> Puntuaciones
    }

    cvars = {
        "joy_enable": "1",
        "joy_deadzone_move": "0.175",
        "joy_deadzone_look": "0.175",
        "joy_deadzone_trigger": "0.2",
        "joy_exponent": "2",
        "joy_exponent_move": "2",
        "joy_invert": "0",
        "joy_sensitivity_pitch": "130",
        "joy_sensitivity_yaw": "240",
        "joy_swapmovelook": "0",
    }

    lines = []
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

    # Filtrar binds viejos para evitar duplicados
    bind_keys = {k.upper() for k in binds}
    cvar_keys = {k.lower() for k in cvars}

    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].lower() == "bind":
            k = parts[1].strip('"').upper()
            if k in bind_keys:
                continue
        elif len(parts) >= 1:
            c = parts[0].strip('"').lower()
            if c in cvar_keys:
                continue
        new_lines.append(line)

    for k, v in cvars.items():
        new_lines.append(f'{k} "{v}"\n')
    for k, v in binds.items():
        new_lines.append(f'bind "{k}" "{v}"\n')

    with open(cfg_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def configure_yamagi_quake2():
    """Configura Quake II (yamagi-quake2) para mando ShanWan."""
    cfg_path = os.path.expanduser("~/.yq2/baseq2/config.cfg")
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)

    binds = {
        "TRIG_RIGHT": "+attack",           # RT -> Disparar
        "BTN_SOUTH": "+moveup",            # Botón A -> Saltar (+moveup en Q2)
        "BTN_EAST": "+movedown",           # Botón B -> Agacharse (+movedown en Q2)
        "SHOULDR_RIGHT": "weapnext",       # RB -> Cambiar arma siguiente
        "SHOULDR_LEFT": "weapprev",        # LB -> Cambiar arma anterior
        "BTN_NORTH": "invuse",             # Botón X -> Usar item
        "STICK_LEFT": "+speed",            # L3 -> Correr
        "BTN_START": "pause",              # Start -> Pausa
        "BTN_BACK": "inven",               # Select -> Inventario
    }

    cvars = {
        "cl_run": "1",
        "in_grab": "2",
        "joy_left_deadzone": "0.16",
        "joy_right_deadzone": "0.16",
        "joy_trigger": "0.2",
        "joy_sensitivity": "3",
    }

    lines = []
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

    bind_keys = {k.upper() for k in binds}
    cvar_keys = {k.lower() for k in cvars}

    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].lower() == "bind":
            k = parts[1].strip('"').upper()
            if k in bind_keys:
                continue
        elif len(parts) >= 2 and parts[0].lower() == "set":
            c = parts[1].strip('"').lower()
            if c in cvar_keys:
                continue
        new_lines.append(line)

    for k, v in cvars.items():
        new_lines.append(f'set {k} "{v}"\n')
    for k, v in binds.items():
        new_lines.append(f'bind {k} "{v}"\n')

    with open(cfg_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def configure_scummvm():
    """Configura ScummVM para emulación de puntero de ratón con mando ShanWan."""
    ini_path = os.path.expanduser("~/.config/scummvm/scummvm.ini")
    if not os.path.exists(ini_path):
        return

    with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Asegurar joystick_num=0 bajo la sección [scummvm]
    if "[scummvm]" in content:
        if "joystick_num=" in content:
            content = re.sub(r"^joystick_num=.*$", "joystick_num=0", content, flags=re.MULTILINE)
        else:
            content = content.replace("[scummvm]\n", "[scummvm]\njoystick_num=0\n")

        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(content)


def configure_sdlpop():
    """Configura opciones de mando para SDLPoP en SDLPoP.ini."""
    ini_path = os.path.expanduser("~/arcade/native/sdlpop/SDLPoP.ini")
    if not os.path.exists(ini_path):
        return

    with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Asegurar enable_controller_rumble y threshold
    if "enable_controller_rumble" in content:
        content = re.sub(r"^enable_controller_rumble\s*=.*$", "enable_controller_rumble = true", content, flags=re.MULTILINE)
    if "joystick_threshold" in content:
        content = re.sub(r"^joystick_threshold\s*=.*$", "joystick_threshold = 8000", content, flags=re.MULTILINE)

    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(content)


def apply_for_game(game_id: str):
    """Aplica la configuración según el id del juego."""
    gid = game_id.lower()
    if gid in ["doom", "doom2"]:
        configure_crispy_doom()
    elif gid == "quake":
        configure_quakespasm()
    elif gid == "quake2":
        configure_yamagi_quake2()
    elif gid in ["monkey1", "monkey2", "tentacle", "atlantis", "samnmax"]:
        configure_scummvm()
    elif gid == "prince_of_persia":
        configure_sdlpop()
    elif gid in ["all", "--all"]:
        configure_crispy_doom()
        configure_quakespasm()
        configure_yamagi_quake2()
        configure_scummvm()
        configure_sdlpop()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "--all"
    apply_for_game(target)

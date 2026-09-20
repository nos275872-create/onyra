#!/bin/bash
# ONYRA - Lanzador DOSBox genérico para juegos "PC Nativo" (DOS).
# Uso: dosbox_run.sh <ruta_al_conf_o_directorio> [args_extra...]
set -u

TARGET="${1:-}"
[ $# -gt 0 ] && shift || true

if [ -z "$TARGET" ]; then
    clear
    echo "============================================================"
    echo "  ONYRA - Especifica un archivo de configuración o carpeta DOSBox"
    echo "============================================================"
    read -t 3 -p "  Volviendo al menú de ONYRA..." || true
    exit 1
fi

CONF=""
GAME_DIR=""

if [ -f "$TARGET" ]; then
    CONF="$TARGET"
    GAME_DIR="$(dirname "$TARGET")"
elif [ -d "$TARGET" ]; then
    GAME_DIR="$TARGET"
    if [ -f "$TARGET/dosbox.conf" ]; then
        CONF="$TARGET/dosbox.conf"
    elif [ -f "$TARGET/dosbox.cfg" ]; then
        CONF="$TARGET/dosbox.cfg"
    else
        CONF="$(find "$TARGET" -maxdepth 2 -name "*.conf" -print -quit 2>/dev/null)"
    fi
fi

if [ -z "$CONF" ] || [ ! -f "$CONF" ]; then
    clear
    echo "============================================================"
    echo "  ONYRA - No se ha encontrado archivo de configuración DOSBox:"
    echo "    $TARGET"
    echo "============================================================"
    read -t 3 -p "  Volviendo al menú de ONYRA..." || true
    exit 1
fi

DOSBOX_BIN="$(command -v dosbox || echo /usr/bin/dosbox)"
if [ ! -x "$DOSBOX_BIN" ]; then
    clear
    echo "============================================================"
    echo "  DOSBox no está instalado. Instálalo con: sudo apt install dosbox"
    echo "============================================================"
    read -t 3 -p "  Volviendo al menú de ONYRA..." || true
    exit 1
fi

# Detectar terminal virtual (VT) actual para restaurarlo siempre al salir
ORIG_VT="$(fgconsole 2>/dev/null || echo 1)"
[ -z "$ORIG_VT" ] && ORIG_VT=1

# Buscar número de DISPLAY libre (:1, :2, etc.) y limpiar bloqueos obsoletos
DISP_NUM=1
for d in 1 2 3 4 5; do
    if [ ! -e "/tmp/.X11-unix/X$d" ] && [ ! -f "/tmp/.X$d-lock" ]; then
        DISP_NUM="$d"
        break
    fi
done

if [ -f "/tmp/.X${DISP_NUM}-lock" ]; then
    LOCK_PID="$(cat "/tmp/.X${DISP_NUM}-lock" 2>/dev/null | tr -d ' \n')"
    if [ -n "$LOCK_PID" ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
        rm -f "/tmp/.X${DISP_NUM}-lock" "/tmp/.X11-unix/X${DISP_NUM}" 2>/dev/null || true
    fi
fi

# DOSBox 0.74 usa SDL 1.2, que requiere X11 y no soporta SDL_VIDEODRIVER=kmsdrm
unset SDL_VIDEODRIVER

if [ -n "$GAME_DIR" ] && [ -d "$GAME_DIR" ]; then
    cd "$GAME_DIR" || exit 1
fi

if [ -z "${DISPLAY:-}" ]; then
    cleanup() {
        # Matar procesos DOSBox y Xorg
        killall -9 dosbox >/dev/null 2>&1 || true
        sudo killall -9 Xorg >/dev/null 2>&1 || true
        sudo pkill -9 -f "Xorg" >/dev/null 2>&1 || true
        sudo rm -f "/tmp/.X${DISP_NUM:-1}-lock" "/tmp/.X11-unix/X${DISP_NUM:-1}" 2>/dev/null || true

        # Restaurar VT original para evitar pantalla negra
        if [ -n "${ORIG_VT:-}" ] && [ "$ORIG_VT" -gt 0 ] 2>/dev/null; then
            sudo chvt "$ORIG_VT" 2>/dev/null || true
        fi

        # Restaurar modo del teclado y terminal
        sudo kbd_mode -u -f 2>/dev/null || true
        stty sane 2>/dev/null || true
    }
    trap cleanup EXIT INT TERM

    # Lanzar servidor Xorg dedicado para el juego DOSBox
    if [ -n "$ORIG_VT" ] && [ "$ORIG_VT" -gt 0 ] 2>/dev/null; then
        xinit "$DOSBOX_BIN" -conf "$CONF" -noconsole -c "exit" "$@" -- ":$DISP_NUM" "vt$ORIG_VT" -keeptty -nolisten tcp 2>/tmp/xorg_dosbox.log || \
        xinit "$DOSBOX_BIN" -conf "$CONF" -noconsole -c "exit" "$@" -- ":$DISP_NUM" -nolisten tcp 2>/tmp/xorg_dosbox.log
    else
        xinit "$DOSBOX_BIN" -conf "$CONF" -noconsole -c "exit" "$@" -- ":$DISP_NUM" -nolisten tcp 2>/tmp/xorg_dosbox.log
    fi
else
    "$DOSBOX_BIN" -conf "$CONF" -noconsole -c "exit" "$@"
fi

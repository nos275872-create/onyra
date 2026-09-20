#!/bin/bash
# ONYRA - Lanzador Wine genérico para juegos "PC Nativo".
# Uso: wine_run.sh <ruta_absoluta_al_exe> <nombre_prefix> [args_extra...]
set -u

EXE="$1"; shift || true
PREFIX_NAME="${1:-default}"
[ $# -gt 0 ] && shift

# Búsqueda insensible a mayúsculas/minúsculas si la ruta exacta no existe en disco
if [ -n "${EXE:-}" ] && [ ! -f "$EXE" ]; then
    EXE_DIR="$(dirname "$EXE")"
    EXE_BASE="$(basename "$EXE")"
    if [ -d "$EXE_DIR" ]; then
        MATCH="$(find "$EXE_DIR" -maxdepth 1 -iname "$EXE_BASE" -print -quit 2>/dev/null)"
        if [ -n "$MATCH" ] && [ -f "$MATCH" ]; then
            EXE="$MATCH"
        elif [ "$EXE_BASE" = "WARGAME.EXE" ] || [ "$EXE_BASE" = "wargame.exe" ]; then
            for alt in "Comandos.exe" "comandos.exe" "Commandos.exe" "commandos.exe"; do
                if [ -f "$EXE_DIR/$alt" ]; then
                    EXE="$EXE_DIR/$alt"
                    break
                fi
            done
        fi
    fi
fi

if [ -z "${EXE:-}" ] || [ ! -f "$EXE" ]; then
    clear
    echo "============================================================"
    echo "  ONYRA - No se ha encontrado el ejecutable:"
    echo "    ${EXE:-<vacío>}"
    echo "============================================================"
    read -t 3 -p "  Volviendo al menú de ONYRA..." || true
    exit 1
fi

if ! command -v wine >/dev/null 2>&1; then
    clear
    echo "============================================================"
    echo "  Wine no está instalado. Instálalo con: sudo apt install wine wine32:i386"
    echo "  (o vuelve a ejecutar ./install.sh --with-wine)"
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

cleanup() {
    # 1. Matar servidor Wine y procesos X (con sudo para alcanzar Xorg suid-root)
    wineserver -k >/dev/null 2>&1 || true
    sudo killall -9 Xorg >/dev/null 2>&1 || true
    sudo pkill -9 -f "Xorg" >/dev/null 2>&1 || true
    sudo rm -f "/tmp/.X${DISP_NUM:-1}-lock" "/tmp/.X11-unix/X${DISP_NUM:-1}" 2>/dev/null || true

    # 2. Restaurar VT original para evitar pantalla negra
    if [ -n "${ORIG_VT:-}" ] && [ "$ORIG_VT" -gt 0 ] 2>/dev/null; then
        sudo chvt "$ORIG_VT" 2>/dev/null || true
    fi

    # 3. Restaurar modo del teclado y terminal
    sudo kbd_mode -u -f 2>/dev/null || true
    stty sane 2>/dev/null || true
}
trap cleanup EXIT INT TERM

export WINEPREFIX="$HOME/arcade/wine/$PREFIX_NAME"
mkdir -p "$WINEPREFIX"
export WINEDEBUG=-all
export WINEDLLOVERRIDES="mscoree,mshtml="
unset SDL_VIDEODRIVER

cd "$(dirname "$EXE")" || exit 1
EXE_NAME="$(basename "$EXE")"
WINE_BIN="$(command -v wine || echo /usr/bin/wine)"

if [ -z "${DISPLAY:-}" ]; then
    # Lanzar servidor Xorg dedicado para el juego
    if [ -n "$ORIG_VT" ] && [ "$ORIG_VT" -gt 0 ] 2>/dev/null; then
        xinit "$WINE_BIN" "$EXE_NAME" "$@" -- ":$DISP_NUM" "vt$ORIG_VT" -keeptty -nolisten tcp 2>/tmp/xorg_run.log || \
        xinit "$WINE_BIN" "$EXE_NAME" "$@" -- ":$DISP_NUM" -nolisten tcp 2>/tmp/xorg_run.log
    else
        xinit "$WINE_BIN" "$EXE_NAME" "$@" -- ":$DISP_NUM" -nolisten tcp 2>/tmp/xorg_run.log
    fi
else
    "$WINE_BIN" "$EXE_NAME" "$@"
    wineserver -w
fi

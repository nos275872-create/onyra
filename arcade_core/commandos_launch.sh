#!/bin/bash
# ONYRA - Lanzador para Commandos: Behind Enemy Lines
# Pyro Studios (1998)
GAME_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$GAME_DIR" || exit 1

# Buscar ejecutable común de Commandos
EXE=""
for cand in "WARGAME.EXE" "wargame.exe" "Commandos.exe" "commandos.exe" "comandos.exe"; do
    if [ -f "$cand" ]; then
        EXE="$cand"
        break
    fi
done

if [ -z "$EXE" ]; then
    clear
    echo "============================================================"
    echo "  ONYRA - Commandos: Behind Enemy Lines (Pyro Studios 1998)"
    echo "============================================================"
    echo ""
    echo "  No se ha encontrado el ejecutable del juego (WARGAME.EXE)."
    echo "  Por favor, copia los archivos de instalación del juego en:"
    echo "    $GAME_DIR"
    echo ""
    echo "============================================================"
    read -p "  Pulsa ENTER para volver al menú de ONYRA..."
    exit 1
fi

if ! command -v wine >/dev/null 2>&1; then
    clear
    echo "============================================================"
    echo "  Wine no está instalado en el sistema."
    echo "  Para instalarlo, sal a la terminal y ejecuta:"
    echo "    sudo apt update && sudo apt install -y wine"
    echo "============================================================"
    read -p "  Pulsa ENTER para volver al menú de ONYRA..."
    exit 1
fi

# Si se ejecuta directamente en consola sin servidor X11 activo:
if [ -z "$DISPLAY" ]; then
    xinit /usr/bin/wine "$EXE" -- :1 vt$(fgconsole 2>/dev/null || echo 1)
else
    wine "$EXE"
fi

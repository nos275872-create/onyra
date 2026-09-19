#!/usr/bin/env bash
# ==============================================================================
# ONYRA - Luxury Retro Gaming Experience: Instalador Automatizado
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "    ONYRA - Luxury Retro Gaming Experience"
echo "    Instalación y Configuración del Sistema"
echo "============================================================"
echo ""

# 1. Comprobar paquetes del sistema
echo "[1/5] Verificando dependencias del sistema..."
MISSING_PKGS=()
for pkg in python3 python3-venv python3-pip mednafen alsa-utils; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "Faltan paquetes necesarios: ${MISSING_PKGS[*]}"
    echo "Instalando paquetes mediante sudo apt..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${MISSING_PKGS[@]}"
else
    echo "✓ Todas las dependencias del sistema están presentes."
fi

# 2. Comprobar grupos de usuario (audio, video, input)
echo "[2/5] Verificando permisos de hardware..."
CURRENT_GROUPS=$(groups)
for grp in video input audio; do
    if [[ ! "$CURRENT_GROUPS" =~ $grp ]]; then
        echo "Añadiendo usuario $USER al grupo $grp..."
        sudo usermod -aG "$grp" "$USER" || true
    fi
done

# 3. Entorno virtual de Python
echo "[3/5] Configurando entorno virtual Python (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "✓ Entorno virtual preparado con pygame-ce, pillow, evdev y dependencias."

# 4. Enlazar lanzador a ~/.local/bin/emulador
echo "[4/5] Configurando ejecutable de terminal 'emulador'..."
mkdir -p "$HOME/.local/bin"
cp -p "$SCRIPT_DIR/bin/emulador" "$HOME/.local/bin/emulador"
chmod +x "$HOME/.local/bin/emulador"
chmod +x "$SCRIPT_DIR/arcade_core/commandos_launch.sh" 2>/dev/null || true

# Asegurar ~/.local/bin en PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    if [ -f "$HOME/.bashrc" ] && ! grep -q 'HOME/.local/bin' "$HOME/.bashrc"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
fi
echo "✓ Lanzador instalado en $HOME/.local/bin/emulador"

# 5. Comprobar archivos de audio y fuentes
echo "[5/5] Comprobando assets y fuentes..."
if [ -d "assets/fonts" ]; then
    echo "✓ Fuentes oficiales cargadas correctamente."
fi

echo ""
echo "============================================================"
echo "  ¡Instalación completada con éxito!"
echo "  Para abrir ONYRA en cualquier momento, escribe:"
echo "    emulador"
echo "============================================================"
echo ""

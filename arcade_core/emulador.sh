#!/bin/bash
# ==============================================================================
# ARCADE RETRO STATION / ONYRA - Lanzador Ultraligero (Curses + Framebuffer Boxart)
# ==============================================================================
# Compatible con consola framebuffer / KMSDRM y HDMI de la tele.
# Rendimiento 100% nativo, cero parpadeo, cero bloqueo de pantalla al salir.

if [ -z "$DISPLAY" ]; then
    export SDL_VIDEODRIVER=kmsdrm
fi

cd /home/jcgar/arcade || exit 1

# Volumen inicial de hardware al 65% (sin persistencia)
amixer set Master 65% unmute >/dev/null 2>&1 || true

# Ejecutar el frontend interactivo con soporte de carátulas en /dev/fb0
/home/jcgar/.emulador/venv/bin/python /home/jcgar/arcade/arcade.py

# Al salir: limpieza inmediata y retorno limpio a la terminal
killall -9 mednafen 2>/dev/null || true
wineserver -k 2>/dev/null || true
sudo killall -9 dosbox 2>/dev/null || true
sudo killall -9 Xorg 2>/dev/null || true
sudo rm -f /tmp/.X*-lock /tmp/.X11-unix/X* 2>/dev/null || true
sudo kbd_mode -u -f 2>/dev/null || true
stty sane 2>/dev/null || true
amixer set Master 100% unmute >/dev/null 2>&1 || true
clear
tput cnorm 2>/dev/null || true
printf "\033[?25h" 2>/dev/null || true
echo "Arcade cerrado. Rendimiento liberado."
echo "Para volver a jugar:  emulador"
echo "Para volver a la TV:   deportes"
echo ""

#!/bin/bash
# ONYRA - Luxury Retro Gaming Experience
# Lanzador compatible con terminal truecolor, consola KMSDRM y HDMI

# Exportar controladores de bajo nivel para SDL si no hay servidor X
if [ -z "$DISPLAY" ]; then
    export SDL_VIDEODRIVER=kmsdrm
fi

cd /home/jcgar/.emulador || exit 1

# Volumen inicial de hardware al 65% (sin persistencia)
amixer set Master 65% unmute >/dev/null 2>&1 || true

# Ejecutar ONYRA en su entorno virtual optimizado
/home/jcgar/.emulador/venv/bin/python /home/jcgar/.emulador/app.py

# Al salir: limpieza absoluta de recursos y restauración de terminal
killall -9 mednafen 2>/dev/null || true
sudo kbd_mode -u -f 2>/dev/null || true
stty sane 2>/dev/null || true
amixer set Master 100% unmute >/dev/null 2>&1 || true
clear
tput cnorm 2>/dev/null || true
echo "ONYRA cerrado. Rendimiento liberado."
echo "Para volver a jugar:  emulador"
echo "Para volver a la TV:   deportes"
echo ""

# INSTRUCCIONES DEL PROYECTO: INTEGRACIÓN SISTEMÁTICA DE JUEGOS EN ONYRA

> **LEER OBLIGATORIAMENTE AL TRABAJAR CON ONYRA / RETRO ARCADE**:
> Este documento contiene el procedimiento exacto y sistemático para añadir cualquier juego al sistema arcade **ONYRA**.
> **NO pierdas tokens explorando el código desde cero**. Sigue esta guía paso a paso según el tipo de juego.

---

## 1. Arquitectura y Ubicaciones Clave de ONYRA

* **Frontend Activo (Curses + Framebuffer Boxart /dev/fb0)**: `/home/jcgar/arcade/arcade.py`
* **Frontend Gráfico Alternativo (Pygame KMSDRM)**: `/home/jcgar/.emulador/`
* **Catálogo Maestro de Juegos (`GAMES`)**:
  * Archivo 1: `/home/jcgar/arcade/arcade.py`
  * Archivo 2: `/home/jcgar/.emulador/arcade_core/arcade.py`
  * ⚠️ **REGLA CRÍTICA**: Siempre mantén **AMBOS** archivos `arcade.py` sincronizados con el mismo contenido.
* **Directorio de ROMs de Consola**: `/home/jcgar/arcade/roms/` (`snes`, `megadrive`, `nes`, `gb`)
* **Directorio de Juegos de PC (Nativos / Wine / DOSBox)**: `/home/jcgar/arcade/native/<id_juego>/`
* **Prefijos de Wine existentes**: `/home/jcgar/arcade/wine/` (`win98` para clásicos de los 90, `winxp` para 2000-2014)
* **Lanzador Wine desacoplado**: `/home/jcgar/arcade/wine_run.sh`
* **Lanzador DOSBox desacoplado**: `/home/jcgar/arcade/dosbox_run.sh`
* **Caché de Carátulas (Boxart)**: `/home/jcgar/.emulador/cache/covers/<id_juego>.png`

---

## 2. Procedimiento Sistemático según el Tipo de Juego

El catálogo de ONYRA valida en tiempo real la existencia física del archivo. Si el archivo o ejecutable no existe en disco, el juego no aparecerá en el menú.

---

### TIPO A: ROMs de Consola Clásica (SNES, Mega Drive, NES, Game Boy)
*Motor: Mednafen (KMSDRM / softfb / SDL2)*

1. **Colocar la ROM en su carpeta correspondiente**:
   * SNES: `/home/jcgar/arcade/roms/snes/NombreJuego.sfc` (o `.smc`)
   * Mega Drive: `/home/jcgar/arcade/roms/megadrive/NombreJuego.md` (o `.bin`)
   * NES: `/home/jcgar/arcade/roms/nes/NombreJuego.nes`
   * Game Boy: `/home/jcgar/arcade/roms/gb/NombreJuego.gb` (o `.gbc`)

2. **Registrar en la lista `GAMES` de `arcade.py`**:
   ```python
   {
       "id": "mi_juego",
       "title": "Nombre del Juego (Región)",
       "system": "SNES",  # "SNES" | "Mega Drive" | "NES" | "Game Boy"
       "year": "1994",
       "dev": "Desarrollador",
       "genre": "Plataformas / Acción",
       "rom": os.path.join(ROMS_DIR, "snes/NombreJuego.sfc"),
       "desc": "Descripción atractiva e histórica en español...",
       "controls": "Cruceta: Mover | A: Acción | B: Salto | Start: Pausa",
   },
   ```

3. **Añadir Carátula**:
   Descarga la carátula en `/home/jcgar/.emulador/cache/covers/mi_juego.png` (formato PNG, vertical o cuadrado).

---

### TIPO B: Motor Nativo Linux / Source Port (Doom, Quake, SDLPoP, etc.)
*Cero emulación, 100% C/C++/SDL2*

1. **Colocar datos y binario en `/home/jcgar/arcade/native/<id_juego>/`**.
2. **Registrar en la lista `GAMES` de `arcade.py`**:
   ```python
   {
       "id": "mi_juego_nativo",
       "title": "Nombre del Juego",
       "system": "PC Nativo",
       "year": "1996",
       "dev": "Desarrollador",
       "genre": "FPS / Acción",
       "cmd": ["binario_o_lanzador", "-args", os.path.join(NATIVE_DIR, "mi_juego_nativo/DATA.WAD")],
       "cwd": os.path.join(NATIVE_DIR, "mi_juego_nativo"),
       "desc": "Descripción histórica...",
       "controls": "Mando / Teclado...",
   },
   ```
3. **Añadir Carátula**: `/home/jcgar/.emulador/cache/covers/mi_juego_nativo.png`.

---

### TIPO C: Aventuras Gráficas ScummVM
*Motor: scummvm -f -p <ruta> <gameid>*

1. **Colocar los archivos de datos en**: `/home/jcgar/arcade/native/scummvm/<juego>/`
2. **Registrar en `arcade.py`**:
   ```python
   {
       "id": "mi_aventura",
       "title": "Nombre de la Aventura",
       "system": "PC Nativo",
       "year": "1993",
       "dev": "LucasArts",
       "genre": "Aventura Gráfica",
       "cmd": ["scummvm", "-f", "-p", os.path.join(NATIVE_DIR, "scummvm/mi_aventura"), "target_scummvm"],
       "desc": "...",
       "controls": "Ratón: Apuntar y Clic | F5: Menú y Guardar",
   },
   ```
3. **Añadir Carátula**: `/home/jcgar/.emulador/cache/covers/mi_aventura.png`.

---

### TIPO D: Juegos de PC Windows mediante Wine (Abandonware / Clásicos)
*Lanzador: wine_run.sh con prefijo dedicado*

1. **Crear la carpeta del juego**:
   `mkdir -p /home/jcgar/arcade/native/<id_juego>/`
   Copiar o descomprimir aquí los archivos del juego (ejecutable `.exe`, DLLs, carpetas de datos/audio).

2. **Configuración de Pantalla Completa**:
   Si el juego tiene archivo `.ini` o `config.lua`, asegurar `fullscreen = true` (o resolución 1280x720 / 1920x1080).

3. **Elegir el prefijo Wine**:
   * Para juegos de Windows 95/98 / 16-32 bits clásicos (ej. *Commandos*, *Age of Empires*): usar `"win98"`.
   * Para juegos de Windows XP / 7 / DirectX 9 / OpenGL (ej. *Angry Birds Star Wars II*): usar `"winxp"`.

4. **Registrar en la lista `GAMES` de `arcade.py`**:
   ```python
   {
       "id": "mi_juego_pc",
       "title": "Nombre del Juego",
       "system": "PC Nativo",
       "year": "2013",
       "dev": "Desarrollador / Distribuidor",
       "genre": "Estrategia / Puzles",
       "cmd": [
           os.path.join(CORE_DIR, "wine_run.sh"),
           os.path.join(NATIVE_DIR, "mi_juego_pc/JUEGO.EXE"),
           "winxp",  # o "win98"
       ],
       "cwd": os.path.join(NATIVE_DIR, "mi_juego_pc"),
       "desc": "Descripción atractiva...",
       "controls": "Ratón / Teclado...",
   },
   ```

5. **Añadir Carátula**:
   Guardar la portada en `/home/jcgar/.emulador/cache/covers/mi_juego_pc.png`.

---

### TIPO E: Juegos de PC DOS mediante DOSBox (Abandonware Clásico)
*Lanzador: dosbox_run.sh con archivo de configuración dedicado*

1. **Crear la carpeta del juego**:
   `mkdir -p /home/jcgar/arcade/native/<id_juego>/`
   Copiar o descomprimir aquí los archivos del juego DOS (ejecutables `.exe`, `.com`, `.bat`, directorios de datos y sonido).

2. **Crear el archivo de configuración `dosbox.conf`**:
   Crear `/home/jcgar/arcade/native/<id_juego>/dosbox.conf` adaptado al juego.
   > ⚠️ **IMPORTANTE**: DOSBox 0.74 requiere X11 (utiliza SDL 1.2). El lanzador `dosbox_run.sh` levanta automáticamente una sesión limpia de Xorg bajo demanda y restaura el terminal al salir. En la sección `[autoexec]`, monta la carpeta y ejecuta el archivo principal terminando siempre con `exit` para volver al menú de ONYRA al cerrar el juego.

   *Plantilla recomendada*:
   ```ini
   [sdl]
   fullscreen=true
   fulldouble=false
   fullresolution=desktop
   windowresolution=original
   output=overlay
   autolock=true
   sensitivity=100
   waitonerror=true
   priority=higher,normal
   usescancodes=true

   [dosbox]
   machine=svga_s3
   memsize=16

   [render]
   frameskip=0
   aspect=true
   scaler=normal2x

   [cpu]
   core=auto
   cputype=auto
   cycles=auto limit 16000
   cycleup=1000
   cycledown=1000

   [mixer]
   nosound=false
   rate=44100
   blocksize=1024
   prebuffer=25

   [sblaster]
   sbtype=sb16
   sbbase=220
   irq=7
   dma=1
   hdma=5
   sbmixer=true
   oplmode=auto
   oplrate=44100

   [dos]
   xms=true
   ems=true
   umb=true

   [autoexec]
   @echo off
   mount c "/home/jcgar/arcade/native/<id_juego>"
   c:
   cls
   juego.bat
   exit
   ```

3. **Registrar en la lista `GAMES` de `arcade.py` (en AMBOS archivos)**:
   ```python
   {
       "id": "mi_juego_dos",
       "title": "Nombre del Juego",
       "system": "PC Nativo",
       "year": "1994",
       "dev": "Desarrollador / Distribuidor",
       "genre": "Estrategia / Táctica por Turnos",
       "cmd": [
           os.path.join(CORE_DIR, "dosbox_run.sh"),
           os.path.join(NATIVE_DIR, "mi_juego_dos/dosbox.conf"),
       ],
       "cwd": os.path.join(NATIVE_DIR, "mi_juego_dos"),
       "desc": "Descripción atractiva e histórica en español...",
       "controls": "Ratón: Apuntar y seleccionar | Teclado: Accesos directos | Salir: Tecla ESC",
   },
   ```

4. **Añadir Carátula**:
   Guardar la portada en `/home/jcgar/.emulador/cache/covers/<id_juego>.png`.

---

## 3. Comprobación Rápida de Validación (1 Solo Comando)

Una vez colocado el juego y editado `arcade.py`, ejecuta este comando para confirmar que ONYRA lo reconoce sin errores:

```bash
/home/jcgar/.emulador/venv/bin/python -c '
import sys; sys.path.insert(0, "/home/jcgar/.emulador")
import data
cat = data.get_catalog()
found = [g for games in cat.values() for g in games if g["id"] == "<ID_DEL_JUEGO>"]
if found:
    g = found[0]
    t, s, c = g["title"], g["system"], bool(g.get("cover_path"))
    print(f"✅ ÉXITO: {t} ({s}) detectado. Carátula: {c}")
else:
    print("❌ ERROR: El juego no fue detectado en el catálogo. Revisa la ruta en cmd/rom.")
'
```

---

## 4. Dónde Conseguir los Juegos (Atajo Rápido para la IA)

Para no perder tokens buscando en la web:
* **Internet Archive (`archive.org`)**:
  Usa la API JSON directa:
  `curl -s "https://archive.org/advancedsearch.php?q=title:(<nombre_juego>)&fl[]=identifier,title,mediatype&rows=10&output=json"`
  Y luego consulta los archivos: `https://archive.org/metadata/<identifier>/files`.
  La URL de descarga directa es: `https://archive.org/download/<identifier>/<filename>`.
* **Carátulas**:
  Wikipedia REST API o Wikimedia Commons:
  `curl -s "https://en.wikipedia.org/api/rest_v1/page/summary/<Article_Name>"` (campo `thumbnail.source` o `originalimage.source`).

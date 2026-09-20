# 🎮 ONYRA — Luxury Retro Gaming Experience

> **Frontend gráfico nativo de ultra-bajo retardo para consolas retro y PC nativo.**  
> Diseñado para ejecutarse a 60 FPS estables directamente sobre **Linux KMSDRM (Kernel Mode Setting)** con SDL2 y Pygame-CE, sin necesidad ni sobrecarga de servidor gráfico X11 o Wayland.

---

## 🌟 Características Principales

* **Traspaso Limpio de DRM Master (Zero-Flicker):**  
  Al arrancar un juego (vía Mednafen o binario nativo), ONYRA suspende el gestor de eventos, cierra el display y libera el DRM Master del kernel de Linux. Al salir, restaura el modo gráfico a resolución nativa (ej. 1080p60) y restablece el terminal sin corrupción visual ni pérdida de foco.
* **Control Físico Unificado por `evdev` (Latencia Cero):**  
  Lectura a nivel de driver Linux de teclado y mandos arcade/gamepads (ShanWan, DualShock, Xbox, mandos USB genéricos) en hilo de fondo dedicado, evitando caídas de eventos y latencia en consolas TTY.
* **Estética "Luxury Dark Mint Neon + Violet" (Regla 60/30/10):**
  * **60% Fondo:** Negro abisal `#08090D`
  * **30% Paneles:** Grafito oscuro `#0E1116` con bordes finos redondeados
  * **10% Acentos:** Verde Menta Neón `#3DFFC0` y Violeta Suave `#9B7BFF`
  * Halo tenue de glow exterior y cursor de selección con interpolación de movimiento fluida (*exponential easing*).
* **Catálogo Integrado Multiconsola:**
  * **Super Nintendo (SNES)** (vía Mednafen)
  * **Sega Mega Drive / Genesis** (vía Mednafen)
  * **PC Nativo:** Cero emulación en clásicos con motor abierto en C/SDL2 (*DOOM*, *DOOM II*, *Prince of Persia*, *Quake*, *Quake II*), aventuras gráficas SCUMM en castellano (*Monkey Island 1 & 2*, *Day of the Tentacle*, *Indiana Jones Fate of Atlantis*, *Sam & Max*) y táctica para PC (*Commandos: Behind Enemy Lines*).
  * **NES (8-Bit)** (vía Mednafen)
  * **Nintendo Game Boy** (vía Mednafen)
* **Gestión Inteligente de Savestates:**  
  Detección instantánea de partidas guardadas en disco (`.mca`), ofreciendo al usuario continuar la aventura exactamente donde la dejó o iniciar una partida limpia.
* **Buscador Reactivo y Filtro en Tiempo Real:**  
  Búsqueda instantánea en el catálogo pulsando cualquier tecla en pantalla de juegos.

---

## 📁 Arquitectura del Proyecto

```text
.emulador/
├── app.py                     # Bucle principal (60 FPS, vsync, máquina de estados)
├── launcher.py                # Gestor de lanzamiento y liberación de DRM
├── data.py                    # Motor de datos, catálogo, persistencia y estado
├── theme.py                   # Paleta visual, caché de fuentes antialias y efectos neon
├── logo.py                    # Generador procedural de pixel art y banners
├── input_manager.py           # Driver evdev para mandos y teclado físico
├── gamepad.py                 # Mapeo y normalización de gamepad
├── scraper.py                 # Gestor y descargador de carátulas / logos
├── renderer.py                # Utilerías de renderizado auxiliar
│
├── bin/
│   └── emulador               # Script lanzador global para ~/.local/bin/emulador
│
├── screens/                   # Vistas de la aplicación
│   ├── boot_view.py           # Pantalla de inicio con pulso de glow
│   ├── systems_view.py        # Selector de sistemas con cursor animado
│   └── games_view.py          # Selector split-screen, carátulas HD y metadatos
│
├── assets/
│   └── fonts/                 # Tipografías antialias incluidas
│       ├── regular.ttf
│       ├── bold.ttf
│       ├── sans.ttf
│       └── sans_bold.ttf
│
├── cache/                     # Caché persistente de alto rendimiento
│   ├── covers/                # Carátulas HD de los juegos
│   ├── logos/                 # Logos monocromos de los sistemas
│   └── metadata/              # Metadatos cacheados
│
├── arcade_core/               # Núcleo de integración y configuración retro
│   ├── arcade.py              # Catálogo detallado de juegos, descripciones y comandos
│   ├── volume.py              # Gestor hardware de volumen ALSA
│   ├── sound.py               # Generador de efectos de sonido sintetizados
│   ├── apply_input_config.py  # Autoconfigurador de controles para Mednafen
│   ├── apply_native_gamepad_config.py # Autoconfigurador de mando ShanWan para juegos de PC
│   ├── mednafen_arcade.cfg    # Configuración de rendimiento de Mednafen
│   ├── emulador.sh            # Lanzador auxiliar
│   └── wine_run.sh            # Lanzador genérico para juegos de PC / Wine
│
├── old_textual/               # Versión histórica TUI (Textual) conservada como referencia
│
├── install.sh                 # Instalador automatizado en un solo paso
├── requirements.txt           # Dependencias Python
└── state.json                 # Persistencia de última consola y juego seleccionado
```

---

## 🚀 Instalación Rápida

### 1. Clonar el repositorio
```bash
git clone https://github.com/nos275872-create/onyra.git ~/.emulador
cd ~/.emulador
```

### 2. Ejecutar el instalador automatizado
```bash
chmod +x install.sh
./install.sh
```

El instalador:
1. Instala los paquetes necesarios del sistema (`python3-venv`, `mednafen`, `alsa-utils`).
2. Configura los permisos de grupos de hardware (`video`, `input`, `audio`).
3. Crea el entorno virtual en `venv/` con `pygame-ce`, `pillow`, `evdev`, etc.
4. Instala el comando `emulador` en `~/.local/bin/emulador` y lo añade al `$PATH`.

---

## 🎮 Cómo Jugar

Una vez instalado, simplemente escribe en cualquier terminal:
```bash
emulador
```

### Controles Universales (Mando y Teclado)

| Acción | Mando Arcade / Gamepad | Teclado |
| :--- | :--- | :--- |
| **Moverse / Navegar** | Cruceta D-Pad / Stick Analógico | Flechas Arriba / Abajo / Izq / Der |
| **Seleccionar / Jugar** | Botón **A** / Botón Sur | **ENTER** o **ESPACIO** |
| **Volver / Atrás** | Botón **B** / Botón Este | **ESCAPE** o **BACKSPACE** |
| **Buscar juego** | — | Escribir letras directamente |
| **Borrar búsqueda** | — | **BACKSPACE** |
| **Salir de ONYRA** | Botón **SELECT** (en pantalla sistemas) | **ESCAPE** (en pantalla sistemas) |
| **Salir de cualquier juego** | Mantén pulsada **Q** durante 1 segundo | Mantén pulsada **Q** durante 1 segundo |

---

## 📂 Organización de ROMs y Juegos

Las ROMs y juegos nativos se organizan por defecto en `~/arcade/`:

```text
~/arcade/
├── roms/
│   ├── snes/          # ROMs de Super Nintendo (.sfc, .smc)
│   ├── megadrive/     # ROMs de Mega Drive (.md, .bin)
│   ├── nes/           # ROMs de NES (.nes)
│   └── gb/            # ROMs de Game Boy (.gb, .gbc)
└── native/
    ├── doom/          # DOOM.WAD, DOOM2.WAD (ejecutados con crispy-doom)
    ├── quake/         # Directorio id1 (ejecutado con quakespasm)
    ├── quake2/        # Directorio baseq2 (ejecutado con yamagi-quake2)
    ├── sdlpop/        # Prince of Persia nativo C
    ├── scummvm/       # Aventuras gráficas SCUMM (Monkey Island, DOTT, etc.)
    └── commandos/     # Commandos: Behind Enemy Lines (WARGAME.EXE + Wine)
```

> **Nota de Inteligencia:** ONYRA solo mostrará en pantalla aquellos juegos cuya ROM o ejecutable exista en disco. Si falta algún juego, se omite de forma limpia sin generar errores.

---

## 🍷 Soporte e Integración de Juegos Windows (Wine)

ONYRA incluye integración nativa y genérica para juegos clásicos de Windows (PC Nativo) mediante `arcade_core/wine_run.sh`:

1. **Gestión de prefijos aislados:** Agrupa juegos por época en `~/arcade/wine/<nombre_prefix>` (p. ej. `win98`), evitando duplicar gigabytes de librerías.
2. **Subsesión X11 transparente:** Si se ejecuta desde consola TTY pura sin servidor X activo, lanza automáticamente una sesión dedicada mediante `xinit` a través del VT actual, con audio y gráficos directos.
3. **Limpieza total:** Mata automáticamente `wineserver` al salir o al forzar la salida manteniendo pulsada la tecla `Q`.
4. **Instalación de Wine:** Se puede instalar fácilmente ejecutando `./install.sh --with-wine` (o mediante `sudo apt install wine xinit`).

---

## ➕ Añadir un juego Wine nuevo

Añadir cualquier juego de Windows al catálogo es trivial: solo requiere añadir una entrada en la lista `GAMES` de `arcade_core/arcade.py` siguiendo este patrón:

```python
{
    "id": "<id_unico>",
    "title": "<Título del juego>",
    "system": "PC Nativo",
    "year": "<año>",
    "dev": "<desarrollador>",
    "genre": "<género>",
    "cmd": [
        os.path.join(CORE_DIR, "wine_run.sh"),
        os.path.join(NATIVE_DIR, "<carpeta>/<EJECUTABLE.exe>"),
        "<nombre_prefix>",
    ],
    "cwd": os.path.join(NATIVE_DIR, "<carpeta>"),
    "desc": "<descripción>",
    "controls": "<controles>",
},
```

* **Cero cambios de código:** No es necesario tocar ningún script ni modificar `launcher.py`, `app.py`, `input_manager.py` ni `data.py`.
* **Colocación de archivos:** Copia los archivos del juego en `~/arcade/native/<carpeta>/`.
* **Carátula (opcional):** Coloca una imagen en formato PNG en `cache/covers/<id_unico>.png`.

---

## ⚙️ Configuración y Personalización

* **Paleta de Colores:** Modificable en `theme.py` (constantes `COLOR_BG`, `COLOR_PANEL`, `COLOR_MINT`, `COLOR_VIOLET`).
* **Catálogo de Juegos:** Modificable en `arcade_core/arcade.py` (lista `GAMES`).
* **Carátulas:** Coloca cualquier imagen en formato `.png` en `cache/covers/<id_juego>.png`.
* **Volumen:** Gestionado por `arcade_core/volume.py` (por defecto arranca al 65% para confort auditivo y vuelve al 100% al salir).

---

## 📄 Licencia

Desarrollado para disfrute personal y preservación del videojuego retro. Código libre para personalización y uso en consolas de emulación domésticas.

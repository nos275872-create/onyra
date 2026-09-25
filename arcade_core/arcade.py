#!/usr/bin/env python3
"""
ARCADE RETRO STATION — Lanzador de Emuladores Retro para Terminal
Emulación real de NES, SNES, Sega Genesis y Game Boy con Mednafen.
0% de carga en reposo, 100% libre al salir, cero impacto en Deportes TV.
"""

import curses
import datetime
import glob
import os
import select
import signal
import subprocess
import sys
import time

try:
    import evdev
except ImportError:
    evdev = None

# Importar sintetizador de sonido arcade y gestor de volumen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import sound
except Exception:
    sound = None

try:
    import volume
except Exception:
    volume = None


try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

ROMS_DIR = os.path.expanduser("~/arcade/roms")
NATIVE_DIR = os.path.expanduser("~/arcade/native")
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(CORE_DIR, "wine_run.sh")):
    _alt_core = os.path.expanduser("~/.emulador/arcade_core")
    if os.path.exists(os.path.join(_alt_core, "wine_run.sh")):
        CORE_DIR = _alt_core

# Catálogo oficial de juegos (Obras maestras históricas + PC Nativo + Clásicos Capcom)
GAMES = [
    # =========================================================================
    # --- JUEGOS NATIVOS DE PC (Cero Emulación, 100% Rendimiento C/SDL2) ---
    # =========================================================================
    {
        "id": "doom",
        "title": "DOOM (The Ultimate DOOM)",
        "system": "PC Nativo",
        "year": "1993",
        "dev": "id Software (Carmack / Romero)",
        "genre": "FPS Legendario",
        "cmd": ["crispy-doom", "-iwad", os.path.join(NATIVE_DIR, "doom/DOOM.WAD"), "-fullscreen"],
        "desc": "La obra maestra que revolucionó los videojuegos de PC y tema del documental insignia de Ahoy ('DOOM: The Fake 3D Cult'). Laberintos viscerales, hordas demoníacas y código C ultrarrápido sin emular hardware.",
        "controls": "Mando: Stick Izq Mover/Strafe | Stick Der Girar | RT Disparar | Botón A Usar | B Correr | LB/RB Armas | Select Mapa",
    },
    {
        "id": "doom2",
        "title": "DOOM II: Hell on Earth",
        "system": "PC Nativo",
        "year": "1994",
        "dev": "id Software",
        "genre": "FPS Clásico",
        "cmd": ["crispy-doom", "-iwad", os.path.join(NATIVE_DIR, "doom/DOOM2.WAD"), "-fullscreen"],
        "desc": "La invasión llega a la Tierra. La icónica Super Shotgun de dos cañones, 30 mapas colosales y la cúspide de la era dorada de los 90 a 60 FPS nativos a 1080p.",
        "controls": "Mando: Stick Izq Mover/Strafe | Stick Der Girar | RT Disparar | Botón A Usar | B Correr | LB/RB Armas | Select Mapa",
    },
    {
        "id": "prince_of_persia",
        "title": "Prince of Persia",
        "system": "PC Nativo",
        "year": "1989",
        "dev": "Jordan Mechner / SDLPoP",
        "genre": "Plataformas Cinemático",
        "cmd": [os.path.join(NATIVE_DIR, "sdlpop/prince")],
        "cwd": os.path.join(NATIVE_DIR, "sdlpop"),
        "desc": "Pionero absoluto de la rotoscopia cinemática y la animación fluida realista. 60 minutos para escapar de las mazmorras del visir Jaffar sorteando trampas mortales y duelos de espada.",
        "controls": "Mover / Agacharse: Flechas o WASD | SALTAR: Flecha Arriba / ESPACIO | Acción / Espada / Sigilo: Shift Izq | Mando: Cruceta + A",
    },
    {
        "id": "quake",
        "title": "Quake",
        "system": "PC Nativo",
        "year": "1996",
        "dev": "id Software",
        "genre": "FPS Gótico 3D",
        "cmd": ["quakespasm", "-basedir", os.path.join(NATIVE_DIR, "quake"), "-fullscreen"],
        "desc": "El primer motor de polígonos 3D real con iluminación y arquitectura gótica lovecraftiana. Sonido oscuro compuesto por Trent Reznor (Nine Inch Nails) y el origen del 'rocket jump'.",
        "controls": "Mover: WASD | Apuntar: Ratón | Disparo: Clic izq / Ctrl | Saltar: ESPACIO | Armas: 1-8 | Mando: Sticks + Gatillos",
    },
    {
        "id": "quake2",
        "title": "Quake II",
        "system": "PC Nativo",
        "year": "1997",
        "dev": "id Software",
        "genre": "FPS Sci-Fi",
        "cmd": ["/usr/lib/yamagi-quake2/quake2", "+set", "basedir", os.path.join(NATIVE_DIR, "quake2"), "+set", "vid_fullscreen", "1"],
        "desc": "Guerra industrial de ciencia ficción contra la raza cibernética Strogg. Railgun de precisión, misiones tácticas interconectadas y banda sonora de Sonic Mayhem a 60 FPS estables.",
        "controls": "Mover: WASD | Apuntar: Ratón | Disparo: Clic izq / Ctrl | Saltar: ESPACIO | Agacharse: C | Mando: Sticks + Gatillos",
    },
    {
        "id": "monkey1",
        "title": "The Secret of Monkey Island",
        "system": "PC Nativo",
        "year": "1990",
        "dev": "LucasArts (Gilbert / Schafer)",
        "genre": "Aventura Gráfica (Español)",
        "cmd": ["scummvm", "--fullscreen", "-p", os.path.join(NATIVE_DIR, "scummvm/The Secret of Monkey Island"), "monkey"],
        "desc": "'Me llamo Guybrush Threepwood y ¡quiero ser pirata!'. La cumbre del humor absurdo, duelos de insultos a espada en la isla Mêlée y el motor SCUMM en perfecto castellano con música CD remasterizada.",
        "controls": "Control del cursor: Ratón o Stick del Mando | Seleccionar verbo / Diálogo: Clic Izq o Botón A | Menú / Guardar: Tecla F5",
    },
    {
        "id": "monkey2",
        "title": "Monkey Island 2: LeChuck's Revenge",
        "system": "PC Nativo",
        "year": "1991",
        "dev": "LucasArts",
        "genre": "Aventura Gráfica (Español)",
        "cmd": ["scummvm", "--fullscreen", "-p", os.path.join(NATIVE_DIR, "scummvm/Monkey Island 2 LeChuck's Revenge"), "monkey2"],
        "desc": "Obra maestra inmortal con fondos ilustrados escaneados por Peter Chan, el revolucionario sistema musical adaptativo iMUSE y la búsqueda del tesoro 'Big Whoop' en la isla Scabb.",
        "controls": "Control del cursor: Ratón o Stick del Mando | Seleccionar verbo / Diálogo: Clic Izq o Botón A | Menú / Guardar: Tecla F5",
    },
    {
        "id": "tentacle",
        "title": "Day of the Tentacle (El Día del Tentáculo)",
        "system": "PC Nativo",
        "year": "1993",
        "dev": "LucasArts (Schafer / Grossman)",
        "genre": "Aventura Gráfica (Español)",
        "cmd": ["scummvm", "--fullscreen", "-p", os.path.join(NATIVE_DIR, "scummvm/Maniac Mansion 2 El Dia del Tentaculo"), "tentacle-es"],
        "desc": "Secuela de Maniac Mansion con dibujos animados al estilo Warner Bros. Bernard, Hoagie y Laverne viajan en el tiempo alterando el pasado y futuro para detener al Tentáculo Púrpura.",
        "controls": "Control del cursor: Ratón o Stick del Mando | Acciones: Clic Izq o Botón A | Menú / Guardar: Tecla F5",
    },
    {
        "id": "atlantis",
        "title": "Indiana Jones and the Fate of Atlantis",
        "system": "PC Nativo",
        "year": "1992",
        "dev": "LucasArts (Hal Barwood)",
        "genre": "Aventura Gráfica (Español)",
        "cmd": ["scummvm", "--fullscreen", "-p", os.path.join(NATIVE_DIR, "scummvm/Indiana Jones y el Destino de la Atlantida"), "atlantis"],
        "desc": "Aclamada unánimemente como la mejor aventura de Indiana Jones. Tres caminos diferentes (Ingenio, Puños o Cooperativo con Sophia) resolviendo los enigmas del oricalco de la Atlántida.",
        "controls": "Control del cursor: Ratón o Stick del Mando | Interactuar: Clic Izq o Botón A | Menú / Guardar: Tecla F5",
    },
    {
        "id": "samnmax",
        "title": "Sam & Max Hit the Road",
        "system": "PC Nativo",
        "year": "1993",
        "dev": "LucasArts (Steve Purcell)",
        "genre": "Aventura Gráfica (Español)",
        "cmd": ["scummvm", "--fullscreen", "-p", os.path.join(NATIVE_DIR, "scummvm/Sam and Max Hit the Road"), "samnmax-es"],
        "desc": "La policía independiente freelance más desquiciada. Un perro detective y un conejo hiperactivo cruzando las atracciones turísticas más estrambóticas de Estados Unidos en busca de un Sasquatch.",
        "controls": "Control del cursor: Ratón o Stick del Mando | Clic Derecho: Cambiar modo de acción | Menú / Guardar: Tecla F5",
    },
    {
        "id": "commandos",
        "title": "Commandos: Behind Enemy Lines",
        "system": "PC Nativo",
        "year": "1998",
        "dev": "Pyro Studios / Eidos Interactive",
        "genre": "Táctica en Tiempo Real",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "commandos/WARGAME.EXE"),
            "win98",
        ],
        "cwd": os.path.join(NATIVE_DIR, "commandos"),
        "desc": "La legendaria obra maestra de Pyro Studios. Lidera a un grupo de 6 comandos aliados (Boina Verde, Francotirador, Marine, Zapador, Conductor y Espía) infiltrándote en misiones tácticas tras las líneas del Eje durante la Segunda Guerra Mundial.",
        "controls": "Ratón: Seleccionar comandos, mover e interactuar | Teclado: 1-6 Selección, G Pistola, K Cuchillo, H Ver cono | Menú: Tecla ESC",
    },
    {
        "id": "aoe_ror",
        "title": "Age of Empires: The Rise of Rome",
        "system": "PC Nativo",
        "year": "1998",
        "dev": "Ensemble Studios / Microsoft",
        "genre": "Estrategia en Tiempo Real (RTS)",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "aoe/EMPIRESX.EXE"),
            "win98",
        ],
        "cwd": os.path.join(NATIVE_DIR, "aoe"),
        "desc": "La expansión definitiva del legendario RTS histórico de Ensemble Studios. Conduce a Roma, Palmira, Macedonia y Cartago desde la Edad de Piedra hasta el esplendor del Imperio Romano con nuevas unidades como el Elefante de Guerra y catapultas pesadas.",
        "controls": "Ratón: Seleccionar aldeanos/ejército, construir y ordenar ataque | Teclado: Accesos directos y grupos de control (Ctrl+1-9) | Menú: F10",
    },
    {
        "id": "aoe2_tc",
        "title": "Age of Empires II: The Conquerors",
        "system": "PC Nativo",
        "year": "2000",
        "dev": "Ensemble Studios / Microsoft",
        "genre": "Estrategia en Tiempo Real (RTS)",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "aoe2/age2_x1.exe"),
            "win98",
        ],
        "cwd": os.path.join(NATIVE_DIR, "aoe2"),
        "desc": "La cúspide indiscutible de la estrategia en tiempo real medieval. Añade civilizaciones icónicas como los Españoles, Mayas, Hunos, Aztecas y Coreanos, además de las campañas legendarias de El Cid, Atila el Huno y Moctezuma.",
        "controls": "Ratón: Seleccionar unidades, crear formaciones y recolectar recursos | Teclado: Grupos (Ctrl+1-9), ir al centro urbano (H) | Menú: F10",
    },
    {
        "id": "angrybirds_sw2",
        "title": "Angry Birds Star Wars II",
        "system": "PC Nativo",
        "year": "2013",
        "dev": "Rovio Entertainment / Lucasfilm",
        "genre": "Física y Puzles / Estrategia",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "angrybirds_starwars2/AngryBirdsStarWarsII.exe"),
            "winxp",
        ],
        "cwd": os.path.join(NATIVE_DIR, "angrybirds_starwars2"),
        "desc": "¡Únete a los pájaros o únete al lado porcino! Basado en las precuelas y la trilogía original de Star Wars, con más de 30 personajes jugables con sables láser y poderes de la Fuerza (Yoda, Darth Maul, Anakin, Boba Fett). Edición completa que incluye todos los capítulos hasta la versión 1.9.25.",
        "controls": "Ratón: Arrastrar el tirachinas con Clic Izquierdo para apuntar y soltar | Clic en el aire: Activar poder de la Fuerza / sable láser | ESC: Menú",
    },
    {
        "id": "evil_genius",
        "title": "Evil Genius",
        "system": "PC Nativo",
        "year": "2004",
        "dev": "Elixir Studios / Sierra Entertainment",
        "genre": "Estrategia / Simulación y Gestión",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "evil_genius/ReleaseExe/EvilGeniusExeStub-Release.exe"),
            "winxp",
        ],
        "cwd": os.path.join(NATIVE_DIR, "evil_genius/ReleaseExe"),
        "desc": "Ponte en la piel de un supervillano al más puro estilo de las películas de espías de los 60 y 70. Construye tu base secreta en una isla desierta, entrena esbirros, coloca trampas mortales contra los agentes secretos de la justicia y organiza actos de infamia por todo el planeta para conseguir la dominación mundial.",
        "controls": "Ratón: Seleccionar, construir y dar órdenes | Clic Derecho: Cámara y opciones | Teclado: WASD / Flechas para desplazar la cámara | Barra espaciadora: Pausa táctica",
    },
    {
        "id": "battlefront2",
        "title": "Star Wars: Battlefront II",
        "system": "PC Nativo",
        "year": "2005",
        "dev": "Pandemic Studios / LucasArts",
        "genre": "Acción / Disparos (FPS/TPS)",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "battlefront2/BattlefrontII.exe"),
            "winxp",
        ],
        "cwd": os.path.join(NATIVE_DIR, "battlefront2"),
        "desc": "La aclamada obra cumbre de los juegos de acción bélica de Star Wars. Lidera a la legendaria Legión 501 a lo largo de la galaxia en batallas masivas terrestres y espaciales durante las Guerras Clon y la Guerra Civil Galáctica. Controla soldados, pilotos, vehículos icónicos (AT-AT, cazas X-Wing y TIE) y empuña sables láser como héroes y villanos (Darth Vader, Luke Skywalker, Yoda, Boba Fett).",
        "controls": "Teclado: WASD Mover, Espacio Saltar, C Agacharse, R Recargar, E Entrar vehículo | Ratón: Apuntar y Disparar | ESC: Menú",
    },
    {
        "id": "startopia",
        "title": "StarTopia",
        "system": "PC Nativo",
        "year": "2001",
        "dev": "Mucky Foot Productions / Eidos Interactive",
        "genre": "Estrategia / Simulación Espacial",
        "cmd": [
            os.path.join(CORE_DIR, "wine_run.sh"),
            os.path.join(NATIVE_DIR, "startopia/startopia.exe"),
            "win98",
        ],
        "cwd": os.path.join(NATIVE_DIR, "startopia"),
        "desc": "Aclamada joya de la estrategia y simulación creada por veteranos de Bullfrog. Gestiona y reconstruye colosales estaciones espaciales toroidales divididas en tres cubiertas (Ingeniería, Ocio y Bio-cubierta). Atrae, cuida y satisface a diversas razas alienígenas mientras equilibras la economía, la investigación y la defensa ante amenazas galácticas. Incluye textos y voces dobladas al español.",
        "controls": "Ratón: Seleccionar, construir y rotar cámara (Rueda/Botón Central) | Teclado: Flechas/WASD para mover vista | 1-3: Cambiar de cubierta | Espacio: Pausa | ESC: Menú",
    },
    {
        "id": "xcom",
        "title": "X-COM: UFO Defense",
        "system": "PC Nativo",
        "year": "1994",
        "dev": "Mythos Games / MicroProse",
        "genre": "Estrategia / Táctica por Turnos",
        "cmd": [
            os.path.join(CORE_DIR, "dosbox_run.sh"),
            os.path.join(NATIVE_DIR, "xcom/dosbox.conf"),
        ],
        "cwd": os.path.join(NATIVE_DIR, "xcom"),
        "desc": "La legendaria obra maestra de Julian Gollop que definió el género táctico. Dirige el proyecto multinacional secreto X-COM para proteger la Tierra de una invasión alienígena: detecta OVNIs e intercepta amenazas aéreas en el Geoscape, gestiona bases, investiga armamento extraterrestre y combate en tensas misiones tácticas por turnos en el Battlescape con niebla de guerra.",
        "controls": "Ratón: Mover unidades, apuntar y seleccionar acciones en Geoscape/Battlescape | Teclado: 1-9 Accesos rápidos, Barra espaciadora: Siguiente unidad | Menú / Salir: Tecla ESC",
    },


    # =========================================================================
    # --- SUPER NINTENDO (SNES) ---
    # =========================================================================
    {
        "id": "final_fight",
        "title": "Final Fight",
        "system": "SNES",
        "year": "1990",
        "dev": "Capcom",
        "genre": "Beat 'em up Urbano",
        "rom": os.path.join(ROMS_DIR, "snes/Final Fight (USA).sfc"),
        "desc": "El beat 'em up fundacional de Capcom que definió a los salones recreativos. El alcalde Mike Haggar y Cody limpian las calles de Metro City a puñetazo limpio contra la banda Mad Gear.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Golpe/Combo: Shift/Z | Golpe Especial (360°): X/C | Mando: A/B/X/Y",
    },
    {
        "id": "captain_commando",
        "title": "Captain Commando",
        "system": "SNES",
        "year": "1995",
        "dev": "Capcom",
        "genre": "Beat 'em up Sci-Fi",
        "rom": os.path.join(ROMS_DIR, "snes/Captain Commando (USA).sfc"),
        "desc": "El justiciero futurista y mascota original de Capcom. Metro City en 2026 junto al ninja Sho, la momia alienígena Mack y el bebé genio en un mecha de combate.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Golpe: Shift/Z | Ataque Especial: X/C | Correr: Doble toque adelante",
    },
    {
        "id": "super_ghouls",
        "title": "Super Ghouls 'n Ghosts",
        "system": "SNES",
        "year": "1991",
        "dev": "Capcom",
        "genre": "Acción Gótica / Plataformas",
        "rom": os.path.join(ROMS_DIR, "snes/Super Ghouls 'N Ghosts (USA).sfc"),
        "desc": "Dificultad de leyenda, armadura dorada y doble salto en el aire. Sir Arthur cruzando el reino demoníaco en uno de los juegos más exigentes y gratificantes jamás concebidos.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W (Doble salto) | Disparar arma: Shift/Z | Magia: Mantener Shift | Mando: A/B",
    },
    {
        "id": "super_metroid",
        "title": "Super Metroid",
        "system": "SNES",
        "year": "1994",
        "dev": "Nintendo R&D1",
        "genre": "Metroidvania / Sci-Fi",
        "rom": os.path.join(ROMS_DIR, "snes/Super Metroid (Japan, USA) (En,Ja).sfc"),
        "desc": "La cumbre del diseño de aislamiento y atmósfera en 16 bits. Samus Aran explora las profundidades no lineales del planeta Zebes, guiada únicamente por el sonido espectral y la arquitectura alienígena.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Disparo: Shift/Z | Correr: X | Apuntar diagonal: C/V | Mando: A/B/X/Y",
    },
    {
        "id": "chrono_trigger",
        "title": "Chrono Trigger",
        "system": "SNES",
        "year": "1995",
        "dev": "Square",
        "genre": "JRPG / Viaje Temporal",
        "rom": os.path.join(ROMS_DIR, "snes/Chrono Trigger (USA).sfc"),
        "desc": "El 'Dream Team' japonés: Sakaguchi (Final Fantasy), Horii (Dragon Quest) y Akira Toriyama (Dragon Ball). Revolucionó los JRPG con combates sin transición, viajes temporales y partitura de Yasunori Mitsuda.",
        "controls": "Mover: Flechas/WASD | Confirmar: ESPACIO / Z / Enter | Cancelar/Correr: Shift/X | Menú: C | Mando: A/B/X/Y",
    },
    {
        "id": "super_castlevania_4",
        "title": "Super Castlevania IV",
        "system": "SNES",
        "year": "1991",
        "dev": "Konami",
        "genre": "Acción Gótica",
        "rom": os.path.join(ROMS_DIR, "snes/Super Castlevania IV (USA).sfc"),
        "desc": "Gótico puro y demostración de fuerza audiovisual. Simon Belmont empuña el látigo en 8 direcciones, balanceándose entre trampas en Modo 7 y una de las composiciones sonoras más oscuras de Konami.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Látigo: Shift/Z | Subarma: X/C | Mando: A/B/X/Y",
    },
    {
        "id": "mega_man_x",
        "title": "Mega Man X",
        "system": "SNES",
        "year": "1993",
        "dev": "Capcom",
        "genre": "Acción / Plataformas",
        "rom": os.path.join(ROMS_DIR, "snes/Mega Man X (USA).sfc"),
        "desc": "Una lección magistral de diseño de videojuegos y enseñanza orgánica. El nivel introductorio enseña la escalada de muros y el dash sin una sola palabra. Ritmo implacable y maestría mecánica.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Disparar: Shift/Z | Dash: X/C | Mando: A/B/X/Y",
    },
    {
        "id": "earthbound",
        "title": "EarthBound",
        "system": "SNES",
        "year": "1994",
        "dev": "Ape / HAL / Nintendo",
        "genre": "JRPG de Culto / Surrealista",
        "rom": os.path.join(ROMS_DIR, "snes/EarthBound (USA).sfc"),
        "desc": "La deconstrucción surrealista del JRPG dirigida por Shigesato Itoi. Una sátira mordaz, tierna y perturbadora de la cultura pop de los 90, ovnis, bates de béisbol y el terror cósmico de Giygas.",
        "controls": "Mover: Flechas/WASD | Hablar/Inspeccionar: ESPACIO / Z / Enter | Cancelar: Shift/X | Menú: C | Mando: A/B/X/Y",
    },
    {
        "id": "ff3",
        "title": "Final Fantasy III (VI)",
        "system": "SNES",
        "year": "1994",
        "dev": "Square",
        "genre": "JRPG Épico",
        "rom": os.path.join(ROMS_DIR, "snes/Final Fantasy III (USA) (Rev 1).sfc"),
        "desc": "La cima dramática del rol en 16 bits. Steampunk, nihilismo, la memorable escena de la ópera de Nobuo Uematsu y la ruptura del mundo a manos de Kefka, el villano más retorcido de la saga.",
        "controls": "Mover: Flechas/WASD | Confirmar: ESPACIO / Z / Enter | Cancelar/Correr: Shift/X | Menú: C | Mando: A/B/X/Y",
    },
    {
        "id": "contra_3",
        "title": "Contra III: The Alien Wars",
        "system": "SNES",
        "year": "1992",
        "dev": "Konami",
        "genre": "Run and Gun",
        "rom": os.path.join(ROMS_DIR, "snes/Contra III - The Alien Wars (USA).sfc"),
        "desc": "Acción cinética implacable. Pirotecnia visual, niveles en perspectiva cenital giratoria con Modo 7 y una cadencia frenética que definió la cumbre de los shooters arcade cooperativos.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Disparo: Shift/Z | Bomba: X | Cambiar arma: C | Mando: A/B/X/Y",
    },
    {
        "id": "smw",
        "title": "Super Mario World",
        "system": "SNES",
        "year": "1990",
        "dev": "Nintendo",
        "genre": "Plataformas",
        "rom": os.path.join(ROMS_DIR, "snes/Super Mario World (U) [!].smc"),
        "desc": "La piedra angular del lanzamiento de 16-bits. Dinosaur Land, Yoshi, 96 salidas secretas magistralmente interconectadas y una física de inercia y capa que rozó la perfección.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W / Z | Correr/Coger: Shift/X | Giro Spin: C | Mando: A/B/X/Y",
    },
    {
        "id": "zelda_alttp",
        "title": "The Legend of Zelda: A Link to the Past",
        "system": "SNES",
        "year": "1991",
        "dev": "Nintendo",
        "genre": "Acción / Aventura",
        "rom": os.path.join(ROMS_DIR, "snes/The Legend of Zelda - A Link to the Past.smc"),
        "desc": "El canon definitivo del diseño de aventuras cenitales. El contraste entre el Mundo de la Luz y la corrupción del Mundo Oscuro, templos inolvidables y la forja de la Espada Maestra.",
        "controls": "Mover: Flechas/WASD | Espada: Shift/X | Objeto: C/V | Acción: ESPACIO / Z | Mando: A/B/X/Y",
    },
    {
        "id": "fzero",
        "title": "F-Zero",
        "system": "SNES",
        "year": "1990",
        "dev": "Nintendo",
        "genre": "Carreras Futuristas",
        "rom": os.path.join(ROMS_DIR, "snes/F-Zero (USA).sfc"),
        "desc": "El escaparate técnico que asombró al mundo en 1990. Velocidad extrema a 60 FPS simulando un circuito 3D mediante Modo 7 en el universo cyberpunk de Captain Falcon.",
        "controls": "Girar: Flechas/WASD | Acelerar: ESPACIO / Z | Frenar: Shift/X | Ladeos: C/V | Mando: A/B + L1/R1",
    },
    {
        "id": "sf2_turbo",
        "title": "Street Fighter II Turbo",
        "system": "SNES",
        "year": "1993",
        "dev": "Capcom",
        "genre": "Lucha Arcade",
        "rom": os.path.join(ROMS_DIR, "snes/Street Fighter II Turbo.smc"),
        "desc": "El fenómeno cultural que definió el videojuego competitivo en los recreativos. Ryu, Chun-Li, Guile... Combates frenéticos con velocidad Turbo ajustable y precisión al milisegundo.",
        "controls": "Mover: Flechas/WASD | Puños: Shift/X/C | Patadas: ESPACIO / Z / V | Mando: A/B/X/Y + L1/R1",
    },
    {
        "id": "dkc",
        "title": "Donkey Kong Country",
        "system": "SNES",
        "year": "1994",
        "dev": "Rare / Nintendo",
        "genre": "Plataformas",
        "rom": os.path.join(ROMS_DIR, "snes/Donkey Kong Country.sfc"),
        "desc": "Revolución gráfica prerenderizada en estaciones Silicon Graphics. Rareware asombró a la industria con una ambientación visual sin precedentes y la música ambiental hipnótica de David Wise.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W / Z | Rodar/Correr: Shift/X | Mando: A/B/X/Y",
    },
    {
        "id": "mario_kart",
        "title": "Super Mario Kart",
        "system": "SNES",
        "year": "1992",
        "dev": "Nintendo",
        "genre": "Carreras / Karts",
        "rom": os.path.join(ROMS_DIR, "snes/Super Mario Kart.smc"),
        "desc": "El creador del género de carreras con combate. Modo 7 exprimiendo la perspectiva en pista, plátanos, caparazones y un modo batalla que forjó rivalidades históricas.",
        "controls": "Girar: Flechas/WASD | Acelerar: ESPACIO / Z | Frenar/Saltar: Shift/X | Usar Objeto: C/V | Mando: A/B/X/Y",
    },
    {
        "id": "tetris_drmario",
        "title": "Tetris & Dr. Mario",
        "system": "SNES",
        "year": "1994",
        "dev": "Nintendo",
        "genre": "Puzle Clásico",
        "rom": os.path.join(ROMS_DIR, "snes/Tetris & Dr. Mario.sfc"),
        "desc": "La pureza geométrica del diseño soviético de Alexey Pajitnov combinada con las píldoras de Dr. Mario, acompañados de arreglos orquestales de 16 bits.",
        "controls": "Mover: Flechas/WASD | Rotar: ESPACIO / Z / X | Caída rápida: Abajo/S | Start: Enter",
    },

    # =========================================================================
    # --- SEGA MEGA DRIVE / GENESIS ---
    # =========================================================================
    {
        "id": "sor2",
        "title": "Streets of Rage 2",
        "system": "Mega Drive",
        "year": "1992",
        "dev": "Sega / Ancient",
        "genre": "Beat 'em up Urbano",
        "rom": os.path.join(ROMS_DIR, "megadrive/Streets of Rage 2 (USA).md"),
        "desc": "El pináculo del 'brawler' urbano en 16 bits. Callejuelas nocturnas iluminadas por neones y la legendaria banda sonora electrónica de club de Yuzo Koshiro exprimiendo el chip FM YM2612.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Golpe/Combo: Shift/Z | Ataque Especial: X/C | Mando: A/B/X/Y",
    },
    {
        "id": "mercs",
        "title": "Mercs (Commando II)",
        "system": "Mega Drive",
        "year": "1991",
        "dev": "Capcom / Sega",
        "genre": "Run and Gun Militar",
        "rom": os.path.join(ROMS_DIR, "megadrive/Mercs (World).md"),
        "desc": "La secuela directa de Commando. Acción explosiva a 60 FPS que incluye el 'Original Mode' exclusivo de Mega Drive con tienda de armas, subidas de nivel y personajes desbloqueables.",
        "controls": "Mover: Flechas/WASD | Disparo: Shift/Z | Megabomba: ESPACIO / ARRIBA / W / X | Mando: A/B/C",
    },
    {
        "id": "gunstar_heroes",
        "title": "Gunstar Heroes",
        "system": "Mega Drive",
        "year": "1993",
        "dev": "Treasure",
        "genre": "Run and Gun Frenético",
        "rom": os.path.join(ROMS_DIR, "megadrive/Gunstar Heroes (USA).md"),
        "desc": "El debut triunfal del mítico estudio Treasure. Desafió los límites técnicos del Motorola 68000 con jefes multi-segmentados articulados, explosiones colosales y acrobacias cinéticas.",
        "controls": "Mover: Flechas/WASD | Disparo: Shift/Z | SALTAR: ESPACIO / ARRIBA / W | Cambiar tiro/Agarre: X/C | Mando: A/B/X/Y",
    },
    {
        "id": "shinobi_3",
        "title": "Shinobi III: Return of the Ninja Master",
        "system": "Mega Drive",
        "year": "1993",
        "dev": "Sega",
        "genre": "Acción Ninja",
        "rom": os.path.join(ROMS_DIR, "megadrive/Shinobi III - Return of the Ninja Master (USA).md"),
        "desc": "La elegancia marcial de Joe Musashi. Combate ninja a 60 FPS con animaciones impecables, carreras a caballo, persecuciones acuáticas y devastadoras magias ninjutsu.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Shuriken/Katana: Shift/Z | Magia Ninjutsu: X/C | Mando: A/B/X/Y",
    },
    {
        "id": "castlevania_bloodlines",
        "title": "Castlevania: Bloodlines",
        "system": "Mega Drive",
        "year": "1994",
        "dev": "Konami",
        "genre": "Acción Gótica",
        "rom": os.path.join(ROMS_DIR, "megadrive/Castlevania - Bloodlines (USA).md"),
        "desc": "La única entrega de Castlevania en Mega Drive. Una sangrienta odisea por los campos de batalla de la Primera Guerra Mundial en Europa, con efectos de torsión y la inolvidable música de Michiru Yamane.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Ataque: Shift/Z | Subarma: X/C | Mando: A/B/X/Y",
    },
    {
        "id": "sonic",
        "title": "Sonic The Hedgehog",
        "system": "Mega Drive",
        "year": "1991",
        "dev": "Sega / Sonic Team",
        "genre": "Plataformas / Velocidad",
        "rom": os.path.join(ROMS_DIR, "megadrive/Sonic The Hedgehog.md"),
        "desc": "El icono supersónico que cambió el equilibrio de la industria. Físicas de inercia y aceleración por colinas y bucles vertiginosos que definieron la actitud rebelde de Sega en los 90.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W / Shift / Z / X | Rodar: Abajo en carrera | Mando: A/B/X",
    },

    # =========================================================================
    # --- NES (8-BIT) ---
    # =========================================================================
    {
        "id": "commando",
        "title": "Commando",
        "system": "NES",
        "year": "1986",
        "dev": "Capcom",
        "genre": "Shoot 'em up Vertical",
        "rom": os.path.join(ROMS_DIR, "nes/Commando (USA).nes"),
        "desc": "Super Joe en territorio hostil. El arcade que fijó las reglas de los shooters de acción militar en perspectiva cenital, ametrallando batallones y lanzando granadas.",
        "controls": "Mover: Flechas/WASD | Disparo: Shift/Z | Granadas: ESPACIO / ARRIBA / W | Mando: A/B",
    },
    {
        "id": "ninja_gaiden",
        "title": "Ninja Gaiden",
        "system": "NES",
        "year": "1988",
        "dev": "Tecmo",
        "genre": "Acción Cinemática",
        "rom": os.path.join(ROMS_DIR, "nes/Ninja Gaiden (USA).nes"),
        "desc": "Pionero absoluto de la narrativa cinemática mediante las revolucionarias 'Tecmo Cinema Screens'. Ryu Hayabusa en una prueba de reflejos y disciplina con banda sonora chiptune de alto voltaje.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Espada: Shift/Z | Subarma: Arriba+Shift / X | Mando: A/B",
    },
    {
        "id": "castlevania_3",
        "title": "Castlevania III: Dracula's Curse",
        "system": "NES",
        "year": "1989",
        "dev": "Konami",
        "genre": "Acción Gótica",
        "rom": os.path.join(ROMS_DIR, "nes/Castlevania III - Dracula's Curse (USA).nes"),
        "desc": "La cúspide de la saga en 8 bits. Rutas no lineales con múltiples caminos, compañeros con habilidades exclusivas (Alucard, Sypha, Grant) y arquitectura de niveles gótica magistral.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Látigo: Shift/Z | Subarma: Arriba+Shift / X | Mando: A/B",
    },
    {
        "id": "metal_gear",
        "title": "Metal Gear",
        "system": "NES",
        "year": "1987",
        "dev": "Konami",
        "genre": "Sigilo Táctico",
        "rom": os.path.join(ROMS_DIR, "nes/Metal Gear (USA).nes"),
        "desc": "La génesis de la infiltración táctica concebida por Hideo Kojima. Solid Snake se infiltra en Outer Heaven revolucionando los juegos de acción: evitar el combate es la clave para la supervivencia.",
        "controls": "Mover: Flechas/WASD | Puñetazo/Disparo: Shift/Z | Equipo/Menú: Tab/Enter | Mando: A/B",
    },
    {
        "id": "contra",
        "title": "Contra",
        "system": "NES",
        "year": "1988",
        "dev": "Konami",
        "genre": "Run and Gun",
        "rom": os.path.join(ROMS_DIR, "nes/Contra.nes"),
        "desc": "El 'run and gun' arcade por antonomasia que inmortalizó el Código Konami. Bill y Lance abriéndose paso a balazo limpio contra la amenaza extraterrestre Red Falcon.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Disparo: Shift/Z | Turbo: X/C | Mando: A/B",
    },
    {
        "id": "smb",
        "title": "Super Mario Bros.",
        "system": "NES",
        "year": "1985",
        "dev": "Nintendo",
        "genre": "Plataformas",
        "rom": os.path.join(ROMS_DIR, "nes/Super Mario Bros.nes"),
        "desc": "El título que refundó la industria del videojuego tras el crash de 1983. Shigeru Miyamoto y Takashi Tezuka sentaron las bases físicas de inercia, precisión y diseño de niveles moderno.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Correr/Fuego: Shift/Z | Mando: A/B",
    },
    {
        "id": "pacman",
        "title": "Pac-Man",
        "system": "NES",
        "year": "1984",
        "dev": "Namco",
        "genre": "Arcade Maze",
        "rom": os.path.join(ROMS_DIR, "nes/Pac-Man (USA) (Namco).nes"),
        "desc": "Toru Iwatani concibió el primer fenómeno pop global no violento de la historia del ocio digital. Cuatro fantasmas gobernados por algoritmos e inteligencias artificiales diferenciadas.",
        "controls": "Dirigir: Flechas del cursor o WASD | Mando: Cruceta / Stick | Start: Enter",
    },

    # =========================================================================
    # --- GAME BOY (PORTÁTIL) ---
    # =========================================================================
    {
        "id": "links_awakening",
        "title": "The Legend of Zelda: Link's Awakening",
        "system": "Game Boy",
        "year": "1993",
        "dev": "Nintendo",
        "genre": "Aventura / Misterio Surrealista",
        "rom": os.path.join(ROMS_DIR, "gb/Legend of Zelda, The - Link's Awakening (USA, Europe) (Rev 2).gb"),
        "desc": "Una joya melancólica inspirada en Twin Peaks. El náufrago Link despierta en la enigmática isla Koholint, custodiada por el Pez del Viento, en una de las historias más emotivas de Nintendo.",
        "controls": "Mover: Flechas/WASD | Botón A: ESPACIO / ARRIBA / W | Botón B: Shift/Z | Menú/Mapa: Tab/Enter | Mando: A/B",
    },
    {
        "id": "metroid_2",
        "title": "Metroid II: Return of Samus",
        "system": "Game Boy",
        "year": "1991",
        "dev": "Nintendo",
        "genre": "Sci-Fi / Supervivencia",
        "rom": os.path.join(ROMS_DIR, "gb/Metroid II - Return of Samus (World).gb"),
        "desc": "Misión de exterminio solitaria en el planeta SR388. Atmósfera opresiva y claustrofóbica en blanco y negro, donde Samus da caza a la especie Metroid hasta el nacimiento de la cría.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Disparo: Shift/Z | Morfosfera: Abajo | Menú: Tab/Enter",
    },
    {
        "id": "pokemon_red",
        "title": "Pokemon - Red Version",
        "system": "Game Boy",
        "year": "1996",
        "dev": "Game Freak",
        "genre": "RPG / Coleccionismo",
        "rom": os.path.join(ROMS_DIR, "gb/Pokemon - Red Version.gb"),
        "desc": "Satoshi Tajiri convirtió su fascinación infantil por la entomología en el mayor imperio de entretenimiento contemporáneo. De Pueblo Paleta a la Liga Pokémon.",
        "controls": "Mover: Flechas/WASD | Aceptar (A): ESPACIO / ARRIBA / W / X | Cancelar (B): Shift/Z | Menú: Enter",
    },
    {
        "id": "wario_land",
        "title": "Super Mario Land 3: Wario Land",
        "system": "Game Boy",
        "year": "1994",
        "dev": "Nintendo",
        "genre": "Plataformas",
        "rom": os.path.join(ROMS_DIR, "gb/Super Mario Land 3 - Wario Land.gb"),
        "desc": "La sátira cómica del héroe tradicional. El debut de Wario en busca de oro pirata, con embestidas destructivas de hombro y sombreros especiales de dragón y toro.",
        "controls": "Mover: Flechas/WASD | SALTAR: ESPACIO / ARRIBA / W | Embestida: Shift/Z | Start: Enter",
    },
]

# Tabs / Categorías
CATEGORIES = ["TODOS", "PC NATIVO", "SUPER NINTENDO", "MEGA DRIVE", "NES (8-BIT)", "GAME BOY"]

SYSTEM_MAP = {
    "PC NATIVO": "PC Nativo",
    "SUPER NINTENDO": "SNES",
    "MEGA DRIVE": "Mega Drive",
    "NES (8-BIT)": "NES",
    "GAME BOY": "Game Boy",
}


def init_arcade_colors():
    curses.start_color()
    curses.use_default_colors()
    # Paleta Synthwave / Arcade Neon
    curses.init_pair(1, curses.COLOR_MAGENTA, -1)   # Bordes / Neón Rosa
    curses.init_pair(2, curses.COLOR_CYAN,    -1)   # Neón Azul / Títulos
    curses.init_pair(3, curses.COLOR_YELLOW,  -1)   # Oro / Monedas / Destacados
    curses.init_pair(4, curses.COLOR_GREEN,   -1)   # Verde Arcade / Ready
    curses.init_pair(5, curses.COLOR_RED,     -1)   # Rojo Alerta / Fuego
    curses.init_pair(6, curses.COLOR_BLACK,   curses.COLOR_CYAN)    # Barra selección
    curses.init_pair(7, curses.COLOR_WHITE,   curses.COLOR_MAGENTA) # Badge sistema
    curses.init_pair(8, curses.COLOR_BLACK,   curses.COLOR_YELLOW)  # Botones acción


def poll_input(stdscr):
    """Lee entrada del teclado o del mando USB."""
    if volume:
        k = volume.get_gamepad_key()
        if k is not None:
            return k
    return stdscr.getch()


def get_game_autosave(game):
    """Busca si existe una instantánea guardada previa (.mca) para este juego."""
    if game.get("system") == "PC Nativo":
        return None
    rom_path = game.get("rom")
    if not rom_path:
        return None
    base = os.path.splitext(os.path.basename(rom_path))[0]
    mcs_dir = os.path.expanduser("~/.mednafen/mcs")
    matches = glob.glob(os.path.join(mcs_dir, f"{base}.*.mca"))
    for m in matches:
        if os.path.isfile(m) and os.path.getsize(m) > 0:
            return m
    return None


# ---------------------------------------------------------------------------
# RENDERIZADO DE CARÁTULA Y FICHA REAL EN FRAMEBUFFER (/dev/fb0)
# Estilo Deportes TV / Plex
# ---------------------------------------------------------------------------
_FB_DEV = "/dev/fb0"
_fb_geom = None
_fb_last_rect = None
_fb_cache = {}

_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
COVERS_DIR = os.path.expanduser("~/.emulador/cache/covers")


def _fb_geometry():
    global _fb_geom
    if _fb_geom is None:
        try:
            with open("/sys/class/graphics/fb0/virtual_size") as f:
                fbw, fbh = (int(v) for v in f.read().strip().split(","))
            with open("/sys/class/graphics/fb0/bits_per_pixel") as f:
                bpp = int(f.read())
            with open("/sys/class/graphics/fb0/stride") as f:
                stride = int(f.read())
            ok = (bpp == 32 and os.access(_FB_DEV, os.W_OK) and _HAS_PIL)
            _fb_geom = (fbw, fbh, stride) if ok else False
        except Exception:
            _fb_geom = False
    return _fb_geom


def fb_available():
    return bool(_fb_geometry())


def get_game_cover(game):
    gid = game.get("id", "")
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        p = os.path.join(COVERS_DIR, f"{gid}{ext}")
        if os.path.isfile(p):
            return p
    rom = game.get("rom")
    if rom:
        base = os.path.splitext(os.path.basename(rom))[0]
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            p = os.path.join(COVERS_DIR, f"{base}{ext}")
            if os.path.isfile(p):
                return p
    return None


def _compose_game_panel(game, aw: int, ah: int) -> bytes:
    """Compone póster real a la izquierda y ficha antialiasada a la derecha."""
    lienzo = Image.new("RGB", (aw, ah), (13, 15, 24))
    draw = ImageDraw.Draw(lienzo)

    cover_path = get_game_cover(game)
    poster = None
    if cover_path:
        try:
            poster = Image.open(cover_path).convert("RGB")
        except Exception:
            poster = None

    if poster is not None:
        iw, ih = poster.size
        esc = min((ah - 28) / ih, (aw * 0.38) / iw)
        pw, ph = max(1, round(iw * esc)), max(1, round(ih * esc))
        px = 14
        py = (ah - ph) // 2
        resized = poster.resize((pw, ph), Image.LANCZOS)
        lienzo.paste(resized, (px, py))
        draw.rectangle([px - 1, py - 1, px + pw, py + ph], outline=(0, 220, 255), width=2)
    else:
        pw = min(round(ah * 0.7), round(aw * 0.35))
        px = 14
        py = 14
        draw.rectangle([px, py, px + pw, ah - 14], fill=(22, 25, 38), outline=(60, 70, 95), width=1)
        f_ph = ImageFont.truetype(_FONT_BOLD if os.path.exists(_FONT_BOLD) else "DejaVuSans", 20)
        draw.text((px + 20, ah // 2 - 10), "[ SIN CARÁTULA ]", fill=(120, 130, 150), font=f_ph)

    # Tipografías
    f_bold = ImageFont.truetype(_FONT_BOLD, 26) if os.path.exists(_FONT_BOLD) else ImageFont.load_default()
    f_sub = ImageFont.truetype(_FONT_BOLD, 17) if os.path.exists(_FONT_BOLD) else ImageFont.load_default()
    f_reg = ImageFont.truetype(_FONT_REG, 16) if os.path.exists(_FONT_REG) else ImageFont.load_default()
    f_sm = ImageFont.truetype(_FONT_REG, 14) if os.path.exists(_FONT_REG) else ImageFont.load_default()

    ix = px + pw + 25
    info_w = max(100, aw - ix - 16)
    y = 16

    # 1. Título
    title = game.get("title", "")
    draw.text((ix, y), title[:65], fill=(255, 255, 255), font=f_bold)
    y += 34

    # 2. Metadatos
    sys_str = game.get("system", "")
    year_str = game.get("year", "")
    dev_str = game.get("dev", "")
    draw.text((ix, y), f"{sys_str}  ·  {year_str}  ·  {dev_str}"[:75], fill=(0, 220, 255), font=f_sub)
    y += 26

    # 3. Badge Rendimiento / Género
    perf_badge = "★ 60 FPS Bloqueados  ·  Cero Emulación" if sys_str == "PC Nativo" else "★ 60 FPS  ·  Mednafen KMSDRM  ·  Autosave"
    bw = min(info_w, int(draw.textlength(perf_badge, font=f_sm) + 24))
    draw.rounded_rectangle([ix, y, ix + bw, y + 22], radius=4, fill=(24, 30, 48), outline=(255, 210, 60))
    draw.text((ix + 12, y + 3), perf_badge, fill=(255, 210, 60), font=f_sm)
    y += 32

    # Línea divisoria
    draw.line([(ix, y), (aw - 16, y)], fill=(45, 55, 80), width=1)
    y += 10

    # 4. Sinopsis / Historia (wrap)
    desc = game.get("desc", "")
    words = desc.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=f_reg) <= info_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    # Dibujar hasta 5-6 líneas
    max_desc_lines = max(2, min(5, (ah - y - 70) // 22))
    for l in lines[:max_desc_lines]:
        draw.text((ix, y), l, fill=(215, 220, 230), font=f_reg)
        y += 22

    # 5. Caja de Mandos
    y_ctrl = max(y + 8, ah - 58)
    ctrl_text = game.get("controls", "")
    draw.rounded_rectangle([ix, y_ctrl, aw - 16, ah - 8], radius=6, fill=(18, 22, 34), outline=(0, 220, 255))
    draw.text((ix + 10, y_ctrl + 4), "MANDOS (Mando ShanWan / USB / Teclado):", fill=(255, 210, 60), font=f_sm)
    draw.text((ix + 10, y_ctrl + 24), ctrl_text[:85], fill=(255, 255, 255), font=f_sm)

    return lienzo.tobytes("raw", "BGRX")


def fb_draw_panel(game, col: int, row: int, ncols: int, nrows: int, term_cols: int, term_rows: int) -> bool:
    global _fb_last_rect
    geom = _fb_geometry()
    if not geom or game is None:
        return False
    fbw, fbh, stride = geom
    cell_w = max(1, fbw // max(1, term_cols))
    cell_h = max(1, fbh // max(1, term_rows))
    x0, y0 = col * cell_w, row * cell_h
    aw = min(ncols * cell_w, fbw - x0)
    ah = min(nrows * cell_h, fbh - y0)
    if aw <= 60 or ah <= 60:
        return False

    key = (game.get("id", ""), aw, ah)
    raw = _fb_cache.get(key)
    if raw is None:
        try:
            raw = _compose_game_panel(game, aw, ah)
        except Exception:
            return False
        if len(_fb_cache) > 20:
            _fb_cache.clear()
        _fb_cache[key] = raw

    try:
        fd = os.open(_FB_DEV, os.O_WRONLY)
        try:
            fila = aw * 4
            for y in range(ah):
                os.pwrite(fd, raw[y * fila : (y + 1) * fila], (y0 + y) * stride + x0 * 4)
        finally:
            os.close(fd)
    except Exception:
        return False

    _fb_last_rect = (x0, y0, aw, ah)
    return True


def fb_clear():
    global _fb_last_rect
    rect = _fb_last_rect
    _fb_last_rect = None
    geom = _fb_geometry()
    if not rect or not geom:
        return
    x0, y0, aw, ah = rect
    _, _, stride = geom
    negro = bytes(aw * 4)
    try:
        fd = os.open(_FB_DEV, os.O_WRONLY)
        try:
            for y in range(ah):
                os.pwrite(fd, negro, (y0 + y) * stride + x0 * 4)
        finally:
            os.close(fd)
    except Exception:
        pass


def _find_input_devices():
    if not evdev:
        return []
    devices = []
    try:
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                # Solo teclados físicos: NUNCA interceptar mandos de juego
                name_lower = dev.name.lower()
                if "shanwan" in name_lower or "gamepad" in name_lower or "joystick" in name_lower:
                    continue
                caps = dev.capabilities()
                if evdev.ecodes.EV_KEY in caps:
                    keys = caps[evdev.ecodes.EV_KEY]
                    if (evdev.ecodes.KEY_Q in keys or
                        evdev.ecodes.KEY_VOLUMEUP in keys or
                        evdev.ecodes.KEY_VOLUMEDOWN in keys or
                        evdev.ecodes.KEY_MUTE in keys):
                        devices.append(dev)
            except Exception:
                pass
    except Exception:
        pass
    return devices


def _force_kill(proc: subprocess.Popen, is_wine_or_dos: bool) -> None:
    """Garantiza que el proceso del juego (y su grupo) muere pase lo que pase."""
    if proc.poll() is not None:
        return
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=2.0)
        except Exception:
            pass
    if is_wine_or_dos:
        subprocess.run(["wineserver", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["killall", "-9", "dosbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "killall", "-9", "Xorg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "pkill", "-9", "-f", "Xorg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "rm", "-f", "/tmp/.X1-lock", "/tmp/.X2-lock", "/tmp/.X11-unix/X1", "/tmp/.X11-unix/X2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "chvt", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.system("sudo sh -c 'echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null || true'")


def _watch_process_and_q_key(proc: subprocess.Popen, is_wine_or_dos: bool = False) -> None:
    if not evdev:
        proc.wait()
        return

    devices = _find_input_devices()
    q_press_start = None
    last_vol_time = 0.0

    while proc.poll() is None:
        if devices:
            try:
                r, _, _ = select.select(devices, [], [], 0.05)
                for dev in r:
                    try:
                        for ev in dev.read():
                            if ev.type == evdev.ecodes.EV_KEY:
                                # 1. Pulsación de Q mantenida durante 1s para forzar salida limpia
                                if ev.code == evdev.ecodes.KEY_Q:
                                    if ev.value == 1 and q_press_start is None:
                                        q_press_start = time.monotonic()
                                    elif ev.value == 0:
                                        q_press_start = None

                                # 2. Teclas multimedia específicas de volumen del teclado
                                elif ev.code == evdev.ecodes.KEY_VOLUMEUP and ev.value in (1, 2):
                                    now = time.monotonic()
                                    if now - last_vol_time >= 0.08:
                                        if volume:
                                            volume.set_volume_delta(+5)
                                        else:
                                            subprocess.run(["amixer", "set", "Master", "5%+", "unmute"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                        last_vol_time = now

                                elif ev.code == evdev.ecodes.KEY_VOLUMEDOWN and ev.value in (1, 2):
                                    now = time.monotonic()
                                    if now - last_vol_time >= 0.08:
                                        if volume:
                                            volume.set_volume_delta(-5)
                                        else:
                                            subprocess.run(["amixer", "set", "Master", "5%-", "unmute"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                        last_vol_time = now

                                elif ev.code == evdev.ecodes.KEY_MUTE and ev.value == 1:
                                    if volume:
                                        volume.toggle_mute()
                                    else:
                                        subprocess.run(["amixer", "set", "Master", "toggle"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except (OSError, BlockingIOError):
                        pass

            except Exception:
                time.sleep(0.1)
                devices = _find_input_devices()
                continue

            # ÚNICA condición que cierra el juego: tecla Q pulsada durante 1 segundo entero
            if q_press_start is not None and (time.monotonic() - q_press_start) >= 1.0:
                _force_kill(proc, is_wine_or_dos)
                break
        else:
            time.sleep(0.1)
            devices = _find_input_devices()

    for dev in devices:
        try:
            dev.close()
        except Exception:
            pass
    if is_wine_or_dos:
        _force_kill(proc, is_wine_or_dos)


def launch_retro_game(stdscr, game):
    """Lanza el juego en Mednafen o motor nativo de PC por KMSDRM/ALSA."""
    is_native = (game.get("system") == "PC Nativo")
    if not is_native:
        rom_path = game.get("rom")
        if not rom_path or not os.path.exists(rom_path):
            return

    if volume:
        volume.set_emulator_active(True)

    if sound:
        sound.play("coin")
        time.sleep(0.35)
    subprocess.run(["killall", "-9", "aplay"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Limpiar panel de imagen antes de ceder la pantalla al juego
    fb_clear()

    # Suspender curses completamente para ceder la pantalla al juego
    curses.def_prog_mode()
    curses.endwin()

    env = os.environ.copy()
    if not env.get("DISPLAY"):
        env["SDL_VIDEODRIVER"] = "kmsdrm"
    env.pop("SDL_AUDIODRIVER", None)

    # Inyectar mapeo estándar de mando ShanWan para motores SDL2
    env["SDL_GAMECONTROLLERCONFIG"] = (
        "03008dbf632500007505000011010000,ShanWan Gamepad,"
        "platform:Linux,"
        "a:b0,b:b1,x:b3,y:b4,"
        "back:b10,start:b11,guide:b12,"
        "leftshoulder:b6,rightshoulder:b7,"
        "lefttrigger:b8,righttrigger:b9,"
        "leftx:a0,lefty:a1,rightx:a2,righty:a3,"
        "dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
    )

    try:
        if is_native:
            cmd = game["cmd"]
            cwd = game.get("cwd", None)

            native_script = "/home/jcgar/arcade/apply_native_gamepad_config.py"
            if os.path.exists(native_script):
                subprocess.run(
                    [sys.executable, native_script, game.get("id", "")],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            is_wine_or_dos = ("wine" in str(cmd) or "dosbox" in str(cmd))
            proc = subprocess.Popen(cmd, env=env, cwd=cwd, start_new_session=True)
            _watch_process_and_q_key(proc, is_wine_or_dos=is_wine_or_dos)
        else:
            # Mednafen toma control exclusivo de la GPU/DRM y audio con SDL, autosave instantáneo
            subprocess.run([sys.executable, "/home/jcgar/arcade/apply_input_config.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cmd = ["mednafen", "-ovconfig", "/home/jcgar/arcade/mednafen_arcade.cfg", "-video.driver", "softfb", "-sound.driver", "sdl", "-autosave", "1", game["rom"]]
            proc = subprocess.Popen(cmd, env=env, start_new_session=True)
            _watch_process_and_q_key(proc, is_wine_or_dos=False)
    except Exception:
        pass
    finally:
        subprocess.run([sys.executable, "/home/jcgar/arcade/apply_input_config.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if volume:
            volume.set_emulator_active(False)
        # Restaurar modo de teclado del kernel, VT y terminal
        os.system("sudo chvt 1 2>/dev/null; sudo sh -c 'echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null || true'; sudo kbd_mode -u -f 2>/dev/null; stty sane 2>/dev/null")
        curses.reset_prog_mode()
        stdscr.erase()
        stdscr.refresh()


def prompt_launch_mode(stdscr, game):
    """Si hay partida guardada, muestra diálogo interactivo: Reanudar o Empezar de nuevo."""
    save_file = get_game_autosave(game)
    if not save_file:
        # No hay partida previa: arrancar directamente
        launch_retro_game(stdscr, game)
        return

    if sound:
        sound.play("bonus")

    mtime = os.path.getmtime(save_file)
    date_str = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y a las %H:%M")

    opt_idx = 0  # 0: Reanudar, 1: Empezar de nuevo

    while True:
        max_y, max_x = stdscr.getmaxyx()
        box_w = min(66, max_x - 4)
        box_h = 13
        box_y = max(1, (max_y - box_h) // 2)
        box_x = max(1, (max_x - box_w) // 2)

        try:
            # Limpiar fondo del modal
            for r in range(box_h):
                stdscr.addstr(box_y + r, box_x, " " * box_w, curses.color_pair(1))

            # Borde exterior doble neón
            stdscr.addstr(box_y, box_x, "╔" + "═" * (box_w - 2) + "╗", curses.color_pair(3) | curses.A_BOLD)
            for r in range(1, box_h - 1):
                stdscr.addstr(box_y + r, box_x, "║", curses.color_pair(3))
                stdscr.addstr(box_y + r, box_x + box_w - 1, "║", curses.color_pair(3))
            stdscr.addstr(box_y + box_h - 1, box_x, "╚" + "═" * (box_w - 2) + "╝", curses.color_pair(3) | curses.A_BOLD)

            # Cabecera
            title = "★ PARTIDA GUARDADA DETECTADA ★"
            stdscr.addstr(box_y + 1, box_x + max(0, (box_w - len(title)) // 2), title, curses.color_pair(3) | curses.A_BOLD)

            g_title = f"[ {game['title'][:box_w - 8]} ]"
            stdscr.addstr(box_y + 2, box_x + max(0, (box_w - len(g_title)) // 2), g_title, curses.color_pair(2) | curses.A_BOLD)

            time_info = f"Última instantánea: {date_str}"
            stdscr.addstr(box_y + 3, box_x + max(0, (box_w - len(time_info)) // 2), time_info, curses.A_DIM)

            sep = "╟" + "─" * (box_w - 2) + "╢"
            stdscr.addstr(box_y + 4, box_x, sep, curses.color_pair(3))

            q = "¿Qué deseas hacer con esta partida?"
            stdscr.addstr(box_y + 5, box_x + max(0, (box_w - len(q)) // 2), q, curses.color_pair(4) | curses.A_BOLD)

            # Opción 1: Reanudar
            opt1 = " ▶ 1. REANUDAR PARTIDA  (Continuar donde lo dejaste) "
            attr1 = (curses.color_pair(6) | curses.A_BOLD) if opt_idx == 0 else curses.color_pair(2)
            stdscr.addstr(box_y + 7, box_x + max(2, (box_w - len(opt1)) // 2), opt1, attr1)

            # Opción 2: Empezar de nuevo
            opt2 = " ▶ 2. EMPEZAR DE NUEVO  (Reiniciar desde el inicio)  "
            attr2 = (curses.color_pair(6) | curses.A_BOLD) if opt_idx == 1 else curses.color_pair(5)
            stdscr.addstr(box_y + 9, box_x + max(2, (box_w - len(opt2)) // 2), opt2, attr2)

            # Indicaciones al pie
            hint = "[▲/▼/WASD]: Elegir  |  [ENTER/ESPACIO/A]: Confirmar  |  [Q/B]: Cancelar"
            stdscr.addstr(box_y + 11, box_x + max(1, (box_w - len(hint)) // 2), hint[:box_w - 2], curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()
        k = poll_input(stdscr)

        if k in [curses.KEY_UP, ord("w"), ord("W")]:
            if opt_idx > 0:
                opt_idx = 0
                if sound:
                    sound.play("hit")
        elif k in [curses.KEY_DOWN, ord("s"), ord("S")]:
            if opt_idx < 1:
                opt_idx = 1
                if sound:
                    sound.play("hit")
        elif k in [ord("1")]:
            opt_idx = 0
            break
        elif k in [ord("2")]:
            opt_idx = 1
            break
        elif k in [ord("\n"), 10, 13, ord(" ")]:
            break
        elif k in [ord("q"), ord("Q"), 27]:
            if sound:
                sound.play("hit")
            stdscr.erase()
            stdscr.refresh()
            return

    # Procesar selección
    if opt_idx == 1:
        # Borrar la instantánea previa para empezar desde 0 limpio
        try:
            os.remove(save_file)
        except Exception:
            pass
        if sound:
            sound.play("explosion")
            time.sleep(0.15)
    else:
        if sound:
            sound.play("coin")

    launch_retro_game(stdscr, game)


def draw_marquee(stdscr, start_y, start_x, width, frame):
    """Pinta la marquesina superior con estética recreativa de los 80."""
    art = [
        r"  █████╗ ██████╗  ██████╗ █████╗ ██████╗ ███████╗ ",
        r" ██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝ ",
        r" ███████║██████╔╝██║     ███████║██║  ██║█████╗   ",
        r" ██╔══██║██╔══██╗██║     ██╔══██║██║  ██║██╔══╝   ",
        r" ██║  ██║██║  ██║╚██████╗██║  ██║██████╔╝███████╗ ",
        r" ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ",
    ]
    color = curses.color_pair(2 if frame % 2 == 0 else 1) | curses.A_BOLD
    for idx, line in enumerate(art):
        px = max(0, start_x + (width - len(line)) // 2)
        try:
            stdscr.addstr(start_y + idx, px, line, color)
        except curses.error:
            pass

    # Subtítulo marquesina
    sub = "★ R E T R O   S T A T I O N ★  (COIN-OP CLASSICS)"
    px_sub = max(0, start_x + (width - len(sub)) // 2)
    try:
        stdscr.addstr(start_y + len(art), px_sub, sub, curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass


def arcade_main(stdscr):
    init_arcade_colors()
    curses.curs_set(0)
    stdscr.timeout(400)    # Reactivo: espera tecla o anima cada 400ms (cero parpadeo y 0% CPU)

    if volume:
        volume.init_arcade_volume() # Forzar siempre al 65% al arrancar
        volume.start_listener()

    cat_idx = 0
    selected_idx = 0
    scroll_offset = 0
    anim_frame = 0

    if sound:
        sound.play("coin")

    while True:
        anim_frame += 1

        # Filtrar lista de juegos según categoría
        active_cat = CATEGORIES[cat_idx]
        if active_cat == "TODOS":
            filtered_games = GAMES
        else:
            target_sys = SYSTEM_MAP.get(active_cat)
            filtered_games = [g for g in GAMES if g["system"] == target_sys]

        if selected_idx >= len(filtered_games):
            selected_idx = max(0, len(filtered_games) - 1)

        max_y, max_x = stdscr.getmaxyx()
        stdscr.erase()    # erase() en búfer de memoria (NUNCA clear() físico)

        # Marco exterior Neón
        for x in range(max_x - 1):
            try:
                stdscr.addstr(0, x, "═", curses.color_pair(1) | curses.A_BOLD)
                stdscr.addstr(max_y - 1, x, "═", curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass
        for y in range(max_y):
            try:
                stdscr.addstr(y, 0, "║", curses.color_pair(1) | curses.A_BOLD)
                stdscr.addstr(y, max_x - 2, "║", curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        # Marquesina
        draw_marquee(stdscr, 1, 2, max_x - 4, anim_frame)

        # Tabs de Categorías
        tab_y = 8
        tab_str = "  "
        for i, c in enumerate(CATEGORIES):
            if i == cat_idx:
                tab_str += f" ► [{c}] ◄  "
            else:
                tab_str += f"   {c}    "
        try:
            stdscr.addstr(tab_y, 4, tab_str[:max_x - 18], curses.color_pair(3) | curses.A_BOLD)
            if filtered_games:
                count_str = f"[{selected_idx + 1}/{len(filtered_games)}]"
                stdscr.addstr(tab_y, max_x - len(count_str) - 4, count_str, curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(tab_y + 1, 2, "─" * (max_x - 4), curses.color_pair(1))
        except curses.error:
            pass

        # División en 2 columnas: Izquierda (Lista de Juegos) | Derecha (Ficha Arcade)
        split_x = max(34, int(max_x * 0.44))
        content_y = tab_y + 2
        content_h = max_y - content_y - 4

        # Línea separadora vertical
        for cy in range(content_y, content_y + content_h):
            try:
                stdscr.addstr(cy, split_x, "│", curses.color_pair(1))
            except curses.error:
                pass

        # Columna Izquierda: Lista de Juegos con scroll reactivo
        list_w = split_x - 4
        max_visible = max(1, content_h // 2)

        # Ventana deslizante para mantener el juego seleccionado siempre visible
        if selected_idx < scroll_offset:
            scroll_offset = selected_idx
        elif selected_idx >= scroll_offset + max_visible:
            scroll_offset = selected_idx - max_visible + 1

        visible_games = filtered_games[scroll_offset : scroll_offset + max_visible]
        for i, g in enumerate(visible_games):
            idx = scroll_offset + i
            gy = content_y + i * 2
            if gy + 1 >= content_y + content_h:
                break

            is_sel = (idx == selected_idx)
            if g["system"] == "PC Nativo":
                badge = "[PC  ]"
            else:
                badge = f"[{g['system'][:4]}]"
            name = g["title"]

            if is_sel:
                line_text = f" ► {badge} {name} "
                line_padded = f"{line_text:<{list_w}}"[:list_w]
                attr = curses.color_pair(6) | curses.A_BOLD
            else:
                line_text = f"   {badge} {name} "
                line_padded = f"{line_text:<{list_w}}"[:list_w]
                attr = curses.color_pair(2)

            try:
                stdscr.addstr(gy, 3, line_padded, attr)
                # Pequeña info de género bajo el título
                genre_hint = f"      {g['genre']} · {g['year']}"
                stdscr.addstr(gy + 1, 3, genre_hint[:list_w], curses.color_pair(3) if not is_sel else curses.color_pair(6))
            except curses.error:
                pass

        # Columna Derecha: Tarjeta / Ficha del Juego
        has_fb = fb_available()
        if filtered_games:
            cur_game = filtered_games[selected_idx]
            card_x = split_x + 3
            card_w = max_x - card_x - 3
            card_y = content_y
            card_h = content_h

            if not has_fb:
                cy = content_y
                try:
                    # Título y Sistema
                    title_line = f"★ {cur_game['title']} ★"
                    stdscr.addstr(cy, card_x, title_line[:card_w], curses.color_pair(4) | curses.A_BOLD)
                    cy += 1

                    meta_line = f"Sistema: {cur_game['system']}   Año: {cur_game['year']}   Desarrollador: {cur_game['dev']}"
                    stdscr.addstr(cy, card_x, meta_line[:card_w], curses.color_pair(3))
                    cy += 2

                    # Recuadro de rendimiento
                    perf_box = "╔═ RENDIMIENTO EN TU CELERON ═════════════════════════════════╗"
                    if cur_game.get("system") == "PC Nativo":
                        perf_txt = "║  Carga CPU: < 3%  |  Motor Nativo Linux  |  Sin emulación   ║"
                    else:
                        perf_txt = "║  Carga CPU: < 2%  |  60 FPS Bloqueados  |  Sin calor/ruido  ║"
                    perf_end = "╚══════════════════════════════════════════════════════════════╝"
                    stdscr.addstr(cy, card_x, perf_box[:card_w], curses.color_pair(4))
                    cy += 1
                    stdscr.addstr(cy, card_x, perf_txt[:card_w], curses.color_pair(4) | curses.A_BOLD)
                    cy += 1
                    stdscr.addstr(cy, card_x, perf_end[:card_w], curses.color_pair(4))
                    cy += 2

                    # Sinopsis
                    stdscr.addstr(cy, card_x, "HISTORIA Y DETALLES:", curses.color_pair(1) | curses.A_BOLD)
                    cy += 1
                    words = cur_game["desc"].split()
                    line = ""
                    for w in words:
                        if len(line) + len(w) + 1 < card_w - 2:
                            line += (" " if line else "") + w
                        else:
                            stdscr.addstr(cy, card_x, line, curses.color_pair(2))
                            cy += 1
                            line = w
                    if line:
                        stdscr.addstr(cy, card_x, line, curses.color_pair(2))
                        cy += 2

                    # Mandos y Atajos
                    stdscr.addstr(cy, card_x, "MANDOS (Mando USB/ShanWan o Teclado):", curses.color_pair(3) | curses.A_BOLD)
                    cy += 1
                    stdscr.addstr(cy, card_x, cur_game["controls"][:card_w], curses.A_BOLD)
                    cy += 2

                    stdscr.addstr(cy, card_x, "ATAJOS DENTRO DEL JUEGO:", curses.color_pair(5) | curses.A_BOLD)
                    cy += 1
                    stdscr.addstr(cy, card_x, "• Salir: Mantén pulsada Q durante 1 segundo", curses.color_pair(4) | curses.A_BOLD)
                    cy += 1
                    if cur_game.get("system") == "PC Nativo":
                        stdscr.addstr(cy, card_x, "• Guardado: Menú propio del juego (F2/F5 Guardar / F3/F7 Cargar)", curses.A_NORMAL)
                    else:
                        stdscr.addstr(cy, card_x, "• Guardado: ¡Automático al salir con Q! Al volver, sigues donde lo dejaste", curses.A_NORMAL)
                except curses.error:
                    pass

        # Barra de Estado Inferior Recreativa con indicador de Volumen
        footer_y = max_y - 2
        coin_blinker = "★ INSERT COIN ★" if (anim_frame % 2 == 0) else "  INSERT COIN  "
        vol_hud = f" VOL: {volume.format_volume_bar(6)} [+/-] " if volume else ""
        help_bar = f" {coin_blinker}   [ENTER] JUGAR   [◄/►] CONSOLA   [▲/▼] JUEGO  {vol_hud} [Q] SALIR "
        try:
            stdscr.addstr(footer_y, 2, help_bar[:max_x - 4], curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass

        stdscr.refresh()

        # Dibuja la carátula y ficha gráfica sobre /dev/fb0 si está disponible
        if filtered_games and has_fb:
            fb_draw_panel(cur_game, card_x, card_y, card_w, card_h, max_x, max_y)

        # Manejo de teclas reactivo (espera hasta 400ms o despierta al instante al pulsar teclado o mando)
        key = poll_input(stdscr)
        if key == -1 or key is None:
            continue

        if key in [ord("q"), ord("Q"), 27]: # ESC o Q
            fb_clear()
            break
        elif key in [curses.KEY_UP, ord("w"), ord("W")]:
            if selected_idx > 0:
                selected_idx -= 1
                if sound:
                    sound.play("hit")
        elif key in [curses.KEY_DOWN, ord("s"), ord("S")]:
            if selected_idx < len(filtered_games) - 1:
                selected_idx += 1
                if sound:
                    sound.play("hit")
        elif key in [curses.KEY_PPAGE]:
            selected_idx = max(0, selected_idx - 5)
            if sound:
                sound.play("hit")
        elif key in [curses.KEY_NPAGE]:
            selected_idx = min(len(filtered_games) - 1, selected_idx + 5)
            if sound:
                sound.play("hit")
        elif key in [curses.KEY_LEFT, ord("a"), ord("A")]:
            cat_idx = (cat_idx - 1) % len(CATEGORIES)
            selected_idx = 0
            scroll_offset = 0
            if sound:
                sound.play("bonus")
        elif key in [curses.KEY_RIGHT, ord("d"), ord("D")]:
            cat_idx = (cat_idx + 1) % len(CATEGORIES)
            selected_idx = 0
            scroll_offset = 0
            if sound:
                sound.play("bonus")
        elif key in [ord("\n"), 10, 13, ord(" ")]: # Enter o Espacio
            if filtered_games:
                prompt_launch_mode(stdscr, filtered_games[selected_idx])
        elif key in [ord("c"), ord("C"), ord("5")]: # Moneda arcade
            if sound:
                sound.play("coin")
        elif key in [ord("+"), ord("=")]: # Subir volumen
            if volume:
                volume.set_volume_delta(+5)
                if sound:
                    sound.play("hit")
        elif key in [ord("-"), ord("_")]: # Bajar volumen
            if volume:
                volume.set_volume_delta(-5)
                if sound:
                    sound.play("hit")
        elif key in [ord("m"), ord("M")]: # Silenciar
            if volume:
                volume.toggle_mute()
                if sound:
                    sound.play("hit")


def main():
    try:
        curses.wrapper(arcade_main)
    finally:
        fb_clear()
        if volume:
            volume.stop_listener()
            volume.reset_to_100()
        os.system("sudo chvt 1 2>/dev/null; sudo sh -c 'echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null || true'; sudo kbd_mode -u -f 2>/dev/null; stty sane 2>/dev/null")
        # Asegurar reseteo de cursor y pantalla limpia
        print("\033[?25h", end="")
        os.system("clear")


if __name__ == "__main__":
    main()

"""
ONYRA - Native Graphic Frontend (Pygame / SDL2 / KMSDRM)
Bucle principal a 60 FPS, vsync, gestión de vistas y eventos unificados de mando y teclado.
"""

import os
import sys
import time
import pygame

# Añadir ruta del proyecto
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

import theme
from input_manager import input_mgr, EVENT_ONYRA_INPUT
from screens.boot_view import BootView
from screens.systems_view import SystemsView
from screens.games_view import GamesView

try:
    sys.path.insert(0, "/home/jcgar/arcade")
    import volume
except Exception:
    volume = None


def main():
    # Asegurar controlador de bajo nivel KMSDRM si no hay servidor X
    if not os.environ.get("DISPLAY"):
        os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
    os.environ.pop("SDL_AUDIODRIVER", None)

    # Fijar volumen de arranque al 65%
    if volume:
        volume.init_arcade_volume()

    pygame.init()
    pygame.display.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)

    # Obtener resolución nativa de la pantalla (ej. 1920x1080)
    modes = pygame.display.list_modes()
    res = modes[0] if modes else (1920, 1080)
    screen = pygame.display.set_mode(res, pygame.FULLSCREEN | pygame.DOUBLEBUF)
    pygame.display.set_caption("ONYRA")

    screen_w, screen_h = screen.get_size()

    # Iniciar gestor de entrada física (evdev)
    input_mgr.start()

    clock = pygame.time.Clock()

    # Vistas
    boot_view = BootView(screen_w, screen_h)
    systems_view = None
    games_view = None

    current_state = "BOOT"

    running = True
    last_time = time.monotonic()

    while running:
        now = time.monotonic()
        dt = min(0.1, now - last_time) # Clamping de delta time para estabilidad
        last_time = now

        # Obtener siempre la superficie activa del display (tras volver de emulador)
        screen = pygame.display.get_surface()
        if screen is None:
            time.sleep(0.05)
            continue
        screen_w, screen_h = screen.get_size()

        try:
            # Procesar eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                # Eventos normalizados de evdev (mando y teclado)
                elif event.type == EVENT_ONYRA_INPUT:
                    action = getattr(event, "action", "")
                    char_val = getattr(event, "char", "")

                    if current_state == "BOOT":
                        boot_view.handle_input(action, char_val)
                    elif current_state == "SYSTEMS" and systems_view:
                        systems_view.handle_input(action, char_val)
                    elif current_state == "GAMES" and games_view:
                        games_view.handle_input(action, char_val)
                        active_surf = pygame.display.get_surface()
                        if active_surf is not None:
                            screen = active_surf
                            screen_w, screen_h = screen.get_size()

            # Lógica de estados y transiciones
            if current_state == "BOOT":
                boot_view.update(dt)
                boot_view.draw(screen)
                if boot_view.finished:
                    systems_view = SystemsView(screen_w, screen_h)
                    current_state = "SYSTEMS"

            elif current_state == "SYSTEMS" and systems_view:
                systems_view.update(dt)
                systems_view.draw(screen)

                if systems_view.should_exit:
                    running = False
                elif systems_view.selected_system_id:
                    sys_id = systems_view.selected_system_id
                    systems_view.selected_system_id = None
                    games_view = GamesView(sys_id, screen_w, screen_h)
                    current_state = "GAMES"

            elif current_state == "GAMES" and games_view:
                games_view.update(dt)
                games_view.draw(screen)

                if games_view.should_back_to_systems:
                    games_view = None
                    systems_view = SystemsView(screen_w, screen_h)
                    current_state = "SYSTEMS"

            pygame.display.flip()
            clock.tick(60)
        except Exception:
            time.sleep(0.02)

    # Limpieza final
    input_mgr.stop()
    pygame.display.quit()
    pygame.quit()

    if volume:
        volume.reset_to_100()

    os.system("sudo kbd_mode -u -f 2>/dev/null; stty sane 2>/dev/null")


if __name__ == "__main__":
    main()

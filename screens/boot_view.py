"""
ONYRA - Pantalla 1: Boot Splash Screen (Pygame / 60 FPS)
Fade-in suave del logo ONYRA desde negro, subtítulo RETRO GAMES y barra de carga neón.
"""

import time
import pygame
import theme
import logo


class BootView:
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.duration = 2.4 # segundos
        self.elapsed = 0.0
        self.finished = False

        # Pre-renderizar logo a la escala óptima según resolución
        scale = max(6, int(screen_h / 120))
        self.logo_surf = logo.create_onyra_logo_surface(scale=scale, alpha=1.0)
        self.logo_w = self.logo_surf.get_width()
        self.logo_h = self.logo_surf.get_height()

        self.center_x = screen_w // 2
        self.center_y = screen_h // 2 - 40

        # Subtítulo
        self.sub_surf = theme.render_text("R E T R O   G A M E S", font_name="sans_bold", size=max(16, screen_h // 55), color=theme.COLOR_TEXT_DIM)

    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True

    def handle_input(self, action: str, char: str = "") -> None:
        # Cualquier tecla o botón salta el boot
        self.finished = True

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.COLOR_BG)

        # 1. Fade-in del logo (primeros 1.0s)
        fade_progress = min(1.0, self.elapsed / 1.0)
        alpha = int(255 * fade_progress)

        logo_copy = self.logo_surf.copy()
        logo_copy.set_alpha(alpha)
        logo_x = self.center_x - self.logo_w // 2
        logo_y = self.center_y - self.logo_h // 2
        screen.blit(logo_copy, (logo_x, logo_y))

        # 2. Línea divisoria y subtítulo (a partir de 0.8s)
        if self.elapsed >= 0.7:
            sub_fade = min(1.0, (self.elapsed - 0.7) / 0.5)
            sub_alpha = int(255 * sub_fade)

            line_y = logo_y + self.logo_h + 18
            line_w = min(self.logo_w, 450)
            line_rect = pygame.Rect(self.center_x - line_w // 2, line_y, line_w, 1)

            line_surf = pygame.Surface((line_w, 1))
            line_surf.fill(theme.COLOR_BORDER_INACTIVE)
            line_surf.set_alpha(sub_alpha)
            screen.blit(line_surf, line_rect.topleft)

            sub_copy = self.sub_surf.copy()
            sub_copy.set_alpha(sub_alpha)
            screen.blit(sub_copy, (self.center_x - sub_copy.get_width() // 2, line_y + 14))

        # 3. Barra de progreso fina (de violeta oscuro #4B3A99 a menta #3DFFC0)
        bar_w = min(self.logo_w, 450)
        bar_h = 4
        bar_y = logo_y + self.logo_h + 75
        bar_rect = pygame.Rect(self.center_x - bar_w // 2, bar_y, bar_w, bar_h)

        # Fondo barra
        pygame.draw.rect(screen, theme.COLOR_PANEL, bar_rect, border_radius=2)
        pygame.draw.rect(screen, theme.COLOR_BORDER_INACTIVE, bar_rect, width=1, border_radius=2)

        # Relleno con degradado horizontal
        progress = min(1.0, self.elapsed / self.duration)
        filled_w = int(bar_w * progress)

        if filled_w > 0:
            fill_surf = pygame.Surface((filled_w, bar_h))
            for x in range(filled_w):
                t = x / float(max(1, bar_w - 1))
                c = theme.lerp_color(theme.COLOR_SHADOW, theme.COLOR_MINT, t)
                pygame.draw.line(fill_surf, c, (x, 0), (x, bar_h))
            screen.blit(fill_surf, bar_rect.topleft)

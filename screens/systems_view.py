"""
ONYRA - Pantalla 2: Selector de Sistemas (Pygame / 60 FPS)
Dos filas de tarjetas centradas con logos monocromos nítidos, halo de glow real
y recuadro de selección animado con easing fluido menta a violeta.
"""

import os
import time
from typing import Dict, List, Any, Optional, Tuple
import pygame
from PIL import Image

import data
import theme
import logo

CACHE_LOGOS_DIR = os.path.expanduser("~/.emulador/cache/logos")


def load_system_logo_surface(sys_id: str, target_w: int, target_h: int) -> Tuple[pygame.Surface, pygame.Surface]:
    """
    Carga el logo del sistema y devuelve una tupla (surf_inactiva, surf_activa).
    Para 'pc', usa los glifos pixel de ONYRA.
    """
    if sys_id == "pc":
        scale = max(4, target_h // 12)
        surf_dim = logo.create_pixel_text_surface("PC", scale=scale, color=theme.COLOR_SYSTEM_DIM)
        surf_mint = logo.create_pixel_text_surface("PC", scale=scale, color=theme.COLOR_MINT)
        return surf_dim, surf_mint

    png_path = os.path.join(CACHE_LOGOS_DIR, f"{sys_id}.png")
    if os.path.exists(png_path):
        try:
            pil_img = Image.open(png_path).convert("RGBA")
            bbox = pil_img.getbbox()
            if bbox:
                pil_img = pil_img.crop(bbox)

            orig_w, orig_h = pil_img.size
            ratio = orig_w / float(orig_h)

            fit_h = target_h
            fit_w = int(fit_h * ratio)
            if fit_w > target_w:
                fit_w = target_w
                fit_h = int(fit_w / ratio)

            pil_img = pil_img.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
            mode = pil_img.mode
            size = pil_img.size
            data_bytes = pil_img.tobytes()

            base_surf = pygame.image.fromstring(data_bytes, size, mode)

            # Generar versión inactiva (gris verdoso apagado)
            surf_dim = base_surf.copy()
            tint_dim = pygame.Surface(size, pygame.SRCALPHA)
            tint_dim.fill(theme.COLOR_SYSTEM_DIM)
            surf_dim.blit(tint_dim, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            # Generar versión activa (menta neón)
            surf_mint = base_surf.copy()
            tint_mint = pygame.Surface(size, pygame.SRCALPHA)
            tint_mint.fill(theme.COLOR_MINT)
            surf_mint.blit(tint_mint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            return surf_dim, surf_mint
        except Exception:
            pass

    # Fallback si no hay logo
    surf_dim = theme.render_text(sys_id.upper(), font_name="sans_bold", size=24, color=theme.COLOR_SYSTEM_DIM)
    surf_mint = theme.render_text(sys_id.upper(), font_name="sans_bold", size=24, color=theme.COLOR_MINT)
    return surf_dim, surf_mint


class SystemsView:
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.systems = data.get_active_systems()

        # Separar en 2 filas
        self.rows: List[List[Dict[str, Any]]] = [[], []]
        for s in self.systems:
            r = min(1, s.get("row", 0))
            self.rows[r].append(s)

        if not self.rows[1] and len(self.rows[0]) > 2:
            mid = (len(self.rows[0]) + 1) // 2
            self.rows[1] = self.rows[0][mid:]
            self.rows[0] = self.rows[0][:mid]

        # Dimensiones de tarjetas escalables
        self.card_w = min(280, int(screen_w * 0.16))
        self.card_h = min(170, int(screen_h * 0.17))
        self.gap_x = 36
        self.gap_y = 28

        # Pre-cargar logos en caché
        self.logo_surfs: Dict[str, Tuple[pygame.Surface, pygame.Surface]] = {}
        for s in self.systems:
            self.logo_surfs[s["id"]] = load_system_logo_surface(s["id"], self.card_w - 60, self.card_h - 70)

        # Restaurar último sistema
        state = data.load_state()
        last_sys = state.get("last_system_id", "snes")
        self.cur_row = 0
        self.cur_col = 0
        for r_idx, row in enumerate(self.rows):
            for c_idx, s in enumerate(row):
                if s["id"] == last_sys:
                    self.cur_row = r_idx
                    self.cur_col = c_idx
                    break

        # Calcular posiciones absolutas de cada tarjeta
        self.card_rects: List[List[pygame.Rect]] = []
        total_grid_h = len(self.rows) * self.card_h + (len(self.rows) - 1) * self.gap_y
        start_y = (screen_h - total_grid_h) // 2 - 20

        for r_idx, row in enumerate(self.rows):
            r_list = []
            row_w = len(row) * self.card_w + (len(row) - 1) * self.gap_x
            row_start_x = (screen_w - row_w) // 2
            y = start_y + r_idx * (self.card_h + self.gap_y)

            for c_idx, _ in enumerate(row):
                x = row_start_x + c_idx * (self.card_w + self.gap_x)
                r_list.append(pygame.Rect(x, y, self.card_w, self.card_h))
            self.card_rects.append(r_list)

        # Coordenadas del recuadro de selección para animación de easing
        init_rect = self.card_rects[self.cur_row][self.cur_col]
        self.cursor_x = float(init_rect.x)
        self.cursor_y = float(init_rect.y)
        self.cursor_w = float(init_rect.width)
        self.cursor_h = float(init_rect.height)

        # Estado
        self.selected_system_id: Optional[str] = None
        self.should_exit = False
        self.created_at = time.monotonic()

    def update(self, dt: float) -> None:
        target_rect = self.card_rects[self.cur_row][self.cur_col]
        speed = 22.0 # Velocidad de interpolación fluida (easing exponencial)
        factor = min(1.0, speed * dt)

        self.cursor_x += (target_rect.x - self.cursor_x) * factor
        self.cursor_y += (target_rect.y - self.cursor_y) * factor
        self.cursor_w += (target_rect.width - self.cursor_w) * factor
        self.cursor_h += (target_rect.height - self.cursor_h) * factor

    def handle_input(self, action: str, char: str = "") -> None:
        if action == "LEFT":
            if self.cur_col > 0:
                self.cur_col -= 1
            else:
                self.cur_col = len(self.rows[self.cur_row]) - 1
            self._on_navigate()

        elif action == "RIGHT":
            if self.cur_col < len(self.rows[self.cur_row]) - 1:
                self.cur_col += 1
            else:
                self.cur_col = 0
            self._on_navigate()

        elif action == "UP":
            if self.cur_row > 0:
                self.cur_row -= 1
                self.cur_col = min(self.cur_col, len(self.rows[self.cur_row]) - 1)
                self._on_navigate()

        elif action == "DOWN":
            if self.cur_row < len(self.rows) - 1:
                self.cur_row += 1
                self.cur_col = min(self.cur_col, len(self.rows[self.cur_row]) - 1)
                self._on_navigate()

        elif action == "ENTER":
            cur_sys = self.rows[self.cur_row][self.cur_col]
            self.selected_system_id = cur_sys["id"]

        elif action == "BACK":
            if time.monotonic() - self.created_at > 0.5:
                self.should_exit = True

    def _on_navigate(self) -> None:
        cur_sys = self.rows[self.cur_row][self.cur_col]
        data.save_state(cur_sys["id"], data.load_state().get("last_game_id", ""))

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.COLOR_BG)

        # 1. Cabecera pequeña ONYRA
        header_surf = theme.render_text("O  N  Y  R  A", font_name="sans_bold", size=22, color=theme.COLOR_MINT)
        screen.blit(header_surf, (self.screen_w // 2 - header_surf.get_width() // 2, 32))

        # 2. Tarjetas de sistemas
        for r_idx, row in enumerate(self.rows):
            for c_idx, s in enumerate(row):
                rect = self.card_rects[r_idx][c_idx]
                is_current = (r_idx == self.cur_row and c_idx == self.cur_col)

                # Fondo del panel inactivo
                theme.draw_rounded_panel(screen, rect, bg_color=theme.COLOR_PANEL, border_color=theme.COLOR_BORDER_INACTIVE, radius=12, border_width=1)

                # Logo del sistema centrado
                surf_dim, surf_mint = self.logo_surfs[s["id"]]
                logo_to_draw = surf_mint if is_current else surf_dim
                lx = rect.centerx - logo_to_draw.get_width() // 2
                ly = rect.y + 26
                screen.blit(logo_to_draw, (lx, ly))

                # Etiqueta de nombre bajo el logo
                name_col = theme.COLOR_MINT if is_current else theme.COLOR_TEXT_DIM
                name_surf = theme.render_text(s["name"].upper(), font_name="sans_bold", size=15, color=name_col)
                screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2, rect.bottom - 34))

        # 3. Recuadro de selección neón animado con halo de glow y degradado
        cursor_rect = pygame.Rect(int(self.cursor_x), int(self.cursor_y), int(self.cursor_w), int(self.cursor_h))
        theme.draw_neon_selection_box(screen, cursor_rect, radius=14)

        # 4. Información del sistema seleccionado bajo la cuadrícula
        cur_sys = self.rows[self.cur_row][self.cur_col]
        info_y = self.card_rects[-1][0].bottom + 38

        title_surf = theme.render_text(cur_sys["name"].upper(), font_name="sans_bold", size=26, color=theme.COLOR_TEXT)
        screen.blit(title_surf, (self.screen_w // 2 - title_surf.get_width() // 2, info_y))

        count_text = f"◆  {cur_sys['games_count']} JUEGOS DISPONIBLES  ◆"
        count_surf = theme.render_text(count_text, font_name="regular", size=16, color=theme.COLOR_VIOLET)
        screen.blit(count_surf, (self.screen_w // 2 - count_surf.get_width() // 2, info_y + 36))

        # 5. Barra de ayuda inferior
        footer_y = self.screen_h - 42
        help_surf = theme.render_text(
            "[◀ / ▶ / ▲ / ▼] Navegar   [ENTER / Botón A] Elegir Sistema   [ESC / Q / Botón B] Salir",
            font_name="regular", size=14, color=theme.COLOR_TEXT_DIM
        )
        screen.blit(help_surf, (self.screen_w // 2 - help_surf.get_width() // 2, footer_y))

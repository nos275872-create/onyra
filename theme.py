"""
ONYRA - Motor de Estilo y Paleta Visual (Luxury Dark Mint Neon + Violet)
Colores oficiales, carga de fuentes antialiasadas, renderizado de bordes redondeados y glow.
"""

import os
from typing import Dict, Tuple
import pygame

# Paleta oficial (Regla 60/30/10)
COLOR_BG = (8, 9, 13)              # #08090D (60%)
COLOR_PANEL = (14, 17, 22)         # #0E1116 (30%)
COLOR_BORDER_INACTIVE = (29, 36, 48) # #1D2430
COLOR_MINT = (61, 255, 192)        # #3DFFC0 (10% acento principal)
COLOR_VIOLET = (155, 123, 255)     # #9B7BFF (acento de apoyo)
COLOR_SHADOW = (75, 58, 153)       # #4B3A99 (glow y sombra)
COLOR_TEXT = (232, 238, 242)       # #E8EEF2
COLOR_TEXT_DIM = (122, 135, 148)   # #7A8794
COLOR_SYSTEM_DIM = (58, 80, 88)

FONTS_DIR = os.path.expanduser("~/.emulador/assets/fonts")
_font_cache: Dict[Tuple[str, int], pygame.font.Font] = {}
_text_cache: Dict[Tuple[str, str, int, Tuple[int, int, int]], pygame.Surface] = {}


def reset_theme_cache():
    """Limpia la caché de fuentes y textos tras reabrir Pygame."""
    _font_cache.clear()
    _text_cache.clear()
    pygame.font.init()


def get_font(name: str = "regular", size: int = 18) -> pygame.font.Font:
    """Devuelve una fuente TTF antialiasada en memoria caché."""
    key = (name, size)
    if key not in _font_cache:
        font_file = os.path.join(FONTS_DIR, f"{name}.ttf")
        if not os.path.exists(font_file):
            font_file = os.path.join(FONTS_DIR, "regular.ttf")
        if os.path.exists(font_file):
            _font_cache[key] = pygame.font.Font(font_file, size)
        else:
            _font_cache[key] = pygame.font.SysFont("monospace", size)
    return _font_cache[key]


def render_text(text: str, font_name: str = "regular", size: int = 18, color: Tuple[int, int, int] = COLOR_TEXT) -> pygame.Surface:
    """Renderiza texto antialiasado con caché."""
    key = (text, font_name, size, color)
    if key not in _text_cache:
        font = get_font(font_name, size)
        _text_cache[key] = font.render(text, True, color)
    return _text_cache[key]


def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def draw_rounded_panel(surf: pygame.Surface, rect: pygame.Rect, bg_color: Tuple[int, int, int] = COLOR_PANEL, border_color: Tuple[int, int, int] = COLOR_BORDER_INACTIVE, radius: int = 12, border_width: int = 1):
    """Dibuja un panel oscuro elegante con bordes redondeados finos."""
    # Fondo panel
    pygame.draw.rect(surf, bg_color, rect, border_radius=radius)
    # Borde fino
    if border_width > 0 and border_color:
        pygame.draw.rect(surf, border_color, rect, width=border_width, border_radius=radius)


def draw_neon_selection_box(surf: pygame.Surface, rect: pygame.Rect, radius: int = 14):
    """
    Dibuja el recuadro de selección con degradado de menta a violeta y halo exterior suave.
    """
    # 1. Halo tenue exterior (glow)
    glow_rect = rect.inflate(6, 6)
    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(glow_surf, (*COLOR_SHADOW, 60), glow_surf.get_rect(), width=3, border_radius=radius + 3)
    surf.blit(glow_surf, glow_rect.topleft)

    # 2. Borde principal con degradado menta a violeta
    # Dibuja el marco en una superficie temporal para aplicar el degradado vertical
    box_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(box_surf, (255, 255, 255, 255), box_surf.get_rect(), width=2, border_radius=radius)

    # Aplicar gradiente vertical (Menta arriba -> Violeta abajo)
    h = rect.height
    for y in range(h):
        t = y / float(max(1, h - 1))
        col = lerp_color(COLOR_MINT, COLOR_VIOLET, t)
        # Línea de color modulada
        line_rect = pygame.Rect(0, y, rect.width, 1)
        grad_line = pygame.Surface((rect.width, 1))
        grad_line.fill(col)
        box_surf.blit(grad_line, (0, y), special_flags=pygame.BLEND_RGBA_MULT)

    surf.blit(box_surf, rect.topleft)

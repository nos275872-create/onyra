"""
ONYRA - Motor de Renderizado del Logo Pixel y Glifos
Renderiza el logo tipográfico oficial con píxeles cuadrados nítidos,
sombra desplazada en violeta oscuro y degradado horizontal menta a violeta.
"""

from typing import Dict, Tuple
import pygame
import theme

ONYRA_GRID = [
    "..####....####..##..##....##..######......####..",
    ".######...####..##...##..##...##...###...######.",
    "###..###..##.##.##....####....##....##..###..###",
    "##....##..##.##.##.....##.....##...###..##....##",
    "##....##..##.##.##.....##.....######....########",
    "###..###..##.##.##.....##.....##.###....########",
    ".######...##..####.....##.....##..###...##....##",
    "..####....##..####.....##.....##...###..##....##",
]
GRID_W = 48
GRID_H = 8

# Glifos 'P' y 'C' con el mismo estilo pixel exacto (8px alto, trazo 2px, esquinas cortadas)
PIXEL_GLYPHS = {
    "P": [
        "######..",
        "##...###",
        "##....##",
        "##...###",
        "######..",
        "##......",
        "##......",
        "##......",
    ],
    "C": [
        "..####..",
        ".######.",
        "###..###",
        "##......",
        "##......",
        "###..###",
        ".######.",
        "..####..",
    ],
}


def create_onyra_logo_surface(scale: int = 8, alpha: float = 1.0) -> pygame.Surface:
    """
    Crea una Surface con el logo ONYRA escalado por píxeles nítidos enteros.
    - Sombra (+1, +1 pixel original) en violeta oscuro #4B3A99.
    - Logo frontal con degradado horizontal #3DFFC0 a #9B7BFF.
    """
    total_cols = GRID_W + 1
    total_rows = GRID_H + 1

    surf_w = total_cols * scale
    surf_h = total_rows * scale

    surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    # 1. Sombra (+1, +1)
    shadow_col = (*theme.COLOR_SHADOW, int(255 * alpha))
    for y in range(GRID_H):
        for x in range(GRID_W):
            if ONYRA_GRID[y][x] == "#":
                rect = pygame.Rect((x + 1) * scale, (y + 1) * scale, scale, scale)
                surf.fill(shadow_col, rect)

    # 2. Logo frontal con degradado horizontal
    for y in range(GRID_H):
        for x in range(GRID_W):
            if ONYRA_GRID[y][x] == "#":
                t = x / float(GRID_W - 1)
                col = theme.lerp_color(theme.COLOR_MINT, theme.COLOR_VIOLET, t)
                rect = pygame.Rect(x * scale, y * scale, scale, scale)
                surf.fill((*col, int(255 * alpha)), rect)

    return surf


def create_pixel_text_surface(text: str, scale: int = 6, color: Tuple[int, int, int] = theme.COLOR_MINT) -> pygame.Surface:
    """
    Dibuja texto corto usando los glifos pixel de ONYRA (por ejemplo 'PC').
    """
    lines = ["" for _ in range(GRID_H)]
    for char in text.upper():
        glyph = PIXEL_GLYPHS.get(char)
        if glyph:
            for row in range(GRID_H):
                lines[row] += glyph[row] + ".."
        else:
            for row in range(GRID_H):
                lines[row] += "...."

    cols = len(lines[0]) if lines else 0
    surf = pygame.Surface((cols * scale, GRID_H * scale), pygame.SRCALPHA)

    for y in range(GRID_H):
        for x in range(cols):
            if lines[y][x] == "#":
                rect = pygame.Rect(x * scale, y * scale, scale, scale)
                surf.fill((*color, 255), rect)

    return surf

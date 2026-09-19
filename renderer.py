"""
ONYRA - Motor de Renderizado Gráfico para Terminal
Generación de logos, siluetas vectoriales y carátulas a medios bloques truecolor.
"""

import os
from typing import Optional, Tuple
from PIL import Image
from rich.text import Text
from rich.style import Style

# Paleta oficial ONYRA (Luxury Dark Mint Neon + Violet)
COLOR_BG = (0x08, 0x09, 0x0D)          # #08090D Fondo general
COLOR_PANEL = (0x0E, 0x11, 0x16)       # #0E1116 Paneles
COLOR_BORDER_INACTIVE = (0x1D, 0x24, 0x30) # #1D2430 Bordes inactivos
COLOR_MINT = (0x3D, 0xFF, 0xC0)        # #3DFFC0 Menta neón
COLOR_VIOLET = (0x9B, 0x7B, 0xFF)      # #9B7BFF Violeta
COLOR_SHADOW = (0x4B, 0x3A, 0x99)      # #4B3A99 Violeta oscuro (sombra)
COLOR_TEXT = (0xE8, 0xEE, 0xF2)        # #E8EEF2 Texto principal
COLOR_TEXT_DIM = (0x7A, 0x87, 0x94)    # #7A8794 Texto secundario
COLOR_SYSTEM_DIM = (0x3A, 0x50, 0x58)  # Gris verdoso apagado para logos inactivos

# Matriz oficial tipográfica de ONYRA (48x8 píxeles)
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
GRID_WIDTH = 48
GRID_HEIGHT = 8

CACHE_LOGOS_DIR = os.path.expanduser("~/.emulador/cache/logos")
CACHE_COVERS_DIR = os.path.expanduser("~/.emulador/cache/covers")


def lerp_rgb(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Interpola linealmente entre dos colores RGB."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def hex_rgb(c: Tuple[int, int, int]) -> str:
    """Convierte tupla RGB a cadena hexadecimal #RRGGBB."""
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def render_onyra_logo(alpha: float = 1.0, bg: Tuple[int, int, int] = COLOR_BG) -> Text:
    """
    Renderiza el logo tipográfico de ONYRA.
    - Cuadrícula de 48x8 píxeles.
    - Sombra (+1, +1) en violeta oscuro (#4B3A99).
    - Degradado horizontal de menta (#3DFFC0) a violeta (#9B7BFF).
    - Codificado en 4-5 filas de texto con medios bloques '▀'.
    - alpha: 0.0 (negro/fondo) a 1.0 (brillo completo).
    """
    buf_w = GRID_WIDTH + 1
    buf_h = GRID_HEIGHT + 1
    buf = [[None for _ in range(buf_w)] for _ in range(buf_h)]

    # 1. Sombra (+1 col, +1 fila)
    s_col = lerp_rgb(bg, COLOR_SHADOW, alpha)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if ONYRA_GRID[y][x] == "#":
                buf[y + 1][x + 1] = s_col

    # 2. Logo frontal con degradado horizontal menta -> violeta
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if ONYRA_GRID[y][x] == "#":
                t = x / float(GRID_WIDTH - 1)
                col = lerp_rgb(COLOR_MINT, COLOR_VIOLET, t)
                if alpha < 1.0:
                    col = lerp_rgb(bg, col, alpha)
                buf[y][x] = col

    result = Text()
    text_rows = (buf_h + 1) // 2
    for tr in range(text_rows):
        y_top = tr * 2
        y_bot = y_top + 1
        for x in range(buf_w):
            top_c = buf[y_top][x] if y_top < buf_h and buf[y_top][x] is not None else bg
            bot_c = buf[y_bot][x] if y_bot < buf_h and buf[y_bot][x] is not None else bg
            st = Style(color=hex_rgb(top_c), bgcolor=hex_rgb(bot_c))
            result.append("▀", style=st)
        if tr < text_rows - 1:
            result.append("\n")
    return result


def render_system_logo(sys_id: str, selected: bool = False, target_lines: int = 4, max_cols: int = 24, bg: Tuple[int, int, int] = COLOR_PANEL) -> Text:
    """
    Renderiza el logo oficial de un sistema en silueta monocroma a medios bloques.
    - sys_id: identificador ('snes', 'megadrive', 'nes', 'gb', 'pc', etc.)
    - selected: True para menta neón, False para gris verdoso apagado.
    """
    os.makedirs(CACHE_LOGOS_DIR, exist_ok=True)
    png_path = os.path.join(CACHE_LOGOS_DIR, f"{sys_id}.png")

    if not os.path.exists(png_path):
        # Fallback si no está descargado aún
        fallback = Text()
        name_str = sys_id.upper()
        col = COLOR_MINT if selected else COLOR_SYSTEM_DIM
        pad_lines = max(0, (target_lines - 1) // 2)
        for _ in range(pad_lines):
            fallback.append(" " * max_cols + "\n")
        line = f" {name_str} ".center(max_cols)
        fallback.append(line, style=Style(color=hex_rgb(col), bold=True))
        return fallback

    try:
        img = Image.open(png_path).convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        orig_w, orig_h = img.size
        pixel_h = target_lines * 2
        pixel_w = int(orig_w * (pixel_h / orig_h))

        if pixel_w > max_cols:
            pixel_w = max_cols
            pixel_h = int(orig_h * (pixel_w / orig_w))
            if pixel_h % 2 != 0:
                pixel_h += 1

        img = img.resize((pixel_w, pixel_h), Image.Resampling.LANCZOS)
        tint = COLOR_MINT if selected else COLOR_SYSTEM_DIM

        res = Text()
        num_rows = pixel_h // 2
        pad_left = (max_cols - pixel_w) // 2
        pad_right = max_cols - pixel_w - pad_left

        for row in range(num_rows):
            if pad_left > 0:
                res.append(" " * pad_left, style=Style(bgcolor=hex_rgb(bg)))

            y_top = row * 2
            y_bot = y_top + 1

            for x in range(pixel_w):
                p_top = img.getpixel((x, y_top))
                p_bot = img.getpixel((x, y_bot))

                a_top = p_top[3] / 255.0
                a_bot = p_bot[3] / 255.0

                top_c = (
                    int(bg[0] * (1 - a_top) + tint[0] * a_top),
                    int(bg[1] * (1 - a_top) + tint[1] * a_top),
                    int(bg[2] * (1 - a_top) + tint[2] * a_top),
                )
                bot_c = (
                    int(bg[0] * (1 - a_bot) + tint[0] * a_bot),
                    int(bg[1] * (1 - a_bot) + tint[1] * a_bot),
                    int(bg[2] * (1 - a_bot) + tint[2] * a_bot),
                )

                res.append("▀", style=Style(color=hex_rgb(top_c), bgcolor=hex_rgb(bot_c)))

            if pad_right > 0:
                res.append(" " * pad_right, style=Style(bgcolor=hex_rgb(bg)))

            if row < num_rows - 1:
                res.append("\n")

        return res
    except Exception:
        fallback = Text()
        fallback.append(sys_id.upper().center(max_cols), style=Style(color=hex_rgb(COLOR_MINT if selected else COLOR_SYSTEM_DIM)))
        return fallback


def render_cover_image(img_path: Optional[str], max_cols: int = 34, max_lines: int = 15, bg: Tuple[int, int, int] = COLOR_PANEL, game_title: str = "ONYRA") -> Text:
    """
    Renderiza una carátula fotográfica a medios bloques truecolor respetando la relación de aspecto.
    Si no existe la imagen o falla, genera un placeholder elegante con estética ONYRA.
    """
    if img_path and os.path.exists(img_path):
        try:
            img = Image.open(img_path).convert("RGB")
            orig_w, orig_h = img.size
            pixel_max_h = max_lines * 2

            # Mantener proporción
            ratio = orig_w / float(orig_h)
            pixel_h = pixel_max_h
            pixel_w = int(pixel_h * ratio)

            if pixel_w > max_cols:
                pixel_w = max_cols
                pixel_h = int(pixel_w / ratio)
                if pixel_h % 2 != 0:
                    pixel_h += 1

            img = img.resize((pixel_w, pixel_h), Image.Resampling.LANCZOS)
            res = Text()
            num_rows = pixel_h // 2
            pad_left = max(0, (max_cols - pixel_w) // 2)
            pad_right = max(0, max_cols - pixel_w - pad_left)

            for row in range(num_rows):
                if pad_left > 0:
                    res.append(" " * pad_left, style=Style(bgcolor=hex_rgb(bg)))

                y_top = row * 2
                y_bot = y_top + 1

                for x in range(pixel_w):
                    c_top = img.getpixel((x, y_top))
                    c_bot = img.getpixel((x, y_bot))
                    res.append("▀", style=Style(color=hex_rgb(c_top), bgcolor=hex_rgb(c_bot)))

                if pad_right > 0:
                    res.append(" " * pad_right, style=Style(bgcolor=hex_rgb(bg)))

                if row < num_rows - 1:
                    res.append("\n")

            return res
        except Exception:
            pass

    # Placeholder elegante
    res = Text()
    lines_used = 0
    box_w = min(max_cols, 32)
    pad_h = (max_lines - 6) // 2

    for _ in range(max(0, pad_h)):
        res.append(" " * max_cols + "\n")
        lines_used += 1

    border_top = "╭" + "─" * (box_w - 2) + "╮"
    border_mid = "│" + " " * (box_w - 2) + "│"
    border_bot = "╰" + "─" * (box_w - 2) + "╯"

    indent = " " * max(0, (max_cols - box_w) // 2)

    res.append(indent + border_top + "\n", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))
    res.append(indent + border_mid + "\n", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))

    # Línea ONYRA central
    logo_txt = "O N Y R A"
    pad_l = (box_w - 2 - len(logo_txt)) // 2
    pad_r = box_w - 2 - len(logo_txt) - pad_l
    content_line = "│" + " " * pad_l + logo_txt + " " * pad_r + "│"
    res.append(indent, style=Style())
    res.append("│", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))
    res.append(" " * pad_l, style=Style())
    res.append(logo_txt, style=Style(color=hex_rgb(COLOR_MINT), bold=True))
    res.append(" " * pad_r, style=Style())
    res.append("│\n", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))

    # Subtítulo NO COVER
    sub_txt = "RETRO ARCHIVE"
    pad_l = (box_w - 2 - len(sub_txt)) // 2
    pad_r = box_w - 2 - len(sub_txt) - pad_l
    res.append(indent, style=Style())
    res.append("│", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))
    res.append(" " * pad_l, style=Style())
    res.append(sub_txt, style=Style(color=hex_rgb(COLOR_TEXT_DIM)))
    res.append(" " * pad_r, style=Style())
    res.append("│\n", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))

    res.append(indent + border_mid + "\n", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))
    res.append(indent + border_bot + "\n", style=Style(color=hex_rgb(COLOR_BORDER_INACTIVE)))

    return res

import sys

LOGO_GRID = [
    "..####....####..##..##....##..######......####..",
    ".######...####..##...##..##...##...###...######.",
    "###..###..##.##.##....####....##....##..###..###",
    "##....##..##.##.##.....##.....##...###..##....##",
    "##....##..##.##.##.....##.....######....########",
    "###..###..##.##.##.....##.....##.###....########",
    ".######...##..####.....##.....##..###...##....##",
    "..####....##..####.....##.....##...###..##....##",
]

WIDTH = 48
HEIGHT = 8

# Colores hex
MINT = (0x3D, 0xFF, 0xC0)    # #3DFFC0
VIOLET = (0x9B, 0x7B, 0xFF)  # #9B7BFF
SHADOW = (0x4B, 0x3A, 0x99)  # #4B3A99 violeta oscuro
BG = (0x08, 0x09, 0x0D)      # #08090D fondo

def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )

def render_logo_lines(alpha=1.0):
    # Buffer de píxeles: WIDTH+1 x HEIGHT+1 para dar espacio a la sombra (+1, +1)
    buf_w = WIDTH + 1
    buf_h = HEIGHT + 1
    buf = [[None for _ in range(buf_w)] for _ in range(buf_h)]

    # 1. Sombra (+1 col, +1 fila)
    s_col = lerp_color(BG, SHADOW, alpha)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if LOGO_GRID[y][x] == "#":
                buf[y + 1][x + 1] = s_col

    # 2. Logo principal (con degradado horizontal MINT -> VIOLET) encima
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if LOGO_GRID[y][x] == "#":
                t = x / (WIDTH - 1)
                col = lerp_color(MINT, VIOLET, t)
                if alpha < 1.0:
                    col = lerp_color(BG, col, alpha)
                buf[y][x] = col

    # 3. Agrupar de 2 en 2 filas de píxeles para generar caracteres de medio bloque ▀
    # Si buf_h es impar (9 filas), hacemos 5 filas de texto (la última con inferior BG)
    out_lines = []
    text_rows = (buf_h + 1) // 2
    for tr in range(text_rows):
        y_top = tr * 2
        y_bot = y_top + 1
        line_parts = []
        for x in range(buf_w):
            top_c = buf[y_top][x] if y_top < buf_h and buf[y_top][x] is not None else BG
            bot_c = buf[y_bot][x] if y_bot < buf_h and buf[y_bot][x] is not None else BG
            line_parts.append(f"\033[38;2;{top_c[0]};{top_c[1]};{top_c[2]}m\033[48;2;{bot_c[0]};{bot_c[1]};{bot_c[2]}m▀\033[0m")
        out_lines.append("".join(line_parts))
    return out_lines

if __name__ == "__main__":
    for line in render_logo_lines():
        print(line)

from rich.text import Text
from rich.style import Style
from rich.console import Console

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

MINT = (0x3D, 0xFF, 0xC0)
VIOLET = (0x9B, 0x7B, 0xFF)
SHADOW = (0x4B, 0x3A, 0x99)
BG = (0x08, 0x09, 0x0D)

def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )

def to_hex(c):
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"

def build_rich_logo(alpha=1.0):
    buf_w = WIDTH + 1
    buf_h = HEIGHT + 1
    buf = [[None for _ in range(buf_w)] for _ in range(buf_h)]

    s_col = lerp_color(BG, SHADOW, alpha)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if LOGO_GRID[y][x] == "#":
                buf[y + 1][x + 1] = s_col

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if LOGO_GRID[y][x] == "#":
                t = x / (WIDTH - 1)
                col = lerp_color(MINT, VIOLET, t)
                if alpha < 1.0:
                    col = lerp_color(BG, col, alpha)
                buf[y][x] = col

    result = Text()
    text_rows = (buf_h + 1) // 2
    for tr in range(text_rows):
        y_top = tr * 2
        y_bot = y_top + 1
        for x in range(buf_w):
            top_c = buf[y_top][x] if y_top < buf_h and buf[y_top][x] is not None else BG
            bot_c = buf[y_bot][x] if y_bot < buf_h and buf[y_bot][x] is not None else BG
            st = Style(color=to_hex(top_c), bgcolor=to_hex(bot_c))
            result.append("▀", style=st)
        if tr < text_rows - 1:
            result.append("\n")
    return result

console = Console(color_system="truecolor")
console.print(build_rich_logo())

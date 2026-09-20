#!/usr/bin/env python3
"""
fbui.py — Interfaz ONYRA dibujada con PIL directamente en /dev/fb0.

Sin pygame, sin SDL, sin KMSDRM. Todo el aspecto visual (boot, selector de
sistemas con recuadro neón animado, lista de juegos con carátula y ficha,
modal de partida guardada) se compone en memoria y se escribe en el
framebuffer sólo en las zonas que cambian. curses se usa únicamente para leer
teclado / mando y para ceder la pantalla al emulador.

Uso desde arcade.py:

    fbui.run(stdscr, fb, games=GAMES, cover_fn=get_game_cover,
             save_fn=get_game_autosave, launch_fn=launch_retro_game,
             poll_fn=poll_input, sound=sound, volume=volume)
"""

import curses
import datetime
import fcntl
import os
import struct
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# PALETA — copia aquí los valores EXACTOS de theme.py de ONYRA
# ─────────────────────────────────────────────────────────────────────────────
BG          = (8, 9, 13)
PANEL       = (14, 17, 23)
PANEL_SEL   = (20, 26, 36)
BORDER      = (38, 44, 58)      # COLOR_BORDER_INACTIVE
MINT        = (61, 255, 192)    # COLOR_MINT   #3DFFC0
VIOLET      = (150, 120, 255)   # COLOR_VIOLET
SHADOW      = (75, 58, 153)     # COLOR_SHADOW #4B3A99
TEXT        = (232, 236, 244)   # COLOR_TEXT
TEXT_DIM    = (128, 138, 156)   # COLOR_TEXT_DIM
SYSTEM_DIM  = (86, 108, 102)    # COLOR_SYSTEM_DIM
DANGER      = (255, 90, 120)

LOGOS_DIR = os.path.expanduser("~/.emulador/cache/logos")

IDLE_MS = 150    # espera de teclado en reposo (no se redibuja nada)
FRAME_MS = 20    # espera durante animaciones (~50 FPS máx.)

# Tarjetas de la pantalla de sistemas (id = nombre del PNG en LOGOS_DIR)
SYSTEM_CARDS = [
    {"id": "snes",      "name": "Super Nintendo", "system": "SNES",       "logos": ["snes", "sfc", "superfamicom"]},
    {"id": "megadrive", "name": "Mega Drive",     "system": "Mega Drive", "logos": ["megadrive", "genesis", "md"]},
    {"id": "nes",       "name": "NES",            "system": "NES",        "logos": ["nes", "famicom"]},
    {"id": "gb",        "name": "Game Boy",       "system": "Game Boy",   "logos": ["gb", "gameboy"]},
    {"id": "pc",        "name": "PC Nativo",      "system": "PC Nativo",  "logos": []},
]

# ─────────────────────────────────────────────────────────────────────────────
# Escala (el diseño de ONYRA está pensado para 1080p)
# ─────────────────────────────────────────────────────────────────────────────
_K = 1.0


def set_scale(fb_h):
    global _K
    _K = max(0.5, min(2.0, fb_h / 1080.0))


def u(n):
    return max(1, int(round(n * _K)))


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de dibujo
# ─────────────────────────────────────────────────────────────────────────────
_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
_FONT_CACHE = {}
_FONT_PATHS = {
    True:  ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
    False: ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"],
}


def font(bold, size):
    key = (bold, size)
    f = _FONT_CACHE.get(key)
    if f is None:
        for p in _FONT_PATHS[bold]:
            try:
                f = ImageFont.truetype(p, size)
                break
            except Exception:
                pass
        if f is None:
            try:
                f = ImageFont.load_default(size)
            except Exception:
                f = ImageFont.load_default()
        _FONT_CACHE[key] = f
    return f


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def panel(d, box, fill, outline, radius, width=1):
    x, y, w, h = box
    d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=radius, fill=fill, outline=outline, width=width)


def fit(d, s, f, maxw):
    if d.textlength(s, font=f) <= maxw:
        return s
    while s and d.textlength(s + "…", font=f) > maxw:
        s = s[:-1]
    return s + "…"


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# Glifos pixel 5x7 (logo ONYRA y "PC")
_GLYPHS = {
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
}


def pixel_text(txt, scale, color, gap=1):
    cols = 5 * len(txt) + gap * (len(txt) - 1)
    im = Image.new("RGBA", (cols * scale, 7 * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 0
    for ch in txt:
        for r, row in enumerate(_GLYPHS[ch]):
            for c, v in enumerate(row):
                if v == "#":
                    d.rectangle([(x + c) * scale, r * scale, (x + c + 1) * scale - 1, (r + 1) * scale - 1],
                                fill=color + (255,))
        x += 5 + gap
    return im


def _tint(alpha, color):
    im = Image.new("RGBA", alpha.size, color + (255,))
    im.putalpha(alpha)
    return im


def load_logo(card, tw, th):
    """Devuelve (versión apagada, versión menta) del logo del sistema."""
    alpha = None
    if card["id"] == "pc":
        alpha = pixel_text("PC", max(4, th // 12), (255, 255, 255), gap=1).getchannel("A")
    else:
        for cand in card.get("logos", []) + [card["id"]]:
            p = os.path.join(LOGOS_DIR, cand + ".png")
            if os.path.isfile(p):
                try:
                    im = Image.open(p).convert("RGBA")
                    bb = im.getchannel("A").getbbox()
                    if bb:
                        im = im.crop(bb)
                    ratio = im.width / float(im.height)
                    fh = th
                    fw = int(fh * ratio)
                    if fw > tw:
                        fw = tw
                        fh = int(fw / ratio)
                    alpha = im.resize((max(1, fw), max(1, fh)), _LANCZOS).getchannel("A")
                    break
                except Exception:
                    alpha = None
    if alpha is None:  # fallback: texto
        f = font(True, u(24))
        tmp = Image.new("L", (u(300), u(40)), 0)
        ImageDraw.Draw(tmp).text((0, 0), card["name"].upper(), font=f, fill=255)
        alpha = tmp.crop(tmp.getbbox() or (0, 0, 1, 1))
    return _tint(alpha, SYSTEM_DIM), _tint(alpha, MINT)


_NEON_CACHE = {}


def neon_box(w, h, r):
    """Recuadro de selección: borde degradado menta→violeta con halo (RGBA)."""
    key = (w, h, r)
    hit = _NEON_CACHE.get(key)
    if hit:
        return hit
    m = u(22)
    W_, H_ = w + 2 * m, h + 2 * m
    box = [m, m, m + w - 1, m + h - 1]

    glow = Image.new("L", (W_, H_), 0)
    ImageDraw.Draw(glow).rounded_rectangle(box, radius=r, outline=255, width=max(3, u(5)))
    glow = glow.filter(ImageFilter.GaussianBlur(u(9))).point(lambda v: int(v * 0.60))

    ring = Image.new("L", (W_, H_), 0)
    ImageDraw.Draw(ring).rounded_rectangle(box, radius=r, outline=255, width=max(2, u(3)))

    grad = Image.new("RGB", (W_, H_))
    gd = ImageDraw.Draw(grad)
    for x in range(W_):
        t = min(1.0, max(0.0, (x - m) / float(max(1, w - 1))))
        gd.line([(x, 0), (x, H_)], fill=lerp(MINT, VIOLET, t))

    out = grad.convert("RGBA")
    out.putalpha(ImageChops.lighter(glow, ring))
    _NEON_CACHE[key] = (out, m)
    return out, m


# ─────────────────────────────────────────────────────────────────────────────
# Framebuffer
# ─────────────────────────────────────────────────────────────────────────────
class FB:
    DEV = "/dev/fb0"

    def __init__(self):
        self.ok = False
        self.fd = None
        self.w = self.h = self.stride = 0
        self._graphics = False
        self.ok = self._open()
        if self.ok:
            set_scale(self.h)

    def _open(self):
        try:
            fd = os.open(self.DEV, os.O_RDWR)
        except Exception:
            return False
        try:
            var = fcntl.ioctl(fd, 0x4600, bytes(160))            # FBIOGET_VSCREENINFO
            xres, yres, _, _, _, _, bpp = struct.unpack("7I", var[:28])
            with open("/sys/class/graphics/fb0/stride") as f:
                stride = int(f.read().strip())
            if bpp != 32 or stride < xres * 4:
                raise OSError("fb no compatible")
        except Exception:
            os.close(fd)
            return False
        self.fd, self.w, self.h, self.stride = fd, xres, yres, stride
        return True

    def write(self, img, x, y):
        if img.mode != "RGB":
            img = img.convert("RGB")
        raw = img.tobytes("raw", "BGRX")
        w, h = img.size
        try:
            if x == 0 and w * 4 == self.stride:
                os.pwrite(self.fd, raw, y * self.stride)
            else:
                row = w * 4
                for j in range(h):
                    os.pwrite(self.fd, raw[j * row:(j + 1) * row], (y + j) * self.stride + x * 4)
        except Exception:
            pass

    def fill(self, color=BG):
        self.write(Image.new("RGB", (self.w, self.h), color), 0, 0)

    def set_graphics(self, on):
        """KD_GRAPHICS: evita que fbcon repinte texto/cursor encima de la UI."""
        try:
            fcntl.ioctl(0, 0x4B3A, 1 if on else 0)               # KDSETMODE
            self._graphics = on
        except Exception:
            pass

    def release(self):
        """Suelta el framebuffer antes de lanzar un emulador."""
        self.set_graphics(False)
        if self.fd is not None:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None

    def acquire(self):
        if self._open():
            self.ok = True
        self.set_graphics(True)

    def close(self):
        self.set_graphics(False)
        if self.fd is not None:
            try:
                self.fill((0, 0, 0))
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None


# ─────────────────────────────────────────────────────────────────────────────
# Pantallas
# ─────────────────────────────────────────────────────────────────────────────
class Screen:
    footer_y_off = 42
    footer_size = 14

    def __init__(self, fb):
        self.W, self.H = fb.w, fb.h
        self.base = None
        self.scene = None
        self.overlay = None       # (RGBA, x, y)
        self.dirty = []
        self.animating = False
        self.help = ""
        self.vol_text = ""

    def mark(self, x, y, w, h):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.W, int(x + w)), min(self.H, int(y + h))
        if x1 > x0 and y1 > y0:
            self.dirty.append((x0, y0, x1 - x0, y1 - y0))

    def full(self):
        self.dirty = []
        self.mark(0, 0, self.W, self.H)

    def update(self, dt):
        pass

    def compose(self, rect):
        x, y, w, h = rect
        reg = self.scene.crop((x, y, x + w, y + h))
        if self.overlay:
            ov, ox, oy = self.overlay
            ix0, iy0 = max(x, ox), max(y, oy)
            ix1, iy1 = min(x + w, ox + ov.width), min(y + h, oy + ov.height)
            if ix1 > ix0 and iy1 > iy0:
                reg = reg.convert("RGBA")
                part = ov.crop((ix0 - ox, iy0 - oy, ix1 - ox, iy1 - oy))
                reg.alpha_composite(part, dest=(ix0 - x, iy0 - y))
        return reg

    def flush(self):
        rects, self.dirty = self.dirty, []
        return [(r[0], r[1], self.compose(r)) for r in rects]

    # Barra de ayuda inferior + volumen
    def redraw_footer(self):
        if self.base is None or getattr(self, "modal", False):
            return
        d = ImageDraw.Draw(self.base)
        y = self.H - u(self.footer_y_off)
        d.rectangle([0, y - u(6), self.W, y + u(30)], fill=BG)
        f = font(False, u(self.footer_size))
        d.text((self.W // 2, y), self.help, font=f, fill=TEXT_DIM, anchor="mt")
        if self.vol_text:
            d.text((self.W - u(40), y), self.vol_text, font=f, fill=MINT, anchor="rt")
        self.mark(0, y - u(6), self.W, u(36))

    def set_vol(self, txt):
        if txt != self.vol_text:
            self.vol_text = txt
            self.redraw_footer()


# ── 1. BOOT ──────────────────────────────────────────────────────────────────
class BootScreen(Screen):
    DURATION = 2.4

    def __init__(self, fb):
        super().__init__(fb)
        self.t = 0.0
        self.finished = False
        self.animating = True
        W, H = self.W, self.H
        scale = max(6, int(H / 120))
        logo = pixel_text("ONYRA", scale, MINT, gap=2)
        pad = scale * 4
        lw, lh = logo.width + 2 * pad, logo.height + 2 * pad
        mask = Image.new("L", (lw, lh), 0)
        mask.paste(logo.getchannel("A"), (pad, pad))
        glow = mask.filter(ImageFilter.GaussianBlur(scale * 1.5)).point(lambda v: int(v * 0.45))
        layer = Image.new("RGB", (lw, lh), BG)
        layer.paste(MINT, (0, 0, lw, lh), glow)
        layer.paste(logo, (pad, pad), logo)
        self.logo_layer = layer
        cx = W // 2
        logo_y = H // 2 - u(40) - logo.height // 2
        self.logo_pos = (cx - lw // 2, logo_y - pad)

        line_w = min(logo.width, u(450))
        line_y = logo_y + logo.height + u(18)
        f = font(True, max(u(16), H // 55))
        sub = "R E T R O   G A M E S"
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        sw = int(probe.textlength(sub, font=f)) + u(30)
        sub_w = max(line_w, sw)
        sub_h = u(14) + f.size + u(10)
        sl = Image.new("RGB", (sub_w, sub_h), BG)
        sd = ImageDraw.Draw(sl)
        sd.line([((sub_w - line_w) // 2, 0), ((sub_w + line_w) // 2, 0)], fill=BORDER)
        sd.text((sub_w // 2, u(14)), sub, font=f, fill=TEXT_DIM, anchor="mt")
        self.sub_layer = sl
        self.sub_pos = (cx - sub_w // 2, line_y)

        self.bar_w = line_w
        self.bar_h = max(3, u(4))
        self.bar_pos = (cx - self.bar_w // 2, logo_y + logo.height + u(75))
        self.bar_grad = Image.new("RGB", (self.bar_w, self.bar_h))
        gd = ImageDraw.Draw(self.bar_grad)
        for x in range(self.bar_w):
            gd.line([(x, 0), (x, self.bar_h)], fill=lerp(SHADOW, MINT, x / float(max(1, self.bar_w - 1))))
        bar_bg = Image.new("RGB", (self.bar_w, self.bar_h), PANEL)
        ImageDraw.Draw(bar_bg).rounded_rectangle([0, 0, self.bar_w - 1, self.bar_h - 1], radius=2, outline=BORDER)
        self.bar_bg = bar_bg
        self.out = [(0, 0, Image.new("RGB", (W, H), BG))]

    def full(self):
        self.out = [(0, 0, Image.new("RGB", (self.W, self.H), BG))]

    def handle(self, action, ch=""):
        self.finished = True

    def update(self, dt):
        if self.finished:
            return
        prev = self.t
        self.t += dt
        if self.t >= self.DURATION:
            self.finished = True
        if prev < 1.0:
            f1 = min(1.0, self.t / 1.0)
            bg = Image.new("RGB", self.logo_layer.size, BG)
            self.out.append((self.logo_pos[0], self.logo_pos[1], Image.blend(bg, self.logo_layer, f1)))
        if self.t >= 0.7 and prev < 1.2:
            f2 = min(1.0, (self.t - 0.7) / 0.5)
            bg = Image.new("RGB", self.sub_layer.size, BG)
            self.out.append((self.sub_pos[0], self.sub_pos[1], Image.blend(bg, self.sub_layer, f2)))
        fw = int(self.bar_w * min(1.0, self.t / self.DURATION))
        bar = self.bar_bg.copy()
        if fw > 0:
            bar.paste(self.bar_grad.crop((0, 0, fw, self.bar_h)), (0, 0))
        self.out.append((self.bar_pos[0], self.bar_pos[1], bar))

    def flush(self):
        o, self.out = self.out, []
        return o


# ── 2. SISTEMAS ──────────────────────────────────────────────────────────────
class SystemsScreen(Screen):
    footer_y_off = 42
    footer_size = 14

    def __init__(self, fb, cards, last_id=None):
        super().__init__(fb)
        W, H = self.W, self.H
        self.help = "[◀ / ▶ / ▲ / ▼] Navegar   [ENTER / A] Elegir Sistema   [ESC / Q / B] Salir"
        self.t0 = time.monotonic()
        self.chosen = None
        self.exit = False

        n0 = (len(cards) + 1) // 2
        self.rows = [cards[:n0], cards[n0:]] if len(cards) > 2 else [cards, []]
        self.rows = [r for r in self.rows if r]

        self.cw = min(u(280), int(W * 0.16))
        self.ch = min(u(170), int(H * 0.17))
        gx, gy = u(36), u(28)
        self.logos = {c["id"]: load_logo(c, self.cw - u(60), self.ch - u(70)) for c in cards}

        self.r = self.c = 0
        for ri, row in enumerate(self.rows):
            for ci, s in enumerate(row):
                if s["id"] == last_id:
                    self.r, self.c = ri, ci

        total_h = len(self.rows) * self.ch + (len(self.rows) - 1) * gy
        sy = (H - total_h) // 2 - u(20)
        self.rects = []
        for ri, row in enumerate(self.rows):
            rw = len(row) * self.cw + (len(row) - 1) * gx
            sx = (W - rw) // 2
            y = sy + ri * (self.ch + gy)
            self.rects.append([(sx + ci * (self.cw + gx), y, self.cw, self.ch) for ci in range(len(row))])
        allr = [rc for row in self.rects for rc in row]
        m = u(30)
        self.grid_rect = (min(r[0] for r in allr) - m, min(r[1] for r in allr) - m,
                          max(r[0] + r[2] for r in allr) - min(r[0] for r in allr) + 2 * m,
                          max(r[1] + r[3] for r in allr) - min(r[1] for r in allr) + 2 * m)
        self.info_y = self.rects[-1][0][1] + self.ch + u(38)

        x0, y0, _, _ = self.rects[self.r][self.c]
        self.cx, self.cy = float(x0), float(y0)
        self._build()
        self._place()
        self.full()

    def _build(self):
        W, H = self.W, self.H
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, u(32)), "O  N  Y  R  A", font=font(True, u(22)), fill=MINT, anchor="mt")
        for ri, row in enumerate(self.rows):
            for ci, s in enumerate(row):
                x, y, w, h = self.rects[ri][ci]
                cur = (ri, ci) == (self.r, self.c)
                panel(d, (x, y, w, h), PANEL, BORDER, u(12))
                dim, mint = self.logos[s["id"]]
                lg = mint if cur else dim
                img.paste(lg, (x + w // 2 - lg.width // 2, y + u(26)), lg)
                d.text((x + w // 2, y + h - u(34)), s["name"].upper(), font=font(True, u(15)),
                       fill=MINT if cur else TEXT_DIM, anchor="mt")
        cur_sys = self.rows[self.r][self.c]
        d.text((W // 2, self.info_y), cur_sys["name"].upper(), font=font(True, u(26)), fill=TEXT, anchor="mt")
        d.text((W // 2, self.info_y + u(36)), f"◆  {cur_sys['count']} JUEGOS DISPONIBLES  ◆",
               font=font(False, u(16)), fill=VIOLET, anchor="mt")
        self.base = self.scene = img
        self.redraw_footer()

    def _place(self):
        img, m = neon_box(self.cw, self.ch, u(14))
        if self.overlay:
            o = self.overlay
            self.mark(o[1], o[2], o[0].width, o[0].height)
        self.overlay = (img, int(round(self.cx)) - m, int(round(self.cy)) - m)
        self.mark(self.overlay[1], self.overlay[2], img.width, img.height)

    def update(self, dt):
        if not self.animating:
            return
        tx, ty, _, _ = self.rects[self.r][self.c]
        f = min(1.0, 18.0 * dt)
        self.cx += (tx - self.cx) * f
        self.cy += (ty - self.cy) * f
        if abs(tx - self.cx) < 0.6 and abs(ty - self.cy) < 0.6:
            self.cx, self.cy = float(tx), float(ty)
            self.animating = False
        self._place()

    def _nav(self):
        self._build()
        self.mark(*self.grid_rect)
        self.mark(0, self.info_y - u(6), self.W, u(80))
        self.animating = True
        return "hit"

    def handle(self, action, ch=""):
        row = self.rows[self.r]
        if action == "LEFT":
            self.c = (self.c - 1) % len(row)
            return self._nav()
        if action == "RIGHT":
            self.c = (self.c + 1) % len(row)
            return self._nav()
        if action == "UP" and self.r > 0:
            self.r -= 1
            self.c = min(self.c, len(self.rows[self.r]) - 1)
            return self._nav()
        if action == "DOWN" and self.r < len(self.rows) - 1:
            self.r += 1
            self.c = min(self.c, len(self.rows[self.r]) - 1)
            return self._nav()
        if action == "ENTER":
            self.chosen = self.rows[self.r][self.c]
            return "coin"
        if action == "BACK" and time.monotonic() - self.t0 > 0.5:
            self.exit = True
        return None


# ── 3. JUEGOS ────────────────────────────────────────────────────────────────
class GamesScreen(Screen):
    footer_y_off = 36
    footer_size = 13

    def __init__(self, fb, sys_title, games, cover_fn=None, save_fn=None, last_idx=0):
        super().__init__(fb)
        W, H = self.W, self.H
        self.help = "[▲ / ▼] Elegir   [ENTER / A] JUGAR   [/] Buscar   [ESC / Q / B] Volver a Sistemas"
        self.title = sys_title.upper()
        self.all = list(games)
        self.games = list(games)
        self.sel = max(0, min(last_idx, len(games) - 1))
        self.cover_fn, self.save_fn = cover_fn, save_fn
        self.query, self.search = "", False
        self.modal, self.modal_opt, self.modal_save = False, 0, None
        self.launch = None
        self.back = False

        pad = u(40)
        py = u(70)
        ph = H - py - u(50)
        lw = int((W - pad * 2 - u(24)) * 0.40)
        rw = W - pad * 2 - u(24) - lw
        self.left = (pad, py, lw, ph)
        self.right = (pad + lw + u(24), py, rw, ph)
        self.ph = ph
        self.item_h = u(48)
        self.search_box = (pad + u(18), py + u(54), lw - u(36), u(36))
        ly = self.search_box[1] + self.search_box[3] + u(14)
        self.list_rect = (pad + u(10), ly, lw - u(20), py + ph - ly - u(16))
        self._rc = {}
        self._row_cache = {}

        self.scroll = 0.0
        self._build()
        self.scroll = self._target()
        self._paste_list()
        self.full()

    # ── geometría del scroll ──
    def _target(self):
        vis = max(1, (self.ph - u(120)) // self.item_h)
        top = max(0, self.sel - vis // 2) * self.item_h
        max_top = max(0, len(self.games) * self.item_h - self.list_rect[3] + u(4))
        return float(min(top, max_top))

    # ── construcción estática ──
    def _build(self):
        W, H = self.W, self.H
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, u(24)), "O  N  Y  R  A", font=font(True, u(20)), fill=MINT, anchor="mt")
        panel(d, self.left, PANEL, BORDER, u(12))
        lx, ly, lw, _ = self.left
        d.text((lx + lw // 2, ly + u(18)), f"◆  {self.title}  ◆", font=font(True, u(18)), fill=MINT, anchor="mt")
        self.base = self.scene = img
        self._draw_search()
        self._paste_list()
        self._paste_right()
        self.redraw_footer()

    def _draw_search(self):
        d = ImageDraw.Draw(self.base)
        x, y, w, h = self.search_box
        panel(d, (x, y, w, h), BG, MINT if self.search else BORDER, u(8))
        col = TEXT_DIM
        ix, iy, s = x + u(14), y + u(11), u(11)
        d.ellipse([ix, iy, ix + s, iy + s], outline=col, width=2)
        d.line([(ix + s - 1, iy + s - 1), (ix + s + u(5), iy + s + u(5))], fill=col, width=2)
        f = font(False, u(14))
        if self.query:
            txt, c = self.query, TEXT
        else:
            txt, c = "Buscar juego (pulsa /)...", TEXT_DIM
        d.text((x + u(38), y + h // 2), fit(d, txt, f, w - u(50)), font=f, fill=c, anchor="lm")
        self.mark(x - 2, y - 2, w + 4, h + 4)

    def _row_img(self, g, selected):
        """Fila de la lista ya renderizada (cacheada: el scroll sólo hace paste)."""
        key = (g.get("id", g["title"]), selected)
        hit = self._row_cache.get(key)
        if hit:
            return hit
        w = self.list_rect[2]
        img = Image.new("RGB", (w, self.item_h), PANEL)
        d = ImageDraw.Draw(img)
        box = (u(6), 0, w - u(12), self.item_h - u(4))
        if selected:
            panel(d, box, PANEL_SEL, MINT, u(8))
            txt, f, c = "▶  " + g["title"], font(True, u(15)), MINT
        else:
            txt, f, c = "   " + g["title"], font(False, u(15)), TEXT_DIM
        d.text((box[0] + u(12), box[3] // 2), fit(d, txt, f, box[2] - u(24)), font=f, fill=c, anchor="lm")
        if len(self._row_cache) > 400:
            self._row_cache.clear()
        self._row_cache[key] = img
        return img

    def _paste_list(self):
        x, y, w, h = self.list_rect
        img = Image.new("RGB", (w, h), PANEL)
        top = int(self.scroll)
        first = max(0, top // self.item_h)
        for idx in range(first, len(self.games)):
            iy = idx * self.item_h - top
            if iy >= h:
                break
            img.paste(self._row_img(self.games[idx], idx == self.sel), (0, iy))
        if not self.games:
            ImageDraw.Draw(img).text((w // 2, u(40)), "Sin resultados", font=font(False, u(15)),
                                     fill=TEXT_DIM, anchor="mt")
        self.base.paste(img, (x, y))
        self.mark(x, y, w, h)

    # ── ficha derecha (cacheada) ──
    def _prep_cover(self, path, max_w, max_h):
        im = Image.open(path).convert("RGBA")
        ratio = im.width / float(im.height)
        fh = max_h
        fw = int(fh * ratio)
        if fw > max_w:
            fw = max_w
            fh = int(fw / ratio)
        im = im.resize((max(1, fw), max(1, fh)), _LANCZOS)
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=u(12), fill=255)
        im.putalpha(mask)
        return im

    def _render_right(self, g):
        key = g.get("id", g["title"])
        hit = self._rc.get(key)
        if hit:
            return hit
        _, _, w, h = self.right
        img = Image.new("RGB", (w, h), BG)
        d = ImageDraw.Draw(img)
        panel(d, (0, 0, w, h), PANEL, BORDER, u(12))

        cover_h = min(u(360), int(h * 0.46))
        max_w = min(u(360), int(w * 0.60))
        max_h = min(u(360), int(h * 0.48), cover_h)
        area = (u(24), u(20), w - u(48), cover_h)
        cov = None
        cp = self.cover_fn(g) if self.cover_fn else None
        if cp:
            try:
                cov = self._prep_cover(cp, max_w, max_h)
            except Exception:
                cov = None
        if cov:
            img.paste(cov, (area[0] + (area[2] - cov.width) // 2, area[1] + (area[3] - cov.height) // 2), cov)
        else:
            cx, cy = area[0] + area[2] // 2, area[1] + area[3] // 2
            panel(d, (cx - u(120), cy - u(100), u(240), u(200)), (18, 22, 30), BORDER, u(12))
            d.text((cx, cy - u(12)), "O N Y R A", font=font(True, u(18)), fill=MINT, anchor="mm")
            d.text((cx, cy + u(16)), "RETRO ARCHIVE", font=font(False, u(12)), fill=TEXT_DIM, anchor="mm")

        x0 = u(36)
        y = area[1] + area[3] + u(16)
        d.text((x0, y), fit(d, g["title"].upper(), font(True, u(24)), w - u(72)),
               font=font(True, u(24)), fill=TEXT)
        y += u(34)

        fl, fv = font(True, u(13)), font(False, u(13))
        c2 = int(w * 0.50)

        def pair(label, val, x, yy, maxw):
            d.text((x, yy), label, font=fl, fill=VIOLET)
            lw_ = d.textlength(label, font=fl) + u(8)
            d.text((x + lw_, yy), fit(d, str(val), fv, maxw - lw_), font=fv, fill=TEXT)

        pair("AÑO:", g.get("year", "N/A"), x0, y, c2 - x0 - u(12))
        pair("GÉNERO:", g.get("genre", "N/A"), c2, y, w - c2 - u(24))
        y += u(24)
        pair("DESARROLLADOR:", g.get("dev", "N/A"), x0, y, c2 - x0 - u(12))
        pair("SISTEMA:", g.get("system", "N/A"), c2, y, w - c2 - u(24))
        y += u(30)
        d.line([(x0, y), (w - x0, y)], fill=BORDER)
        y += u(14)

        fc = font(False, u(13))
        ctrl_lines = wrap(d, g.get("controls", ""), fc, w - u(72))[:3]
        block_h = (u(20) + len(ctrl_lines) * u(19)) if ctrl_lines else 0
        ctrl_y = h - block_h - u(22)

        fd = font(False, u(14))
        lines = wrap(d, g.get("desc", ""), fd, w - u(72))
        n = max(1, (ctrl_y - u(10) - y) // u(21))
        if len(lines) > n:
            lines = lines[:n]
            lines[-1] = fit(d, lines[-1] + "…", fd, w - u(72))
        for ln in lines:
            d.text((x0, y), ln, font=fd, fill=TEXT_DIM)
            y += u(21)

        if ctrl_lines:
            d.text((x0, ctrl_y), "MANDOS:", font=font(True, u(12)), fill=MINT)
            for i, ln in enumerate(ctrl_lines):
                d.text((x0, ctrl_y + u(20) + i * u(19)), ln, font=fc, fill=TEXT_DIM)

        if len(self._rc) > 24:
            self._rc.clear()
        self._rc[key] = img
        return img

    def _paste_right(self):
        x, y, w, h = self.right
        if self.games:
            img = self._render_right(self.games[self.sel])
        else:
            img = Image.new("RGB", (w, h), BG)
            d = ImageDraw.Draw(img)
            panel(d, (0, 0, w, h), PANEL, BORDER, u(12))
        self.base.paste(img, (x, y))
        self.mark(x, y, w, h)

    # ── modal de partida guardada ──
    def _open_modal(self, save_file):
        self.modal, self.modal_opt, self.modal_save = True, 0, save_file
        dark = Image.blend(self.base, Image.new("RGB", self.base.size, BG), 0.82)
        self.modal_bg = dark
        self.scene = dark
        self._draw_dialog()
        self.full()

    def _close_modal(self):
        self.modal = False
        self.scene = self.base
        self.full()

    def _draw_dialog(self):
        d = ImageDraw.Draw(self.scene)
        dw, dh = u(640), u(320)
        dx, dy = (self.W - dw) // 2, (self.H - dh) // 2
        panel(d, (dx, dy, dw, dh), PANEL, VIOLET, u(16), width=2)
        cx = dx + dw // 2
        d.text((cx, dy + u(30)), "★  PARTIDA GUARDADA DETECTADA  ★", font=font(True, u(20)), fill=VIOLET, anchor="mt")
        gname = fit(d, self.games[self.sel]["title"], font(True, u(18)), dw - u(80))
        d.text((cx, dy + u(68)), f"[ {gname} ]", font=font(True, u(18)), fill=MINT, anchor="mt")
        try:
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(self.modal_save)).strftime("%d/%m/%Y a las %H:%M")
        except Exception:
            ts = "N/A"
        d.text((cx, dy + u(98)), f"Última instantánea: {ts}", font=font(False, u(14)), fill=TEXT_DIM, anchor="mt")

        def btn(y_off, label, active, color):
            box = (dx + u(50), dy + y_off, dw - u(100), u(48))
            col = color if active else TEXT_DIM
            panel(d, box, PANEL_SEL if active else (14, 17, 22), col, u(10), width=2 if active else 1)
            d.text((box[0] + box[2] // 2, box[1] + box[3] // 2), label, font=font(True, u(15)), fill=col, anchor="mm")

        btn(u(145), "▶  1. REANUDAR PARTIDA  (Continuar donde lo dejaste)", self.modal_opt == 0, MINT)
        btn(u(205), "▶  2. EMPEZAR DE NUEVO  (Reiniciar desde el inicio)", self.modal_opt == 1, DANGER)
        d.text((cx, dy + dh - u(36)), "[▲ / ▼] Elegir   [ENTER] Confirmar   [ESC / Q] Cancelar",
               font=font(False, u(13)), fill=TEXT_DIM, anchor="mt")
        self.mark(dx, dy, dw, dh)

    def _handle_modal(self, action, ch):
        if action in ("UP", "LEFT", "OPT1"):
            self.modal_opt = 0
        elif action in ("DOWN", "RIGHT", "OPT2"):
            self.modal_opt = 1
        elif action == "BACK":
            self._close_modal()
            return "hit"
        if action in ("ENTER", "OPT1", "OPT2"):
            g = self.games[self.sel]
            restart = self.modal_opt == 1
            self._close_modal()
            self.launch = (g, restart)
            return "explosion" if restart else "coin"
        self._draw_dialog()
        return "hit"

    # ── lógica ──
    def _changed(self):
        self.animating = True
        self._paste_list()
        self._paste_right()

    def _apply_filter(self):
        q = self.query.strip().lower()
        if not q:
            self.games = list(self.all)
        else:
            self.games = [g for g in self.all
                          if q in g["title"].lower() or q in g.get("genre", "").lower()
                          or q in g.get("dev", "").lower()]
        self.sel = 0
        self._draw_search()
        self._changed()

    def update(self, dt):
        if self.modal or not self.animating:
            return
        tgt = self._target()
        self.scroll += (tgt - self.scroll) * min(1.0, 16.0 * dt)
        if abs(tgt - self.scroll) < 0.5:
            self.scroll = tgt
            self.animating = False
        self._paste_list()

    def handle(self, action, ch=""):
        if self.modal:
            return self._handle_modal(action, ch)
        n = len(self.games)
        if action == "UP" and self.sel > 0:
            self.sel -= 1
            self._changed()
            return "hit"
        if action == "DOWN" and self.sel < n - 1:
            self.sel += 1
            self._changed()
            return "hit"
        if action == "LEFT" and n:
            self.sel = max(0, self.sel - 6)
            self._changed()
            return "hit"
        if action == "RIGHT" and n:
            self.sel = min(n - 1, self.sel + 6)
            self._changed()
            return "hit"
        if action == "SEARCH":
            self.search = True
            self._draw_search()
            return "bonus"
        if action == "CHAR" and self.search:
            self.query += ch
            self._apply_filter()
            return None
        if action == "BACKSPACE" and self.search and self.query:
            self.query = self.query[:-1]
            self._apply_filter()
            return None
        if action == "BACK":
            if self.search or self.query:
                self.search, self.query = False, ""
                self._apply_filter()
                return "hit"
            self.back = True
            return "hit"
        if action == "ENTER":
            if self.search:
                self.search = False
                self._draw_search()
                return None
            if not n:
                return None
            g = self.games[self.sel]
            sf = self.save_fn(g) if self.save_fn else None
            if sf:
                self._open_modal(sf)
                return "bonus"
            self.launch = (g, False)
            return "coin"
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Entrada: curses → acciones
# ─────────────────────────────────────────────────────────────────────────────
def key_to_action(k, searching=False):
    if k in (None, -1):
        return None, ""
    if k == curses.KEY_UP:
        return "UP", ""
    if k == curses.KEY_DOWN:
        return "DOWN", ""
    if k == curses.KEY_LEFT:
        return "LEFT", ""
    if k == curses.KEY_RIGHT:
        return "RIGHT", ""
    if k in (curses.KEY_BACKSPACE, 127, 8):
        return "BACKSPACE", ""
    if k in (10, 13, curses.KEY_ENTER):
        return "ENTER", ""
    if k == 27:
        return "BACK", ""
    if searching:
        if 32 <= k < 127:
            return "CHAR", chr(k)
        return None, ""
    if k in (ord("w"), ord("W")):
        return "UP", ""
    if k in (ord("s"), ord("S")):
        return "DOWN", ""
    if k in (ord("a"), ord("A")):
        return "LEFT", ""
    if k in (ord("d"), ord("D")):
        return "RIGHT", ""
    if k == ord(" "):
        return "ENTER", ""
    if k in (ord("q"), ord("Q")):
        return "BACK", ""
    if k == ord("/"):
        return "SEARCH", ""
    if k == ord("1"):
        return "OPT1", ""
    if k == ord("2"):
        return "OPT2", ""
    return None, ""


# ─────────────────────────────────────────────────────────────────────────────
# Bucle principal
# ─────────────────────────────────────────────────────────────────────────────
def run(stdscr, fb, games, cover_fn=None, save_fn=None, launch_fn=None, poll_fn=None,
        sound=None, volume=None, skip_boot=False):

    def play(name):
        if sound and name:
            try:
                sound.play(name)
            except Exception:
                pass

    def vol_txt():
        try:
            return ("VOL " + volume.format_volume_bar(6)) if volume else ""
        except Exception:
            return ""

    poll = poll_fn or (lambda s: s.getch())

    try:
        curses.curs_set(0)
    except Exception:
        pass
    stdscr.clear()
    stdscr.refresh()          # una sola vez, ANTES de pintar en el framebuffer
    fb.set_graphics(True)
    fb.fill(BG)

    if volume:
        try:
            volume.init_arcade_volume()
            volume.start_listener()
        except Exception:
            pass

    cards = []
    for c in SYSTEM_CARDS:
        n = sum(1 for g in games if g["system"] == c["system"])
        if n:
            cards.append(dict(c, count=n))
    last_sel = {}
    last_sys = [None]

    def new_systems():
        s = SystemsScreen(fb, cards, last_sys[0])
        s.set_vol(vol_txt())
        return s

    def new_games(card):
        gl = [g for g in games if g["system"] == card["system"]]
        s = GamesScreen(fb, card["name"], gl, cover_fn, save_fn, last_sel.get(card["id"], 0))
        s.set_vol(vol_txt())
        s.card = card
        return s

    def run_game(game, restart):
        if restart and save_fn:
            sf = save_fn(game)
            if sf:
                try:
                    os.remove(sf)
                except OSError:
                    pass
        fb.release()
        try:
            launch_fn(stdscr, game)
        finally:
            fb.acquire()
            try:
                curses.flushinp()
                curses.curs_set(0)
            except Exception:
                pass

    screen = new_systems() if skip_boot else BootScreen(fb)
    play("coin")
    last, prev_anim = time.monotonic(), False

    try:
        while True:
            now = time.monotonic()
            dt = min(0.1, now - last) if prev_anim else 1.0 / 30
            last = now
            screen.update(dt)
            for x, y, img in screen.flush():
                fb.write(img, x, y)
            prev_anim = screen.animating

            # ── transiciones ──
            if isinstance(screen, BootScreen):
                if screen.finished:
                    screen = new_systems()
                    continue
            elif isinstance(screen, SystemsScreen):
                if screen.exit:
                    break
                if screen.chosen:
                    card = screen.chosen
                    last_sys[0] = card["id"]
                    screen = new_games(card)
                    continue
            elif isinstance(screen, GamesScreen):
                if screen.launch:
                    game, restart = screen.launch
                    screen.launch = None
                    run_game(game, restart)
                    screen.full()
                    last, prev_anim = time.monotonic(), False
                    continue
                if screen.back:
                    last_sel[screen.card["id"]] = screen.sel
                    screen = new_systems()
                    continue

            stdscr.timeout(FRAME_MS if screen.animating else IDLE_MS)
            k = poll(stdscr)
            if k in (-1, None):
                continue

            if isinstance(screen, BootScreen):
                screen.handle("ANY")
                continue

            searching = getattr(screen, "search", False)
            if not searching and not getattr(screen, "modal", False):
                if k in (ord("+"), ord("=")) and volume:
                    volume.set_volume_delta(+5); play("hit"); screen.set_vol(vol_txt()); continue
                if k in (ord("-"), ord("_")) and volume:
                    volume.set_volume_delta(-5); play("hit"); screen.set_vol(vol_txt()); continue
                if k in (ord("m"), ord("M")) and volume:
                    volume.toggle_mute(); play("hit"); screen.set_vol(vol_txt()); continue
                if k in (ord("c"), ord("C"), ord("5")):
                    play("coin"); continue

            action, ch = key_to_action(k, searching)
            if action:
                play(screen.handle(action, ch))
    finally:
        pass  # arcade.main() se encarga de parar el listener de volumen y restaurar la consola

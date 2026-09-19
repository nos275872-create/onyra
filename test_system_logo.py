import os
import requests
from PIL import Image
from rich.text import Text
from rich.style import Style
from rich.console import Console

CACHE_DIR = "/home/jcgar/.emulador/cache/logos"
os.makedirs(CACHE_DIR, exist_ok=True)

SYSTEM_URLS = {
    "snes": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Nintendo%20-%20Super%20Nintendo%20Entertainment%20System.png",
    "megadrive": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Sega%20-%20Mega%20Drive%20-%20Genesis.png",
    "nes": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Nintendo%20-%20Nintendo%20Entertainment%20System.png",
    "gb": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/Nintendo%20-%20Game%20Boy.png",
    "pc": "https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png/DOS.png",
}

# Paleta ONYRA
BG = (0x08, 0x09, 0x0D)
PANEL_BG = (0x0E, 0x11, 0x16)
MINT = (0x3D, 0xFF, 0xC0)
DIM_MINT_GRAY = (0x4E, 0x6E, 0x68)

def download_logos():
    for sys_name, url in SYSTEM_URLS.items():
        dest = os.path.join(CACHE_DIR, f"{sys_name}.png")
        if not os.path.exists(dest):
            r = requests.get(url, timeout=10)
            with open(dest, "wb") as f:
                f.write(r.content)

def render_logo_to_text(png_path, target_height_chars=4, max_width_chars=20, selected=False, bg_color=PANEL_BG):
    """
    Convierte la imagen PNG transparente a un Rich Text con medios bloques.
    target_height_chars: altura en caracteres (cada línea = 2 píxeles de alto)
    """
    img = Image.open(png_path).convert("RGBA")
    
    # Recortar espacios vacíos transparentes alrededor
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    orig_w, orig_h = img.size
    pixel_h = target_height_chars * 2
    pixel_w = int(orig_w * (pixel_h / orig_h))
    
    if pixel_w > max_width_chars:
        pixel_w = max_width_chars
        pixel_h = int(orig_h * (pixel_w / orig_w))
        # Asegurar paridad
        if pixel_h % 2 != 0:
            pixel_h += 1

    img = img.resize((pixel_w, pixel_h), Image.Resampling.LANCZOS)
    
    tint_color = MINT if selected else DIM_MINT_GRAY
    
    # Render a rich Text
    res = Text()
    num_rows = pixel_h // 2
    
    # Asegurar centrado horizontal
    pad_left = (max_width_chars - pixel_w) // 2
    pad_right = max_width_chars - pixel_w - pad_left
    
    for row in range(num_rows):
        if pad_left > 0:
            res.append(" " * pad_left, style=Style(bgcolor=f"#{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}"))
            
        y_top = row * 2
        y_bot = y_top + 1
        
        for x in range(pixel_w):
            top_p = img.getpixel((x, y_top))
            bot_p = img.getpixel((x, y_bot))
            
            # top alpha y bot alpha
            alpha_top = top_p[3] / 255.0
            alpha_bot = bot_p[3] / 255.0
            
            # Mezclar con bg_color
            top_c = (
                int(bg_color[0] * (1 - alpha_top) + tint_color[0] * alpha_top),
                int(bg_color[1] * (1 - alpha_top) + tint_color[1] * alpha_top),
                int(bg_color[2] * (1 - alpha_top) + tint_color[2] * alpha_top),
            )
            bot_c = (
                int(bg_color[0] * (1 - alpha_bot) + tint_color[0] * alpha_bot),
                int(bg_color[1] * (1 - alpha_bot) + tint_color[1] * alpha_bot),
                int(bg_color[2] * (1 - alpha_bot) + tint_color[2] * alpha_bot),
            )
            
            res.append("▀", style=Style(
                color=f"#{top_c[0]:02x}{top_c[1]:02x}{top_c[2]:02x}",
                bgcolor=f"#{bot_c[0]:02x}{bot_c[1]:02x}{bot_c[2]:02x}"
            ))
            
        if pad_right > 0:
            res.append(" " * pad_right, style=Style(bgcolor=f"#{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}"))
            
        if row < num_rows - 1:
            res.append("\n")
            
    return res

if __name__ == "__main__":
    download_logos()
    console = Console(color_system="truecolor")
    for s in SYSTEM_URLS:
        p = os.path.join(CACHE_DIR, f"{s}.png")
        print(f"--- Sistema: {s.upper()} (Reposo) ---")
        console.print(render_logo_to_text(p, selected=False))
        print(f"--- Sistema: {s.upper()} (Seleccionado) ---")
        console.print(render_logo_to_text(p, selected=True))

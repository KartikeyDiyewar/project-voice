"""
Vector Icon Provider for Project Voice
Generates razor-sharp, anti-aliased monochrome line icons directly in memory
using high-resolution supersampled PIL vector rendering.
Eliminates OS emoji font inconsistencies and provides 100% pixel-perfect
Windows 11 Fluent icons across all display scaling levels (100%, 125%, 150%, 200%).
"""

import math
from PIL import Image, ImageDraw
import customtkinter as ctk

_icon_cache = {}

def get_icon(name: str, color: str = "#475569", size: tuple[int, int] = (18, 18)) -> ctk.CTkImage:
    """
    Returns a cached CTkImage with crisp vector drawing for the given icon name and tint.
    Available names:
    - 'home', 'voice', 'shortcuts', 'settings', 'about'
    - 'bell', 'wave', 'windows', 'play', 'words'
    """
    cache_key = (name, color, size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    # Render at 48x48 (high-res supersampling for 18x18 display)
    canvas_size = 48
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if name == "home":
        # Clean architectural home outline
        d.polygon([(24, 7), (7, 21), (11, 21), (11, 41), (37, 41), (37, 21), (41, 21)], outline=color, width=3)
        d.rectangle([19, 27, 29, 41], outline=color, width=2)

    elif name in ("voice", "mic"):
        # Modern podcast/dictation microphone
        d.rounded_rectangle([18, 7, 30, 26], radius=6, outline=color, width=3)
        d.arc([11, 14, 37, 32], start=0, end=180, fill=color, width=3)
        d.line([24, 32, 24, 41], fill=color, width=3)
        d.line([16, 41, 32, 41], fill=color, width=3)

    elif name == "shortcuts":
        # Grid/keyboard layout icon
        d.rounded_rectangle([7, 12, 41, 36], radius=5, outline=color, width=3)
        d.line([14, 20, 18, 20], fill=color, width=2)
        d.line([22, 20, 26, 20], fill=color, width=2)
        d.line([30, 20, 34, 20], fill=color, width=2)
        d.line([16, 28, 32, 28], fill=color, width=2)

    elif name == "settings":
        # 6-tooth mechanical cog
        d.ellipse([14, 14, 34, 34], outline=color, width=3)
        d.ellipse([20, 20, 28, 28], outline=color, width=2)
        for angle in [0, 60, 120, 180, 240, 300]:
            rad = math.radians(angle)
            x1, y1 = 24 + 13 * math.cos(rad), 24 + 13 * math.sin(rad)
            x2, y2 = 24 + 18 * math.cos(rad), 24 + 18 * math.sin(rad)
            d.line([x1, y1, x2, y2], fill=color, width=4)

    elif name == "about":
        # Minimal info circle with 'i'
        d.ellipse([8, 8, 40, 40], outline=color, width=3)
        d.ellipse([22, 14, 26, 18], fill=color)
        d.line([24, 22, 24, 34], fill=color, width=3)

    elif name == "bell":
        # Notification chime bell
        d.arc([12, 12, 36, 36], start=180, end=360, fill=color, width=3)
        d.line([12, 24, 8, 34], fill=color, width=3)
        d.line([36, 24, 40, 34], fill=color, width=3)
        d.line([8, 34, 40, 34], fill=color, width=3)
        d.arc([21, 33, 27, 39], start=0, end=180, fill=color, width=3)

    elif name == "wave":
        # 4 vertical equalizer bars
        bars = [(10, 18, 30), (19, 10, 38), (28, 14, 34), (37, 20, 28)]
        for bx, y1, y2 in bars:
            d.line([bx, y1, bx, y2], fill=color, width=3)

    elif name == "windows":
        # 4-tile Windows 11 logo
        d.rectangle([9, 9, 21, 21], fill=color)
        d.rectangle([25, 9, 37, 21], fill=color)
        d.rectangle([9, 25, 21, 37], fill=color)
        d.rectangle([25, 25, 37, 37], fill=color)

    elif name == "play":
        # Equilateral play triangle
        d.polygon([(14, 10), (38, 24), (14, 38)], fill=color)

    elif name == "words":
        # Dictionary / vocabulary keyboard badge
        d.rounded_rectangle([7, 12, 41, 36], radius=5, outline=color, width=3)
        d.line([14, 24, 34, 24], fill=color, width=2)
        d.line([14, 20, 22, 20], fill=color, width=2)
        d.line([26, 20, 34, 20], fill=color, width=2)

    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
    _icon_cache[cache_key] = ctk_img
    return ctk_img

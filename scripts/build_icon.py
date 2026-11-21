"""
Builds the Project Voice application icon.

The shipped icon was a 64px blue glyph upscaled by Windows, which is why it
looked blocky in Explorer and on the installer. This generates every size
Windows actually asks for, at native resolution, in the brand accent.

Design: a warm-paper (or accent) rounded square carrying the same mic glyph the
dashboard draws, so the taskbar icon, the window icon and the in-app logo all
agree.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(r"C:\Users\diyew\OneDrive\Desktop\projects\project-voice\assets\icon.ico")

# Brand tokens (must match ui/theme.py LIGHT/DARK accent)
ACCENT = (196, 65, 50, 255)          # #C44132
ACCENT_DARK = (179, 37, 23, 255)     # #B32517
PAPER = (249, 245, 242, 255)         # #F9F5F2
GLYPH = (255, 255, 255, 255)

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
SS = 8  # supersample factor


def rounded_square(size: int, radius_ratio: float = 0.225) -> Image.Image:
    """Accent tile with a soft vertical gradient and rounded corners."""
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    r = int(big * radius_ratio)
    # gradient body, drawn in horizontal bands so corners stay smooth
    for y in range(big):
        t = y / max(1, big - 1)
        colour = tuple(
            round(ACCENT[i] + (ACCENT_DARK[i] - ACCENT[i]) * t) for i in range(3)
        ) + (255,)
        d.rounded_rectangle([0, y, big - 1, big - 1 + y], radius=r, fill=colour)

    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=r, fill=255)
    img.putalpha(mask)
    return img


def draw_mic(img: Image.Image):
    """White microphone, drawn as vector-ish geometry then antialiased down."""
    big = img.size[0]
    d = ImageDraw.Draw(img)
    s = big / 100.0  # work in a 100-unit design grid

    def box(x0, y0, x1, y1):
        return [x0 * s, y0 * s, x1 * s, y1 * s]

    # capsule: the body of the mic, deliberately narrow so the cradle can pass
    # either side of it without touching
    d.rounded_rectangle(box(39, 18, 61, 50), radius=11 * s, fill=GLYPH)
    # cradle: lower half-ring, opened up so it clears the capsule
    d.arc(box(24, 30, 76, 70), start=20, end=160, fill=GLYPH, width=int(6.5 * s))
    # stem
    d.rounded_rectangle(box(47, 68, 53, 78), radius=3 * s, fill=GLYPH)
    # base
    d.rounded_rectangle(box(36, 76, 64, 82), radius=3 * s, fill=GLYPH)


def make(size: int) -> Image.Image:
    img = rounded_square(size)
    draw_mic(img)
    return img.resize((size, size), Image.LANCZOS)


def main():
    frames = [make(s) for s in SIZES]
    # Pillow writes every supplied size as its own ICO frame.
    frames[-1].save(OUT, format="ICO",
                    sizes=[(s, s) for s in SIZES],
                    append_images=frames[:-1])
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    for s, f in zip(SIZES, frames):
        print(f"  {s}x{s}")


if __name__ == "__main__":
    main()

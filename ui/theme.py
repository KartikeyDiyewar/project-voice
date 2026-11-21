"""
Project Voice - Design Tokens
Single source of truth for colour, type, spacing and geometry.

Palette authored in OKLCH: neutrals are tinted warm (hue 58-62) so surfaces
feel related rather than dead grey, and the accent is a burnt terracotta
(hue 30) instead of the default tech blue. Light is "warm paper", dark is
"espresso ink". Equal lightness steps, clamped chroma at the extremes.
"""

import customtkinter as ctk
from config.settings import settings

LIGHT = {
    "canvas":        "#F9F5F2",
    "sidebar":       "#F2ECE8",
    "surface":       "#FFFDFC",
    "surface_sunk":  "#F4F0ED",
    "ink":           "#211A16",
    "ink_raised":    "#2E2723",
    "ink_border":    "#463D37",
    "on_ink":        "#F5F1EE",
    "on_ink_muted":  "#B5ABA4",
    "text":          "#26201C",
    "text_muted":    "#5D554F",
    "text_subtle":   "#6E6660",
    "border":        "#E2DCD8",
    "border_strong": "#CDC6C1",
    "switch_off":    "#CFC7C1",
    "switch_knob":   "#FFFFFF",
    "accent":        "#C44132",
    "accent_hover":  "#B32517",
    "accent_soft":   "#FFE8E3",
    "accent_text":   "#B63325",
    "success":       "#2D7546",
    "success_soft":  "#DBF2E0",
    "warning":       "#BA7E23",
    "warning_soft":  "#FCEED6",
    "danger":        "#C72D2E",
    "danger_soft":   "#FFE7E4",
}

DARK = {
    "canvas":        "#110E0B",
    "sidebar":       "#171310",
    "surface":       "#1E1A17",
    "surface_sunk":  "#191512",
    "ink":           "#0C0A08",
    "ink_raised":    "#241F1B",
    "ink_border":    "#3C3530",
    "on_ink":        "#F3EFEC",
    "on_ink_muted":  "#A79E97",
    "text":          "#F1EEEC",
    "text_muted":    "#B8B1AB",
    "text_subtle":   "#8F8881",
    "border":        "#2F2A27",
    "border_strong": "#423C37",
    "switch_off":    "#4A423C",
    "switch_knob":   "#F1EEEC",
    "accent":        "#EC715F",
    "accent_hover":  "#FF826F",
    "accent_soft":   "#3A1E19",
    "accent_text":   "#FF9685",
    "success":       "#6CC185",
    "success_soft":  "#132819",
    "warning":       "#E5AC4C",
    "warning_soft":  "#34250B",
    "danger":        "#F7655E",
    "danger_soft":   "#3D1D1A",
}

# 1-4-9 rhythm: every gap is a multiple of 4px, section breaks at 36.
GAP = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 36}

RADIUS = {"card": 14, "control": 10, "pill": 8}

DISPLAY_FONT = "Segoe UI Variable Display"
TEXT_FONT = "Segoe UI Variable Text"
MONO_FONT = "Cascadia Mono"

_fonts_resolved = False


def _resolve_fonts():
    """Pick real installed families once Tk exists; avoids silent Tk fallback."""
    global DISPLAY_FONT, TEXT_FONT, MONO_FONT, _fonts_resolved
    if _fonts_resolved:
        return
    try:
        from tkinter import font as tkfont
        available = set(tkfont.families())
    except Exception:
        return
    _fonts_resolved = True
    if "Segoe UI Variable Display" not in available:
        DISPLAY_FONT = "Segoe UI" if "Segoe UI" in available else "Tahoma"
        TEXT_FONT = "Segoe UI" if "Segoe UI" in available else "Tahoma"
    if "Cascadia Mono" not in available:
        MONO_FONT = "Consolas" if "Consolas" in available else "Courier New"


_session_mode = "light"


def init_mode():
    """Apply the saved appearance, falling back to light when nothing is stored."""
    global _session_mode
    _session_mode = "dark" if settings.appearance == "dark" else "light"
    return _session_mode


def mode() -> str:
    return _session_mode


def set_mode(new_mode: str, persist: bool = True):
    """Switch appearance and remember the choice across launches."""
    global _session_mode
    _session_mode = "dark" if str(new_mode).lower() == "dark" else "light"
    if persist:
        settings.update_settings({"appearance": _session_mode})
    return _session_mode


init_mode()


def t(key: str) -> str:
    """Resolve a semantic colour role for the current appearance."""
    table = DARK if mode() == "dark" else LIGHT
    return table.get(key, LIGHT.get(key, "#FF00FF"))


def on_ink(key: str) -> str:
    """Roles for surfaces that are always dark (the floating pill, hero band)."""
    return DARK.get(key, "#FF00FF")


def font(size: int, weight: str = "normal", family: str | None = None) -> ctk.CTkFont:
    _resolve_fonts()
    if family is None:
        family = DISPLAY_FONT if size >= 17 else TEXT_FONT
    return ctk.CTkFont(family=family, size=size, weight=weight)


def mono(size: int, weight: str = "normal") -> ctk.CTkFont:
    _resolve_fonts()
    return ctk.CTkFont(family=MONO_FONT, size=size, weight=weight)

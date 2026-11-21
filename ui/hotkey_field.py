"""
Hotkey capture field.

Replaces the fixed dropdown with a click-to-record field, the way Discord and
other voice apps let you bind a key: click, press the chord you want, and it is
stored. Escape cancels, Backspace clears back to the default.

The recorder listens through pynput for real key events, so it accepts any single
key or combination, and it normalises the result into the same "ctrl+space"
string the rest of the app already uses.
"""

import threading
import tkinter as tk

from pynput import keyboard

from ui import theme

# Modifier key names, in the order they are written into the chord string.
MODIFIERS = {
    "ctrl": "ctrl",
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "shift": "shift",
    "shift_l": "shift",
    "shift_r": "shift",
    "alt": "alt",
    "alt_l": "alt",
    "alt_r": "alt",
    "alt_gr": "alt",
    "cmd": "win",
    "cmd_l": "win",
    "cmd_r": "win",
}

# Keys that are only readable in a nice form.
SPECIAL = {
    "space": "space",
    "tab": "tab",
    "enter": "enter",
    "esc": "escape",
    "backspace": "backspace",
    "delete": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "page_up": "page_up",
    "page_down": "page_down",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "caps_lock": "caps_lock",
    "num_lock": "num_lock",
    "scroll_lock": "scroll_lock",
    "print_screen": "print_screen",
    "pause": "pause",
}


def _key_token(key) -> str | None:
    """Converts a pynput key into a stable token, or None if unusable."""
    name = getattr(key, "name", None)
    if name:
        if name in MODIFIERS:
            return MODIFIERS[name]
        if name in SPECIAL:
            return SPECIAL[name]
        if name.startswith("f") and name[1:].isdigit():
            return name
    char = getattr(key, "char", None)
    if char and char.isprintable() and char.strip():
        return char.lower()
    return None


def pretty(chord: str) -> str:
    """ctrl+shift+space -> Ctrl + Shift + Space"""
    parts = [p for p in chord.split("+") if p]
    out = []
    for p in parts:
        if p in ("ctrl", "shift", "alt", "win"):
            out.append(p.capitalize())
        elif p == "space":
            out.append("Space")
        elif len(p) == 1:
            out.append(p.upper())
        else:
            out.append(p.upper() if p.startswith("f") and p[1:].isdigit() else p.capitalize())
    return " + ".join(out)


class HotkeyField(tk.Canvas):
    """A click-to-record key field, styled to sit inside the settings surface."""

    W, H = 232, 40

    def __init__(self, master, chord: str, on_change, bg=None):
        bg = bg or theme.t("canvas")
        super().__init__(master, width=self.W, height=self.H, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.chord = chord
        self.on_change = on_change
        self._hover = False
        self._recording = False
        self._listener = None
        self._pending_mods = []
        self._bg = bg

        self.bind("<Button-1>", lambda _e: self.start_recording())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Destroy>", lambda _e: self.cancel_recording())
        self._render()

    # -- appearance ---------------------------------------------------------
    def _set_hover(self, on: bool):
        self._hover = on
        self._render()

    def _round_rect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0 + r, x1, y1 - r,
               x1 - r, y1, x0 + r, y1, x0, y1 - r, x0, y0 + r]
        return self.create_polygon(pts, smooth=True, **kw)

    def _render(self):
        self.delete("all")
        recording = self._recording
        hover = self._hover

        if recording:
            fill = theme.t("accent_soft")
            border = theme.t("accent")
            text_colour = theme.t("accent_text")
            label = "Press a key or chord…"
        else:
            # Always use the sunken surface plus a strong border so the field
            # separates from the card in both themes, including dark.
            fill = theme.t("surface_sunk")
            border = theme.t("accent") if hover else theme.t("border_strong")
            text_colour = theme.t("text")
            label = pretty(self.chord)

        # Draw the filled shape, then an outline shape with no fill on top. The
        # outline must be its own item: a smoothed polygon ignores an outline
        # colour passed alongside a fill.
        self._round_rect(1, 1, self.W - 1, self.H - 1, 9,
                         fill=fill, outline=fill)
        self._round_rect(2, 2, self.W - 2, self.H - 2, 8,
                         fill="", outline=border, width=2 if recording else 1)

        self.create_text(14, self.H / 2, anchor="w", text=label,
                         fill=text_colour, font=theme.mono(12, "bold"))

        # small action glyph on the right
        if recording:
            self.create_oval(self.W - 22, self.H / 2 - 4, self.W - 14, self.H / 2 + 4,
                             fill=theme.t("accent"), outline="")
        else:
            self.create_text(self.W - 14, self.H / 2, anchor="e", text="✎",
                             fill=theme.t("text_subtle"), font=theme.font(11))

    # -- capture ------------------------------------------------------------
    def start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._pending_mods = []
        self._render()
        self.focus_set()
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def cancel_recording(self):
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        if self._recording:
            self._recording = False
            try:
                self._render()
            except Exception:
                pass

    def _stop_listener(self):
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _on_press(self, key):
        token = _key_token(key)
        if token is None:
            return

        # Escape cancels, Backspace resets to the shipped default.
        if token == "escape":
            self.after(0, self.cancel_recording)
            return
        if token == "backspace":
            self.after(0, lambda: self._commit("ctrl+space"))
            return

        if token in ("ctrl", "shift", "alt", "win"):
            if token not in self._pending_mods:
                self._pending_mods.append(token)
            mods = self._pending_mods
            self.after(0, lambda: self._render_pending(mods))
            return

        mods = list(self._pending_mods)
        self.after(0, lambda: self._commit("+".join(mods + [token])))

    def _on_release(self, key):
        token = _key_token(key)
        if token in ("ctrl", "shift", "alt", "win") and token in self._pending_mods:
            self._pending_mods.remove(token)
            if not self._pending_mods and not self._recording:
                return

    def _render_pending(self, mods):
        if not self._recording:
            return
        label = " + ".join(m.capitalize() for m in mods) + " + …"
        self.delete("all")
        self._round_rect(1, 1, self.W - 1, self.H - 1, 9,
                         fill=theme.t("accent_soft"), outline="")
        self._round_rect(1, 1, self.W - 1, self.H - 1, 9,
                         fill="", outline=theme.t("accent"), width=2)
        self.create_text(14, self.H / 2, anchor="w", text=label,
                         fill=theme.t("accent_text"), font=theme.mono(12, "bold"))
        self.create_text(self.W - 14, self.H / 2, anchor="e", text="●",
                         fill=theme.t("accent"), font=theme.font(11))

    def _commit(self, chord: str):
        self._stop_listener()
        self._recording = False
        self._pending_mods = []
        if chord != self.chord:
            self.chord = chord
            try:
                self.on_change(chord)
            except Exception:
                pass
        self._render()

    def set_chord(self, chord: str):
        self.chord = chord
        self._render()

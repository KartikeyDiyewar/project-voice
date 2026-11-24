"""
Hotkey capture field.

Replaces the fixed dropdown with an explicit record-then-confirm control, the way
Discord and other voice apps let you bind a key:

    click the field  ->  press any key or chord  ->  click the tick to save

Keys are never saved the moment they are pressed. That was the bug in the first
attempt: a stray keypress silently overwrote the binding, and key events arriving
from pynput's listener thread could be dropped because Tk was called from the
wrong thread.

Design notes:
- pynput callbacks only enqueue tokens; the widget drains that queue on the Tk
  main loop, so no cross-thread Tk calls.
- The tick stays disabled until a usable binding has been captured.
- Escape or the cross button cancels and restores the previous chord.
"""

import queue
import tkinter as tk

from pynput import keyboard

from ui import theme

MODIFIER_ORDER = ("ctrl", "shift", "alt", "win")

MODIFIERS = {
    "ctrl": "ctrl", "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "shift": "shift", "shift_l": "shift", "shift_r": "shift",
    "alt": "alt", "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "cmd": "win", "cmd_l": "win", "cmd_r": "win",
}

SPECIAL = {
    "space": "space", "tab": "tab", "enter": "enter", "esc": "escape",
    "backspace": "backspace", "delete": "delete", "insert": "insert",
    "home": "home", "end": "end", "page_up": "page_up",
    "page_down": "page_down", "up": "up", "down": "down",
    "left": "left", "right": "right", "caps_lock": "caps_lock",
    "num_lock": "num_lock", "scroll_lock": "scroll_lock",
    "print_screen": "print_screen", "pause": "pause", "menu": "menu",
}

# Single keys that make poor dictation triggers on their own because they also
# confirm dialogs or move focus. They are still allowed with a modifier.
UNSAFE_ALONE = {"escape", "enter", "tab", "backspace", "delete", "insert"}


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
    if char and char.strip() and char.isprintable():
        return char.lower()
    return None


def _pretty_token(token: str) -> str:
    if token in ("ctrl", "shift", "alt", "win"):
        return token.capitalize()
    if token in ("space", "escape", "enter", "tab", "backspace", "delete",
                 "insert", "home", "end", "up", "down", "left", "right"):
        return token.capitalize()
    if token.startswith("page_"):
        return "Pg" + token.split("_")[1].capitalize()
    if token.startswith("caps"):
        return "Caps Lock"
    if token.startswith("num"):
        return "Num Lock"
    if token.startswith("scroll"):
        return "Scroll Lock"
    if token.startswith("print"):
        return "PrtScr"
    if len(token) == 1:
        return token.upper()
    return token.capitalize()


def pretty(chord: str) -> str:
    """ctrl+shift+space -> Ctrl + Shift + Space"""
    parts = [p for p in chord.split("+") if p]
    return " + ".join(_pretty_token(p) for p in parts)


def _canonical(tokens) -> str:
    """Modifiers first, in a stable order, then the base key."""
    mods = [m for m in MODIFIER_ORDER if m in tokens]
    base = [t for t in tokens if t not in MODIFIER_ORDER]
    return "+".join(mods + base)


class HotkeyField(tk.Frame):
    """Record-then-confirm key binder."""

    FIELD_W, FIELD_H = 236, 40

    def __init__(self, master, chord: str, on_change,
                 bg=None, on_capture_start=None, on_capture_end=None):
        bg = bg or theme.t("canvas")
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self.chord = chord
        self.on_change = on_change
        self.on_capture_start = on_capture_start
        self.on_capture_end = on_capture_end
        self._bg = bg

        self._tokens = []
        self._capturing = False
        self._hover = False
        self._listener = None
        self._events = queue.Queue()
        self._pump_job = None

        self.canvas = tk.Canvas(self, width=self.FIELD_W, height=self.FIELD_H,
                                bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack(side="left")
        self.canvas.bind("<Button-1>", lambda _e: self.start_capture())
        self.canvas.bind("<Enter>", lambda _e: self._set_hover(True))
        self.canvas.bind("<Leave>", lambda _e: self._set_hover(False))

        # Confirm / cancel only exist while a capture is in progress.
        self.tick_btn = tk.Button(
            self, text="✓", width=3, relief="flat", bd=0,
            font=("Segoe UI", 12, "bold"), cursor="hand2",
            command=self.confirm, state="disabled")
        self.cross_btn = tk.Button(
            self, text="✕", width=3, relief="flat", bd=0,
            font=("Segoe UI", 11), cursor="hand2",
            command=self.cancel_capture)

        self._paint_buttons()
        self._render()

    # -- appearance ---------------------------------------------------------
    def _set_hover(self, on: bool):
        self._hover = on
        self._render()

    def _round_rect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0 + r, x1, y1 - r,
               x1 - r, y1, x0 + r, y1, x0, y1 - r, x0, y0 + r]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def _paint_buttons(self):
        """Tint the confirm/cancel buttons for the current theme."""
        if self._capturing:
            self.tick_btn.configure(
                bg=theme.t("accent"), fg="#FFFFFF", activebackground=theme.t("accent_hover"),
                activeforeground="#FFFFFF", disabledforeground="#FFFFFF")
            self.cross_btn.configure(
                bg=theme.t("surface_sunk"), fg=theme.t("text_muted"),
                activebackground=theme.t("border"), activeforeground=theme.t("text"))
        else:
            for btn in (self.tick_btn, self.cross_btn):
                btn.configure(bg=self._bg, fg=theme.t("text_subtle"),
                              activebackground=self._bg)

    def _render(self):
        c = self.canvas
        c.delete("all")
        recording = self._capturing

        if recording:
            fill = theme.t("accent_soft")
            border = theme.t("accent")
            text_colour = theme.t("accent_text")
        else:
            fill = theme.t("surface_sunk")
            border = theme.t("accent") if self._hover else theme.t("border_strong")
            text_colour = theme.t("text")

        # 1px inset so the border is not clipped by the canvas edge.
        self._round_rect(1, 1, self.FIELD_W - 1, self.FIELD_H - 1, 9,
                         fill=fill, outline=fill)
        self._round_rect(2, 2, self.FIELD_W - 2, self.FIELD_H - 2, 8,
                         fill="", outline=border, width=2 if recording else 1)

        if recording:
            if self._tokens:
                self._draw_chips(text_colour)
            else:
                c.create_text(14, self.FIELD_H / 2, anchor="w",
                              text="Press a key…", fill=text_colour,
                              font=theme.mono(12, "bold"))
        else:
            c.create_text(14, self.FIELD_H / 2, anchor="w",
                          text=pretty(self.chord), fill=text_colour,
                          font=theme.mono(12, "bold"))
            c.create_text(self.FIELD_W - 14, self.FIELD_H / 2, anchor="e",
                          text="✎", fill=theme.t("text_subtle"),
                          font=theme.font(11))

    def _draw_chips(self, colour):
        """Shows the captured chord as key chips, like a keyboard rebind dialog."""
        c = self.canvas
        x = 12
        for i, token in enumerate(self._tokens):
            label = _pretty_token(token)
            width = 10 + len(label) * 7
            if x + width > self.FIELD_W - 12:
                break
            if i:
                c.create_text(x, self.FIELD_H / 2, anchor="w", text="+",
                              fill=theme.t("text_subtle"), font=theme.font(10))
                x += 12
            self.canvas.create_rectangle(x, 11, x + width, self.FIELD_H - 11,
                                         fill=theme.t("accent"), outline="")
            c.create_text(x + width / 2, self.FIELD_H / 2, text=label,
                          fill="#FFFFFF", font=theme.mono(10, "bold"))
            x += width + 6
        if x < self.FIELD_W - 24:
            c.create_text(x + 4, self.FIELD_H / 2, anchor="w", text="…",
                          fill=theme.t("text_subtle"), font=theme.font(11))

    # -- capture ------------------------------------------------------------
    def start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self._tokens = []
        self._paint_buttons()

        self.tick_btn.configure(state="disabled")
        self.tick_btn.pack(side="left", padx=(8, 0))
        self.cross_btn.pack(side="left", padx=(6, 0))

        if self.on_capture_start:
            try:
                self.on_capture_start()
            except Exception:
                pass

        self._listener = keyboard.Listener(
            on_press=lambda k: self._events.put(("down", k)),
            on_release=lambda k: self._events.put(("up", k)))
        self._listener.daemon = True
        self._listener.start()

        self._render()
        self._drain()

    def _drain(self):
        """Consumes key events on the Tk thread, then reschedules itself."""
        if not self._capturing:
            self._pump_job = None
            return
        try:
            while True:
                kind, key = self._events.get_nowait()
                self._handle(kind, key)
                if not self._capturing:
                    break
        except queue.Empty:
            pass
        if self._capturing:
            self._pump_job = self.after(40, self._drain)
        else:
            self._pump_job = None

    def _handle(self, kind, key):
        if kind != "down":
            return
        token = _key_token(key)
        if token is None:
            return

        if token == "escape":
            self.cancel_capture()
            return

        # A fresh press replaces the previously captured base key, so retries
        # do not pile up. Modifiers accumulate instead.
        if token in MODIFIER_ORDER:
            if token not in self._tokens:
                self._tokens.append(token)
        else:
            self._tokens = [t for t in self._tokens if t in MODIFIER_ORDER] + [token]

        self.tick_btn.configure(state=self._confirm_state())
        self._render()

    def _confirm_state(self) -> str:
        """Any key or chord can be bound; only a bare modifier is incomplete."""
        if not self._tokens:
            return "disabled"
        bases = [t for t in self._tokens if t not in MODIFIER_ORDER]
        return "normal" if bases else "disabled"

    def warning(self) -> str:
        """Explains a risky choice without blocking it."""
        bases = [t for t in self._tokens if t not in MODIFIER_ORDER]
        has_mod = any(t in MODIFIER_ORDER for t in self._tokens)
        if bases and not has_mod and bases[0] in UNSAFE_ALONE:
            return (f"{_pretty_token(bases[0])} alone also confirms dialogs "
                    f"in other apps. Add Ctrl or Shift to be safe.")
        return ""

    def confirm(self):
        if not self._capturing or self._confirm_state() == "disabled":
            return
        chord = _canonical(self._tokens)
        self._end_capture()
        # Always report the confirmed chord. Re-binding the same key is a real
        # action (the user pressed the tick), so the caller should acknowledge
        # it rather than silently doing nothing.
        self.chord = chord
        try:
            self.on_change(chord)
        except Exception:
            pass
        self._render()

    def cancel_capture(self):
        if not self._capturing:
            return
        self._end_capture()
        self._render()

    def _end_capture(self):
        self._capturing = False
        self._tokens = []
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        if self._pump_job is not None:
            try:
                self.after_cancel(self._pump_job)
            except Exception:
                pass
            self._pump_job = None
        while not self._events.empty():
            try:
                self._events.get_nowait()
            except queue.Empty:
                break

        self.tick_btn.pack_forget()
        self.cross_btn.pack_forget()
        self._paint_buttons()
        if self.on_capture_end:
            try:
                self.on_capture_end()
            except Exception:
                pass

    def set_chord(self, chord: str):
        self.chord = chord
        self._render()

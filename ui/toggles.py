"""
Project Voice - Animated Toggle Controls

Four switch personalities, all drawn on a plain canvas so they render crisply at
any DPI and never depend on widget theming:

  boulder - a knob that rolls across the track and lands with a squash
  tide    - the accent colour rises like water behind a soft wave line
  matrix  - a dot grid that lights up in a diagonal cascade
  blob    - an organic blob that stretches awake and settles

Transition length is short (product motion is functional), and the extra idle
"breath" only runs while the pointer is over a switch, so a page full of these
costs nothing when nobody is touching them.
"""

import math
import time
import tkinter as tk

from ui import theme

STYLES = ("boulder", "tide", "matrix", "blob")
DEFAULT_STYLE = "tide"

BASE_W, BASE_H = 46, 26
TICK_MS = 16
IDLE_MS = 45
TRANSITION_S = 0.26


def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def _mix(c1: str, c2: str, t: float) -> str:
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _pill_path(w: float, h: float, r: float, steps: int = 24):
    """Closed pill outline. Enough steps per cap that the curve reads as round."""
    r = max(1.0, min(r, h / 2, w / 2))
    pts = []
    for i in range(steps + 1):
        pts.append((r + (w - 2 * r) * i / steps, 0.0))
    cx, cy = w - r, h / 2
    for i in range(1, steps + 1):
        a = math.radians(-90 + 180 * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for i in range(steps + 1):
        pts.append((w - r - (w - 2 * r) * i / steps, h))
    cx = r
    for i in range(1, steps + 1):
        a = math.radians(90 + 180 * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _blob_points(cx, cy, rx, ry, seed, wobble=1.0):
    pts = []
    for i in range(44):
        a = math.tau * i / 44
        k = 1 + wobble * (0.10 * math.sin(3 * a + seed) + 0.055 * math.cos(5 * a - seed * 1.7))
        pts.append(cx + rx * k * math.cos(a))
        pts.append(cy + ry * k * math.sin(a))
    return pts


class AnimatedToggle(tk.Canvas):
    """One switch, four personalities. Same footprint, same public API."""

    def __init__(self, master, value=False, command=None, bg=None, style=None,
                 track_off=None, track_on=None, knob=None):
        self.scale = 1.0
        for attr in ("_get_widget_scaling", "_get_window_scaling"):
            fn = getattr(master, attr, None)
            if callable(fn):
                try:
                    self.scale = float(fn()) or 1.0
                except Exception:
                    pass
                break

        self.w = int(round(BASE_W * self.scale))
        self.h = int(round(BASE_H * self.scale))
        bg = bg or theme.t("canvas")
        super().__init__(master, width=self.w, height=self.h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")

        self.command = command
        self.value = bool(value)
        self.style = style if style in STYLES else DEFAULT_STYLE
        self.colors = {
            "off": track_off or theme.t("switch_off"),
            "on": track_on or theme.t("accent"),
            "knob": knob or theme.t("switch_knob"),
            "bg": bg,
        }

        self._progress = 1.0 if self.value else 0.0
        self._anim_from = self._progress
        self._anim_start = 0.0
        self._anim_job = None
        self._idle_job = None
        self._idle_t = 0.0
        self._hover = False

        self.bind("<Button-1>", lambda _e: self.toggle())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Destroy>", lambda _e: self._cancel_jobs())

        self._render()

    # -- public API ---------------------------------------------------------
    def get(self) -> int:
        return 1 if self.value else 0

    def select(self):
        if not self.value:
            self.value = True
            self._start_transition()

    def deselect(self):
        if self.value:
            self.value = False
            self._start_transition()

    def toggle(self):
        self.value = not self.value
        self._start_transition()
        if self.command:
            self.command()

    def set_style(self, style: str):
        if style in STYLES and style != self.style:
            self.style = style
            self._render()
            if self._hover:
                self._start_idle()

    # -- animation plumbing -------------------------------------------------
    def _cancel_jobs(self):
        for job in (self._anim_job, self._idle_job):
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        self._anim_job = self._idle_job = None

    def _start_transition(self):
        self._anim_from = self._progress
        self._anim_start = time.perf_counter()
        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
        self._tick_transition()

    def _tick_transition(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        target = 1.0 if self.value else 0.0
        t = min(1.0, (time.perf_counter() - self._anim_start) / TRANSITION_S)
        self._progress = self._anim_from + (target - self._anim_from) * _ease_out_cubic(t)
        self._render()

        if t < 1.0:
            self._anim_job = self.after(TICK_MS, self._tick_transition)
        else:
            self._progress = target
            self._anim_job = None
            self._render()

    def _set_hover(self, hover: bool):
        self._hover = hover
        if hover:
            self._start_idle()
        else:
            if self._idle_job:
                try:
                    self.after_cancel(self._idle_job)
                except Exception:
                    pass
                self._idle_job = None
            self._render()

    def _start_idle(self):
        if self._idle_job:
            return

        def _tick():
            self._idle_job = None
            try:
                if not self.winfo_exists() or not self._hover:
                    return
            except Exception:
                return
            self._idle_t += IDLE_MS / 1000.0
            self._render()
            self._idle_job = self.after(IDLE_MS, _tick)

        self._idle_job = self.after(IDLE_MS, _tick)

    # -- rendering ----------------------------------------------------------
    def _render(self):
        try:
            self.delete("all")
        except Exception:
            return
        p = max(0.0, min(1.0, self._progress))
        painter = {
            "boulder": self._draw_boulder,
            "tide": self._draw_tide,
            "matrix": self._draw_matrix,
            "blob": self._draw_blob,
        }[self.style]
        painter(p)

    def _track_color(self, p):
        return _mix(self.colors["off"], self.colors["on"], p)

    def _pill(self, fill, outline=""):
        s = self.scale
        return self.create_polygon(_pill_path(self.w, self.h, self.h / 2),
                                   smooth=True, fill=fill, outline=outline,
                                   width=1 * s)

    # boulder: a knob that rolls over and squashes on landing ---------------
    def _draw_boulder(self, p):
        s = self.scale
        r = self.h / 2
        self.create_polygon(_pill_path(self.w, self.h, r), smooth=True,
                             fill=self._track_color(p), outline="")

        knob_d = self.h - 6 * s
        kr = knob_d / 2
        left = 3 * s + kr
        right = self.w - 3 * s - kr
        # slight overshoot then settle reads as weight
        travel = _ease_out_cubic(p)
        if p > 0.94:
            travel = 1.0
        cx = left + (right - left) * travel

        squash = 1.0
        if 0.2 < p < 0.95:
            squash = 0.86 + 0.14 * abs(math.sin(p * math.pi * 2.0))
        cy = self.h / 2
        rx = kr * (2.0 - squash)
        ry = kr * squash

        bob = math.sin(self._idle_t * 2.2) * 0.6 * s if self._hover else 0.0
        self.create_oval(cx - rx, cy - ry + bob, cx + rx, cy + ry + bob,
                         fill=self.colors["knob"], outline="")
        # rim mark shows rotation as it rolls
        angle = math.radians(-360 * travel + 90)
        mr = kr * 0.42
        mx = cx + mr * math.cos(angle)
        my = cy + bob
        self.create_oval(mx - 1.6 * s, my - 1.6 * s, mx + 1.6 * s, my + 1.6 * s,
                         fill=_mix(self.colors["knob"], self.colors["on"], 0.55), outline="")

    # tide: accent rises behind a soft wave line ---------------------------
    def _draw_tide(self, p):
        s = self.scale
        r = self.h / 2
        self.create_polygon(_pill_path(self.w, self.h, r), smooth=True,
                             fill=self.colors["off"], outline="")
        if p <= 0.001:
            return

        amplitude = 1.5 * s
        phase = self._idle_t * 2.4 if self._hover else 0.0
        level = self.h + 2 * s - (self.h + 4 * s) * p

        def surface(x):
            # fade the wave out near both caps so it never cuts the pill curve
            edge = min(1.0, min(x, self.w - x) / max(1.0, r))
            return level + amplitude * edge * math.sin(x / self.w * math.tau * 1.6 + phase)

        pts = []
        for x, y in _pill_path(self.w, self.h, r):
            pts.append((x, y if y >= surface(x) else surface(x)))
        self.create_polygon(pts, smooth=True, fill=self.colors["on"], outline="")

        # the droplet rides the surface inside the pill, and fades out once the
        # track is full so it never bites a notch out of the rounded cap
        if p < 0.92:
            inner = r + 2.5 * s
            dx = inner + (self.w - 2 * inner) * (0.22 + 0.55 * p)
            dy = min(self.h - 3.5 * s, max(3.5 * s, surface(dx)))
            dy += math.sin(self._idle_t * 2.6) * 0.8 * s if self._hover else 0
            dr = 2.6 * s * (1.0 - max(0.0, (p - 0.6) / 0.32))
            if dr > 0.4 * s:
                self.create_oval(dx - dr, dy - dr, dx + dr, dy + dr,
                                 fill=self.colors["knob"], outline="")

    # matrix: dots light up in a diagonal cascade --------------------------
    def _draw_matrix(self, p):
        s = self.scale
        cols, rows = 7, 3
        gap_x = self.w / cols
        gap_y = self.h / rows
        dot = min(gap_x, gap_y) * 0.30

        for c in range(cols):
            for rr in range(rows):
                order = (c + rr * 0.7) / (cols - 1 + (rows - 1) * 0.7)
                local = max(0.0, min(1.0, (p - order * 0.55) / 0.45))
                colour = _mix(self.colors["off"], self.colors["on"], local)
                pop = 1.0 + 0.35 * math.sin(local * math.pi)
                cx = gap_x * (c + 0.5)
                cy = gap_y * (rr + 0.5)
                rad = dot * pop
                self.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                 fill=colour, outline="")

    # blob: stretches awake and settles -----------------------------------
    def _draw_blob(self, p):
        s = self.scale
        # the body never leaves the track: it grows, then slides, staying inset
        margin = 3.0 * s
        ry = (self.h * 0.34) + ((self.h * 0.40) - (self.h * 0.34)) * p
        rx = (self.w * 0.26) + (self.w * 0.14) * p
        cx = margin + rx + (self.w - 2 * margin - 2 * rx) * p
        breathe = math.sin(self._idle_t * 2.0) * 0.5 * s if self._hover else 0.0
        cy = self.h / 2 + breathe
        colour = _mix(self.colors["off"], self.colors["on"], p)
        self.create_polygon(_blob_points(cx, cy, rx, ry, 1.35 + p * 0.5, 0.85),
                             smooth=True, fill=colour, outline="")
        if p > 0.35:
            # a single soft highlight so it reads as a body, not a stain
            hr = min(rx, ry) * 0.20
            hx = cx - rx * 0.32
            hy = cy - ry * 0.32
            self.create_oval(hx - hr, hy - hr, hx + hr, hy + hr,
                             fill=self.colors["knob"], outline="")


def make_toggle(master, value=False, command=None, bg=None, style=None):
    return AnimatedToggle(master, value=value, command=command, bg=bg,
                          style=style or theme.toggle_style())

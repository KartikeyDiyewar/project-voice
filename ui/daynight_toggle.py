"""
Day / Night Toggle

A stroke-based stadium switch: the pill is an outline rather than a filled track,
half of its perimeter is lit, and the celestial body in the centre morphs between
a crescent moon and a full sun as it turns.

Geometry follows the reference: the path starts at top-centre and runs clockwise,
so the two neutral split points are top-centre and bottom-centre. Everything is
sampled from one continuous perimeter, which keeps the lit arc and its round caps
exactly on the outline at any size.
"""

import math
import tkinter as tk

from ui import theme

TRACK_WIDTH = 3.2
INSET_RATIO = 0.09
CORE_RATIO = 0.40
DURATION = 0.55
TICK_MS = 16
SAMPLES = 44

# Mask offsets expressed as a fraction of the core radius, taken from the
# reference viewBox where the body has r=11.5 and the mask sits at (-6,-2) /
# (-26,-18). Keeping them relative makes the crescent identical at any size.
MASK_NEAR = (-0.52, -0.17)
MASK_FAR = (-2.26, -1.57)
MASK_RATIO = 0.87


def _ease(t: float) -> float:
    """Material standard curve, matching the reference easing."""
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def _blend(c1: str, c2: str, t: float) -> str:
    """Cross-fade between two hex colours (canvas has no alpha)."""
    t = max(0.0, min(1.0, t))
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _perimeter(w: float, h: float, inset: float):
    """Returns (points, cumulative_fractions) for the stadium outline."""
    r = max(1.0, h / 2 - inset)
    cy = h / 2
    lcx = inset + r
    rcx = max(lcx + 0.01, w - inset - r)
    top, bottom = inset, h - inset
    mid = w / 2

    pts = []

    def push(x, y):
        if not pts or abs(pts[-1][0] - x) > 0.01 or abs(pts[-1][1] - y) > 0.01:
            pts.append((x, y))

    # top-centre -> right cap, clockwise
    for i in range(SAMPLES + 1):
        push(mid + (rcx - mid) * i / SAMPLES, top)
    for i in range(1, SAMPLES + 1):
        a = math.radians(-90 + 180 * i / SAMPLES)
        push(rcx + r * math.cos(a), cy + r * math.sin(a))
    for i in range(1, SAMPLES + 1):
        push(rcx + (lcx - rcx) * i / SAMPLES, bottom)
    for i in range(1, SAMPLES + 1):
        a = math.radians(90 + 180 * i / SAMPLES)
        push(lcx + r * math.cos(a), cy + r * math.sin(a))
    for i in range(1, SAMPLES + 1):
        push(lcx + (mid - lcx) * i / SAMPLES, top)
    if len(pts) > 1:
        push(pts[0][0], pts[0][1])

    lengths = [0.0]
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]
        lengths.append(lengths[-1] + math.hypot(dx, dy))
    total = lengths[-1] or 1.0
    return pts, [v / total for v in lengths]


def _slice(pts, fracs, start, end):
    """Points along the perimeter between two normalised positions."""
    start, end = max(0.0, start), min(1.0, end)
    if end <= start:
        return []
    out = []
    for i, (x, y) in enumerate(pts):
        f = fracs[i]
        if start <= f <= end:
            out.append((x, y))
        elif i and fracs[i - 1] < start < f:
            t = (start - fracs[i - 1]) / (f - fracs[i - 1])
            out.insert(0, (pts[i - 1][0] + (x - pts[i - 1][0]) * t,
                           pts[i - 1][1] + (y - pts[i - 1][1]) * t))
        elif i and fracs[i - 1] < end < f:
            t = (end - fracs[i - 1]) / (f - fracs[i - 1])
            out.append((pts[i - 1][0] + (x - pts[i - 1][0]) * t,
                        pts[i - 1][1] + (y - pts[i - 1][1]) * t))
            break
    return out


class DayNightToggle(tk.Canvas):
    """Stroke-based stadium switch.

    Two personalities share the same track and arc maths:
      kind="theme" - crescent moon / sun morph for dark mode
      kind="onoff" - ring that collapses into a bar for off / on
    """

    def __init__(self, master, value=False, command=None, bg=None,
                 width=None, height=None, on_done=None, kind="theme"):
        scale = 1.0
        for attr in ("_get_widget_scaling", "_get_window_scaling"):
            fn = getattr(master, attr, None)
            if callable(fn):
                try:
                    scale = float(fn()) or 1.0
                except Exception:
                    pass
                break
        self.scale = scale

        self.w = int(round((width or 68) * scale))
        self.h = int(round((height or 34) * scale))
        bg = bg or theme.t("canvas")
        super().__init__(master, width=self.w, height=self.h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")

        self.command = command
        self.on_done = on_done
        self.kind = kind if kind in ("theme", "onoff") else "theme"
        self.value = bool(value)
        self._bg = bg
        self._progress = 1.0 if self.value else 0.0
        self._from = self._progress
        self._start = 0.0
        self._job = None
        self._hover = False

        # Geometry never changes for a given size, so sample it once. Re-deriving
        # 200+ points on every animation frame is what made the flip look jerky.
        inset = TRACK_WIDTH * scale + 0.6 * scale
        self._pts, self._fracs = _perimeter(self.w, self.h, inset)
        self._track_flat = [c for pt in self._pts for c in pt]
        self._stroke_w = TRACK_WIDTH * scale
        self._inset = inset

        self.bind("<Button-1>", lambda _e: self.toggle())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Destroy>", lambda _e: self._cancel())
        self._render()

    # -- public API ---------------------------------------------------------
    def get(self) -> int:
        return 1 if self.value else 0

    def select(self):
        if not self.value:
            self.value = True
            self._animate()

    def deselect(self):
        if self.value:
            self.value = False
            self._animate()

    def toggle(self):
        self.value = not self.value
        self._animate()
        if self.command:
            self.command()

    # -- animation ----------------------------------------------------------
    def _cancel(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _animate(self):
        import time
        self._from = self._progress
        self._start = time.perf_counter()
        self._cancel()
        self._tick()

    def _tick(self):
        import time
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        target = 1.0 if self.value else 0.0
        t = min(1.0, (time.perf_counter() - self._start) / DURATION)
        self._progress = self._from + (target - self._from) * _ease(t)
        self._render()
        if t < 1.0:
            self._job = self.after(TICK_MS, self._tick)
        else:
            self._progress = target
            self._job = None
            self._render()
            if self.on_done:
                self.on_done()

    def _set_hover(self, hover):
        self._hover = hover
        self._render()

    # -- rendering ----------------------------------------------------------
    def _palette(self):
        """Track, lit arc and celestial body colours for the current theme."""
        if theme.mode() == "dark":
            return theme.t("border_strong"), theme.t("text"), theme.t("accent")
        return theme.t("border_strong"), theme.t("ink"), theme.t("ink")

    def _stroke(self, pts, colour, width):
        """Draws the outline as one polyline.

        A single create_line with round joins is both correct (it follows the
        sampled path exactly) and cheap - one canvas item instead of hundreds,
        which is what keeps the animation at 60fps.
        """
        if len(pts) < 2:
            return
        flat = [c for pt in pts for c in pt]
        self.create_line(*flat, fill=colour, width=width,
                         capstyle=tk.ROUND, joinstyle=tk.ROUND)

    def _draw_onoff_glyph(self, cx, cy, r_core, colour, p):
        """Ring (off) collapses to a dot while a vertical bar (on) grows.

        p=0 -> ring at full size, p=1 -> bar at full height. Both cross-fade in
        the middle, which reads as one glyph turning into the other.
        """
        s = self.scale
        line = 2.6 * s

        # ring shrinks and fades out
        ring_scale = 1.0 - 0.70 * p
        ring_alpha = 1.0 - min(1.0, p / 0.65)
        if ring_alpha > 0.02:
            rr = r_core * 0.86 * ring_scale
            shade = _blend(self._bg, colour, ring_alpha)
            self.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                             outline=shade, width=line)

        # bar grows in height and fades in
        bar = min(1.0, max(0.0, (p - 0.35) / 0.65))
        if bar > 0.02:
            half = r_core * 0.95 * bar
            shade = _blend(self._bg, colour, bar)
            self.create_line(cx, cy - half, cx, cy + half, fill=shade,
                             width=3.2 * s, capstyle=tk.ROUND)

    def _render(self):
        try:
            self.delete("all")
        except Exception:
            return

        s = self.scale
        p = max(0.0, min(1.0, self._progress))   # 1.0 = dark mode
        w, h = self.w, self.h
        inset = self._inset
        stroke = self._stroke_w

        pts, fracs = self._pts, self._fracs
        track_col, lit_col, core_col = self._palette()

        # base stadium outline (one cached canvas item)
        self.create_line(*self._track_flat, fill=track_col, width=stroke,
                         capstyle=tk.ROUND, joinstyle=tk.ROUND)

        # Lit half is the right side in day and the left side at night, so the
        # arc orbits a full half-turn as the switch moves.
        start = 0.5 * p
        lit_pts = _slice(pts, fracs, start, start + 0.5)
        if len(lit_pts) > 1:
            self._stroke(lit_pts, lit_col, stroke)

        # Celestial body: whole sun by day, crescent moon by night.
        cx, cy = w / 2, h / 2
        r_core = (h / 2 - inset) * CORE_RATIO
        if self._hover:
            r_core *= 1.05

        if self.kind == "onoff":
            self._draw_onoff_glyph(cx, cy, r_core, core_col, p)
            return

        self.create_oval(cx - r_core, cy - r_core, cx + r_core, cy + r_core,
                         fill=core_col, outline="")

        mask_r = r_core * MASK_RATIO
        near = (MASK_NEAR[0] * r_core, MASK_NEAR[1] * r_core)
        far = (MASK_FAR[0] * r_core, MASK_FAR[1] * r_core)
        ox = far[0] + (near[0] - far[0]) * p
        oy = far[1] + (near[1] - far[1]) * p
        angle = math.radians(180 * (1.0 - p))   # group turns as the theme flips
        mx = ox * math.cos(angle) - oy * math.sin(angle)
        my = ox * math.sin(angle) + oy * math.cos(angle)
        if math.hypot(mx, my) < r_core + mask_r:
            self.create_oval(cx + mx - mask_r, cy + my - mask_r,
                             cx + mx + mask_r, cy + my + mask_r,
                             fill=self._bg, outline="")

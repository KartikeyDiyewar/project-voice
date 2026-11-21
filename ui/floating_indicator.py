"""
Floating Visual Indicator Pill (Wispr Flow Style - 60 FPS Focus-Locked)
A sleek, non-intrusive glowing pill that appears at the bottom-center of the screen
with fluid, 60 FPS animated sound visualizers and dynamic moving ellipsis.
Features:
- WS_EX_NOACTIVATE: 100% immune to stealing focus from active application (zero caret flicker)
- WS_EX_TOOLWINDOW: Hidden from Alt+Tab switcher and taskbar
- HWND_TOPMOST: Stays comfortably above fullscreen apps
- 60 FPS liquid animation with raised-cosine easing
- Dynamic states: Listening (Cyan), Processing (Amber), Pasted (Green), Error (Red)
"""

import ctypes
from ctypes import wintypes
import math
import tkinter as tk
import customtkinter as ctk
from config.settings import settings
from ui import theme

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008

SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

# Colour used as the window's transparent key. Windows colour-keying only
# removes exact matches, so the anti-aliased pixels along the pill's rounded
# corners keep a blend of this colour and the border. A near-ink tone therefore
# reads as a soft dark edge, while a saturated key would leave a visible fringe.
CHROMA_KEY = "#2B2622"
GWL_STYLE = -16
WS_EX_LAYERED = 0x00080000
LWA_COLORKEY = 0x00000001

class FloatingIndicator:
    def __init__(self, master=None):
        self.master = master
        self.current_state = "idle"
        self.anim_phase = 0.0
        self.anim_tick_count = 0
        self.is_animating = False
        self.latch = False
        self._hwnd = None
        self._init_window()

    def _init_window(self):
        # Uses CTkToplevel attached to master
        self.root = ctk.CTkToplevel(self.master)
        self.root.title("Project Voice Pill")
        self.root.overrideredirect(True)        # Borderless
        self.root.attributes("-topmost", True)   # Always on top

        # Dimensions & bottom-center positioning (Pill layout: 300x46)
        width = 300
        height = 46
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = screen_h - 110  # Positioned comfortably above Windows taskbar

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        # The window itself is painted in the chroma key so only the pill below
        # is visible; without this the dark window background shows as a
        # rectangle around the rounded corners.
        self.root.configure(fg_color=CHROMA_KEY)
        try:
            self.root.wm_attributes("-transparentcolor", CHROMA_KEY)
        except Exception:
            pass

        # Container frame styled like a rounded pill
        self.container = ctk.CTkFrame(
            self.root,
            fg_color=theme.on_ink("ink_raised"),
            border_width=1,
            border_color=theme.on_ink("ink_border"),
            corner_radius=23
        )
        self.container.pack(fill="both", expand=True)

        # Dynamic Sound Wave Canvas Visualizer
        self.canvas = tk.Canvas(
            self.container,
            width=46,
            height=26,
            bg=theme.on_ink("ink_raised"),
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(side="left", padx=(12, 6))

        # Status message text with animated moving ellipsis
        self.text_label = ctk.CTkLabel(
            self.container,
            text="Listening...",
            font=theme.font(12, "bold"),
            text_color=theme.on_ink("on_ink")
        )
        self.text_label.pack(side="left")

        # Pill right badge (Hotkey tag or LPU state)
        self.sub_label = ctk.CTkLabel(
            self.container,
            text="[ Ctrl + Space ]",
            font=theme.mono(10, "bold"),
            text_color=theme.on_ink("on_ink_muted"),
            fg_color=theme.on_ink("ink"),
            corner_radius=6,
            padx=6,
            pady=2
        )
        self.sub_label.pack(side="right", padx=(0, 14))

        # Apply Win32 Extended Styles (Focus-Lock)
        self.root.update_idletasks()
        self._apply_win32_styles()

        # Start hidden
        self.root.withdraw()

    def _get_hwnd(self) -> int:
        if not self._hwnd and self.root:
            try:
                self._hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            except Exception:
                pass
        return self._hwnd or 0

    def _apply_win32_styles(self):
        """Applies WS_EX_NOACTIVATE so pill never steals focus from active app."""
        hwnd = self._get_hwnd()
        if hwnd:
            try:
                cur_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(
                    hwnd,
                    GWL_EXSTYLE,
                    cur_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
                )
            except Exception:
                pass
        self._apply_transparency(hwnd)

    def _apply_transparency(self, hwnd):
        """Makes the chroma-key colour fully transparent on the layered window."""
        if not hwnd:
            return
        try:
            r = int(CHROMA_KEY[1:3], 16)
            g = int(CHROMA_KEY[3:5], 16)
            b = int(CHROMA_KEY[5:7], 16)
            colorref = r | (g << 8) | (b << 16)
            user32.SetLayeredWindowAttributes(hwnd, colorref, 0, LWA_COLORKEY)
        except Exception:
            pass

    def _show_no_activate(self):
        """Shows window without stealing cursor/caret focus."""
        try:
            self.root.deiconify()
            hwnd = self._get_hwnd()
            if hwnd:
                user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 60 FPS FLUID ANIMATION ENGINE (Zero CPU overhead when idle)
    # -------------------------------------------------------------------------
    def _start_animation(self):
        anim_style = getattr(settings, "indicator_animation", "wave_bars")
        self._bar_items = []
        self._dot_items = []
        self.canvas.delete("all")

        if anim_style in ("off", "none", "static"):
            if self.current_state == "listening":
                self.canvas.create_oval(17, 8, 27, 18, fill=theme.on_ink("accent"), outline="")
                self.text_label.configure(text="Listening...", text_color=theme.on_ink("on_ink"))
            elif self.current_state == "processing":
                self.canvas.create_oval(17, 8, 27, 18, outline=theme.on_ink("warning"), width=2)
                self.text_label.configure(text="Refining voice...", text_color=theme.on_ink("warning"))
            return

        if not self.is_animating:
            self.is_animating = True
            self.anim_phase = 0.0
            self.anim_tick_count = 0
            self._tick_animation()

    def _stop_animation(self):
        self.is_animating = False
        self._bar_items = []
        self._dot_items = []

    def _tick_animation(self):
        if not self.is_animating or not self.root:
            return

        # 60 FPS tick step
        self.anim_phase += 0.09
        self.anim_tick_count += 1
        anim_style = getattr(settings, "indicator_animation", "wave_bars")

        if self.current_state == "listening":
            if anim_style == "wave_dots":
                if not getattr(self, "_dot_items", None):
                    self.canvas.delete("all")
                    self._dot_items = [
                        self.canvas.create_oval(0, 0, 0, 0, fill=theme.on_ink("accent"), outline="")
                        for _ in range(3)
                    ]
                for i, item in enumerate(self._dot_items):
                    cx = 11 + i * 12
                    cy = 13 + math.sin(self.anim_phase * 2.0 + i * 1.5) * 5.0
                    r = 3.0 + math.sin(self.anim_phase * 2.0 + i * 1.5) * 0.8
                    self.canvas.coords(item, cx - r, cy - r, cx + r, cy + r)

            elif anim_style == "sine_wave":
                self.canvas.delete("all")
                pts = []
                for px in range(4, 44, 3):
                    py = 13 + math.sin(self.anim_phase * 2.0 + (px * 0.28)) * 6.5
                    pts.extend([px, py])
                if len(pts) >= 4:
                    self.canvas.create_line(*pts, smooth=True, width=2.6, fill=theme.on_ink("accent"), capstyle=tk.ROUND)

            else:
                # Default: "wave_bars" (Zero-allocation coords update)
                if not getattr(self, "_bar_items", None):
                    self.canvas.delete("all")
                    ramp = [theme.on_ink("accent"), theme.on_ink("accent_hover"),
                            theme.on_ink("on_ink_muted"), theme.on_ink("accent")]
                    self._bar_items = [
                        self.canvas.create_line(8 + i * 10, 13, 8 + i * 10, 13, width=3.2, fill=ramp[i], capstyle=tk.ROUND)
                        for i in range(4)
                    ]
                for i, item in enumerate(self._bar_items):
                    x = 8 + i * 10
                    h = 3.5 + 7.5 * (0.5 + 0.5 * math.sin(self.anim_phase * 2.0 + i * 1.3))
                    self.canvas.coords(item, x, 13 - h, x, 13 + h)

            # Dynamic moving wave dots on text
            dots_idx = (self.anim_tick_count // 14) % 4
            dots_str = ["", ".", ". .", ". . ."][dots_idx]
            word = "Recording" if self.latch else "Listening"
            self.text_label.configure(text=f"{word} {dots_str}", text_color=theme.on_ink("on_ink"))

        elif self.current_state == "processing":
            if not getattr(self, "_bar_items", None):
                self.canvas.delete("all")
                ramp = [theme.on_ink("warning"), theme.on_ink("warning"),
                        theme.on_ink("on_ink_muted"), theme.on_ink("warning")]
                self._bar_items = [
                    self.canvas.create_line(8 + i * 10, 13, 8 + i * 10, 13, width=3.0, fill=ramp[i], capstyle=tk.ROUND)
                    for i in range(4)
                ]
            for i, item in enumerate(self._bar_items):
                x = 8 + i * 10
                h = 3.0 + 5.5 * (0.5 + 0.5 * math.sin(self.anim_phase * 2.8 + i * 1.1))
                self.canvas.coords(item, x, 13 - h, x, 13 + h)

            dots_idx = (self.anim_tick_count // 14) % 4
            dots_str = ["", ".", ". .", ". . ."][dots_idx]
            self.text_label.configure(text=f"Refining voice {dots_str}", text_color=theme.on_ink("warning"))

        # Schedule next frame at 16ms (~60 FPS)
        self.root.after(16, self._tick_animation)

    # -------------------------------------------------------------------------
    # STATE TRANSITIONS
    # -------------------------------------------------------------------------
    def show_listening(self, latch: bool = False):
        """Shows the listening pill. latch=True means it runs until pressed again."""
        if not self.root:
            return
        self.latch = bool(latch)
        def _apply():
            self.current_state = "listening"
            self.container.configure(border_color=theme.on_ink("accent"))
            self.sub_label.configure(
                text="Press again to stop" if self.latch else f"[ {settings.hotkey.upper()} ]",
                text_color=theme.on_ink("on_ink_muted"))
            self._start_animation()
            self._show_no_activate()
        self.root.after(0, _apply)

    def show_processing(self):
        """Called when user releases Ctrl+Space."""
        if not self.root:
            return
        def _apply():
            self.current_state = "processing"
            self.container.configure(border_color=theme.on_ink("warning"))
            self.sub_label.configure(text="Groq LPU", text_color=theme.on_ink("warning"))
            self._start_animation()
            self._show_no_activate()
        self.root.after(0, _apply)

    def show_pasted(self):
        """Called when text is injected into active window."""
        if not self.root:
            return
        def _apply():
            self._stop_animation()
            self.current_state = "pasted"
            self.canvas.delete("all")
            self._draw_check(theme.on_ink("success"))
            self.container.configure(border_color=theme.on_ink("success"))
            self.text_label.configure(text="Pasted", text_color=theme.on_ink("success"))
            self.sub_label.configure(text="Done", text_color=theme.on_ink("success"))
            self.root.after(700, self._hide_if_idle)
        self.root.after(0, _apply)

    def show_error(self, message="Error"):
        if not self.root:
            return
        def _apply():
            self._stop_animation()
            self.current_state = "error"
            self.canvas.delete("all")
            self._draw_cross(theme.on_ink("danger"))
            self.container.configure(border_color=theme.on_ink("danger"))
            self.text_label.configure(text=message[:20], text_color=theme.on_ink("danger"))
            self.sub_label.configure(text="Error", text_color=theme.on_ink("danger"))
            self.root.after(1400, self._hide_if_idle)
        self.root.after(0, _apply)

    def _draw_check(self, color):
        self.canvas.create_line(16, 13, 21, 18, 28, 8, fill=color,
                                width=2.4, capstyle=tk.ROUND, joinstyle=tk.ROUND)

    def _draw_cross(self, color):
        self.canvas.create_line(17, 8, 29, 18, fill=color, width=2.4, capstyle=tk.ROUND)
        self.canvas.create_line(17, 18, 29, 8, fill=color, width=2.4, capstyle=tk.ROUND)

    def _hide_if_idle(self):
        if self.current_state in ("pasted", "idle", "error"):
            self._stop_animation()
            self.current_state = "idle"
            self.root.withdraw()

    def hide(self):
        if not self.root:
            return
        def _apply():
            self._stop_animation()
            self.root.withdraw()
        self.root.after(0, _apply)

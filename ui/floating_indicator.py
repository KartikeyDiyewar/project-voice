"""
Floating Visual Indicator Pill (Wispr Flow Style)
A sleek, non-intrusive glowing pill that appears at the bottom-center of the screen
with fluid, animated sound visualizers and dynamic moving ellipsis during speech capture and AI refining.
Uses CTkToplevel tied to the main application root for 100% thread-safe UI updates.
"""

import math
import tkinter as tk
import customtkinter as ctk
from config.settings import settings

class FloatingIndicator:
    def __init__(self, master=None):
        self.master = master
        self.current_state = "idle"
        self.anim_phase = 0.0
        self.anim_tick_count = 0
        self.is_animating = False
        self._init_window()

    def _init_window(self):
        # Uses CTkToplevel attached to master
        self.root = ctk.CTkToplevel(self.master)
        self.root.title("Project Voice Pill")
        self.root.overrideredirect(True)        # Borderless
        self.root.attributes("-topmost", True)   # Always on top
        self.root.attributes("-alpha", 0.95)     # Modern sleek glass effect

        # Dimensions & bottom-center positioning (Pill layout: 300x46)
        width = 300
        height = 46
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = screen_h - 110  # Positioned comfortably above Windows taskbar

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(fg_color="#090d16")

        # Container frame styled like a rounded pill
        self.container = ctk.CTkFrame(
            self.root,
            fg_color="#0d1322",
            border_width=1,
            border_color="#22304d",
            corner_radius=23
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # Dynamic Sound Wave Canvas Visualizer
        self.canvas = tk.Canvas(
            self.container,
            width=46,
            height=26,
            bg="#0d1322",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(side="left", padx=(12, 6))

        # Status message text with animated moving ellipsis
        self.text_label = ctk.CTkLabel(
            self.container,
            text="Listening...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f8fafc"
        )
        self.text_label.pack(side="left")

        # Pill right badge (Hotkey tag or LPU state)
        self.sub_label = ctk.CTkLabel(
            self.container,
            text="[ Ctrl + Space ]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#64748b",
            fg_color="#141d33",
            corner_radius=6,
            padx=6,
            pady=2
        )
        self.sub_label.pack(side="right", padx=(0, 14))

        # Start hidden
        self.root.withdraw()

    # -------------------------------------------------------------------------
    # FLUID ANIMATION ENGINE (30 FPS, Zero CPU overhead when idle)
    # -------------------------------------------------------------------------
    def _start_animation(self):
        anim_style = getattr(settings, "indicator_animation", "wave_bars")
        if anim_style in ("off", "none", "static"):
            self.canvas.delete("all")
            if self.current_state == "listening":
                self.canvas.create_oval(17, 8, 27, 18, fill="#38bdf8", outline="")
                self.text_label.configure(text="Listening...", text_color="#f8fafc")
            elif self.current_state == "processing":
                self.canvas.create_text(22, 13, text="✦", fill="#f59e0b", font=("Segoe UI", 12, "bold"))
                self.text_label.configure(text="Refining voice...", text_color="#fde68a")
            return

        if not self.is_animating:
            self.is_animating = True
            self.anim_phase = 0.0
            self.anim_tick_count = 0
            self._tick_animation()

    def _stop_animation(self):
        self.is_animating = False

    def _tick_animation(self):
        if not self.is_animating or not self.root:
            return

        self.anim_phase += 0.18
        self.anim_tick_count += 1
        anim_style = getattr(settings, "indicator_animation", "wave_bars")

        self.canvas.delete("all")

        if self.current_state == "listening":
            if anim_style == "wave_dots":
                # 3 bouncing liquid dots
                for i in range(3):
                    cx = 11 + i * 12
                    cy = 13 + math.sin(self.anim_phase + i * 1.5) * 5.0
                    r = 3.0 + math.sin(self.anim_phase + i * 1.5) * 0.8
                    self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#38bdf8", outline="")
            elif anim_style == "sine_wave":
                # Continuous fluid sine wave curve
                pts = []
                for px in range(4, 44, 3):
                    py = 13 + math.sin(self.anim_phase + (px * 0.28)) * 6.5
                    pts.extend([px, py])
                if len(pts) >= 4:
                    self.canvas.create_line(*pts, smooth=True, width=2.6, fill="#38bdf8", capstyle=tk.ROUND)
            else:
                # Default: "wave_bars" (4 vibrant fluid equalizer bars)
                colors = ["#38bdf8", "#60a5fa", "#818cf8", "#a78bfa"]
                for i in range(4):
                    x = 8 + i * 10
                    h = 3.5 + 7.5 * (0.5 + 0.5 * math.sin(self.anim_phase + i * 1.3))
                    self.canvas.create_line(x, 13 - h, x, 13 + h, width=3.2, fill=colors[i], capstyle=tk.ROUND)

            # Dynamic moving wave dots on text
            dots_idx = (self.anim_tick_count // 7) % 4
            dots_str = ["", ".", ". .", ". . ."][dots_idx]
            self.text_label.configure(text=f"Listening {dots_str}", text_color="#f8fafc")

        elif self.current_state == "processing":
            # Amber shimmering equalizer wave
            colors = ["#fbbf24", "#f59e0b", "#d97706", "#f59e0b"]
            for i in range(4):
                x = 8 + i * 10
                h = 3.0 + 5.5 * (0.5 + 0.5 * math.sin(self.anim_phase * 1.4 + i * 1.1))
                self.canvas.create_line(x, 13 - h, x, 13 + h, width=3.0, fill=colors[i], capstyle=tk.ROUND)

            dots_idx = (self.anim_tick_count // 7) % 4
            dots_str = ["", ".", ". .", ". . ."][dots_idx]
            self.text_label.configure(text=f"Refining voice {dots_str}", text_color="#fde68a")

        self.root.after(30, self._tick_animation)

    # -------------------------------------------------------------------------
    # STATE TRANSITIONS
    # -------------------------------------------------------------------------
    def show_listening(self):
        """Called when user holds Ctrl+Space."""
        if not self.root:
            return
        def _apply():
            self.current_state = "listening"
            self.container.configure(border_color="#38bdf8")
            self.sub_label.configure(text=f"[ {settings.hotkey.upper()} ]", text_color="#94a3b8")
            self._start_animation()
            self.root.deiconify()
            self.root.lift()
        self.root.after(0, _apply)

    def show_processing(self):
        """Called when user releases Ctrl+Space."""
        if not self.root:
            return
        def _apply():
            self.current_state = "processing"
            self.container.configure(border_color="#f59e0b")
            self.sub_label.configure(text="Groq LPU", text_color="#f59e0b")
            self._start_animation()
            self.root.deiconify()
            self.root.lift()
        self.root.after(0, _apply)

    def show_pasted(self):
        """Called when text is injected into active window."""
        if not self.root:
            return
        def _apply():
            self._stop_animation()
            self.current_state = "pasted"
            self.canvas.delete("all")
            self.canvas.create_text(23, 13, text="✔", fill="#10b981", font=("Segoe UI", 13, "bold"))
            self.container.configure(border_color="#10b981")
            self.text_label.configure(text="Pasted!", text_color="#34d399")
            self.sub_label.configure(text="Done", text_color="#10b981")
            self.root.after(700, self._hide_if_idle)
        self.root.after(0, _apply)

    def show_error(self, message="Error"):
        if not self.root:
            return
        def _apply():
            self._stop_animation()
            self.current_state = "error"
            self.canvas.delete("all")
            self.canvas.create_text(23, 13, text="✕", fill="#f87171", font=("Segoe UI", 12, "bold"))
            self.container.configure(border_color="#f87171")
            self.text_label.configure(text=message[:18], text_color="#fca5a5")
            self.sub_label.configure(text="Error", text_color="#f87171")
            self.root.after(1400, self._hide_if_idle)
        self.root.after(0, _apply)

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

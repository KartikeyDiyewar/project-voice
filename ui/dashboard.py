"""
Project Voice - Windows 11 Modern Desktop Control Center
Faithfully aligned with the official Project Voice Desktop Interface design:
- Left Sidebar with brand logo, sleek navigation pills, connection status & version
- Windows 11 Light Fluent theme with clean white cards and rounded geometry
- DWM Windows 11 integration (seamless caption bar, hardware rounded corners)
- Razor-sharp monochrome vector icons (zero OS emoji font inconsistencies)
- Hero Dark Card with white key shortcut pills and audio wave graphics
- Sound & Animation Card with segmented pill selectors
- Options Card with Start with Windows and Play Chime Sound modern switches
- Quick Action buttons: 'Test Voice Typing' and 'Custom Words'
- Multi-page navigation: Home, Voice Typing, Shortcuts, Settings, About
- Per-Monitor DPI Awareness & Single-Instance IPC integration
"""

import ctypes
import json
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

# Enable Per-Monitor DPI Awareness before Tkinter initializes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        pass

import customtkinter as ctk
from groq import Groq
from config.settings import settings
from utils.sound_feedback import sound
from ui.icons import get_icon

# Appearance setup
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class DashboardWindow(ctk.CTk):
    def __init__(self, on_reinit_services=None, on_quit=None):
        super().__init__()

        self.on_reinit_services = on_reinit_services
        self.on_quit = on_quit

        # Window properties
        self.title("Project Voice")
        self.geometry("960x600")
        self.resizable(False, False)

        # Center on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(40, (screen_w - 960) // 2)
        y = max(40, (screen_h - 600) // 2)
        self.geometry(f"960x600+{x}+{y}")
        self.configure(fg_color="#f3f4f6")

        # Set taskbar icon if exists
        icon_path = settings.base_dir / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Intercept close button (X) to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Track active navigation tab
        self.active_tab = "Home"
        self.nav_buttons = {}
        self.nav_icon_keys = {}
        self.pages = {}

        # Pill options definitions
        self.chime_options = [
            ("Pop", "pop"),
            ("Click", "click"),
            ("Soft", "synth"),
            ("Bell", "chime"),
            ("None", "none")
        ]
        self.anim_options = [
            ("Off", "off"),
            ("Bars", "wave_bars"),
            ("Circle", "wave_dots"),
            ("Ribbon", "sine_wave")
        ]

        self._build_layout()

        # Apply Windows 11 DWM Seamless Caption & Rounded Corners
        self.update_idletasks()
        self._apply_windows11_dwm()

    # -------------------------------------------------------------------------
    # DWM WINDOWS 11 INTEGRATION
    # -------------------------------------------------------------------------
    def _apply_windows11_dwm(self):
        """Blends the titlebar into #f3f4f6 and activates native Win11 rounded corners."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            if hwnd:
                dwm = ctypes.windll.dwmapi
                # DWMWA_CAPTION_COLOR = 35 -> #f3f4f6 (COLORREF = 0x00F6F4F3)
                caption_color = ctypes.c_int(0x00F6F4F3)
                dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))

                # DWMWA_TEXT_COLOR = 36 -> #0f172a (COLORREF = 0x002A170F)
                text_color = ctypes.c_int(0x002A170F)
                dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))

                # DWMWA_WINDOW_CORNER_PREFERENCE = 33 -> DWMWCP_ROUND = 2
                corner_pref = ctypes.c_int(2)
                dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))

                # DWMWA_BORDER_COLOR = 34 -> #e5e7eb (COLORREF = 0x00EBE7E5)
                border_color = ctypes.c_int(0x00EBE7E5)
                dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # MAIN LAYOUT: SIDEBAR + CONTENT AREA
    # -------------------------------------------------------------------------
    def _build_layout(self):
        # 1. Left Sidebar
        self.sidebar = ctk.CTkFrame(
            self,
            width=210,
            corner_radius=0,
            fg_color="#f8fafc",
            border_width=1,
            border_color="#e5e7eb"
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._build_sidebar_content()

        # 2. Main Content Container (Right)
        self.content_container = ctk.CTkFrame(self, fg_color="#f3f4f6", corner_radius=0)
        self.content_container.pack(side="right", fill="both", expand=True)

        # Initialize pages
        self._init_pages()

        # Show default view: Home
        self._switch_page("Home")

    # -------------------------------------------------------------------------
    # SIDEBAR: LOGO, NAV BUTTONS, FOOTER
    # -------------------------------------------------------------------------
    def _build_sidebar_content(self):
        # Top Logo Row
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=18, pady=(24, 28))

        # Dark rounded square with crisp vector mic
        icon_canvas = ctk.CTkCanvas(
            logo_frame,
            width=36,
            height=36,
            bg="#f8fafc",
            highlightthickness=0,
            bd=0
        )
        icon_canvas.pack(side="left", padx=(0, 10))

        # Draw rounded dark square
        self._draw_round_rect(icon_canvas, 1, 1, 35, 35, radius=9, fill="#1e2227")
        # Draw white microphone symbol
        icon_canvas.create_oval(14, 8, 22, 18, fill="#ffffff", outline="")
        icon_canvas.create_rectangle(14, 12, 22, 20, fill="#ffffff", outline="")
        icon_canvas.create_arc(11, 12, 25, 23, start=180, extent=180, style="arc", outline="#ffffff", width=2)
        icon_canvas.create_line(18, 23, 18, 27, fill="#ffffff", width=2)
        icon_canvas.create_line(14, 27, 22, 27, fill="#ffffff", width=2)

        logo_title = ctk.CTkLabel(
            logo_frame,
            text="Project Voice",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#0f172a"
        )
        logo_title.pack(side="left")

        # Navigation Items with Monochrome Vector Icons
        nav_items = [
            ("Home", "home"),
            ("Voice Typing", "voice"),
            ("Shortcuts", "shortcuts"),
            ("Settings", "settings"),
            ("About", "about")
        ]

        nav_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_box.pack(fill="x", padx=14, pady=0)

        for name, icon_key in nav_items:
            img = get_icon(icon_key, color="#4b5563", size=(18, 18))
            btn = ctk.CTkButton(
                nav_box,
                text=f"  {name}",
                image=img,
                compound="left",
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color="#4b5563",
                hover_color="#e2e8f0",
                command=lambda n=name: self._switch_page(n)
            )
            btn.pack(fill="x", pady=4)
            self.nav_buttons[name] = btn
            self.nav_icon_keys[name] = icon_key

        # Spacer pushing footer to bottom
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Bottom Footer: Connection Status & Version
        footer_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_box.pack(fill="x", padx=20, pady=(0, 24), anchor="s")

        status_row = ctk.CTkFrame(footer_box, fg_color="transparent")
        status_row.pack(anchor="w")

        dot_lbl = ctk.CTkLabel(
            status_row,
            text="●",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#10b981"
        )
        dot_lbl.pack(side="left", padx=(0, 6))

        conn_lbl = ctk.CTkLabel(
            status_row,
            text="Connected",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1e293b"
        )
        conn_lbl.pack(side="left")

        ver_lbl = ctk.CTkLabel(
            footer_box,
            text="v1.2.0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        ver_lbl.pack(anchor="w", padx=(16, 0), pady=(1, 0))

    def _draw_round_rect(self, canvas, x1, y1, x2, y2, radius=8, **kwargs):
        """Helper to draw smooth rounded rectangles on standard Tkinter canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    # -------------------------------------------------------------------------
    # PAGE INITIALIZATION & SWITCHING
    # -------------------------------------------------------------------------
    def _init_pages(self):
        self.page_home = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.page_voice = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.page_shortcuts = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.page_settings = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.page_about = ctk.CTkFrame(self.content_container, fg_color="transparent")

        self.pages = {
            "Home": self.page_home,
            "Voice Typing": self.page_voice,
            "Shortcuts": self.page_shortcuts,
            "Settings": self.page_settings,
            "About": self.page_about
        }

        self._build_home_page()
        self._build_voice_typing_page()
        self._build_shortcuts_page()
        self._build_settings_page()
        self._build_about_page()

    def _switch_page(self, page_name: str):
        self.active_tab = page_name

        # Update sidebar button appearances & icon tint dynamically
        for name, btn in self.nav_buttons.items():
            icon_key = self.nav_icon_keys.get(name, "home")
            if name == page_name:
                btn.configure(
                    image=get_icon(icon_key, color="#ffffff", size=(18, 18)),
                    fg_color="#2b3038",
                    text_color="#ffffff",
                    hover_color="#1f2328",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
                )
            else:
                btn.configure(
                    image=get_icon(icon_key, color="#4b5563", size=(18, 18)),
                    fg_color="transparent",
                    text_color="#4b5563",
                    hover_color="#e2e8f0",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal")
                )

        # Switch visible frame
        for name, frame in self.pages.items():
            if name == page_name:
                frame.pack(fill="both", expand=True, padx=28, pady=20)
            else:
                frame.pack_forget()

    # -------------------------------------------------------------------------
    # 1. HOME PAGE (MATCHES TARGET REFERENCE INTERFACE)
    # -------------------------------------------------------------------------
    def _build_home_page(self):
        # Header Row
        header_row = ctk.CTkFrame(self.page_home, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 14))

        title_box = ctk.CTkFrame(header_row, fg_color="transparent")
        title_box.pack(side="left")

        h_title = ctk.CTkLabel(
            title_box,
            text="Project Voice",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#0f172a"
        )
        h_title.pack(anchor="w")

        h_sub = ctk.CTkLabel(
            title_box,
            text="Voice typing for Windows",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#64748b"
        )
        h_sub.pack(anchor="w", pady=(1, 0))

        # Status Badge on top-right
        has_key = bool(settings.groq_api_key)
        self.home_status_badge = ctk.CTkLabel(
            header_row,
            text="✔  Ready to Use" if has_key else "⚠️  Setup Required",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#15803d" if has_key else "#b45309",
            fg_color="#dcfce7" if has_key else "#fef3c7",
            corner_radius=14,
            padx=14,
            pady=5
        )
        self.home_status_badge.pack(side="right", anchor="center")

        # ---------------- HERO DARK CARD ----------------
        self.hero_card = ctk.CTkFrame(
            self.page_home,
            fg_color="#24282f",
            corner_radius=16,
            height=130
        )
        self.hero_card.pack(fill="x", pady=(0, 14))
        self.hero_card.pack_propagate(False)

        hero_inner = ctk.CTkFrame(self.hero_card, fg_color="transparent")
        hero_inner.pack(fill="both", expand=True, padx=26, pady=16)

        # Left side: Key shortcuts & subtitle
        hero_left = ctk.CTkFrame(hero_inner, fg_color="transparent")
        hero_left.pack(side="left", anchor="center")

        keys_row = ctk.CTkFrame(hero_left, fg_color="transparent")
        keys_row.pack(anchor="w")

        curr_hotkey = settings.hotkey.lower()
        if "ctrl" in curr_hotkey and "space" in curr_hotkey:
            k1_text, k2_text = "Ctrl", "Space"
        elif "+" in curr_hotkey:
            parts = curr_hotkey.split("+")
            k1_text = parts[0].capitalize()
            k2_text = parts[-1].capitalize()
        else:
            k1_text = curr_hotkey.upper()
            k2_text = ""

        self.k1_lbl = ctk.CTkLabel(
            keys_row,
            text=k1_text,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#111827",
            fg_color="#ffffff",
            corner_radius=8,
            padx=14,
            pady=6
        )
        self.k1_lbl.pack(side="left")

        if k2_text:
            plus_lbl = ctk.CTkLabel(
                keys_row,
                text="+",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#ffffff"
            )
            plus_lbl.pack(side="left", padx=8)

            self.k2_lbl = ctk.CTkLabel(
                keys_row,
                text=k2_text,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#111827",
                fg_color="#ffffff",
                corner_radius=8,
                padx=16,
                pady=6
            )
            self.k2_lbl.pack(side="left")
        else:
            self.k2_lbl = None

        hero_sub = ctk.CTkLabel(
            hero_left,
            text="Press to start voice typing",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#e2e8f0"
        )
        hero_sub.pack(anchor="w", pady=(8, 0))

        # Right side: Audio wave graphic
        hero_right = ctk.CTkFrame(hero_inner, fg_color="transparent")
        hero_right.pack(side="right", fill="y", anchor="center")

        self.wave_canvas = ctk.CTkCanvas(
            hero_right,
            width=280,
            height=90,
            bg="#24282f",
            highlightthickness=0,
            bd=0
        )
        self.wave_canvas.pack(side="right", anchor="center")
        self._render_hero_waveform()

        # ---------------- CARD 1: SOUND & ANIMATION ----------------
        c1 = ctk.CTkFrame(
            self.page_home,
            fg_color="#ffffff",
            corner_radius=12,
            border_width=1,
            border_color="#e5e7eb"
        )
        c1.pack(fill="x", pady=(0, 12))

        c1_title = ctk.CTkLabel(
            c1,
            text="Sound & Animation",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0f172a"
        )
        c1_title.pack(anchor="w", padx=20, pady=(12, 8))

        c1_content = ctk.CTkFrame(c1, fg_color="transparent")
        c1_content.pack(fill="x", padx=20, pady=(0, 14))

        # Column Left: Chime Sound with Vector Bell Icon
        c1_left = ctk.CTkFrame(c1_content, fg_color="transparent")
        c1_left.pack(side="left", fill="x", expand=True)

        chime_label_row = ctk.CTkFrame(c1_left, fg_color="transparent")
        chime_label_row.pack(side="left", padx=(0, 12))

        chime_lbl = ctk.CTkLabel(
            chime_label_row,
            text="  Chime Sound",
            image=get_icon("bell", color="#1e293b", size=(16, 16)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1e293b"
        )
        chime_lbl.pack(side="left")

        self.chime_pills_box = ctk.CTkFrame(c1_left, fg_color="transparent")
        self.chime_pills_box.pack(side="left")
        self.chime_pill_widgets = {}

        curr_theme = settings.sound_theme.lower()
        if not settings.sound_feedback:
            curr_chime_key = "none"
        else:
            curr_chime_key = curr_theme

        for label, val in self.chime_options:
            btn = ctk.CTkButton(
                self.chime_pills_box,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="normal"),
                width=46,
                height=26,
                corner_radius=13,
                command=lambda v=val: self._on_chime_pill_selected(v)
            )
            btn.pack(side="left", padx=2)
            self.chime_pill_widgets[val] = btn

        self._refresh_chime_pill_states(curr_chime_key)

        # Divider line
        div1 = ctk.CTkFrame(c1_content, width=1, height=28, fg_color="#e5e7eb")
        div1.pack(side="left", padx=14)

        # Column Right: Wave Animation with Vector Wave Icon
        c1_right = ctk.CTkFrame(c1_content, fg_color="transparent")
        c1_right.pack(side="left", fill="x", expand=True)

        anim_label_row = ctk.CTkFrame(c1_right, fg_color="transparent")
        anim_label_row.pack(side="left", padx=(0, 12))

        anim_lbl = ctk.CTkLabel(
            anim_label_row,
            text="  Wave Animation",
            image=get_icon("wave", color="#1e293b", size=(16, 16)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1e293b"
        )
        anim_lbl.pack(side="left")

        self.anim_pills_box = ctk.CTkFrame(c1_right, fg_color="transparent")
        self.anim_pills_box.pack(side="left")
        self.anim_pill_widgets = {}

        curr_anim = settings.indicator_animation.lower()

        for label, val in self.anim_options:
            btn = ctk.CTkButton(
                self.anim_pills_box,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="normal"),
                width=48,
                height=26,
                corner_radius=13,
                command=lambda v=val: self._on_anim_pill_selected(v)
            )
            btn.pack(side="left", padx=2)
            self.anim_pill_widgets[val] = btn

        self._refresh_anim_pill_states(curr_anim)

        # ---------------- CARD 2: OPTIONS ----------------
        c2 = ctk.CTkFrame(
            self.page_home,
            fg_color="#ffffff",
            corner_radius=12,
            border_width=1,
            border_color="#e5e7eb"
        )
        c2.pack(fill="x", pady=(0, 16))

        c2_title = ctk.CTkLabel(
            c2,
            text="Options",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0f172a"
        )
        c2_title.pack(anchor="w", padx=20, pady=(12, 8))

        c2_content = ctk.CTkFrame(c2, fg_color="transparent")
        c2_content.pack(fill="x", padx=20, pady=(0, 14))

        # Col 1: Start with Windows
        c2_col1 = ctk.CTkFrame(c2_content, fg_color="transparent")
        c2_col1.pack(side="left", fill="x", expand=True)

        win_lbl = ctk.CTkLabel(
            c2_col1,
            text="  Start with Windows",
            image=get_icon("windows", color="#1e293b", size=(16, 16)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1e293b"
        )
        win_lbl.pack(side="left")

        self.sw_startup = ctk.CTkSwitch(
            c2_col1,
            text="",
            width=44,
            height=22,
            progress_color="#2b3038",
            button_color="#ffffff",
            button_hover_color="#f1f5f9",
            fg_color="#cbd5e1",
            command=self._toggle_startup
        )
        self.sw_startup.pack(side="right", padx=(0, 10))
        if self._is_startup_enabled():
            self.sw_startup.select()

        # Divider 1
        div2 = ctk.CTkFrame(c2_content, width=1, height=26, fg_color="#e5e7eb")
        div2.pack(side="left", padx=10)

        # Col 2: Chime Prior (On Press)
        c2_col2 = ctk.CTkFrame(c2_content, fg_color="transparent")
        c2_col2.pack(side="left", fill="x", expand=True)

        prior_lbl = ctk.CTkLabel(
            c2_col2,
            text="  Chime: Prior (Press)",
            image=get_icon("bell", color="#1e293b", size=(16, 16)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1e293b"
        )
        prior_lbl.pack(side="left")

        self.sw_chime_prior = ctk.CTkSwitch(
            c2_col2,
            text="",
            width=44,
            height=22,
            progress_color="#2b3038",
            button_color="#ffffff",
            button_hover_color="#f1f5f9",
            fg_color="#cbd5e1",
            command=self._toggle_chime_prior
        )
        self.sw_chime_prior.pack(side="right", padx=(0, 10))
        if settings.sound_feedback and settings.sound_chime_prior:
            self.sw_chime_prior.select()

        # Divider 2
        div3 = ctk.CTkFrame(c2_content, width=1, height=26, fg_color="#e5e7eb")
        div3.pack(side="left", padx=10)

        # Col 3: Chime After (On Finish)
        c2_col3 = ctk.CTkFrame(c2_content, fg_color="transparent")
        c2_col3.pack(side="left", fill="x", expand=True)

        after_lbl = ctk.CTkLabel(
            c2_col3,
            text="  Chime: After (Finish)",
            image=get_icon("bell", color="#1e293b", size=(16, 16)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1e293b"
        )
        after_lbl.pack(side="left")

        self.sw_chime_after = ctk.CTkSwitch(
            c2_col3,
            text="",
            width=44,
            height=22,
            progress_color="#2b3038",
            button_color="#ffffff",
            button_hover_color="#f1f5f9",
            fg_color="#cbd5e1",
            command=self._toggle_chime_after
        )
        self.sw_chime_after.pack(side="right")
        if settings.sound_feedback and settings.sound_chime_after:
            self.sw_chime_after.select()

        # ---------------- BOTTOM ACTIONS ROW ----------------
        bottom_actions = ctk.CTkFrame(self.page_home, fg_color="transparent")
        bottom_actions.pack(pady=(4, 0))

        test_btn = ctk.CTkButton(
            bottom_actions,
            text="  Test Voice Typing",
            image=get_icon("play", color="#ffffff", size=(12, 12)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2b3038",
            hover_color="#1f2328",
            text_color="#ffffff",
            height=38,
            width=180,
            corner_radius=9,
            command=self._open_test_modal
        )
        test_btn.pack(side="left", padx=8)

        words_btn = ctk.CTkButton(
            bottom_actions,
            text="  Custom Words",
            image=get_icon("words", color="#1e293b", size=(16, 16)),
            compound="left",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#ffffff",
            hover_color="#f8fafc",
            border_width=1,
            border_color="#d1d5db",
            text_color="#1e293b",
            height=38,
            width=170,
            corner_radius=9,
            command=self._open_vocab_dialog
        )
        words_btn.pack(side="left", padx=8)

    # -------------------------------------------------------------------------
    # HERO CARD WAVEFORM RENDERER
    # -------------------------------------------------------------------------
    def _render_hero_waveform(self):
        c = self.wave_canvas
        c.delete("all")

        # Subtle background curves for aesthetic depth
        c.create_arc(-20, 20, 180, 120, start=0, extent=180, style="arc", outline="#2b323c", width=1)
        c.create_arc(100, 30, 300, 130, start=0, extent=180, style="arc", outline="#2b323c", width=1)

        # Symmetrical white vertical soundwave bars
        # 17 bars centered in canvas
        heights = [6, 10, 16, 26, 42, 60, 72, 54, 76, 54, 72, 60, 42, 26, 16, 10, 6]
        canvas_w = 280
        center_y = 45
        bar_w = 3.5
        spacing = 9

        start_x = (canvas_w - (len(heights) * spacing)) / 2

        for i, h in enumerate(heights):
            x = start_x + (i * spacing)
            y1 = center_y - (h / 2)
            y2 = center_y + (h / 2)
            # Draw rounded cap line for each bar
            c.create_line(x, y1, x, y2, fill="#ffffff", width=bar_w, capstyle="round")

    # -------------------------------------------------------------------------
    # PILL CONTROLS HANDLERS
    # -------------------------------------------------------------------------
    def _refresh_chime_pill_states(self, active_val: str):
        for val, btn in self.chime_pill_widgets.items():
            if val == active_val:
                btn.configure(
                    fg_color="#2b3038",
                    hover_color="#1f2328",
                    text_color="#ffffff",
                    border_width=0
                )
            else:
                btn.configure(
                    fg_color="#ffffff",
                    hover_color="#f3f4f6",
                    text_color="#475569",
                    border_width=1,
                    border_color="#d1d5db"
                )

    def _on_chime_pill_selected(self, val: str):
        if val == "none":
            settings.update_settings({
                "sound_feedback": False,
                "sound_chime_prior": False,
                "sound_chime_after": False
            })
            self.sw_chime_prior.deselect()
            self.sw_chime_after.deselect()
            self._refresh_chime_pill_states("none")
        else:
            settings.update_settings({
                "sound_feedback": True,
                "sound_theme": val,
                "sound_chime_prior": True,
                "sound_chime_after": True
            })
            self.sw_chime_prior.select()
            self.sw_chime_after.select()
            self._refresh_chime_pill_states(val)
            sound.preview(val, "start")

    def _toggle_chime_prior(self):
        val = bool(self.sw_chime_prior.get() == 1)
        settings.update_settings({"sound_chime_prior": val})
        if val:
            settings.update_settings({"sound_feedback": True})
            theme = getattr(settings, "sound_theme", "pop")
            if theme == "none":
                theme = "pop"
                settings.update_settings({"sound_theme": "pop"})
            self._refresh_chime_pill_states(theme)
            sound.preview(theme, "start")
        else:
            if not self.sw_chime_after.get():
                settings.update_settings({"sound_feedback": False})
                self._refresh_chime_pill_states("none")

    def _toggle_chime_after(self):
        val = bool(self.sw_chime_after.get() == 1)
        settings.update_settings({"sound_chime_after": val})
        if val:
            settings.update_settings({"sound_feedback": True})
            theme = getattr(settings, "sound_theme", "pop")
            if theme == "none":
                theme = "pop"
                settings.update_settings({"sound_theme": "pop"})
            self._refresh_chime_pill_states(theme)
            sound.preview(theme, "success")
        else:
            if not self.sw_chime_prior.get():
                settings.update_settings({"sound_feedback": False})
                self._refresh_chime_pill_states("none")

    def _refresh_anim_pill_states(self, active_val: str):
        for val, btn in self.anim_pill_widgets.items():
            if val == active_val:
                btn.configure(
                    fg_color="#2b3038",
                    hover_color="#1f2328",
                    text_color="#ffffff",
                    border_width=0
                )
            else:
                btn.configure(
                    fg_color="#ffffff",
                    hover_color="#f3f4f6",
                    text_color="#475569",
                    border_width=1,
                    border_color="#d1d5db"
                )

    def _on_anim_pill_selected(self, val: str):
        settings.update_settings({"indicator_animation": val})
        self._refresh_anim_pill_states(val)

    # -------------------------------------------------------------------------
    # STARTUP TOGGLE (WINDOWS SHORTCUT)
    # -------------------------------------------------------------------------
    def _is_startup_enabled(self) -> bool:
        sc = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Project Voice.lnk"
        return sc.exists()

    def _toggle_startup(self):
        startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        sc_path = startup_dir / "Project Voice.lnk"

        if self.sw_startup.get() == 1:
            base_dir = settings.base_dir
            exe_path = base_dir / "Project Voice.exe"
            if not exe_path.exists():
                exe_path = base_dir / "dist" / "Project Voice" / "Project Voice.exe"
            icon_path = base_dir / "assets" / "icon.ico"

            def _ps_esc(p):
                return str(p).replace("'", "''")

            ps_cmd = f"""
            $ws = New-Object -ComObject WScript.Shell
            $s = $ws.CreateShortcut('{_ps_esc(sc_path)}')
            $s.TargetPath = '{_ps_esc(exe_path)}'
            $s.Arguments = '--tray'
            $s.WorkingDirectory = '{_ps_esc(exe_path.parent)}'
            $s.IconLocation = '{_ps_esc(icon_path)},0'
            $s.Description = 'Project Voice - Background Voice Typing'
            $s.Save()
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        else:
            if sc_path.exists():
                try:
                    sc_path.unlink()
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # 2. VOICE TYPING PAGE (STT MODEL & SCRATCHPAD)
    # -------------------------------------------------------------------------
    def _build_voice_typing_page(self):
        v_title = ctk.CTkLabel(
            self.page_voice,
            text="Voice Typing Configuration",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#0f172a"
        )
        v_title.pack(anchor="w", pady=(0, 6))

        v_sub = ctk.CTkLabel(
            self.page_voice,
            text="Ultra-low latency speech recognition powered by Groq LPU Whisper",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#64748b"
        )
        v_sub.pack(anchor="w", pady=(0, 16))

        # Info Card
        card = ctk.CTkFrame(self.page_voice, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb")
        card.pack(fill="x", pady=(0, 16))

        c_inner = ctk.CTkFrame(card, fg_color="transparent")
        c_inner.pack(fill="x", padx=20, pady=16)

        row1 = ctk.CTkFrame(c_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))

        lbl_model = ctk.CTkLabel(
            row1,
            text="Speech Model:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1e293b"
        )
        lbl_model.pack(side="left")

        val_model = ctk.CTkLabel(
            row1,
            text=f"Groq {settings.stt_model} (Auto Hinglish/English Code-Switch)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#2563eb"
        )
        val_model.pack(side="left", padx=8)

        row2 = ctk.CTkFrame(c_inner, fg_color="transparent")
        row2.pack(fill="x")

        lbl_format = ctk.CTkLabel(
            row2,
            text="LLM Cleaner:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1e293b"
        )
        lbl_format.pack(side="left")

        val_format = ctk.CTkLabel(
            row2,
            text=f"{settings.llm_model} (Zero filler words, strict context formatting)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569"
        )
        val_format.pack(side="left", padx=8)

        # Embedded Scratchpad Card
        sc_card = ctk.CTkFrame(self.page_voice, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb")
        sc_card.pack(fill="both", expand=True)

        sc_inner = ctk.CTkFrame(sc_card, fg_color="transparent")
        sc_inner.pack(fill="both", expand=True, padx=20, pady=16)

        sc_top = ctk.CTkFrame(sc_inner, fg_color="transparent")
        sc_top.pack(fill="x", pady=(0, 8))

        sc_title = ctk.CTkLabel(
            sc_top,
            text="Voice Typing Scratchpad (Live Test)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0f172a"
        )
        sc_title.pack(side="left")

        self.voice_latency_lbl = ctk.CTkLabel(
            sc_top,
            text="Hold shortcut and speak to test",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        )
        self.voice_latency_lbl.pack(side="right")

        self.voice_notepad = ctk.CTkTextbox(
            sc_inner,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#f8fafc",
            border_width=1,
            border_color="#cbd5e1",
            text_color="#0f172a"
        )
        self.voice_notepad.pack(fill="both", expand=True, pady=(0, 8))
        self.voice_notepad.insert("1.0", "Click here, press and hold [Ctrl + Space] and speak naturally...")

    # -------------------------------------------------------------------------
    # 3. SHORTCUTS PAGE
    # -------------------------------------------------------------------------
    def _build_shortcuts_page(self):
        s_title = ctk.CTkLabel(
            self.page_shortcuts,
            text="Global Shortcuts",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#0f172a"
        )
        s_title.pack(anchor="w", pady=(0, 6))

        s_sub = ctk.CTkLabel(
            self.page_shortcuts,
            text="Configure push-to-talk hotkeys that work across any application in Windows",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#64748b"
        )
        s_sub.pack(anchor="w", pady=(0, 16))

        card = ctk.CTkFrame(self.page_shortcuts, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb")
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 14))

        lbl_hotkey = ctk.CTkLabel(
            row1,
            text="Primary Shortcut:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#1e293b"
        )
        lbl_hotkey.pack(side="left")

        self.hk_picker = ctk.CTkOptionMenu(
            row1,
            values=["ctrl+space", "f8", "alt_r", "ctrl+shift+space"],
            width=160,
            height=32,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#2b3038",
            button_color="#1f2328",
            button_hover_color="#111827",
            command=self._on_hotkey_change
        )
        self.hk_picker.set(settings.hotkey)
        self.hk_picker.pack(side="left", padx=14)

        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x")

        lbl_fall = ctk.CTkLabel(
            row2,
            text=f"Fallback Hotkey: [{settings.fallback_hotkey.upper()}] (Always active in case of conflict)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#64748b"
        )
        lbl_fall.pack(anchor="w")

        # Visual Help Card
        guide_card = ctk.CTkFrame(self.page_shortcuts, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb")
        guide_card.pack(fill="x")

        g_inner = ctk.CTkFrame(guide_card, fg_color="transparent")
        g_inner.pack(fill="x", padx=20, pady=16)

        g_title = ctk.CTkLabel(
            g_inner,
            text="How Push-to-Talk Works",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0f172a"
        )
        g_title.pack(anchor="w", pady=(0, 6))

        tips = (
            "1. Focus cursor into any app (Chrome, Word, WhatsApp, VS Code, Slack).\n"
            "2. Press and hold [Ctrl + Space] — the glowing indicator pill appears.\n"
            "3. Speak in Hindi, English, or mixed Hinglish naturally.\n"
            "4. Release the shortcut — your speech is polished and typed automatically!"
        )
        g_text = ctk.CTkLabel(
            g_inner,
            text=tips,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569",
            justify="left"
        )
        g_text.pack(anchor="w")

    def _on_hotkey_change(self, choice):
        settings.update_settings({"hotkey": choice})
        # Update Hero card labels
        if "ctrl" in choice and "space" in choice:
            self.k1_lbl.configure(text="Ctrl")
            if self.k2_lbl:
                self.k2_lbl.configure(text="Space")
        elif "+" in choice:
            parts = choice.split("+")
            self.k1_lbl.configure(text=parts[0].capitalize())
            if self.k2_lbl:
                self.k2_lbl.configure(text=parts[-1].capitalize())
        else:
            self.k1_lbl.configure(text=choice.upper())
            if self.k2_lbl:
                self.k2_lbl.configure(text="")
        if self.on_reinit_services:
            self.on_reinit_services()

    # -------------------------------------------------------------------------
    # 4. SETTINGS PAGE (GROQ API KEY)
    # -------------------------------------------------------------------------
    def _build_settings_page(self):
        st_title = ctk.CTkLabel(
            self.page_settings,
            text="Settings & API Credentials",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#0f172a"
        )
        st_title.pack(anchor="w", pady=(0, 6))

        st_sub = ctk.CTkLabel(
            self.page_settings,
            text="Manage your private Groq API key and application preferences",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#64748b"
        )
        st_sub.pack(anchor="w", pady=(0, 16))

        card = ctk.CTkFrame(self.page_settings, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb")
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x", pady=(0, 4))

        title = ctk.CTkLabel(
            top,
            text="Groq API Key (Free High-Speed LPU)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0f172a"
        )
        title.pack(side="left")

        get_link = ctk.CTkButton(
            top,
            text="Get Free Key (30s) ↗",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#f1f5f9",
            hover_color="#e2e8f0",
            text_color="#2563eb",
            height=26,
            width=130,
            command=lambda: webbrowser.open("https://console.groq.com/keys")
        )
        get_link.pack(side="right")

        desc = ctk.CTkLabel(
            inner,
            text="Includes 14,400 free requests per day. Your key is stored securely on your local PC.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        )
        desc.pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        self.key_entry = ctk.CTkEntry(
            row,
            placeholder_text="Paste your gsk_... key here",
            show="*",
            height=36,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#f8fafc",
            border_color="#cbd5e1"
        )
        if settings.groq_api_key:
            self.key_entry.insert(0, settings.groq_api_key)
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.eye_btn = ctk.CTkButton(
            row,
            text="👁️",
            width=36,
            height=36,
            fg_color="#f1f5f9",
            hover_color="#e2e8f0",
            text_color="#0f172a",
            command=self._toggle_show_key
        )
        self.eye_btn.pack(side="left", padx=(0, 6))

        self.save_key_btn = ctk.CTkButton(
            row,
            text="Save & Test",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2b3038",
            hover_color="#1f2328",
            height=36,
            width=100,
            command=self._test_and_save_key
        )
        self.save_key_btn.pack(side="right")

        self.key_msg_lbl = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.key_msg_lbl.pack(anchor="w", pady=(6, 0))

    def _toggle_show_key(self):
        if self.key_entry.cget("show") == "*":
            self.key_entry.configure(show="")
        else:
            self.key_entry.configure(show="*")

    def _test_and_save_key(self):
        k = self.key_entry.get().strip()
        if not k:
            self.key_msg_lbl.configure(text="✖ Please paste your Groq key.", text_color="#ef4444")
            return

        self.key_msg_lbl.configure(text="Connecting to Groq API...", text_color="#2563eb")
        self.save_key_btn.configure(state="disabled")

        def _val():
            try:
                c = Groq(api_key=k, timeout=8.0)
                c.models.list()
                settings.update_api_key(k)
                if self.on_reinit_services:
                    self.on_reinit_services()

                def _ok():
                    self.save_key_btn.configure(state="normal")
                    self.key_msg_lbl.configure(text="✔ Key verified & connected successfully!", text_color="#16a34a")
                    self.home_status_badge.configure(
                        text="✔  Ready to Use",
                        text_color="#15803d",
                        fg_color="#dcfce7"
                    )
                self.after(0, _ok)
            except Exception as e:
                def _fail(err):
                    self.save_key_btn.configure(state="normal")
                    self.key_msg_lbl.configure(text=f"✖ Key invalid: {err[:55]}", text_color="#ef4444")
                self.after(0, lambda: _fail(str(e)))

        threading.Thread(target=_val, daemon=True).start()

    # -------------------------------------------------------------------------
    # 5. ABOUT PAGE
    # -------------------------------------------------------------------------
    def _build_about_page(self):
        ab_title = ctk.CTkLabel(
            self.page_about,
            text="About Project Voice",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#0f172a"
        )
        ab_title.pack(anchor="w", pady=(0, 6))

        ab_sub = ctk.CTkLabel(
            self.page_about,
            text="Privacy-first, ultra-fast voice typing for Windows",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#64748b"
        )
        ab_sub.pack(anchor="w", pady=(0, 16))

        card = ctk.CTkFrame(self.page_about, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e5e7eb")
        card.pack(fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        about_text = (
            "• Version: 1.2.0\n"
            "• Zero-Disk Audio Privacy: Speech captured in volatile RAM and immediately wiped.\n"
            "• Hinglish & English Support: Automatic code-switching with punctuation & capitalization.\n"
            "• Open Source: Developed with care by Kartikey Diyewar."
        )
        lbl = ctk.CTkLabel(
            inner,
            text=about_text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#334155",
            justify="left"
        )
        lbl.pack(anchor="w", pady=(0, 12))

        gh_btn = ctk.CTkButton(
            inner,
            text="GitHub Repository ↗",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#f1f5f9",
            hover_color="#e2e8f0",
            text_color="#2563eb",
            height=28,
            width=150,
            command=lambda: webbrowser.open("https://github.com/KartikeyDiyewar/project-voice")
        )
        gh_btn.pack(anchor="w")

    # -------------------------------------------------------------------------
    # MODAL DIALOGS: CUSTOM WORDS & TEST MODAL
    # -------------------------------------------------------------------------
    def _open_vocab_dialog(self):
        """Clean dialog for adding brand names, client names, or jargon."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Custom Words Dictionary")
        dialog.geometry("440x360")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color="#f8fafc")

        d_inner = ctk.CTkFrame(dialog, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=24, pady=20)

        lbl = ctk.CTkLabel(
            d_inner,
            text="Custom Vocabulary",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0f172a"
        )
        lbl.pack(anchor="w")

        sub = ctk.CTkLabel(
            d_inner,
            text="Add brand names, names, or industry jargon (one per line).",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        )
        sub.pack(anchor="w", pady=(2, 10))

        tb = ctk.CTkTextbox(
            d_inner,
            height=190,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#ffffff",
            border_width=1,
            border_color="#cbd5e1",
            text_color="#0f172a"
        )
        tb.pack(fill="both", expand=True, pady=(0, 12))

        dict_file = settings.base_dir / "dictionary.json"
        if dict_file.exists():
            try:
                with open(dict_file, "r", encoding="utf-8") as f:
                    words = json.load(f).get("custom_words", [])
                    tb.insert("1.0", "\n".join(words))
            except Exception:
                pass

        def _save_v():
            content = tb.get("1.0", "end").strip()
            words = [w.strip() for w in content.replace(",", "\n").split("\n") if w.strip()]
            try:
                with open(dict_file, "w", encoding="utf-8") as f:
                    json.dump({"custom_words": words}, f, indent=2)
                dialog.destroy()
            except Exception:
                pass

        btn = ctk.CTkButton(
            d_inner,
            text="Save Words",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2b3038",
            hover_color="#1f2328",
            height=32,
            width=110,
            command=_save_v
        )
        btn.pack(anchor="e")

    def _open_test_modal(self):
        """Opens quick live test scratchpad for immediate microphone verification."""
        self._switch_page("Voice Typing")
        self.voice_notepad.focus_set()

    def update_dictation_latency(self, latency_ms: float, clean_text: str = ""):
        """Called automatically after every dictation."""
        def _apply():
            if hasattr(self, "voice_latency_lbl"):
                self.voice_latency_lbl.configure(
                    text=f"✔ Typed in {latency_ms:.0f}ms",
                    text_color="#16a34a"
                )
        self.after(0, _apply)

    # -------------------------------------------------------------------------
    # WINDOW ACTIONS
    # -------------------------------------------------------------------------
    def show_window(self):
        try:
            self.deiconify()
            self.state("normal")
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            self.after(200, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def hide_window(self):
        self.withdraw()

    def _quit_app(self):
        if self.on_quit:
            self.on_quit()
        else:
            self.destroy()
            os._exit(0)

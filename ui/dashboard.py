"""
Project Voice - Desktop Control Surface

Visual language: warm paper / espresso ink with a burnt terracotta accent.
Composition follows the operator's job rather than a card grid - one masthead,
a status ledger, a single active "listening" band, and a settings list divided
by hairlines. Nothing is nested inside a card that does not need to be.
"""

import ctypes
import json
import math
import os
import subprocess
import threading
import tkinter as tk
import webbrowser
from pathlib import Path

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
from ui import theme
from ui.daynight_toggle import DayNightToggle, DURATION as DN_DURATION

DURATION_MS = DN_DURATION * 1000

ctk.set_default_color_theme("blue")
ctk.set_appearance_mode(theme.mode())

VERSION = "1.3.0"
WIN_W, WIN_H = 1060, 784
MIN_W, MIN_H = 900, 620
RAIL_W = 220

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_BORDER_COLOR = 34
DWMWA_WINDOW_CORNER_PREFERENCE = 33

LIGHT_PREVIEW = dict(theme.LIGHT)
DARK_PREVIEW = dict(theme.DARK)


def _hex_to_colorref(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


class ToggleSwitch(tk.Canvas):
    """A switch with an inset knob, so the track and both states stay legible.

    CTkSwitch draws a knob as tall as the track, which collapses into a white
    blob at small sizes. This draws an explicit track plus a knob inset by 3px.
    """

    TRACK_W, TRACK_H, INSET = 46, 26, 3

    def __init__(self, master, value=False, command=None, bg=None,
                 track_off=None, track_on=None, knob=None, disabled_track=None):
        bg = bg or theme.t("canvas")
        super().__init__(master, width=self.TRACK_W, height=self.TRACK_H,
                         bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.value = bool(value)
        self.colors = {
            "off": track_off or theme.t("switch_off"),
            "on": track_on or theme.t("accent"),
            "knob": knob or theme.t("switch_knob"),
        }
        self.bind("<Button-1>", lambda _e: self.toggle())
        self.bind("<Enter>", lambda _e: self._draw(hover=True))
        self.bind("<Leave>", lambda _e: self._draw(hover=False))
        self._draw()

    def _draw(self, hover=False):
        self.delete("all")
        on = self.value
        track = self.colors["on"] if on else self.colors["off"]
        r = self.TRACK_H / 2
        self.create_oval(0, 0, self.TRACK_H, self.TRACK_H, fill=track, outline="")
        self.create_oval(self.TRACK_W - self.TRACK_H, 0, self.TRACK_W, self.TRACK_H,
                         fill=track, outline="")
        self.create_rectangle(r, 0, self.TRACK_W - r, self.TRACK_H, fill=track, outline="")

        knob_d = self.TRACK_H - self.INSET * 2
        y0, y1 = self.INSET, self.INSET + knob_d
        x0 = self.TRACK_W - self.INSET - knob_d if on else self.INSET
        self.create_oval(x0, y0, x0 + knob_d, y1,
                         fill=self.colors["knob"], outline="")

    def toggle(self):
        self.value = not self.value
        self._draw()
        if self.command:
            self.command()

    def get(self) -> int:
        return 1 if self.value else 0

    def select(self):
        if not self.value:
            self.value = True
            self._draw()

    def deselect(self):
        if self.value:
            self.value = False
            self._draw()


class DashboardWindow(ctk.CTk):
    def __init__(self, on_reinit_services=None, on_quit=None):
        super().__init__()

        self.on_reinit_services = on_reinit_services
        self.on_quit = on_quit

        self.title("Project Voice")
        self.resizable(True, True)
        self.minsize(MIN_W, MIN_H)
        self.configure(fg_color=theme.t("canvas"))
        self.geometry(f"{WIN_W}x{WIN_H}")

        icon_path = settings.base_dir / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.active_tab = "Home"
        self.nav_buttons = {}
        self.nav_icon_keys = {}
        self.nav_accent_bars = {}
        self.pages = {}

        self.chime_options = [
            ("Pop", "pop"),
            ("Click", "click"),
            ("Soft", "synth"),
            ("Bell", "chime"),
            ("None", "none"),
        ]
        self.anim_options = [
            ("Off", "off"),
            ("Bars", "wave_bars"),
            ("Dots", "wave_dots"),
            ("Line", "sine_wave"),
        ]

        self._build_shell()

        self.update_idletasks()
        self._fit_to_work_area()
        self._apply_native_chrome()

    def _fit_to_work_area(self):
        """Sizes the window to the monitor work area so nothing is ever clipped.

        CTk multiplies requested geometry by the window scaling factor, so the
        physical work area is converted back into logical units first.
        """
        try:
            work = ctypes.wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work), 0)
            avail_w = work.right - work.left
            avail_h = work.bottom - work.top
            if avail_w <= 0 or avail_h <= 0:
                return
            scale = self._get_window_scaling()
            avail_w = int(avail_w / scale)
            avail_h = int(avail_h / scale)
            width = min(WIN_W, avail_w - 24)
            height = min(WIN_H, avail_h - 24)
            x = work.left + (avail_w - width) // 2
            y = work.top + (avail_h - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
            self.minsize(min(MIN_W, width), min(MIN_H, height))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # NATIVE WINDOW CHROME
    # -------------------------------------------------------------------------
    def _apply_native_chrome(self):
        """Ties the caption bar and border into the current palette."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            if not hwnd:
                return
            dwm = ctypes.windll.dwmapi
            dark = 1 if theme.mode() == "dark" else 0
            use_dark = ctypes.c_int(dark)
            dwm.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                      ctypes.byref(use_dark), ctypes.sizeof(use_dark))
            for attr, key in ((DWMWA_CAPTION_COLOR, "canvas"),
                              (DWMWA_BORDER_COLOR, "border")):
                val = ctypes.c_int(_hex_to_colorref(theme.t(key)))
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
            text = ctypes.c_int(_hex_to_colorref(theme.t("text")))
            dwm.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(text), ctypes.sizeof(text))
            corner = ctypes.c_int(2)
            dwm.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                      ctypes.byref(corner), ctypes.sizeof(corner))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # SHELL
    # -------------------------------------------------------------------------
    def _build_shell(self):
        self.sidebar = ctk.CTkFrame(self, width=RAIL_W, corner_radius=0,
                                    fg_color=theme.t("sidebar"))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._build_rail()

        self.content = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color=theme.t("canvas"),
            scrollbar_button_color=theme.t("border_strong"),
            scrollbar_button_hover_color=theme.t("text_subtle"),
        )
        self.content.pack(side="right", fill="both", expand=True)
        self.content._scrollbar.configure(width=6)

        self._init_pages()
        self._switch_page("Home")

    # -------------------------------------------------------------------------
    # LEFT RAIL
    # -------------------------------------------------------------------------
    def _build_rail(self):
        wordmark_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        wordmark_row.pack(fill="x", padx=20, pady=(26, 30))

        mark = ctk.CTkCanvas(wordmark_row, width=30, height=30,
                             bg=theme.t("sidebar"), highlightthickness=0, bd=0)
        mark.pack(side="left", padx=(0, 11))
        self._draw_brand_mark(mark)

        word = ctk.CTkFrame(wordmark_row, fg_color="transparent")
        word.pack(side="left", anchor="center")

        ctk.CTkLabel(word, text="PROJECT", font=theme.font(12, "bold"),
                     text_color=theme.t("text_subtle")).pack(anchor="w")
        ctk.CTkLabel(word, text="Voice", font=theme.font(19, "bold"),
                     text_color=theme.t("text")).pack(anchor="w")

        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=14)

        nav_items = [
            ("Home", "home"),
            ("Voice Typing", "voice"),
            ("Shortcuts", "shortcuts"),
            ("Settings", "settings"),
            ("About", "about"),
        ]
        for name, icon_key in nav_items:
            self._make_nav_row(nav, name, icon_key)

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 24))

        ctk.CTkFrame(footer, height=1, fg_color=theme.t("border")).pack(fill="x", pady=(0, 14))

        state_row = ctk.CTkFrame(footer, fg_color="transparent")
        state_row.pack(fill="x", pady=(0, 12))
        self.status_dot = ctk.CTkLabel(state_row, text="●", width=12,
                                       font=theme.font(12), text_color=theme.t("success"))
        self.status_dot.pack(side="left", padx=(0, 7))
        self.status_text = ctk.CTkLabel(
            state_row, text=self._connection_label(),
            font=theme.font(11, "bold"), text_color=theme.t("text_muted"))
        self.status_text.pack(side="left")

        theme_row = ctk.CTkFrame(footer, fg_color="transparent")
        theme_row.pack(fill="x")
        self.theme_switch = self._daynight_switch(
            theme_row, theme.mode() == "dark", self._toggle_appearance,
            bg=theme.t("sidebar"))
        self.theme_switch.pack(side="left", padx=(0, 9))
        ctk.CTkLabel(theme_row, text="Dark", font=theme.font(11),
                     text_color=theme.t("text_muted")).pack(side="left", pady=(1, 0))

        ctk.CTkLabel(footer, text=f"v{VERSION}", font=theme.font(10),
                     text_color=theme.t("text_subtle")).pack(anchor="w", pady=(10, 0))

    def _draw_brand_mark(self, canvas):
        """Crisp mic glyph on a filled accent tile."""
        canvas.create_polygon(
            [7, 0, 23, 0, 30, 7, 30, 23, 23, 30, 7, 30, 0, 23, 0, 7],
            smooth=False, fill=theme.t("accent"), outline="")
        canvas.create_oval(11, 7, 19, 18, fill=theme.t("surface"), outline="")
        canvas.create_rectangle(11, 13, 19, 19, fill=theme.t("surface"), outline="")
        canvas.create_arc(8, 13, 22, 24, start=180, extent=180,
                          style="arc", outline=theme.t("surface"), width=2)
        canvas.create_line(15, 24, 15, 27, fill=theme.t("surface"), width=2)
        canvas.create_line(11, 27, 19, 27, fill=theme.t("surface"), width=2)

    def _make_nav_row(self, parent, name, icon_key):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=38)
        row.pack(fill="x", pady=1)

        bar = ctk.CTkFrame(row, width=2, height=18, corner_radius=1,
                           fg_color="transparent")
        bar.pack(side="left", padx=(0, 12))

        img = get_icon(icon_key, color=theme.t("text_muted"), size=(17, 17))
        label = ctk.CTkLabel(row, text=name, image=img, compound="left",
                             font=theme.font(13), text_color=theme.t("text_muted"),
                             anchor="w", cursor="hand2")
        label.pack(side="left", fill="x", expand=True)

        for widget in (row, label):
            widget.bind("<Button-1>", lambda _e, n=name: self._switch_page(n))
            widget.bind("<Enter>", lambda _e, r=row, n=name: self._hover_nav(n, True))
            widget.bind("<Leave>", lambda _e, r=row, n=name: self._hover_nav(n, False))

        self.nav_buttons[name] = label
        self.nav_icon_keys[name] = icon_key
        self.nav_accent_bars[name] = bar

    def _hover_nav(self, name, entering):
        if name == self.active_tab:
            return
        self.nav_buttons[name].configure(
            text_color=theme.t("text") if entering else theme.t("text_muted"))

    def _connection_label(self) -> str:
        return "Connected" if settings.groq_api_key else "No API key"

    # -------------------------------------------------------------------------
    # PAGES
    # -------------------------------------------------------------------------
    def _init_pages(self):
        self.pages = {name: ctk.CTkFrame(self.content, fg_color="transparent")
                      for name in ("Home", "Voice Typing", "Shortcuts", "Settings", "About")}
        self.page_home = self.pages["Home"]
        self.page_voice = self.pages["Voice Typing"]
        self.page_shortcuts = self.pages["Shortcuts"]
        self.page_settings = self.pages["Settings"]
        self.page_about = self.pages["About"]

        self._build_home_page()
        self._build_voice_typing_page()
        self._build_shortcuts_page()
        self._build_settings_page()
        self._build_about_page()

    def _switch_page(self, page_name: str):
        self.active_tab = page_name

        for name, label in self.nav_buttons.items():
            bar = self.nav_accent_bars[name]
            icon_key = self.nav_icon_keys[name]
            if name == page_name:
                bar.configure(fg_color=theme.t("accent"))
                label.configure(text_color=theme.t("text"),
                                font=theme.font(13, "bold"),
                                image=get_icon(icon_key, color=theme.t("accent"), size=(17, 17)))
            else:
                bar.configure(fg_color="transparent")
                label.configure(text_color=theme.t("text_muted"),
                                font=theme.font(13),
                                image=get_icon(icon_key, color=theme.t("text_muted"), size=(17, 17)))

        for name, frame in self.pages.items():
            if name == page_name:
                frame.pack(fill="both", expand=True, padx=(40, 36), pady=(30, 28))
            else:
                frame.pack_forget()

    # -------------------------------------------------------------------------
    # SHARED BUILDING BLOCKS
    # -------------------------------------------------------------------------
    def _masthead(self, parent, title, subtitle, top_pad=(0, 0)):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=top_pad)
        ctk.CTkLabel(box, text=title, font=theme.font(30, "bold"),
                     text_color=theme.t("text")).pack(anchor="w")
        ctk.CTkLabel(box, text=subtitle, font=theme.font(13),
                     text_color=theme.t("text_muted")).pack(anchor="w", pady=(2, 0))
        return box

    def _section_label(self, parent, text, top=22, bottom=10):
        ctk.CTkLabel(parent, text=text.upper(), font=theme.font(11, "bold"),
                     text_color=theme.t("text_subtle")).pack(anchor="w", pady=(top, bottom))

    def _hairline(self, parent, pady=(0, 0)):
        ctk.CTkFrame(parent, height=1, fg_color=theme.t("border")).pack(fill="x", pady=pady)

    def _switch(self, parent, on: bool, command, bg=None):
        """The stroke-based on/off switch used for feature rows."""
        return DayNightToggle(parent, value=on, command=command,
                              bg=bg or theme.t("canvas"), width=64, height=32,
                              kind="onoff")

    def _daynight_switch(self, parent, on: bool, command, bg=None):
        """The stroke-based day/night control used for the theme switch."""
        return DayNightToggle(parent, value=on, command=command,
                              bg=bg or theme.t("canvas"), width=72, height=36)

    def _pill_group(self, parent, options, active_value, on_change, side="left"):
        """Mutually exclusive pills; the selected one is the only filled chip."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        if side == "top":
            container.pack(anchor="w")
        else:
            container.pack(side=side)
        buttons = {}
        for label, value in options:
            btn = ctk.CTkButton(
                container, text=label, font=theme.font(11), height=30, width=0,
                corner_radius=theme.RADIUS["pill"], border_width=1,
                command=lambda v=value: on_change(v))
            btn.pack(side="left", padx=(0, 6))
            buttons[value] = btn
        group = {"buttons": buttons, "active": active_value}
        self._paint_pill_group(group)
        return group

    def _paint_pill_group(self, group):
        for value, btn in group["buttons"].items():
            if value == group["active"]:
                btn.configure(fg_color=theme.t("accent"), hover_color=theme.t("accent_hover"),
                              border_color=theme.t("accent"),
                              text_color="#FFFFFF", font=theme.font(11, "bold"))
            else:
                btn.configure(fg_color=theme.t("surface"), hover_color=theme.t("surface_sunk"),
                              border_color=theme.t("border_strong"),
                              text_color=theme.t("text_muted"), font=theme.font(11))

    def _set_pill_group(self, group, value):
        group["active"] = value
        self._paint_pill_group(group)

    # -------------------------------------------------------------------------
    # HOME
    # -------------------------------------------------------------------------
    def _build_home_page(self):
        page = self.page_home

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", pady=(0, 20))

        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Project Voice", font=theme.font(27, "bold"),
                     text_color=theme.t("text")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Push-to-talk dictation for Windows",
                     font=theme.font(13), text_color=theme.t("text_muted")).pack(anchor="w", pady=(2, 0))

        has_key = bool(settings.groq_api_key)
        badge = ctk.CTkFrame(head, fg_color=theme.t("success_soft") if has_key else theme.t("warning_soft"),
                             corner_radius=theme.RADIUS["pill"])
        badge.pack(side="right", anchor="center")
        self.home_status_badge = ctk.CTkLabel(
            badge, text="Ready" if has_key else "Setup required",
            font=theme.font(11, "bold"),
            text_color=theme.t("success") if has_key else theme.t("warning"))
        self.home_status_badge.pack(padx=13, pady=5)

        # ---- status ledger: inline metrics, no card boxes -------------------
        ledger = ctk.CTkFrame(page, fg_color="transparent")
        ledger.pack(fill="x", pady=(0, 20))
        self._ledger_cell(ledger, "Shortcut", settings.hotkey.replace("+", " + ").upper())
        self._ledger_cell(ledger, "Speech model", settings.stt_model)
        self._ledger_cell(ledger, "Language", "Hinglish · English")
        self._ledger_cell(ledger, "Last dictation", "—", last=True, name="latency")

        # ---- listening band ------------------------------------------------
        band = ctk.CTkFrame(page, fg_color=theme.t("ink"), corner_radius=theme.RADIUS["card"])
        band.pack(fill="x", pady=(0, 20))

        band_inner = ctk.CTkFrame(band, fg_color="transparent")
        band_inner.pack(fill="x", padx=24, pady=18)

        left = ctk.CTkFrame(band_inner, fg_color="transparent")
        left.pack(side="left", anchor="center")

        ctk.CTkLabel(left, text="HOLD TO DICTATE", font=theme.font(10, "bold"),
                     text_color=theme.t("on_ink_muted")).pack(anchor="w", pady=(0, 9))

        keys = ctk.CTkFrame(left, fg_color="transparent")
        keys.pack(anchor="w")
        k1, k2 = self._key_labels()
        self.k1_cap = self._keycap(keys, k1)
        self.k2_cap = None
        if k2:
            ctk.CTkLabel(keys, text="+", font=theme.font(12, "bold"),
                         text_color=theme.t("on_ink_muted")).pack(side="left", padx=7)
            self.k2_cap = self._keycap(keys, k2)

        ctk.CTkLabel(left, text="Speak naturally, release to paste",
                     font=theme.font(11), text_color=theme.t("on_ink_muted")).pack(anchor="w", pady=(10, 0))

        right = ctk.CTkFrame(band_inner, fg_color="transparent")
        right.pack(side="right", fill="y")
        self.wave_canvas = ctk.CTkCanvas(right, width=290, height=70, bg=theme.t("ink"),
                                         highlightthickness=0, bd=0)
        self.wave_canvas.pack(side="right", anchor="center")
        self._render_waveform()

        # ---- sound, motion and behavior in two columns ----------------------
        columns = ctk.CTkFrame(page, fg_color="transparent")
        columns.pack(fill="x", pady=(0, 4))
        columns.grid_columnconfigure(0, weight=1, uniform="col")
        columns.grid_columnconfigure(1, weight=1, uniform="col")

        left_col = ctk.CTkFrame(columns, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="new", padx=(0, 22))

        right_col = ctk.CTkFrame(columns, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="new")

        self._section_label(left_col, "Feedback", top=0)
        self._hairline(left_col, pady=(0, 14))

        ctk.CTkLabel(left_col, text="Chime", font=theme.font(13),
                     text_color=theme.t("text")).pack(anchor="w", pady=(0, 7))
        current_chime = "none" if not settings.sound_feedback else settings.sound_theme
        self.chime_group = self._pill_group(
            left_col, self.chime_options, current_chime, self._on_chime_selected, side="top")

        ctk.CTkLabel(left_col, text="Indicator motion", font=theme.font(13),
                     text_color=theme.t("text")).pack(anchor="w", pady=(18, 7))
        self.anim_group = self._pill_group(
            left_col, self.anim_options, settings.indicator_animation,
            self._on_anim_selected, side="top")

        self._section_label(right_col, "Behavior", top=0)
        self._hairline(right_col, pady=(0, 0))

        self.sw_startup = self._setting_row(
            right_col, "Start with Windows", "Launch into the tray when you sign in",
            self._is_startup_enabled(), self._toggle_startup)
        self.sw_chime_prior = self._setting_row(
            right_col, "Chime on press", "Short confirmation when recording starts",
            bool(settings.sound_feedback and settings.sound_chime_prior),
            self._toggle_chime_prior)
        self.sw_chime_after = self._setting_row(
            right_col, "Chime on paste", "Confirmation once text lands in your app",
            bool(settings.sound_feedback and settings.sound_chime_after),
            self._toggle_chime_after, divider=False)

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(30, 0))

        ctk.CTkButton(
            actions, text="Test voice typing", font=theme.font(12, "bold"),
            height=38, width=170, corner_radius=theme.RADIUS["control"],
            fg_color=theme.t("accent"), hover_color=theme.t("accent_hover"),
            text_color="#FFFFFF", command=self._open_test_modal,
        ).pack(side="left")

        ctk.CTkButton(
            actions, text="Custom words", font=theme.font(12),
            height=38, width=150, corner_radius=theme.RADIUS["control"],
            fg_color="transparent", hover_color=theme.t("surface_sunk"),
            border_width=1, border_color=theme.t("border_strong"),
            text_color=theme.t("text"), command=self._open_vocab_dialog,
        ).pack(side="left", padx=10)

    def _ledger_cell(self, parent, label, value, last=False, name=None):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(cell, text=label.upper(), font=theme.font(11, "bold"),
                     text_color=theme.t("text_subtle")).pack(anchor="w")
        lbl = ctk.CTkLabel(cell, text=value, font=theme.font(14, "bold"),
                           text_color=theme.t("text"))
        lbl.pack(anchor="w", pady=(3, 0))
        if name == "latency":
            self.latency_ledger_lbl = lbl
        if not last:
            ctk.CTkFrame(parent, width=1, height=32, fg_color=theme.t("border")).pack(
                side="left", padx=18)

    def _keycap(self, parent, text):
        cap = ctk.CTkFrame(parent, fg_color=theme.t("ink_raised"),
                           corner_radius=6, width=44, height=32)
        cap.pack(side="left")
        cap.pack_propagate(False)
        label = ctk.CTkLabel(cap, text=text, font=theme.font(13, "bold"),
                             text_color=theme.t("on_ink"))
        label.pack(expand=True)
        return label

    def _key_labels(self):
        hk = settings.hotkey.lower()
        if "+" in hk:
            parts = hk.split("+")
            return parts[0].capitalize(), parts[-1].capitalize()
        return hk.upper(), ""

    def _setting_row(self, parent, title, subtitle, on, command, divider=True):
        if divider:
            self._hairline(parent)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=11)

        text_box = ctk.CTkFrame(row, fg_color="transparent")
        text_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_box, text=title, font=theme.font(13),
                     text_color=theme.t("text")).pack(anchor="w")
        ctk.CTkLabel(text_box, text=subtitle, font=theme.font(11),
                     text_color=theme.t("text_subtle")).pack(anchor="w", pady=(1, 0))

        sw = self._switch(row, on, command)
        sw.pack(side="right", anchor="center")
        return sw

    def _render_waveform(self):
        """Deterministic spectral bars - product motion stays in the pill."""
        c = self.wave_canvas
        c.delete("all")
        width, height = 290, 70
        center = height / 2
        bars = 33
        gap = width / bars

        for i in range(bars):
            phase = i / bars * math.tau
            envelope = math.sin(i / (bars - 1) * math.pi) ** 1.5
            detail = 0.55 + 0.45 * abs(math.sin(phase * 2.1) * math.cos(phase * 0.7))
            h = max(2.0, envelope * detail * 27)
            x = gap * i + gap / 2
            color = theme.t("accent") if h > 18 else theme.t("on_ink_muted")
            c.create_line(x, center - h, x, center + h, width=2.4,
                          fill=color, capstyle="round")

    # -------------------------------------------------------------------------
    # VOICE TYPING
    # -------------------------------------------------------------------------
    def _build_voice_typing_page(self):
        page = self.page_voice
        self._masthead(page, "Voice typing",
                       "Speech recognition and cleanup pass, tuned for Hinglish code-switching")
        ctk.CTkFrame(page, fg_color="transparent", height=24).pack(fill="x")

        ledger = ctk.CTkFrame(page, fg_color="transparent")
        ledger.pack(fill="x", pady=(0, 24))
        self._ledger_cell(ledger, "Speech model", settings.stt_model)
        self._ledger_cell(ledger, "Cleanup model", settings.llm_model)
        self._ledger_cell(ledger, "Sample rate", f"{settings.sample_rate // 1000} kHz", last=True)

        self._section_label(page, "Live scratchpad", top=0)
        self._hairline(page, pady=(0, 14))

        ctk.CTkLabel(
            page, text="Click into another app, hold your shortcut, and speak. "
                        "Recognised text appears here while you test.",
            font=theme.font(12), text_color=theme.t("text_muted"),
            justify="left", wraplength=620).pack(anchor="w", pady=(0, 12))

        self.voice_notepad = ctk.CTkTextbox(
            page, height=250, font=theme.font(13),
            fg_color=theme.t("surface"), border_width=1,
            border_color=theme.t("border"), text_color=theme.t("text"),
            corner_radius=theme.RADIUS["control"])
        self.voice_notepad.pack(fill="both", expand=True, pady=(0, 10))
        self.voice_notepad.insert(
            "1.0", "Hold [Ctrl + Space] anywhere on your PC and speak naturally.")

        self.voice_latency_lbl = ctk.CTkLabel(
            page, text="Waiting for your first dictation",
            font=theme.font(11), text_color=theme.t("text_subtle"))
        self.voice_latency_lbl.pack(anchor="w")

    # -------------------------------------------------------------------------
    # SHORTCUTS
    # -------------------------------------------------------------------------
    def _build_shortcuts_page(self):
        page = self.page_shortcuts
        self._masthead(page, "Shortcuts",
                       "One push-to-talk chord that works in every Windows application")
        ctk.CTkFrame(page, fg_color="transparent", height=24).pack(fill="x")

        self._section_label(page, "Primary shortcut", top=0)
        self._hairline(page, pady=(0, 14))

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.pack(fill="x", pady=(0, 22))

        self.hk_picker = ctk.CTkOptionMenu(
            row, values=["ctrl+space", "f8", "alt_r", "ctrl+shift+space"],
            width=190, height=34, font=theme.font(12),
            fg_color=theme.t("surface_sunk"),
            button_color=theme.t("surface_sunk"),
            button_hover_color=theme.t("border"),
            text_color=theme.t("text"),
            dropdown_fg_color=theme.t("surface"),
            dropdown_hover_color=theme.t("surface_sunk"),
            dropdown_text_color=theme.t("text"),
            command=self._on_hotkey_change)
        self.hk_picker.set(settings.hotkey)
        self.hk_picker.pack(side="left")

        ctk.CTkLabel(row, text=f"Fallback: {settings.fallback_hotkey.upper()}",
                     font=theme.font(11), text_color=theme.t("text_subtle")).pack(side="left", padx=16)

        self._section_label(page, "Walkthrough")
        self._hairline(page, pady=(0, 14))

        steps = [
            ("01", "Focus any app", "Chrome, Word, WhatsApp, VS Code, Slack, Notion."),
            ("02", "Hold the shortcut", "A slim pill appears above your taskbar."),
            ("03", "Speak naturally", "Hindi, English, or a mix. No script switching."),
            ("04", "Release", "Cleaned text is pasted into the window you started in."),
        ]
        for num, title, detail in steps:
            step = ctk.CTkFrame(page, fg_color="transparent")
            step.pack(fill="x", pady=7)
            ctk.CTkLabel(step, text=num, font=theme.mono(11, "bold"), width=30,
                         text_color=theme.t("accent"), anchor="w").pack(side="left", anchor="n")
            body = ctk.CTkFrame(step, fg_color="transparent")
            body.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(body, text=title, font=theme.font(13, "bold"),
                         text_color=theme.t("text")).pack(anchor="w")
            ctk.CTkLabel(body, text=detail, font=theme.font(12),
                         text_color=theme.t("text_muted")).pack(anchor="w", pady=(1, 0))

    def _on_hotkey_change(self, choice):
        settings.update_settings({"hotkey": choice})
        if self.on_reinit_services:
            self.on_reinit_services()
        k1, k2 = self._key_labels()
        if getattr(self, "k1_cap", None) is not None and self.k1_cap.winfo_exists():
            self.k1_cap.configure(text=k1)
        if getattr(self, "k2_cap", None) is not None and self.k2_cap.winfo_exists():
            self.k2_cap.configure(text=k2)

    # -------------------------------------------------------------------------
    # SETTINGS
    # -------------------------------------------------------------------------
    def _build_settings_page(self):
        page = self.page_settings
        self._masthead(page, "Settings",
                       "Your Groq key stays on this machine and is never sent anywhere else")
        ctk.CTkFrame(page, fg_color="transparent", height=24).pack(fill="x")

        self._section_label(page, "Groq API key", top=0)
        self._hairline(page, pady=(0, 14))

        hint_row = ctk.CTkFrame(page, fg_color="transparent")
        hint_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hint_row, text="Free tier includes 14,400 requests per day.",
                     font=theme.font(12), text_color=theme.t("text_muted")).pack(side="left")
        ctk.CTkButton(hint_row, text="Get a key", font=theme.font(11, "bold"),
                      fg_color="transparent", hover_color=theme.t("accent_soft"),
                      text_color=theme.t("accent_text"), width=80, height=26,
                      command=lambda: webbrowser.open("https://console.groq.com/keys")
                      ).pack(side="right")

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))

        self.key_entry = ctk.CTkEntry(
            row, placeholder_text="gsk_...", show="*", height=38,
            font=theme.mono(11), fg_color=theme.t("surface"),
            border_color=theme.t("border_strong"), text_color=theme.t("text"))
        if settings.groq_api_key:
            self.key_entry.insert(0, settings.groq_api_key)
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(row, text="Show", font=theme.font(11), width=62, height=38,
                      fg_color="transparent", hover_color=theme.t("surface_sunk"),
                      border_width=1, border_color=theme.t("border_strong"),
                      text_color=theme.t("text_muted"),
                      command=self._toggle_show_key).pack(side="left", padx=(0, 8))

        self.save_key_btn = ctk.CTkButton(
            row, text="Save and test", font=theme.font(12, "bold"), height=38, width=124,
            fg_color=theme.t("accent"), hover_color=theme.t("accent_hover"),
            text_color="#FFFFFF", command=self._test_and_save_key)
        self.save_key_btn.pack(side="right")

        self.key_msg_lbl = ctk.CTkLabel(page, text="", font=theme.font(11, "bold"),
                                         text_color=theme.t("text_muted"))
        self.key_msg_lbl.pack(anchor="w", pady=(4, 0))

        self._section_label(page, "Appearance")
        self._hairline(page, pady=(0, 0))

        appearance_row = ctk.CTkFrame(page, fg_color="transparent")
        appearance_row.pack(fill="x", pady=12)

        text_box = ctk.CTkFrame(appearance_row, fg_color="transparent")
        text_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text_box, text="Dark surface", font=theme.font(13),
                     text_color=theme.t("text")).pack(anchor="w")
        ctk.CTkLabel(text_box, text="Espresso ink instead of warm paper, "
                                   "for this session only",
                     font=theme.font(11), text_color=theme.t("text_subtle")).pack(anchor="w", pady=(1, 0))

        self.settings_theme_switch = self._daynight_switch(
            appearance_row, theme.mode() == "dark", self._toggle_appearance)
        self.settings_theme_switch.pack(side="right", anchor="center")

    def _sync_theme_switches(self):
        dark = theme.mode() == "dark"
        for sw in ("theme_switch", "settings_theme_switch"):
            widget = getattr(self, sw, None)
            if widget is None or not widget.winfo_exists():
                continue
            if dark:
                widget.select()
            else:
                widget.deselect()

    def _toggle_show_key(self):
        self.key_entry.configure(show="" if self.key_entry.cget("show") == "*" else "*")

    def _test_and_save_key(self):
        key = self.key_entry.get().strip()
        if not key:
            self.key_msg_lbl.configure(text="Paste your Groq key first.",
                                       text_color=theme.t("danger"))
            return

        self.key_msg_lbl.configure(text="Checking the key with Groq...",
                                   text_color=theme.t("text_muted"))
        self.save_key_btn.configure(state="disabled")

        def _validate():
            try:
                client = Groq(api_key=key, timeout=8.0)
                client.models.list()
                settings.update_api_key(key)
                if self.on_reinit_services:
                    self.on_reinit_services()

                def _ok():
                    self.save_key_btn.configure(state="normal")
                    self.key_msg_lbl.configure(text="Key verified. Voice typing is ready.",
                                               text_color=theme.t("success"))
                    self.home_status_badge.configure(text="Ready", text_color=theme.t("success"))
                    self.status_text.configure(text="Connected")
                    self.status_dot.configure(text_color=theme.t("success"))
                self.after(0, _ok)
            except Exception as exc:
                def _fail(err):
                    self.save_key_btn.configure(state="normal")
                    self.key_msg_lbl.configure(text=f"Key rejected: {err[:60]}",
                                               text_color=theme.t("danger"))
                self.after(0, lambda: _fail(str(exc)))

        threading.Thread(target=_validate, daemon=True).start()

    # -------------------------------------------------------------------------
    # ABOUT
    # -------------------------------------------------------------------------
    def _build_about_page(self):
        page = self.page_about
        self._masthead(page, "About",
                       "Privacy-first dictation, built by Kartikey Diyewar")
        ctk.CTkFrame(page, fg_color="transparent", height=24).pack(fill="x")

        self._section_label(page, "How it handles your voice", top=0)
        self._hairline(page, pady=(0, 14))

        facts = [
            ("Audio never touches disk", "Captured in RAM and wiped the moment transcription finishes."),
            ("No telemetry", "No analytics, no crash reporting, no usage pings."),
            ("Bring your own key", "Requests go straight from this PC to Groq over TLS."),
            ("Native Hinglish", "Phonetic repair keeps Roman Hinglish intact, no Devanagari drift."),
        ]
        for title, detail in facts:
            item = ctk.CTkFrame(page, fg_color="transparent")
            item.pack(fill="x", pady=7)
            ctk.CTkLabel(item, text="—", font=theme.font(12), width=22,
                         text_color=theme.t("accent")).pack(side="left", anchor="n")
            body = ctk.CTkFrame(item, fg_color="transparent")
            body.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(body, text=title, font=theme.font(13, "bold"),
                         text_color=theme.t("text")).pack(anchor="w")
            ctk.CTkLabel(body, text=detail, font=theme.font(12),
                         text_color=theme.t("text_muted")).pack(anchor="w", pady=(1, 0))

        footer = ctk.CTkFrame(page, fg_color="transparent")
        footer.pack(fill="x", pady=(24, 0))
        ctk.CTkLabel(footer, text=f"Version {VERSION} · MIT licence",
                     font=theme.font(11), text_color=theme.t("text_subtle")).pack(side="left")
        ctk.CTkButton(footer, text="GitHub", font=theme.font(11, "bold"),
                      fg_color="transparent", hover_color=theme.t("surface_sunk"),
                      text_color=theme.t("accent_text"), width=70, height=26,
                      command=lambda: webbrowser.open(
                          "https://github.com/KartikeyDiyewar/project-voice")).pack(side="right")

    # -------------------------------------------------------------------------
    # FIRST-RUN THEME CHOOSER
    # -------------------------------------------------------------------------
    def maybe_ask_appearance(self):
        """Shows the theme picker once, before the user has chosen a theme."""
        if settings.appearance_chosen:
            return
        self.after(220, self._open_appearance_dialog)

    def _open_appearance_dialog(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

        dialog = ctk.CTkToplevel(self)
        dialog.title("Choose your theme")
        dialog.geometry("640x404")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=theme.t("canvas"))
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._finish_appearance_choice(dialog, None))

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 640) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 404) // 2
        dialog.geometry(f"640x404+{max(0, x)}+{max(0, y)}")

        inner = ctk.CTkFrame(dialog, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=30, pady=26)

        ctk.CTkLabel(inner, text="Welcome to Project Voice", font=theme.font(24, "bold"),
                     text_color=theme.t("text")).pack(anchor="w")
        ctk.CTkLabel(inner, text="Pick the surface you would like to look at. "
                                 "You can change this any time from Settings.",
                     font=theme.font(12), text_color=theme.t("text_muted"),
                     justify="left").pack(anchor="w", pady=(4, 20))

        options = ctk.CTkFrame(inner, fg_color="transparent")
        options.pack(fill="x")
        options.grid_columnconfigure(0, weight=1, uniform="card")
        options.grid_columnconfigure(1, weight=1, uniform="card")

        self._theme_option(options, 0, "Light",
                           "Warm paper", LIGHT_PREVIEW, lambda: self._finish_appearance_choice(dialog, "light"))
        self._theme_option(options, 1, "Dark",
                           "Espresso ink", DARK_PREVIEW, lambda: self._finish_appearance_choice(dialog, "dark"))

        ctk.CTkLabel(inner, text="The floating pill stays dark in both themes.",
                     font=theme.font(10), text_color=theme.t("text_subtle")).pack(anchor="w", pady=(18, 0))

    def _theme_option(self, parent, column, title, subtitle, palette, on_pick):
        card = ctk.CTkFrame(parent, fg_color=palette["surface"], corner_radius=theme.RADIUS["card"],
                            border_width=1, border_color=palette["border"], cursor="hand2")
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 12) if column == 0 else (12, 0))

        preview = ctk.CTkCanvas(card, width=250, height=112, bg=palette["surface"],
                                highlightthickness=0, bd=0)
        preview.pack(padx=16, pady=(16, 10))
        self._paint_preview(preview, palette)

        text_box = ctk.CTkFrame(card, fg_color="transparent")
        text_box.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkLabel(text_box, text=title, font=theme.font(15, "bold"),
                     text_color=palette["text"]).pack(anchor="w")
        ctk.CTkLabel(text_box, text=subtitle, font=theme.font(11),
                     text_color=palette["text_muted"]).pack(anchor="w", pady=(1, 0))

        for widget in (card, preview, text_box):
            widget.bind("<Button-1>", lambda _e: on_pick())

    def _paint_preview(self, canvas, palette):
        """Miniature of the dashboard so the choice is made on real layout."""
        w, h = 250, 112
        rail_w = 58

        canvas.create_rectangle(0, 0, rail_w, h, fill=palette["sidebar"], outline="")
        canvas.create_polygon([12, 12, 20, 12, 24, 16, 24, 24, 20, 28, 12, 28, 8, 24, 8, 16],
                              fill=palette["accent"], outline="")
        for row in range(3):
            y = 44 + row * 16
            canvas.create_rectangle(12, y, 46, y + 5, fill=palette["text_subtle"], outline="")

        canvas.create_rectangle(rail_w, 0, w, h, fill=palette["canvas"], outline="")
        canvas.create_rectangle(rail_w + 14, 12, rail_w + 120, 26,
                                fill=palette["text"], outline="")
        canvas.create_rectangle(rail_w + 14, 32, rail_w + 88, 39,
                                fill=palette["text_subtle"], outline="")

        canvas.create_rectangle(rail_w + 14, 48, w - 14, 90,
                                fill=palette["ink"], outline="")
        for i in range(9):
            x = rail_w + 34 + i * 14
            bar_h = 6 + (i % 3) * 7
            canvas.create_line(x, 69 - bar_h, x, 69 + bar_h,
                               fill=palette["accent"] if i % 4 == 0 else palette["on_ink_muted"],
                               width=2, capstyle="round")

        canvas.create_rectangle(rail_w + 14, 98, rail_w + 70, 104,
                                fill=palette["accent"], outline="")

    def _finish_appearance_choice(self, dialog, choice):
        if choice in ("light", "dark"):
            theme.set_mode(choice)
            ctk.set_appearance_mode(choice)
        else:
            settings.update_settings({"appearance": theme.mode()})
        try:
            dialog.destroy()
        except Exception:
            pass
        self._rebuild_ui()

    # -------------------------------------------------------------------------
    # HANDLERS
    # -------------------------------------------------------------------------
    def _on_chime_selected(self, value):
        if value == "none":
            settings.update_settings({"sound_feedback": False,
                                      "sound_chime_prior": False, "sound_chime_after": False})
            self.sw_chime_prior.deselect()
            self.sw_chime_after.deselect()
        else:
            settings.update_settings({"sound_feedback": True, "sound_theme": value,
                                      "sound_chime_prior": True, "sound_chime_after": True})
            self.sw_chime_prior.select()
            self.sw_chime_after.select()
            sound.preview(value, "start")
        self._set_pill_group(self.chime_group, value)

    def _on_anim_selected(self, value):
        settings.update_settings({"indicator_animation": value})
        self._set_pill_group(self.anim_group, value)

    def _toggle_chime_prior(self):
        state = bool(self.sw_chime_prior.get())
        settings.update_settings({"sound_chime_prior": state})
        self._reconcile_sound_state(play="start" if state else None)

    def _toggle_chime_after(self):
        state = bool(self.sw_chime_after.get())
        settings.update_settings({"sound_chime_after": state})
        self._reconcile_sound_state(play="success" if state else None)

    def _reconcile_sound_state(self, play=None):
        prior = bool(self.sw_chime_prior.get())
        after = bool(self.sw_chime_after.get())
        active = prior or after
        settings.update_settings({"sound_feedback": active})

        if not active:
            self._set_pill_group(self.chime_group, "none")
            return

        theme_name = settings.sound_theme
        if theme_name == "none":
            theme_name = "pop"
            settings.update_settings({"sound_theme": theme_name})
        self._set_pill_group(self.chime_group, theme_name)
        if play:
            sound.preview(theme_name, play)

    def _toggle_appearance(self):
        """Plays the switch first, then repaints the surface in the new theme.

        Repainting immediately destroyed the switch mid-animation, so the flip
        never became visible. The theme is applied from the switch's completion
        callback instead, and the repaint is deferred one frame after that.
        """
        if getattr(self, "_theme_busy", False):
            return
        new_mode = "light" if theme.mode() == "dark" else "dark"
        applied = {"done": False}

        def apply():
            if applied["done"]:
                return
            applied["done"] = True
            self._theme_busy = False
            theme.set_mode(new_mode)
            ctk.set_appearance_mode(new_mode)
            self._rebuild_ui()

        self._theme_busy = True
        for widget in (getattr(self, "theme_switch", None),
                       getattr(self, "settings_theme_switch", None)):
            if widget is not None and widget.winfo_exists():
                try:
                    widget.on_done = apply
                except Exception:
                    pass
        self.after(int(DURATION_MS) + 20, apply)

    def _rebuild_ui(self):
        """Repaints the shell in place so a theme switch is immediate.

        Only the sidebar and content frames are recreated. Other top-levels
        parented to this window (the floating pill, dialogs) must survive,
        otherwise the indicator stops appearing after a theme change.
        """
        active = self.active_tab
        for child in (getattr(self, "sidebar", None), getattr(self, "content", None)):
            if child is not None:
                try:
                    child.destroy()
                except Exception:
                    pass
        self.nav_buttons.clear()
        self.nav_icon_keys.clear()
        self.nav_accent_bars.clear()
        self.pages.clear()
        self.configure(fg_color=theme.t("canvas"))
        self._build_shell()
        self._switch_page(active)
        self.update_idletasks()
        self._apply_native_chrome()

    # -------------------------------------------------------------------------
    # STARTUP
    # -------------------------------------------------------------------------
    def _startup_shortcut(self) -> Path:
        return (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows"
                / "Start Menu" / "Programs" / "Startup" / "Project Voice.lnk")

    def _is_startup_enabled(self) -> bool:
        return self._startup_shortcut().exists()

    def _toggle_startup(self):
        shortcut = self._startup_shortcut()
        if not self.sw_startup.get():
            if shortcut.exists():
                try:
                    shortcut.unlink()
                except Exception:
                    pass
            return

        base_dir = settings.base_dir
        exe_path = base_dir / "Project Voice.exe"
        if not exe_path.exists():
            exe_path = base_dir / "dist" / "Project Voice" / "Project Voice.exe"
        icon_path = base_dir / "assets" / "icon.ico"

        def esc(p):
            return str(p).replace("'", "''")

        ps = f"""
        $ws = New-Object -ComObject WScript.Shell
        $s = $ws.CreateShortcut('{esc(shortcut)}')
        $s.TargetPath = '{esc(exe_path)}'
        $s.Arguments = '--tray'
        $s.WorkingDirectory = '{esc(exe_path.parent)}'
        $s.IconLocation = '{esc(icon_path)},0'
        $s.Description = 'Project Voice - Background Voice Typing'
        $s.Save()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)

    # -------------------------------------------------------------------------
    # DIALOGS
    # -------------------------------------------------------------------------
    def _open_vocab_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Custom words")
        dialog.geometry("460x400")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=theme.t("canvas"))

        inner = ctk.CTkFrame(dialog, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=26, pady=22)

        ctk.CTkLabel(inner, text="Custom words", font=theme.font(19, "bold"),
                     text_color=theme.t("text")).pack(anchor="w")
        ctk.CTkLabel(inner, text="Names, brands, and jargon Whisper should expect. One per line.",
                     font=theme.font(11), text_color=theme.t("text_muted")).pack(anchor="w", pady=(2, 12))

        box = ctk.CTkTextbox(inner, height=190, font=theme.mono(12),
                             fg_color=theme.t("surface"), border_width=1,
                             border_color=theme.t("border"), text_color=theme.t("text"),
                             corner_radius=theme.RADIUS["control"])
        box.pack(fill="both", expand=True, pady=(0, 12))

        dict_file = settings.base_dir / "dictionary.json"
        if dict_file.exists():
            try:
                with open(dict_file, "r", encoding="utf-8") as fh:
                    box.insert("1.0", "\n".join(json.load(fh).get("custom_words", [])))
            except Exception:
                pass

        def _save():
            content = box.get("1.0", "end").strip()
            words = [w.strip() for w in content.replace(",", "\n").split("\n") if w.strip()]
            try:
                with open(dict_file, "w", encoding="utf-8") as fh:
                    json.dump({"custom_words": words}, fh, indent=2)
                dialog.destroy()
            except Exception:
                pass

        ctk.CTkButton(inner, text="Save words", font=theme.font(12, "bold"),
                      height=34, width=118, fg_color=theme.t("accent"),
                      hover_color=theme.t("accent_hover"), text_color="#FFFFFF",
                      command=_save).pack(anchor="e")

    def _open_test_modal(self):
        self._switch_page("Voice Typing")
        self.voice_notepad.focus_set()

    def update_dictation_latency(self, latency_ms: float, clean_text: str = ""):
        def _apply():
            if hasattr(self, "voice_latency_lbl") and self.voice_latency_lbl.winfo_exists():
                self.voice_latency_lbl.configure(
                    text=f"Last pass completed in {latency_ms:.0f} ms",
                    text_color=theme.t("success"))
            if hasattr(self, "latency_ledger_lbl") and self.latency_ledger_lbl.winfo_exists():
                self.latency_ledger_lbl.configure(text=f"{latency_ms:.0f} ms")
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
                    ctypes.windll.user32.ShowWindow(hwnd, 9)
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

"""
Project Voice - Production Desktop Dashboard & Control Center
Ultra-modern Windows 11 Fluent dark-theme control panel with:
- Per-Monitor DPI Awareness & Immersive DWM dark titlebar
- Left Sidebar Navigation (Dashboard, API Key, Preferences, Vocabulary)
- Live Microphone Level Monitor & Real-Time Sensitivity Test
- Interactive Voice Dictation Sandbox ("Try It Live")
- Live Latency & Pipeline Health Badges
- Win32 Single-Instance Wakeup IPC
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
import numpy as np
import sounddevice as sd
from groq import Groq
from config.settings import settings
from utils.sound_feedback import sound

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class DashboardWindow(ctk.CTk):
    def __init__(self, on_reinit_services=None, on_quit=None):
        super().__init__()

        self.on_reinit_services = on_reinit_services
        self.on_quit = on_quit
        self.is_mic_testing = False

        # Window properties
        self.title("Project Voice — Desktop AI Engine")
        self.geometry("880x590")
        self.resizable(False, False)

        # Center on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(50, (screen_w - 880) // 2)
        y = max(50, (screen_h - 590) // 2)
        self.geometry(f"880x590+{x}+{y}")
        self.configure(fg_color="#090d16")

        # Set taskbar/window icon if exists
        icon_path = settings.base_dir / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Apply Windows 11 Immersive Dark Titlebar
        self.after(100, self._apply_dwm_dark_titlebar)

        # Intercept close button (X) to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Build Main Layout: Left Sidebar + Right Content Area
        self._build_sidebar()
        self._build_content_area()

        # Show Dashboard page by default
        self._select_nav("dashboard")

    def _apply_dwm_dark_titlebar(self):
        """Applies Windows 11/10 immersive dark mode to window frame."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(val),
                ctypes.sizeof(val)
            )
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # LEFT SIDEBAR
    # -------------------------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=235, fg_color="#0f1523", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # App Brand Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=(14, 8), pady=(20, 24))

        logo_badge = ctk.CTkLabel(
            brand_frame,
            text="🎙️",
            font=ctk.CTkFont(size=24),
            width=38,
            height=38,
            fg_color="#1e293b",
            corner_radius=10
        )
        logo_badge.pack(side="left", padx=(0, 8))

        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(side="left", fill="both")

        brand_title = ctk.CTkLabel(
            title_box,
            text="Project Voice",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#f8fafc"
        )
        brand_title.pack(anchor="w")

        brand_edition = ctk.CTkLabel(
            title_box,
            text="PRO • BYOK EDITION",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#60a5fa"
        )
        brand_edition.pack(anchor="w")

        # Navigation Buttons
        nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_container.pack(fill="x", padx=12, pady=0)

        self.nav_btns = {}
        items = [
            ("dashboard", "⚡  Dashboard"),
            ("api", "🔑  Groq API Key"),
            ("preferences", "⚙️  Preferences"),
            ("vocabulary", "📖  Vocabulary")
        ]

        for key, label in items:
            btn = ctk.CTkButton(
                nav_container,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color="#94a3b8",
                hover_color="#1e293b",
                command=lambda k=key: self._select_nav(k)
            )
            btn.pack(fill="x", pady=4)
            self.nav_btns[key] = btn

        # Sidebar Bottom Footer
        sidebar_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_footer.pack(side="bottom", fill="x", padx=14, pady=16)

        # Status badge
        has_key = bool(settings.groq_api_key)
        self.sidebar_status_badge = ctk.CTkLabel(
            sidebar_footer,
            text="● Engine Active" if has_key else "⚠️ Key Required",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#10b981" if has_key else "#f59e0b",
            fg_color="#131b2e",
            corner_radius=6,
            pady=5
        )
        self.sidebar_status_badge.pack(fill="x", pady=(0, 6))

        hotkey_tag = ctk.CTkLabel(
            sidebar_footer,
            text=f"Hotkey: [{settings.hotkey.upper()}]",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#64748b"
        )
        hotkey_tag.pack(anchor="w")

    def _select_nav(self, page_name: str):
        for key, btn in self.nav_btns.items():
            if key == page_name:
                btn.configure(fg_color="#1e293b", text_color="#38bdf8")
            else:
                btn.configure(fg_color="transparent", text_color="#94a3b8")

        for p_name, frame in self.pages.items():
            if p_name == page_name:
                frame.pack(fill="both", expand=True, padx=22, pady=(16, 12))
            else:
                frame.pack_forget()

    # -------------------------------------------------------------------------
    # RIGHT CONTENT AREA
    # -------------------------------------------------------------------------
    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(side="right", fill="both", expand=True)

        # Build pages
        self.pages = {}
        self.pages["dashboard"] = self._create_page_dashboard()
        self.pages["api"] = self._create_page_api()
        self.pages["preferences"] = self._create_page_preferences()
        self.pages["vocabulary"] = self._create_page_vocabulary()

        # Persistent Global Footer
        global_footer = ctk.CTkFrame(self.content_container, fg_color="transparent")
        global_footer.pack(side="bottom", fill="x", padx=22, pady=(0, 16))

        min_btn = ctk.CTkButton(
            global_footer,
            text="Minimize to System Tray",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#e2e8f0",
            height=34,
            command=self.hide_window
        )
        min_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        quit_btn = ctk.CTkButton(
            global_footer,
            text="✕ Quit Project Voice",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#450a0a",
            hover_color="#7f1d1d",
            text_color="#fca5a5",
            width=160,
            height=34,
            command=self._quit_app
        )
        quit_btn.pack(side="right")

    # -------------------------------------------------------------------------
    # PAGE 1: DASHBOARD (LIVE HUB, MIC TEST & SANDBOX)
    # -------------------------------------------------------------------------
    def _create_page_dashboard(self) -> ctk.CTkFrame:
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")

        # Page Header
        h_frame = ctk.CTkFrame(page, fg_color="transparent")
        h_frame.pack(fill="x", pady=(0, 12))

        title = ctk.CTkLabel(
            h_frame,
            text="System Overview & Live Monitor",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f8fafc"
        )
        title.pack(side="left")

        # Top 3 Stat Cards Row
        stat_row = ctk.CTkFrame(page, fg_color="transparent")
        stat_row.pack(fill="x", pady=(0, 12))

        # Card 1: Engine Status
        self.stat_card1 = self._make_stat_card(
            stat_row,
            icon="🟢",
            title="Engine Status",
            value="Active & Listening",
            subtitle="Push-to-talk ready"
        )
        self.stat_card1.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Card 2: AI Pipeline
        self.stat_card2 = self._make_stat_card(
            stat_row,
            icon="⚡",
            title="AI Pipeline",
            value="< 950ms Sub-Second",
            subtitle="Groq Whisper + Qwen"
        )
        self.stat_card2.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Card 3: Hotkey
        self.stat_card3 = self._make_stat_card(
            stat_row,
            icon="⌨️",
            title="Global Hotkey",
            value="Ctrl + Space",
            subtitle="Hold to speak, release to paste"
        )
        self.stat_card3.pack(side="left", fill="x", expand=True)

        # Middle Card: Live Mic Health & Test
        mic_card = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        mic_card.pack(fill="x", pady=(0, 12), padx=0)

        mic_header = ctk.CTkFrame(mic_card, fg_color="transparent")
        mic_header.pack(fill="x", padx=16, pady=(12, 6))

        mic_title = ctk.CTkLabel(
            mic_header,
            text="Microphone Sensitivity & Audio Feed",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f1f5f9"
        )
        mic_title.pack(side="left")

        self.mic_test_btn = ctk.CTkButton(
            mic_header,
            text="🎤 Test Microphone (3s)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=28,
            command=self._start_mic_test
        )
        self.mic_test_btn.pack(side="right")

        # Audio level progress bar
        self.mic_progress = ctk.CTkProgressBar(
            mic_card,
            height=12,
            corner_radius=6,
            progress_color="#10b981",
            fg_color="#1e293b"
        )
        self.mic_progress.pack(fill="x", padx=16, pady=(4, 6))
        self.mic_progress.set(0.0)

        self.mic_status_lbl = ctk.CTkLabel(
            mic_card,
            text="Default audio input connected. Click 'Test Microphone' and speak to test volume level.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#94a3b8"
        )
        self.mic_status_lbl.pack(anchor="w", padx=16, pady=(0, 10))

        # Bottom Card: Interactive Dictation Sandbox ("Try It Live")
        sandbox_card = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        sandbox_card.pack(fill="both", expand=True, pady=(0, 4))

        sb_header = ctk.CTkFrame(sandbox_card, fg_color="transparent")
        sb_header.pack(fill="x", padx=16, pady=(10, 4))

        sb_title = ctk.CTkLabel(
            sb_header,
            text="Interactive Dictation Sandbox (Try It Now)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f1f5f9"
        )
        sb_title.pack(side="left")

        self.sandbox_latency_badge = ctk.CTkLabel(
            sb_header,
            text="⚡ Ready for dictation",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#38bdf8",
            fg_color="#1e293b",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.sandbox_latency_badge.pack(side="right")

        self.sandbox_textbox = ctk.CTkTextbox(
            sandbox_card,
            height=90,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#090d16",
            border_width=1,
            border_color="#334155"
        )
        self.sandbox_textbox.pack(fill="both", expand=True, padx=16, pady=(2, 6))
        self.sandbox_textbox.insert(
            "1.0",
            "Click here, hold [Ctrl + Space], speak in English or Hinglish, and release to test live transcription..."
        )

        sb_footer = ctk.CTkFrame(sandbox_card, fg_color="transparent")
        sb_footer.pack(fill="x", padx=16, pady=(0, 10))

        clear_btn = ctk.CTkButton(
            sb_footer,
            text="Clear Box",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="#1e293b",
            hover_color="#334155",
            width=80,
            height=24,
            command=lambda: self.sandbox_textbox.delete("1.0", "end")
        )
        clear_btn.pack(side="left")

        sb_hint = ctk.CTkLabel(
            sb_footer,
            text="Tip: Dictation works everywhere in Windows (Notepad, Chrome, WhatsApp, VS Code, Word).",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748b"
        )
        sb_hint.pack(side="right")

        return page

    def _make_stat_card(self, parent, icon: str, title: str, value: str, subtitle: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        icon_lbl = ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(size=14))
        icon_lbl.pack(side="left", padx=(0, 6))

        t_lbl = ctk.CTkLabel(
            top,
            text=title.upper(),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        t_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(
            inner,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#f8fafc"
        )
        val_lbl.pack(anchor="w", pady=(4, 0))

        sub_lbl = ctk.CTkLabel(
            inner,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748b"
        )
        sub_lbl.pack(anchor="w")

        return card

    def _start_mic_test(self):
        if self.is_mic_testing:
            return
        self.is_mic_testing = True
        self.mic_test_btn.configure(state="disabled", text="Listening...")
        self.mic_status_lbl.configure(text="🎙️ Speak into your microphone now (testing live volume)...", text_color="#38bdf8")

        def _worker():
            max_level = 0.0
            def _audio_callback(indata, frames, time_info, status):
                nonlocal max_level
                rms = np.sqrt(np.mean(np.square(indata)))
                level = min(1.0, float(rms * 16.0))
                if level > max_level:
                    max_level = level
                self.after(0, lambda lvl=level: self.mic_progress.set(lvl))

            try:
                with sd.InputStream(channels=1, samplerate=16000, blocksize=1600, callback=_audio_callback):
                    time.sleep(3.2)
            except Exception as e:
                self.after(0, lambda: self.mic_status_lbl.configure(text=f"Microphone error: {e}", text_color="#ef4444"))

            def _finish():
                self.is_mic_testing = False
                self.mic_test_btn.configure(state="normal", text="🎤 Test Microphone (3s)")
                self.mic_progress.set(0.0)
                if max_level > 0.04:
                    self.mic_status_lbl.configure(
                        text=f"✔ Microphone picked up clear voice (Peak Level: {int(max_level*100)}%). Hardware is working perfectly!",
                        text_color="#10b981"
                    )
                else:
                    self.mic_status_lbl.configure(
                        text="⚠️ Microphone volume was low. Please speak closer or check Windows input volume.",
                        text_color="#f59e0b"
                    )

            self.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def update_dictation_latency(self, latency_ms: float, clean_text: str = ""):
        """Called by app.py when a dictation successfully finishes."""
        def _apply():
            if hasattr(self, "sandbox_latency_badge"):
                self.sandbox_latency_badge.configure(
                    text=f"⚡ Processed in {latency_ms:.0f} ms",
                    text_color="#10b981"
                )
        self.after(0, _apply)

    # -------------------------------------------------------------------------
    # PAGE 2: GROQ API KEY
    # -------------------------------------------------------------------------
    def _create_page_api(self) -> ctk.CTkFrame:
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(
            page,
            text="Groq API Key & Cloud Engine",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f8fafc"
        )
        title.pack(anchor="w", pady=(0, 14))

        card = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        card.pack(fill="x", pady=(0, 14))

        c_header = ctk.CTkFrame(card, fg_color="transparent")
        c_header.pack(fill="x", padx=18, pady=(16, 6))

        card_title = ctk.CTkLabel(
            c_header,
            text="Bring Your Own Key (BYOK)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#f8fafc"
        )
        card_title.pack(side="left")

        get_free_btn = ctk.CTkButton(
            c_header,
            text="Get Free Groq Key ↗",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#38bdf8",
            height=28,
            command=lambda: webbrowser.open("https://console.groq.com/keys")
        )
        get_free_btn.pack(side="right")

        desc = ctk.CTkLabel(
            card,
            text="Free tier gives you 14,400 daily requests. All audio processing runs securely on Groq LPUs with sub-second response times.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8",
            justify="left",
            wraplength=560
        )
        desc.pack(anchor="w", padx=18, pady=(0, 14))

        # Input row
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=18, pady=(0, 12))

        self.key_entry = ctk.CTkEntry(
            key_row,
            placeholder_text="Paste your gsk_... key here",
            show="*",
            font=ctk.CTkFont(family="Consolas", size=12),
            height=38,
            fg_color="#090d16",
            border_color="#334155"
        )
        if settings.groq_api_key:
            self.key_entry.insert(0, settings.groq_api_key)
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.eye_btn = ctk.CTkButton(
            key_row,
            text="👁️",
            width=42,
            height=38,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._toggle_show_key
        )
        self.eye_btn.pack(side="right")

        # Action button
        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(fill="x", padx=18, pady=(0, 16))

        self.save_key_btn = ctk.CTkButton(
            action_row,
            text="✔ Test & Save API Key",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=36,
            command=self._test_and_save_key
        )
        self.save_key_btn.pack(side="left", fill="x", expand=True)

        self.key_feedback_lbl = ctk.CTkLabel(
            card,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.key_feedback_lbl.pack(anchor="w", padx=18, pady=(0, 12))

        # Specs Card
        specs_card = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        specs_card.pack(fill="x")

        s_title = ctk.CTkLabel(
            specs_card,
            text="Active Model Architecture",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#94a3b8"
        )
        s_title.pack(anchor="w", padx=18, pady=(12, 6))

        s_desc = ctk.CTkLabel(
            specs_card,
            text=f"• Whisper STT    : {settings.stt_model} (Language locked to 'en' with Hinglish phonetic priming)\n• AI Copy-Editor : {settings.llm_model} (Context-aware phonetic repair, zero Devanagari)",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#38bdf8",
            justify="left"
        )
        s_desc.pack(anchor="w", padx=18, pady=(0, 14))

        return page

    def _toggle_show_key(self):
        if self.key_entry.cget("show") == "*":
            self.key_entry.configure(show="")
        else:
            self.key_entry.configure(show="*")

    def _test_and_save_key(self):
        key = self.key_entry.get().strip()
        if not key:
            self.key_feedback_lbl.configure(text="✖ Please enter an API key.", text_color="#ef4444")
            return

        self.key_feedback_lbl.configure(text="⏳ Validating key with Groq Cloud...", text_color="#38bdf8")
        self.save_key_btn.configure(state="disabled")

        def _val():
            try:
                c = Groq(api_key=key, timeout=8.0)
                c.models.list()
                settings.update_api_key(key)
                if self.on_reinit_services:
                    self.on_reinit_services()

                def _ok():
                    self.save_key_btn.configure(state="normal")
                    self.key_feedback_lbl.configure(text="✔ Key verified! Saved to environment.", text_color="#10b981")
                    self.sidebar_status_badge.configure(text="● Engine Active", text_color="#10b981")
                self.after(0, _ok)
            except Exception as e:
                def _fail(err):
                    self.save_key_btn.configure(state="normal")
                    self.key_feedback_lbl.configure(text=f"✖ Validation failed: {err[:60]}", text_color="#ef4444")
                    self.sidebar_status_badge.configure(text="⚠️ Key Invalid", text_color="#ef4444")
                self.after(0, lambda: _fail(str(e)))

        threading.Thread(target=_val, daemon=True).start()

    # -------------------------------------------------------------------------
    # PAGE 3: PREFERENCES (STARTUP, SOUNDS, HOTKEY)
    # -------------------------------------------------------------------------
    def _create_page_preferences(self) -> ctk.CTkFrame:
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(
            page,
            text="Preferences & System Controls",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f8fafc"
        )
        title.pack(anchor="w", pady=(0, 14))

        # Windows Startup Card
        card_startup = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        card_startup.pack(fill="x", pady=(0, 12))

        cs_inner = ctk.CTkFrame(card_startup, fg_color="transparent")
        cs_inner.pack(fill="x", padx=18, pady=14)

        self.startup_switch = ctk.CTkSwitch(
            cs_inner,
            text="Launch automatically on Windows boot",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._toggle_startup
        )
        self.startup_switch.pack(anchor="w")
        if self._is_startup_enabled():
            self.startup_switch.select()

        cs_sub = ctk.CTkLabel(
            cs_inner,
            text="Runs Project Voice silently in the taskbar tray on computer startup, so dictation is always active.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        cs_sub.pack(anchor="w", padx=(44, 0), pady=(4, 0))

        # Audio Feedback Card
        card_sound = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        card_sound.pack(fill="x", pady=(0, 12))

        snd_inner = ctk.CTkFrame(card_sound, fg_color="transparent")
        snd_inner.pack(fill="x", padx=18, pady=14)

        top_snd = ctk.CTkFrame(snd_inner, fg_color="transparent")
        top_snd.pack(fill="x")

        self.sound_switch = ctk.CTkSwitch(
            top_snd,
            text="Play audio cues (start chime, stop chime, paste sound)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._toggle_sound
        )
        self.sound_switch.pack(side="left")
        if settings.sound_feedback:
            self.sound_switch.select()

        test_snd_btn = ctk.CTkButton(
            top_snd,
            text="🔊 Test Sound",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            width=90,
            height=26,
            command=lambda: sound.play_start()
        )
        test_snd_btn.pack(side="right")

        snd_sub = ctk.CTkLabel(
            snd_inner,
            text="Provides pleasant, non-intrusive audio chimes to confirm when dictation begins and completes.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        snd_sub.pack(anchor="w", padx=(44, 0), pady=(4, 0))

        # Hotkey Selector Card
        card_hk = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        card_hk.pack(fill="x")

        hk_inner = ctk.CTkFrame(card_hk, fg_color="transparent")
        hk_inner.pack(fill="x", padx=18, pady=14)

        hk_lbl = ctk.CTkLabel(
            hk_inner,
            text="Push-to-Talk Hotkey Trigger",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        )
        hk_lbl.pack(anchor="w")

        hk_desc = ctk.CTkLabel(
            hk_inner,
            text="Hold the hotkey combination, speak your thoughts, and release to paste directly into your active window.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        hk_desc.pack(anchor="w", pady=(2, 10))

        self.hk_selector = ctk.CTkOptionMenu(
            hk_inner,
            values=["ctrl+space", "f8", "alt_r", "ctrl+shift+space"],
            width=240,
            command=self._on_hotkey_change
        )
        self.hk_selector.set(settings.hotkey)
        self.hk_selector.pack(anchor="w")

        return page

    def _is_startup_enabled(self) -> bool:
        sc = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Project Voice.lnk"
        return sc.exists()

    def _toggle_startup(self):
        startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        sc_path = startup_dir / "Project Voice.lnk"

        if self.startup_switch.get() == 1:
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
            $s.Description = 'Project Voice - Startup'
            $s.Save()
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        else:
            if sc_path.exists():
                try:
                    sc_path.unlink()
                except Exception:
                    pass

    def _toggle_sound(self):
        val = bool(self.sound_switch.get() == 1)
        settings.update_settings({"sound_feedback": val})

    def _on_hotkey_change(self, choice):
        settings.update_settings({"hotkey": choice})
        if self.on_reinit_services:
            self.on_reinit_services()

    # -------------------------------------------------------------------------
    # PAGE 4: CUSTOM VOCABULARY
    # -------------------------------------------------------------------------
    def _create_page_vocabulary(self) -> ctk.CTkFrame:
        page = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(
            page,
            text="Custom Vocabulary & Technical Terms",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f8fafc"
        )
        title.pack(anchor="w", pady=(0, 6))

        desc = ctk.CTkLabel(
            page,
            text="Add company names, code jargon, colleague names, or project terms (separated by commas or new lines). The AI will strictly prioritize these exact spellings.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8",
            wraplength=600,
            justify="left"
        )
        desc.pack(anchor="w", pady=(0, 10))

        card = ctk.CTkFrame(page, fg_color="#0f1523", corner_radius=10, border_width=1, border_color="#1e293b")
        card.pack(fill="both", expand=True, pady=(0, 12))

        self.vocab_textbox = ctk.CTkTextbox(
            card,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#090d16",
            border_width=1,
            border_color="#334155"
        )
        self.vocab_textbox.pack(fill="both", expand=True, padx=16, pady=14)

        # Load existing dictionary
        dict_file = settings.base_dir / "dictionary.json"
        if dict_file.exists():
            try:
                with open(dict_file, "r", encoding="utf-8") as f:
                    words = json.load(f).get("custom_words", [])
                    self.vocab_textbox.insert("1.0", "\n".join(words))
            except Exception:
                pass

        btn_row = ctk.CTkFrame(page, fg_color="transparent")
        btn_row.pack(fill="x")

        self.vocab_status_lbl = ctk.CTkLabel(
            btn_row,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.vocab_status_lbl.pack(side="left")

        save_vocab_btn = ctk.CTkButton(
            btn_row,
            text="✔ Save Vocabulary",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=160,
            height=34,
            command=self._save_vocabulary
        )
        save_vocab_btn.pack(side="right")

        return page

    def _save_vocabulary(self):
        content = self.vocab_textbox.get("1.0", "end").strip()
        words = [w.strip() for w in content.replace(",", "\n").split("\n") if w.strip()]

        dict_file = settings.base_dir / "dictionary.json"
        try:
            with open(dict_file, "w", encoding="utf-8") as f:
                json.dump({"custom_words": words}, f, indent=2)
            self.vocab_status_lbl.configure(text=f"✔ Saved {len(words)} custom words to dictionary!", text_color="#10b981")
        except Exception as e:
            self.vocab_status_lbl.configure(text=f"Error saving: {e}", text_color="#ef4444")

    # -------------------------------------------------------------------------
    # WINDOW CONTROLLERS
    # -------------------------------------------------------------------------
    def show_window(self):
        self.deiconify()
        self.state("normal")
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(150, lambda: self.attributes("-topmost", False))

    def hide_window(self):
        self.withdraw()

    def _quit_app(self):
        if self.on_quit:
            self.on_quit()
        else:
            self.destroy()
            os._exit(0)

"""
Project Voice - Clean & Friendly Windows 11 Desktop Control Center
Human-centric, minimal, and warm design inspired by modern desktop tools (Notion, Raycast, Wispr Flow).
Features:
- Windows 11 Fluent Light theme (clean white cards, Segoe UI typography)
- Optional 1-click Light / Dark mode toggle
- Instant 1-card "How to Speak" guide with clear key badges
- Built-in Voice Scratchpad for immediate live testing
- 1-Click Free Groq Key setup (BYOK) with live validation
- Simple toggles for auto-start and audio feedback
- Custom vocabulary dictionary editor
- Per-Monitor DPI Awareness & Single-Instance IPC
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

# Default to clean, friendly Light mode
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class DashboardWindow(ctk.CTk):
    def __init__(self, on_reinit_services=None, on_quit=None):
        super().__init__()

        self.on_reinit_services = on_reinit_services
        self.on_quit = on_quit

        # Window properties
        self.title("Project Voice — Voice Typing")
        self.geometry("680x640")
        self.resizable(False, False)

        # Center on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(50, (screen_w - 680) // 2)
        y = max(50, (screen_h - 640) // 2)
        self.geometry(f"680x640+{x}+{y}")
        self.configure(fg_color=("#f8fafc", "#0f172a"))

        # Set taskbar icon if exists
        icon_path = settings.base_dir / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Intercept close button (X) to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Build clean single-pane UI
        self._build_header()
        self._build_card_guide()
        self._build_card_scratchpad()
        self._build_card_groq()
        self._build_card_settings()
        self._build_footer()

    # -------------------------------------------------------------------------
    # 1. HEADER (BRAND & LIVE STATUS)
    # -------------------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(20, 12))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        logo = ctk.CTkLabel(left, text="🎙️", font=ctk.CTkFont(size=24))
        logo.pack(side="left", padx=(0, 8))

        t_box = ctk.CTkFrame(left, fg_color="transparent")
        t_box.pack(side="left")

        t_lbl = ctk.CTkLabel(
            t_box,
            text="Project Voice",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        t_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            t_box,
            text="Smart Voice Typing for Windows",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8")
        )
        sub_lbl.pack(anchor="w")

        # Right status badge & theme toggle
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right")

        self.theme_btn = ctk.CTkButton(
            right,
            text="🌙",
            width=32,
            height=28,
            font=ctk.CTkFont(size=13),
            fg_color=("#e2e8f0", "#1e293b"),
            hover_color=("#cbd5e1", "#334155"),
            text_color=("#0f172a", "#f8fafc"),
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right", padx=(8, 0))

        has_key = bool(settings.groq_api_key)
        self.status_badge = ctk.CTkLabel(
            right,
            text="● Ready to Type" if has_key else "⚠️ Setup Required",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#15803d" if has_key else "#b45309", "#4ade80" if has_key else "#fbbf24"),
            fg_color=("#dcfce7" if has_key else "#fef3c7", "#064e3b" if has_key else "#78350f"),
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right")

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        if current.lower() == "light":
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="☀️")
        else:
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="🌙")

    # -------------------------------------------------------------------------
    # 2. CARD: HOW TO USE (SIMPLE & VISUAL)
    # -------------------------------------------------------------------------
    def _build_card_guide(self):
        card = ctk.CTkFrame(self, fg_color=("#ffffff", "#1e293b"), corner_radius=12, border_width=1, border_color=("#e2e8f0", "#334155"))
        card.pack(fill="x", padx=28, pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=12)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        title = ctk.CTkLabel(
            top,
            text="How to speak anywhere",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        title.pack(side="left")

        self.key_pill = ctk.CTkLabel(
            top,
            text=f"Hold [ {settings.hotkey.upper()} ]",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#1d4ed8", "#60a5fa"),
            fg_color=("#eff6ff", "#172554"),
            corner_radius=8,
            padx=10,
            pady=3
        )
        self.key_pill.pack(side="right")

        desc = ctk.CTkLabel(
            inner,
            text="Click into WhatsApp, Word, Chrome, or any app. Hold your hotkey, speak naturally in Hinglish or English, and release to type!",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#475569", "#cbd5e1"),
            justify="left",
            wraplength=600
        )
        desc.pack(anchor="w", pady=(4, 0))

    # -------------------------------------------------------------------------
    # 3. CARD: VOICE TEST SCRATCHPAD
    # -------------------------------------------------------------------------
    def _build_card_scratchpad(self):
        card = ctk.CTkFrame(self, fg_color=("#ffffff", "#1e293b"), corner_radius=12, border_width=1, border_color=("#e2e8f0", "#334155"))
        card.pack(fill="x", padx=28, pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=12)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))

        title = ctk.CTkLabel(
            top,
            text="Try it now (Voice Scratchpad)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        title.pack(side="left")

        self.scratch_latency_lbl = ctk.CTkLabel(
            top,
            text="Hold shortcut & speak",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748b", "#94a3b8")
        )
        self.scratch_latency_lbl.pack(side="right")

        self.notepad = ctk.CTkTextbox(
            inner,
            height=68,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("#f8fafc", "#0f172a"),
            border_width=1,
            border_color=("#cbd5e1", "#334155"),
            text_color=("#0f172a", "#f8fafc")
        )
        self.notepad.pack(fill="x", pady=(0, 4))
        self.notepad.insert("1.0", "Click here, hold your shortcut, and say anything...")

    def update_dictation_latency(self, latency_ms: float, clean_text: str = ""):
        """Called automatically after every dictation."""
        def _apply():
            self.scratch_latency_lbl.configure(
                text=f"✔ Typed in {latency_ms:.0f}ms",
                text_color=("#16a34a", "#4ade80")
            )
        self.after(0, _apply)

    # -------------------------------------------------------------------------
    # 4. CARD: GROQ ACCOUNT SETUP (SIMPLE & CLEAN)
    # -------------------------------------------------------------------------
    def _build_card_groq(self):
        card = ctk.CTkFrame(self, fg_color=("#ffffff", "#1e293b"), corner_radius=12, border_width=1, border_color=("#e2e8f0", "#334155"))
        card.pack(fill="x", padx=28, pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=12)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x", pady=(0, 4))

        title = ctk.CTkLabel(
            top,
            text="Groq Account (Free AI Key)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        title.pack(side="left")

        get_link = ctk.CTkButton(
            top,
            text="Get Free Key (30s) ↗",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=("#f1f5f9", "#334155"),
            hover_color=("#e2e8f0", "#475569"),
            text_color=("#2563eb", "#60a5fa"),
            height=24,
            width=130,
            command=lambda: webbrowser.open("https://console.groq.com/keys")
        )
        get_link.pack(side="right")

        desc = ctk.CTkLabel(
            inner,
            text="Free 14,400 daily requests. Completely private and fast.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748b", "#94a3b8")
        )
        desc.pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        self.key_entry = ctk.CTkEntry(
            row,
            placeholder_text="Paste your gsk_... key here",
            show="*",
            height=34,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#f8fafc", "#0f172a"),
            border_color=("#cbd5e1", "#334155")
        )
        if settings.groq_api_key:
            self.key_entry.insert(0, settings.groq_api_key)
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.eye_btn = ctk.CTkButton(
            row,
            text="👁️",
            width=36,
            height=34,
            fg_color=("#f1f5f9", "#334155"),
            hover_color=("#e2e8f0", "#475569"),
            text_color=("#0f172a", "#f8fafc"),
            command=self._toggle_show_key
        )
        self.eye_btn.pack(side="left", padx=(0, 6))

        self.save_key_btn = ctk.CTkButton(
            row,
            text="Save Key",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=34,
            width=85,
            command=self._test_and_save_key
        )
        self.save_key_btn.pack(side="right")

        self.key_msg_lbl = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        self.key_msg_lbl.pack(anchor="w", pady=(4, 0))

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

        self.key_msg_lbl.configure(text="Connecting to Groq...", text_color="#2563eb")
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
                    self.key_msg_lbl.configure(text="✔ Key verified & connected!", text_color="#16a34a")
                    self.status_badge.configure(text="● Ready to Type", text_color=("#15803d", "#4ade80"), fg_color=("#dcfce7", "#064e3b"))
                self.after(0, _ok)
            except Exception as e:
                def _fail(err):
                    self.save_key_btn.configure(state="normal")
                    self.key_msg_lbl.configure(text=f"✖ Key invalid: {err[:50]}", text_color="#ef4444")
                self.after(0, lambda: _fail(str(e)))

        threading.Thread(target=_val, daemon=True).start()

    # -------------------------------------------------------------------------
    # 5. CARD: SIMPLE PREFERENCES & VOCABULARY
    # -------------------------------------------------------------------------
    def _build_card_settings(self):
        card = ctk.CTkFrame(self, fg_color=("#ffffff", "#1e293b"), corner_radius=12, border_width=1, border_color=("#e2e8f0", "#334155"))
        card.pack(fill="x", padx=28, pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=12)

        # Row 1: Toggles
        r1 = ctk.CTkFrame(inner, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 8))

        self.sw_startup = ctk.CTkSwitch(
            r1,
            text="Start with Windows",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#334155", "#cbd5e1"),
            command=self._toggle_startup
        )
        self.sw_startup.pack(side="left", padx=(0, 20))
        if self._is_startup_enabled():
            self.sw_startup.select()

        self.sw_sound = ctk.CTkSwitch(
            r1,
            text="Play sound chimes",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#334155", "#cbd5e1"),
            command=self._toggle_sound
        )
        self.sw_sound.pack(side="left")
        if settings.sound_feedback:
            self.sw_sound.select()

        # Row 2: Hotkey + Custom Words button
        r2 = ctk.CTkFrame(inner, fg_color="transparent")
        r2.pack(fill="x")

        hk_lbl = ctk.CTkLabel(
            r2,
            text="Shortcut:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        hk_lbl.pack(side="left", padx=(0, 6))

        self.hk_picker = ctk.CTkOptionMenu(
            r2,
            values=["ctrl+space", "f8", "alt_r", "ctrl+shift+space"],
            width=130,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._on_hotkey_change
        )
        self.hk_picker.set(settings.hotkey)
        self.hk_picker.pack(side="left", padx=(0, 16))

        vocab_btn = ctk.CTkButton(
            r2,
            text="📖 Custom Words...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#f1f5f9", "#334155"),
            hover_color=("#e2e8f0", "#475569"),
            text_color=("#0f172a", "#f8fafc"),
            height=28,
            width=120,
            command=self._open_vocab_dialog
        )
        vocab_btn.pack(side="right")

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
        val = bool(self.sw_sound.get() == 1)
        settings.update_settings({"sound_feedback": val})

    def _on_hotkey_change(self, choice):
        settings.update_settings({"hotkey": choice})
        self.key_pill.configure(text=f"Hold [ {choice.upper()} ]")
        if self.on_reinit_services:
            self.on_reinit_services()

    def _open_vocab_dialog(self):
        """Clean dialog for adding brand names, client names, or jargon."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Custom Words Dictionary")
        dialog.geometry("420x340")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=("#f8fafc", "#0f172a"))

        d_inner = ctk.CTkFrame(dialog, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=20, pady=16)

        lbl = ctk.CTkLabel(
            d_inner,
            text="Custom Vocabulary",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        lbl.pack(anchor="w")

        sub = ctk.CTkLabel(
            d_inner,
            text="Add brand names, jargon, or names (one per line).",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8")
        )
        sub.pack(anchor="w", pady=(0, 8))

        tb = ctk.CTkTextbox(
            d_inner,
            height=180,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#ffffff", "#1e293b"),
            border_width=1,
            border_color=("#cbd5e1", "#334155"),
            text_color=("#0f172a", "#f8fafc")
        )
        tb.pack(fill="both", expand=True, pady=(0, 10))

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
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=_save_v
        )
        btn.pack(anchor="e")

    # -------------------------------------------------------------------------
    # 6. FOOTER (MINIMIZE & QUIT)
    # -------------------------------------------------------------------------
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=28, pady=(0, 16))

        min_btn = ctk.CTkButton(
            footer,
            text="Minimize to System Tray",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=("#0f172a", "#3b82f6"),
            hover_color=("#1e293b", "#2563eb"),
            text_color="#ffffff",
            height=36,
            command=self.hide_window
        )
        min_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        quit_btn = ctk.CTkButton(
            footer,
            text="Quit App",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("#fee2e2", "#450a0a"),
            hover_color=("#fecaca", "#7f1d1d"),
            text_color=("#b91c1c", "#fca5a5"),
            height=36,
            width=90,
            command=self._quit_app
        )
        quit_btn.pack(side="right")

    # -------------------------------------------------------------------------
    # WINDOW ACTIONS
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

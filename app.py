"""
=============================================================================
PROJECT VOICE - PRODUCTION APPLICATION CONTROLLER (app.py)
=============================================================================
Modular, Extensible, Production Architecture:

1. Single-Instance Mutex & Win32 IPC (ProjectVoice_ShowEvent)
2. ui/dashboard.py           -> Visual Settings, API Key entry & controls
3. ui/floating_indicator.py   -> Sleek glowing visual pill (Wispr Flow style)
4. ui/tray.py                 -> Windows Taskbar System Tray Icon
5. config/settings.py         -> Centralized Configuration & Hotkeys
6. core/audio_recorder.py     -> High-performance in-memory RAM audio capture
7. core/speech_to_text.py     -> Groq Whisper STT (Primed with Hinglish context)
8. core/llm_cleaner.py        -> AI Formatter (Strict Hinglish/English rules)
9. core/injector.py           -> Virtual Ctrl+V Keystroke Injection
10. utils/hotkey_listener.py  -> Global Multi-key Hook (Default: Ctrl + Space)
11. utils/sound_feedback.py   -> Pleasant audio chimes
=============================================================================
"""

import ctypes
import os
import sys
import threading
import time

# -----------------------------------------------------------------------------
# 1. Single Instance Mutex + Named Event IPC
# -----------------------------------------------------------------------------
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002

_app_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ProjectVoice_SingleInstance_Mutex")
if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
    # Existing instance detected! Signal it to bring its Dashboard window to the front:
    event = ctypes.windll.kernel32.OpenEventW(EVENT_MODIFY_STATE, False, "ProjectVoice_ShowEvent")
    if event:
        ctypes.windll.kernel32.SetEvent(event)
        ctypes.windll.kernel32.CloseHandle(event)
    sys.exit(0)

# Windows UTF-8 console output fix (safe under both python.exe and pythonw.exe)
if sys.stdout is not None and getattr(sys.stdout, "encoding", None) != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_active_window_title() -> str:
    """Retrieves foreground active application window title for context awareness."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value
    except Exception:
        pass
    return ""

from config.settings import settings
from core.audio_recorder import AudioRecorder
from core.speech_to_text import GroqSTTProvider
from core.llm_cleaner import LLMFormatter
from core.injector import TextInjector
from utils.hotkey_listener import HotkeyManager
from utils.sound_feedback import sound
from ui.dashboard import DashboardWindow
from ui.floating_indicator import FloatingIndicator
from ui.tray import TrayIcon

class ProjectVoiceApp:
    def __init__(self):
        print("=" * 65)
        print("🚀 INITIALIZING PROJECT VOICE ENGINE...")
        print(f"👉 Hotkey         : [{settings.hotkey.upper()}] (or [{settings.fallback_hotkey.upper()}])")
        print(f"👉 STT Model      : {settings.stt_model}")
        print(f"👉 LLM Cleaner    : {settings.llm_model}")
        print("=" * 65)

        self.is_running = True

        # 1. Initialize Dashboard GUI Window (Main Thread)
        self.dashboard = DashboardWindow(
            on_reinit_services=self.reinit_services,
            on_quit=self.shutdown
        )

        # 2. Sleek Floating Indicator Pill attached to dashboard master
        self.indicator = FloatingIndicator(master=self.dashboard)

        # 3. Initialize Core Audio & AI Services
        self.recorder = AudioRecorder()
        self.stt = GroqSTTProvider()
        self.llm = LLMFormatter()
        self.injector = TextInjector()

        # 4. Global Hotkey Manager
        self.hotkey_mgr = HotkeyManager(
            on_start=self.on_hotkey_down,
            on_stop=self.on_hotkey_up
        )

        # 5. System Tray Icon (Runs detached in background thread)
        self.tray = TrayIcon(
            on_open_dashboard=self.show_dashboard_from_tray,
            on_exit_callback=self.shutdown
        )

        # 6. Win32 Named Event for Single-Instance Wakeup
        self.show_event = ctypes.windll.kernel32.CreateEventW(None, False, False, "ProjectVoice_ShowEvent")
        self._start_event_listener()

    def _start_event_listener(self):
        def _listen():
            while self.is_running:
                res = ctypes.windll.kernel32.WaitForSingleObject(self.show_event, 800)
                if res == 0:  # WAIT_OBJECT_0 triggered by another launch attempt!
                    self.dashboard.after(0, self.dashboard.show_window)
        threading.Thread(target=_listen, daemon=True).start()

    def show_dashboard_from_tray(self):
        self.dashboard.after(0, self.dashboard.show_window)

    def reinit_services(self):
        print("🔄 Reloading API services and hotkey configuration...")
        self.stt.reload_client()
        self.llm.reload_client()
        self.hotkey_mgr.reload_keys()

    def on_hotkey_down(self):
        """Called when user presses and holds Ctrl+Space (or F8)."""
        self.target_hwnd = ctypes.windll.user32.GetForegroundWindow()
        self.active_context = get_active_window_title()
        sound.play_start()
        self.recorder.start()
        self.indicator.show_listening()
        print("\n🎙️ [LISTENING...] Speak in English or Hinglish...")

    def on_hotkey_up(self):
        """Called when user releases Ctrl+Space (or F8)."""
        sound.play_stop()
        audio_bytes = self.recorder.stop()
        print("🛑 [STOPPED] Processing in memory...")

        if not audio_bytes:
            print("⚠️ Recording too short or empty (ignored).")
            self.indicator.hide()
            return

        self.indicator.show_processing()
        threading.Thread(target=self._process_pipeline, args=(audio_bytes,), daemon=True).start()

    def _process_pipeline(self, audio_bytes: bytes):
        pipeline_start = time.time()

        # 1. Whisper Speech-to-Text
        try:
            raw_text, stt_ms = self.stt.transcribe(audio_bytes)
        except Exception as e:
            print(f"❌ STT Error: {e}")
            sound.play_error()
            self.indicator.show_error("Key / STT Error")
            # If key is missing, open dashboard for user
            if not settings.groq_api_key:
                self.dashboard.after(0, self.dashboard.show_window)
            return

        if not raw_text:
            print("⚠️ No speech recognized.")
            self.indicator.hide()
            return

        print(f"📝 Raw Whisper  : \"{raw_text}\" ({stt_ms:.0f} ms)")

        # 2. AI Formatting & Cleanup
        try:
            clean_text, llm_ms = self.llm.format(raw_text, context=getattr(self, "active_context", ""))
        except Exception as e:
            print(f"❌ LLM Error: {e}, falling back to raw text.")
            clean_text = raw_text
            llm_ms = 0

        print(f"✨ AI Cleaned   : \"{clean_text}\" ({llm_ms:.0f} ms)")

        # 3. OS Auto-Paste Injection
        self.injector.paste(clean_text, target_hwnd=getattr(self, "target_hwnd", 0))
        sound.play_success()
        self.indicator.show_pasted()

        total_ms = (time.time() - pipeline_start) * 1000
        print(f"✅ [AUTO-PASTED!] Total Time: {total_ms:.0f} ms")
        print("-" * 65)

        # Notify dashboard of live completion & latency
        if hasattr(self, "dashboard") and self.dashboard:
            self.dashboard.update_dictation_latency(total_ms, clean_text)

    def start(self):
        """Starts background hotkey listening, system tray, and dashboard mainloop."""
        # Start keyboard listener
        self.hotkey_mgr.start()

        # Start system tray in background
        self.tray.start_in_background()

        # If launched with --tray or --minimized (e.g. from Windows boot startup):
        if "--tray" in sys.argv or "--minimized" in sys.argv:
            self.dashboard.hide_window()
        else:
            # Default desktop double-click: show Dashboard window!
            self.dashboard.show_window()

        # Main Tkinter event loop
        try:
            self.dashboard.mainloop()
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Gracefully stops the application."""
        print("Shutting down Project Voice...")
        self.is_running = False
        self.tray.stop()
        self.hotkey_mgr.stop()
        try:
            self.dashboard.destroy()
        except Exception:
            pass
        os._exit(0)

if __name__ == "__main__":
    app = ProjectVoiceApp()
    app.start()

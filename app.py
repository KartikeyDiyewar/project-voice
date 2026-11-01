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
from ctypes import wintypes
import os
import sys
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Explicit 64-bit Win32 API signatures (prevents pointer truncation)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL
user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenEventW.restype = wintypes.HANDLE
kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.SetEvent.restype = wintypes.BOOL
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

# -----------------------------------------------------------------------------
# 1. Single Instance Mutex + Named Event IPC
# -----------------------------------------------------------------------------
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002

_app_mutex = kernel32.CreateMutexW(None, False, "ProjectVoice_SingleInstance_Mutex")
if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
    # Existing instance detected! Grant it foreground window rights & signal wakeup
    try:
        user32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY
    except Exception:
        pass
    event = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, "ProjectVoice_ShowEvent")
    if event:
        kernel32.SetEvent(event)
        kernel32.CloseHandle(event)
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
        self.injection_lock = threading.Lock()

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
        self.show_event = kernel32.CreateEventW(None, False, False, "ProjectVoice_ShowEvent")
        self._start_event_listener()

    def _start_event_listener(self):
        def _listen():
            while self.is_running:
                res = kernel32.WaitForSingleObject(self.show_event, 800)
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
        self.current_hwnd = user32.GetForegroundWindow()
        self.current_context = get_active_window_title()
        sound.play_start()
        self.recorder.start()
        self.indicator.show_listening()
        print("\n🎙️ [LISTENING...] Speak in English or Hinglish...")

    def on_hotkey_up(self):
        """Called when user releases Ctrl+Space (or F8)."""
        audio_bytes = self.recorder.stop()
        target_hwnd = getattr(self, "current_hwnd", 0)
        captured_ctx = getattr(self, "current_context", "")
        print("🛑 [STOPPED] Processing in memory...")

        if not audio_bytes:
            print("⚠️ Recording too short or empty (ignored).")
            self.indicator.hide()
            return

        self.indicator.show_processing()
        threading.Thread(
            target=self._process_pipeline,
            args=(audio_bytes, captured_ctx, target_hwnd),
            daemon=True
        ).start()

    def _process_pipeline(self, audio_bytes: bytes, context: str, target_hwnd: int):
        pipeline_start = time.time()

        # 1. Whisper Speech-to-Text
        try:
            raw_text, stt_ms = self.stt.transcribe(audio_bytes)
        except Exception as e:
            print(f"❌ STT Error: {e}")
            sound.play_error()
            err_str = str(e).lower()
            if "api key" in err_str or not settings.groq_api_key:
                err_msg = "Key Setup Required"
            elif "connect" in err_str or "timeout" in err_str or "network" in err_str:
                err_msg = "Offline / Network Error"
            elif "rate" in err_str or "429" in err_str:
                err_msg = "Groq Busy (Wait a sec)"
            else:
                err_msg = "Speech Error"
            self.indicator.show_error(err_msg)
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
            clean_text, llm_ms = self.llm.format(raw_text, context=context)
        except Exception as e:
            print(f"❌ LLM Error: {e}, falling back to raw text.")
            clean_text = raw_text
            llm_ms = 0

        print(f"✨ AI Cleaned   : \"{clean_text}\" ({llm_ms:.0f} ms)")

        # 3. OS Auto-Paste Injection (Serialized via lock to prevent clipboard collisions)
        with self.injection_lock:
            self.injector.paste(clean_text, target_hwnd=target_hwnd)
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
        """Gracefully stops the application and releases all hardware & OS handles."""
        print("Shutting down Project Voice...")
        self.is_running = False
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass
        try:
            self.recorder.close()
        except Exception:
            pass
        if hasattr(self, "show_event") and self.show_event:
            try:
                kernel32.CloseHandle(self.show_event)
            except Exception:
                pass
        if _app_mutex:
            try:
                kernel32.CloseHandle(_app_mutex)
            except Exception:
                pass
        try:
            self.dashboard.destroy()
        except Exception:
            pass
        os._exit(0)

if __name__ == "__main__":
    app = ProjectVoiceApp()
    app.start()

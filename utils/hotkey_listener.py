"""
Global Hotkey Manager
Handles multi-key combinations (Ctrl+Space, F8, Alt+Space, etc.).
Features:
- Non-blocking callback dispatch (never blocks Windows WH_KEYBOARD_LL hook thread)
- Hardware-level physical key check via Win32 GetAsyncKeyState (eliminates spacebar hijacking)
- Thread-safe state tracking
"""

import ctypes
import threading
from pynput import keyboard
from config.settings import settings

user32 = ctypes.windll.user32

# Win32 Virtual Key Constants
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_SPACE = 0x20
VK_F8 = 0x77

def is_physical_key_down(vk_code: int) -> bool:
    """Queries Windows hardware keyboard state directly."""
    return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)

class HotkeyManager:
    def __init__(self, on_start, on_stop):
        self.on_start_callback = on_start
        self.on_stop_callback = on_stop
        self.is_active = False

        self.primary_hotkey_str = settings.hotkey.lower()
        self.fallback_hotkey_str = settings.fallback_hotkey.lower()

        self.currently_pressed = set()
        self.lock = threading.Lock()
        self.listener = None

    def reload_keys(self):
        """Updates hotkeys dynamically if changed in settings."""
        with self.lock:
            self.primary_hotkey_str = settings.hotkey.lower()
            self.fallback_hotkey_str = settings.fallback_hotkey.lower()
            self.currently_pressed.clear()
            self.is_active = False

    def _matches_ctrl(self, key):
        return key in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}

    def _matches_space(self, key):
        return key == keyboard.Key.space

    def _matches_fallback(self, key):
        if self.fallback_hotkey_str == "f8":
            return key == keyboard.Key.f8
        return False

    def _on_press(self, key):
        with self.lock:
            self.currently_pressed.add(key)

            # Check primary combo (Ctrl + Space) with hardware confirmation
            has_ctrl = any(self._matches_ctrl(k) for k in self.currently_pressed) and is_physical_key_down(VK_CONTROL)
            has_space = any(self._matches_space(k) for k in self.currently_pressed)

            is_combo_triggered = has_ctrl and has_space
            is_fallback_triggered = any(self._matches_fallback(k) for k in self.currently_pressed)

            if (is_combo_triggered or is_fallback_triggered) and not self.is_active:
                self.is_active = True
                # Dispatch start in worker thread so the hook returns instantaneously (<1ms)
                threading.Thread(target=self.on_start_callback, daemon=True).start()

    def _on_release(self, key):
        with self.lock:
            if key in self.currently_pressed:
                self.currently_pressed.remove(key)

            if self.is_active:
                has_ctrl = any(self._matches_ctrl(k) for k in self.currently_pressed) and is_physical_key_down(VK_CONTROL)
                has_space = any(self._matches_space(k) for k in self.currently_pressed) and is_physical_key_down(VK_SPACE)
                has_fallback = any(self._matches_fallback(k) for k in self.currently_pressed)

                # Stop when the combination is released
                if not ((has_ctrl and has_space) or has_fallback):
                    self.is_active = False
                    self.currently_pressed.clear()  # Clear stuck keys on release
                    # CRITICAL: Run stop callback in a background thread so we NEVER sleep on the OS hook thread!
                    threading.Thread(target=self.on_stop_callback, daemon=True).start()

    def start(self):
        """Starts the global keyboard listener in a background thread."""
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

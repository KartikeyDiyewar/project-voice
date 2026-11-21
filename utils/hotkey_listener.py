"""
Global Hotkey Manager
Handles multi-key combinations (Ctrl+Space, F8, Alt+Space, Ctrl+Shift+Space, etc.) dynamically.
Features:
- Dynamic hotkey combination parser based on runtime settings
- Non-blocking callback dispatch (never blocks Windows WH_KEYBOARD_LL hook thread)
- Hardware-level physical key check via Win32 GetAsyncKeyState (eliminates spacebar hijacking)
- Thread-safe state tracking
"""

import ctypes
from ctypes import wintypes
import threading
from pynput import keyboard
from config.settings import settings

user32 = ctypes.windll.user32
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

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
    """Watches for the configured chord and drives start / stop callbacks.

    Two activation modes:
      hold  - the chord must stay down; releasing stops (push-to-talk)
      latch - one press starts, the next press stops, so long dictation does not
              depend on keeping a key held
    """

    def __init__(self, on_start, on_stop):
        self.on_start_callback = on_start
        self.on_stop_callback = on_stop
        self.is_active = False
        self.latched = False

        self.primary_hotkey_str = settings.hotkey.lower()
        self.fallback_hotkey_str = settings.fallback_hotkey.lower()

        self.currently_pressed = set()
        self.lock = threading.Lock()
        self.listener = None

    def reload_keys(self):
        """Updates hotkeys dynamically if changed in settings."""
        with self.lock:
            was_active = self.is_active
            self.primary_hotkey_str = settings.hotkey.lower()
            self.fallback_hotkey_str = settings.fallback_hotkey.lower()
            self.currently_pressed.clear()
            self.is_active = False
            self.latched = False

        if was_active and self.on_stop_callback:
            try:
                self.on_stop_callback()
            except Exception:
                pass

    def _matches_ctrl(self, key):
        return key in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}

    def _matches_shift(self, key):
        return key in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}

    def _matches_alt(self, key):
        return key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr}

    def _matches_space(self, key):
        return key == keyboard.Key.space

    def _matches_f8(self, key):
        return key == keyboard.Key.f8

    def _is_combination_down(self, hotkey_str: str) -> bool:
        """Dynamically evaluates whether a configured hotkey combination is pressed."""
        if not hotkey_str:
            return False

        tokens = [t.strip() for t in hotkey_str.lower().split("+")]
        for token in tokens:
            if token in ("ctrl", "control"):
                if not (any(self._matches_ctrl(k) for k in self.currently_pressed) and is_physical_key_down(VK_CONTROL)):
                    return False
            elif token == "shift":
                if not (any(self._matches_shift(k) for k in self.currently_pressed) and is_physical_key_down(VK_SHIFT)):
                    return False
            elif token in ("alt", "alt_r", "alt_l", "alt_gr"):
                if not (any(self._matches_alt(k) for k in self.currently_pressed) and is_physical_key_down(VK_MENU)):
                    return False
            elif token == "space":
                if not any(self._matches_space(k) for k in self.currently_pressed):
                    return False
            elif token == "f8":
                if not any(self._matches_f8(k) for k in self.currently_pressed):
                    return False
            else:
                matched = False
                for k in self.currently_pressed:
                    if hasattr(k, "char") and k.char and k.char.lower() == token:
                        matched = True
                        break
                if not matched:
                    return False
        return True

    def _on_press(self, key):
        with self.lock:
            already_down = key in self.currently_pressed
            self.currently_pressed.add(key)

            # Auto-repeat fires press events while a key is held. Only the first
            # one counts, otherwise latch mode would stop the moment it started.
            if already_down:
                return

            is_primary = self._is_combination_down(self.primary_hotkey_str)
            is_fallback = self._is_combination_down(self.fallback_hotkey_str)
            if not (is_primary or is_fallback):
                return

            if settings.activation_mode == "latch":
                if self.is_active:
                    self.is_active = False
                    self.latched = False
                    threading.Thread(target=self.on_stop_callback, daemon=True).start()
                else:
                    self.is_active = True
                    self.latched = True
                    threading.Thread(target=self.on_start_callback, daemon=True).start()
            elif not self.is_active:
                self.is_active = True
                threading.Thread(target=self.on_start_callback, daemon=True).start()

    def _on_release(self, key):
        with self.lock:
            if key in self.currently_pressed:
                self.currently_pressed.remove(key)

            if not self.is_active or self.latched:
                return

            # Hold mode: stop once the chord is no longer fully down.
            is_primary = self._is_combination_down(self.primary_hotkey_str)
            is_fallback = self._is_combination_down(self.fallback_hotkey_str)
            if not (is_primary or is_fallback):
                self.is_active = False
                self.currently_pressed.clear()
                threading.Thread(target=self.on_stop_callback, daemon=True).start()

    def force_stop(self):
        """Ends a latched recording, e.g. when the dashboard closes."""
        with self.lock:
            if not self.is_active:
                return
            self.is_active = False
            self.latched = False
            self.currently_pressed.clear()
        try:
            self.on_stop_callback()
        except Exception:
            pass

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
            try:
                self.listener.stop()
            except Exception:
                pass

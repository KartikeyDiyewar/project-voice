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
VK_LWIN = 0x5B
VK_RWIN = 0x5C

# pynput calls a few keys by a different name than the chord string uses.
KEY_ALIASES = {
    "esc": "escape",
    "return": "enter",
    "control": "ctrl",
    "del": "delete",
    "prior": "page_up",
    "next": "page_down",
}


def normalize_key(name: str) -> str:
    name = (name or "").strip().lower()
    return KEY_ALIASES.get(name, name)


def key_matches_token(key, token: str) -> bool:
    """True when a pressed pynput key is the key named by a chord token.

    Works for named keys (f9, enter, page_up) and for printable characters, so
    any single key the user registers can actually fire.
    """
    token = normalize_key(token)
    name = getattr(key, "name", None)
    if name and normalize_key(name) == token:
        return True
    char = getattr(key, "char", None)
    if char and char.lower() == token:
        return True
    return False


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

    def _modifier_down(self, token: str) -> bool:
        """Modifiers are checked both in the hook state and at the hardware level.

        The hardware check stops a plain Space from firing while Ctrl happens to
        be held for another app.
        """
        key_map = {
            "ctrl": ({keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}, VK_CONTROL),
            "shift": ({keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}, VK_SHIFT),
            "alt": ({keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                     keyboard.Key.alt_gr}, VK_MENU),
            "win": ({keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r}, VK_LWIN),
        }
        keys, vk = key_map[token]
        in_hook = any(k in keys for k in self.currently_pressed)
        if not in_hook:
            return False
        return is_physical_key_down(vk)

    def _is_combination_down(self, hotkey_str: str) -> bool:
        """Dynamically evaluates whether a configured hotkey combination is pressed.

        Every token is handled generically, so a single key (f9, enter, page_up),
        a letter, or any modifier combination all work the same way.
        """
        if not hotkey_str:
            return False

        tokens = [normalize_key(t) for t in hotkey_str.split("+") if t.strip()]
        if not tokens:
            return False

        for token in tokens:
            if token in ("ctrl", "shift", "alt", "win"):
                if not self._modifier_down(token):
                    return False
            else:
                if not any(key_matches_token(k, token) for k in self.currently_pressed):
                    return False
        return True

    def _chord_completed_by(self, chord: str, key) -> bool:
        """Was this press the one that completed the chord?

        Without this, any unrelated key pressed while the chord's keys are held
        (e.g. typing 'r' during Ctrl+Space) would be treated as a fresh trigger.
        The key that arrives must be one of the chord's non-modifier tokens.
        """
        tokens = [normalize_key(t) for t in (chord or "").split("+") if t.strip()]
        base = [t for t in tokens if t not in ("ctrl", "shift", "alt", "win")]
        if not base:
            return False
        return any(key_matches_token(key, t) for t in base)

    def _on_press(self, key):
        with self.lock:
            already_down = key in self.currently_pressed
            self.currently_pressed.add(key)

            # Auto-repeat fires press events while a key is held. Only the first
            # one counts, otherwise latch mode would stop the moment it started.
            if already_down:
                return

            is_primary = (self._chord_completed_by(self.primary_hotkey_str, key)
                          and self._is_combination_down(self.primary_hotkey_str))
            is_fallback = (self._chord_completed_by(self.fallback_hotkey_str, key)
                           and self._is_combination_down(self.fallback_hotkey_str))
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

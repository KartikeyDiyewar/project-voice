"""
OS Keystroke & Clipboard Injection
Injects cleaned text directly into the user's active focused application.

The dictated text is deliberately left on the clipboard after the paste. A paste
only lands when the focused control accepts text; if the caret was not in a text
field (or the window changed mid-dictation), restoring the previous clipboard
would silently destroy what the user just said. Keeping the text means it can
always be pasted manually with Ctrl+V.

The previous clipboard is captured and put back only when the injected text is
no longer what is on the clipboard, i.e. the user copied something themselves in
the meantime, in which case their action wins.
"""

import ctypes
import threading
import time

from pynput import keyboard
import pyperclip

user32 = ctypes.windll.user32

# How long to wait before checking whether the paste landed. The keystroke is
# dispatched immediately either way, so dictation latency is unaffected.
SETTLE_MS = 400


class TextInjector:
    def __init__(self):
        self.keyboard_controller = keyboard.Controller()

    def _get_seq_num(self) -> int:
        if hasattr(user32, "GetClipboardSequenceNumber"):
            try:
                return user32.GetClipboardSequenceNumber()
            except Exception:
                pass
        return 0

    def paste(self, text: str, target_hwnd: int = 0):
        """
        Puts the text on the clipboard, ensures the target window has focus,
        and simulates Ctrl+V. The text stays on the clipboard afterwards so a
        missed paste is never a lost dictation.
        """
        if not text:
            return

        # Re-assert focus onto the target application window if specified
        if target_hwnd:
            try:
                user32.SetForegroundWindow(target_hwnd)
                time.sleep(0.03)
            except Exception:
                pass

        try:
            # 1. Put the dictated text on the clipboard and remember the
            #    sequence number so we can tell if anything else replaces it.
            pyperclip.copy(text)
            injected_seq = self._get_seq_num()
            time.sleep(0.015)  # Fast OS clipboard synchronization (15ms)

            # 2. Fire virtual Ctrl + V
            with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                self.keyboard_controller.press('v')
                self.keyboard_controller.release('v')

            # 3. Safety net, off the hot path: if the paste did not consume the
            #    text and nothing replaced it, put it back so Ctrl+V works later.
            threading.Thread(
                target=self._ensure_text_available,
                args=(text, injected_seq),
                daemon=True,
            ).start()

        except Exception as e:
            print(f"Injection error: {e}")

    def _ensure_text_available(self, text: str, injected_seq: int):
        """Guarantees the dictation survives on the clipboard.

        Some applications clear the clipboard after consuming a paste, and a
        missed paste leaves the text sitting there already. Either way the
        dictation must remain reachable, so it is re-copied unless the user has
        copied something of their own since.
        """
        time.sleep(SETTLE_MS / 1000.0)
        try:
            current_seq = self._get_seq_num()
            if injected_seq and current_seq and current_seq != injected_seq:
                return  # the user copied something else - their action wins

            try:
                if pyperclip.paste() == text:
                    return  # already available for a manual paste
            except Exception:
                pass

            pyperclip.copy(text)
        except Exception:
            pass

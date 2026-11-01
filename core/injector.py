"""
OS Keystroke & Clipboard Injection
Injects cleaned text directly into the user's active focused application.
Preserves user clipboard hygiene by using Win32 clipboard sequence tracking:
restores previous clipboard contents after paste only if the user has not copied anything else.
"""

import ctypes
import threading
import time
from pynput import keyboard
import pyperclip

user32 = ctypes.windll.user32

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
        Pushes text to Windows clipboard, ensures target window focus,
        simulates Ctrl + V keystroke, and cleanly restores previous clipboard contents safely.
        """
        if not text:
            return

        # Re-assert focus onto target application window if specified
        if target_hwnd:
            try:
                user32.SetForegroundWindow(target_hwnd)
                time.sleep(0.03)
            except Exception:
                pass

        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = None

        try:
            # 1. Update clipboard with dictated text
            pyperclip.copy(text)
            injected_seq = self._get_seq_num()
            time.sleep(0.04)  # Small pause to allow OS clipboard synchronization

            # 2. Fire virtual Ctrl + V
            with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                self.keyboard_controller.press('v')
                self.keyboard_controller.release('v')

            # 3. Restore previous clipboard asynchronously only if user didn't copy something else
            if old_clipboard is not None:
                def _restore():
                    time.sleep(0.28)
                    try:
                        # Verify via sequence number if available or content check
                        curr_seq = self._get_seq_num()
                        if curr_seq != 0 and injected_seq != 0:
                            if curr_seq == injected_seq:
                                pyperclip.copy(old_clipboard)
                        elif pyperclip.paste() == text:
                            pyperclip.copy(old_clipboard)
                    except Exception:
                        pass

                threading.Thread(target=_restore, daemon=True).start()

        except Exception as e:
            print(f"Injection error: {e}")

"""
OS Keystroke & Clipboard Injection
Injects cleaned text directly into the user's active focused application.
Preserves user clipboard hygiene by restoring previous clipboard content after paste
only if the clipboard has not been modified by the user.
"""

import ctypes
import threading
import time
from pynput import keyboard
import pyperclip

class TextInjector:
    def __init__(self):
        self.keyboard_controller = keyboard.Controller()

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
                ctypes.windll.user32.SetForegroundWindow(target_hwnd)
                time.sleep(0.04)
            except Exception:
                pass

        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = None

        try:
            # 1. Update clipboard with dictated text
            pyperclip.copy(text)
            time.sleep(0.04)  # Small pause to allow OS clipboard synchronization

            # 2. Fire virtual Ctrl + V
            with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                self.keyboard_controller.press('v')
                self.keyboard_controller.release('v')

            # 3. Restore previous clipboard asynchronously only if user didn't copy something else
            if old_clipboard is not None:
                def _restore():
                    time.sleep(0.25)
                    try:
                        # Only restore if clipboard still holds the text we just pasted
                        if pyperclip.paste() == text:
                            pyperclip.copy(old_clipboard)
                    except Exception:
                        pass

                threading.Thread(target=_restore, daemon=True).start()

        except Exception as e:
            print(f"Injection error: {e}")

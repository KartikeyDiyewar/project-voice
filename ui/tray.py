"""
Windows System Tray Integration
Creates a lightweight icon in the Windows taskbar tray (near the clock) for Project Voice.
Provides quick access to Dashboard / Settings, Project Folder, and clean exit.
"""

import os
import threading
from PIL import Image, ImageDraw
import pystray
from config.settings import BASE_DIR
from ui import theme

class TrayIcon:
    def __init__(self, on_open_dashboard=None, on_exit_callback=None):
        self.on_open_dashboard = on_open_dashboard
        self.on_exit_callback = on_exit_callback
        self.icon = None

    def _create_icon_image(self, color=None):
        """Tray icon: accent disc with the mic glyph, drawn 4x then downsampled.

        Tray icons render at 16-20px, so a bare outline mic disappears. A filled
        accent disc keeps the mark readable at that size.
        """
        accent = color or theme.on_ink("accent")
        size, ss = 64, 4
        big = size * ss
        image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)

        d.ellipse([0, 0, big - 1, big - 1], fill=accent)

        s = big / 100.0

        def box(x0, y0, x1, y1):
            return [x0 * s, y0 * s, x1 * s, y1 * s]

        white = (255, 255, 255, 255)
        d.rounded_rectangle(box(40, 24, 60, 52), radius=10 * s, fill=white)
        d.arc(box(30, 36, 70, 68), start=20, end=160, fill=white, width=int(6 * s))
        d.rounded_rectangle(box(47, 64, 53, 74), radius=3 * s, fill=white)
        d.rounded_rectangle(box(37, 73, 63, 79), radius=3 * s, fill=white)

        return image.resize((size, size), Image.LANCZOS)

    def _open_dashboard(self):
        if self.on_open_dashboard:
            self.on_open_dashboard()

    def _open_folder(self):
        try:
            os.startfile(BASE_DIR)
        except Exception:
            pass

    def _exit_app(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        if self.on_exit_callback:
            self.on_exit_callback()

    def run(self):
        """Starts the system tray icon loop."""
        menu = pystray.Menu(
            pystray.MenuItem("🎙️ Project Voice (Ctrl+Space)", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Settings & Dashboard", lambda icon, item: self._open_dashboard(), default=True),
            pystray.MenuItem("📁 Open Application Folder", lambda icon, item: self._open_folder()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ Exit Project Voice", lambda icon, item: self._exit_app())
        )

        self.icon = pystray.Icon(
            "ProjectVoice",
            self._create_icon_image(),
            "Project Voice (Ctrl+Space)",
            menu
        )
        self.icon.run()

    def start_in_background(self):
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

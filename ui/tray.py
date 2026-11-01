"""
Windows System Tray Integration
Creates a lightweight icon in the Windows taskbar tray (near the clock) for Project Voice.
Provides quick access to Dashboard / Settings, Project Folder, and clean exit.
"""

import os
import subprocess
import threading
from PIL import Image, ImageDraw
import pystray
from config.settings import BASE_DIR

class TrayIcon:
    def __init__(self, on_open_dashboard=None, on_exit_callback=None):
        self.on_open_dashboard = on_open_dashboard
        self.on_exit_callback = on_exit_callback
        self.icon = None

    def _create_icon_image(self, color="#2563eb"):
        """Generates a clean 64x64 blue microphone icon dynamically."""
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Rounded mic capsule
        draw.rounded_rectangle([22, 10, 42, 38], radius=10, fill=color)
        # Mic stand arc
        draw.arc([16, 22, 48, 46], start=0, end=180, fill=color, width=4)
        # Base line
        draw.line([32, 46, 32, 54], fill=color, width=4)
        draw.line([22, 54, 42, 54], fill=color, width=4)

        return image

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

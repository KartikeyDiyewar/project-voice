"""
Floating Visual Indicator Pill (Wispr Flow Style)
A sleek, non-intrusive glowing pill that appears at the bottom-center of the screen
only while recording or processing, and automatically vanishes when done.
Uses CTkToplevel tied to the main application root for 100% thread-safe UI updates.
"""

import customtkinter as ctk

class FloatingIndicator:
    def __init__(self, master=None):
        self.master = master
        self.current_state = "idle"
        self._init_window()

    def _init_window(self):
        # Uses CTkToplevel attached to master
        self.root = ctk.CTkToplevel(self.master)
        self.root.title("Project Voice Pill")
        self.root.overrideredirect(True)        # Borderless
        self.root.attributes("-topmost", True)   # Always on top
        self.root.attributes("-alpha", 0.95)     # Modern sleek glass effect

        # Dimensions & bottom-center positioning (Pill layout: 280x44)
        width = 280
        height = 44
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = screen_h - 110  # Positioned comfortably above Windows taskbar

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(fg_color="#090d16")

        # Container frame styled like a rounded pill
        self.container = ctk.CTkFrame(
            self.root,
            fg_color="#0d1322",
            border_width=1,
            border_color="#22304d",
            corner_radius=22
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # Glowing dot / status indicator icon
        self.dot_label = ctk.CTkLabel(
            self.container,
            text="●",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#ef4444"
        )
        self.dot_label.pack(side="left", padx=(14, 6))

        # Status message text
        self.text_label = ctk.CTkLabel(
            self.container,
            text="Listening...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f8fafc"
        )
        self.text_label.pack(side="left")

        # Pill right badge (Hotkey tag)
        self.sub_label = ctk.CTkLabel(
            self.container,
            text="[ Ctrl + Space ]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#64748b",
            fg_color="#141d33",
            corner_radius=6,
            padx=6,
            pady=2
        )
        self.sub_label.pack(side="right", padx=(0, 14))

        # Start hidden
        self.root.withdraw()

    def show_listening(self):
        """Called when user holds Ctrl+Space."""
        if not self.root:
            return
        def _apply():
            self.current_state = "listening"
            self.dot_label.configure(text="●", text_color="#ef4444")
            self.container.configure(border_color="#ef4444")
            self.text_label.configure(text="Listening...", text_color="#f8fafc")
            self.sub_label.configure(text="[ Ctrl + Space ]", text_color="#94a3b8")
            self.root.deiconify()
            self.root.lift()
        self.root.after(0, _apply)

    def show_processing(self):
        """Called when user releases Ctrl+Space."""
        if not self.root:
            return
        def _apply():
            self.current_state = "processing"
            self.dot_label.configure(text="✦", text_color="#f59e0b")
            self.container.configure(border_color="#f59e0b")
            self.text_label.configure(text="Refining voice...", text_color="#f8fafc")
            self.sub_label.configure(text="Groq LPU", text_color="#f59e0b")
            self.root.deiconify()
            self.root.lift()
        self.root.after(0, _apply)

    def show_pasted(self):
        """Called when text is injected into active window."""
        if not self.root:
            return
        def _apply():
            self.current_state = "pasted"
            self.dot_label.configure(text="✔", text_color="#10b981")
            self.container.configure(border_color="#10b981")
            self.text_label.configure(text="Pasted!", text_color="#34d399")
            self.sub_label.configure(text="Done", text_color="#10b981")
            self.root.after(700, self._hide_if_idle)
        self.root.after(0, _apply)

    def show_error(self, message="Error"):
        if not self.root:
            return
        def _apply():
            self.current_state = "error"
            self.dot_label.configure(text="✕", text_color="#f87171")
            self.container.configure(border_color="#f87171")
            self.text_label.configure(text=message[:18], text_color="#fca5a5")
            self.root.after(1400, self._hide_if_idle)
        self.root.after(0, _apply)

    def _hide_if_idle(self):
        if self.current_state in ("pasted", "idle", "error"):
            self.current_state = "idle"
            self.root.withdraw()

    def hide(self):
        if not self.root:
            return
        self.root.after(0, self.root.withdraw)

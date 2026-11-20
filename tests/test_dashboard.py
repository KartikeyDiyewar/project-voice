import pytest
from ui.dashboard import DashboardWindow
from ui.icons import get_icon
from ui.floating_indicator import FloatingIndicator


def test_dashboard_window_creation():
    """Verify the window builds, switches pages, and keeps the pill alive on retheme.

    _rebuild_ui() used to destroy every child of the root window, which also
    destroyed the floating indicator Toplevel, so Ctrl+Space stopped showing
    any visual feedback after a theme change.
    """
    app = DashboardWindow()
    try:
        app.withdraw()
        app.update()
        assert "Home" in app.pages
        assert "Voice Typing" in app.pages
        assert "Shortcuts" in app.pages
        assert "Settings" in app.pages
        assert "About" in app.pages
        assert app.active_tab == "Home"

        # Test page switching and icon re-tinting
        app._switch_page("Voice Typing")
        app.update()
        assert app.active_tab == "Voice Typing"

        app._switch_page("Home")
        app.update()
        assert app.active_tab == "Home"

        # The floating pill must survive a theme rebuild
        indicator = FloatingIndicator(master=app)
        app.update()
        assert indicator.root.winfo_exists()

        app._toggle_appearance()
        app.update()
        assert indicator.root.winfo_exists(), "pill was destroyed by the theme rebuild"

        indicator.show_listening()
        app.update()
        assert indicator.current_state == "listening"

        app._toggle_appearance()
        app.update()
        assert indicator.root.winfo_exists()
        assert app.active_tab == "Home"
    finally:
        app.destroy()


def test_vector_icons_generation():
    """Verify all 10 monochrome vector icons generate as valid CTkImage objects."""
    icon_names = ["home", "voice", "shortcuts", "settings", "about", "bell", "wave", "windows", "play", "words"]
    for name in icon_names:
        icon = get_icon(name, color="#1e293b", size=(18, 18))
        assert icon is not None
        assert hasattr(icon, "_size")
        assert icon._size == (18, 18)

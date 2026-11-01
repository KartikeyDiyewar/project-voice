import pytest
from ui.dashboard import DashboardWindow
from ui.icons import get_icon

def test_dashboard_window_creation():
    """Verify DashboardWindow initializes, loads pages, and destroys cleanly."""
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

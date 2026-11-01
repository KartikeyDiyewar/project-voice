import pytest
from ui.dashboard import DashboardWindow

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

        # Test page switching
        app._switch_page("Voice Typing")
        app.update()
        assert app.active_tab == "Voice Typing"

        app._switch_page("Home")
        app.update()
        assert app.active_tab == "Home"
    finally:
        app.destroy()

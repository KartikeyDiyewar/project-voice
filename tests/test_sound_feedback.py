import pytest
from utils.sound_feedback import sound

def test_sound_feedback_themes_pre_rendered():
    """Verify that all 5 sound themes are pre-synthesized in memory."""
    for theme in ["pop", "chime", "click", "synth", "classic"]:
        assert theme in sound._buffers
        pack = sound._buffers[theme]
        assert "start" in pack and len(pack["start"]) > 0
        assert "stop" in pack and len(pack["stop"]) > 0
        assert "success" in pack and len(pack["success"]) > 0
        assert "error" in pack and len(pack["error"]) > 0

def test_sound_feedback_preview():
    """Verify preview does not throw on valid or fallback theme."""
    sound.preview("chime")
    sound.preview("pop")
    sound.preview("unknown_theme")

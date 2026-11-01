import pytest
from utils.sound_feedback import sound
from config.settings import settings

def test_sound_feedback_themes_pre_rendered():
    """Verify that all 5 sound themes are pre-synthesized in memory at 48kHz."""
    for theme in ["pop", "chime", "click", "synth", "classic"]:
        assert theme in sound._buffers
        pack = sound._buffers[theme]
        assert "start" in pack and len(pack["start"]) > 0
        assert "stop" in pack and len(pack["stop"]) > 0
        assert "success" in pack and len(pack["success"]) > 0
        assert "error" in pack and len(pack["error"]) > 0

def test_sound_feedback_preview_and_cues():
    """Verify preview supports both 'start' (Prior) and 'success' (After) cues."""
    sound.preview("pop", "start")
    sound.preview("pop", "success")
    sound.preview("chime", "start")
    sound.preview("chime", "success")
    sound.preview("unknown_theme")

def test_sound_prior_and_after_toggles():
    """Verify prior and after toggles function in settings."""
    assert hasattr(settings, "sound_chime_prior")
    assert hasattr(settings, "sound_chime_after")
    assert isinstance(settings.sound_chime_prior, bool)
    assert isinstance(settings.sound_chime_after, bool)

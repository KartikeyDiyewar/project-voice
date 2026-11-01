import json
import pytest
from pathlib import Path
from config import Settings

def test_settings_deep_merge(tmp_path):
    """PV-024: Settings updates must deep-merge nested sections without wiping sibling keys."""
    settings_file = tmp_path / "settings.json"
    env_file = tmp_path / ".env"

    initial_data = {
        "hotkey": "ctrl+space",
        "audio": {"sample_rate": 16000, "channels": 1},
        "ai": {"stt_model": "whisper-large-v3-turbo", "temperature": 0.1}
    }
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    s = Settings(settings_file=settings_file, env_file=env_file)
    # Update nested key in 'ai'
    s.update_settings({"ai": {"temperature": 0.3}})

    # Check that stt_model was not wiped
    assert s.data["ai"]["temperature"] == 0.3
    assert s.data["ai"]["stt_model"] == "whisper-large-v3-turbo"
    assert s.data["audio"]["sample_rate"] == 16000

def test_atomic_api_key_update(tmp_path):
    """PV-025: API key update must write atomically and return success boolean."""
    env_file = tmp_path / ".env"
    settings_file = tmp_path / "settings.json"

    s = Settings(settings_file=settings_file, env_file=env_file)
    res = s.update_api_key("gsk_test123456789")
    assert res is True
    assert s.groq_api_key == "gsk_test123456789"
    assert env_file.exists()
    assert "GROQ_API_KEY=gsk_test123456789" in env_file.read_text(encoding="utf-8")

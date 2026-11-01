"""
Configuration Loader for Wispr Flow
Manages application settings from settings.json and secrets from .env
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

import sys

# Base paths (PyInstaller frozen executable compatibility)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "settings.json"
ENV_FILE = BASE_DIR / ".env"

# Load environment variables
load_dotenv(dotenv_path=ENV_FILE)

class Settings:
    def __init__(self, settings_file: Path = None, env_file: Path = None):
        self.base_dir = BASE_DIR
        self.settings_file = settings_file or SETTINGS_FILE
        self.env_file = env_file or ENV_FILE
        if self.env_file.exists():
            load_dotenv(dotenv_path=self.env_file)
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.data = self._load_json()

    def _load_json(self):
        if not self.settings_file.exists():
            return {
                "hotkey": "ctrl+space",
                "fallback_hotkey": "f8",
                "audio": {"sample_rate": 16000, "channels": 1},
                "ai": {
                    "stt_provider": "groq",
                    "stt_model": "whisper-large-v3-turbo",
                    "llm_provider": "groq",
                    "llm_model": "qwen/qwen3.8-27b",
                    "temperature": 0.1
                },
                "sound_feedback": True
            }
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {self.settings_file.name}: {e}")
            return {}

    @property
    def hotkey(self) -> str:
        return self.data.get("hotkey", "ctrl+space").lower()

    @property
    def fallback_hotkey(self) -> str:
        return self.data.get("fallback_hotkey", "f8").lower()

    @property
    def sample_rate(self) -> int:
        return self.data.get("audio", {}).get("sample_rate", 16000)

    @property
    def channels(self) -> int:
        return self.data.get("audio", {}).get("channels", 1)

    @property
    def stt_model(self) -> str:
        return self.data.get("ai", {}).get("stt_model", "whisper-large-v3-turbo")

    @property
    def stt_language(self) -> str | None:
        """Language code for Whisper. Default 'auto' (None) permits natural code-switching without English acoustic bias."""
        lang = self.data.get("ai", {}).get("stt_language", "auto")
        return None if lang in ("auto", "none", None, "") else lang

    @property
    def llm_model(self) -> str:
        return self.data.get("ai", {}).get("llm_model", "qwen/qwen3.8-27b")

    @property
    def temperature(self) -> float:
        return self.data.get("ai", {}).get("temperature", 0.1)

    @property
    def sound_feedback(self) -> bool:
        return self.data.get("sound_feedback", True)

    @property
    def sound_chime_prior(self) -> bool:
        """Whether to play chime on hotkey press (start listening)."""
        return self.data.get("sound_chime_prior", True)

    @property
    def sound_chime_after(self) -> bool:
        """Whether to play chime on text paste (completion)."""
        return self.data.get("sound_chime_after", True)

    @property
    def sound_theme(self) -> str:
        """Sound pack theme: 'pop', 'chime', 'click', 'synth', 'classic'."""
        return self.data.get("sound_theme", "pop").lower()

    @property
    def indicator_animation(self) -> str:
        """Floating indicator animation: 'wave_bars', 'wave_dots', 'sine_wave'."""
        return self.data.get("indicator_animation", "wave_bars").lower()

    def update_api_key(self, api_key: str) -> bool:
        """Saves GROQ_API_KEY to runtime environment and .env file atomically."""
        self.groq_api_key = api_key.strip()
        os.environ["GROQ_API_KEY"] = self.groq_api_key
        try:
            temp_env = self.env_file.with_suffix(".tmp")
            with open(temp_env, "w", encoding="utf-8") as f:
                f.write(f"GROQ_API_KEY={self.groq_api_key}\n")
            temp_env.replace(self.env_file)
            return True
        except Exception as e:
            print(f"Error saving {self.env_file.name}: {e}")
            return False

    def update_settings(self, updates: dict) -> bool:
        """Deep-merges updates and persists settings.json atomically."""
        def _deep_merge(target, source):
            for k, v in source.items():
                if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                    _deep_merge(target[k], v)
                else:
                    target[k] = v

        _deep_merge(self.data, updates)
        try:
            temp_settings = self.settings_file.with_suffix(".tmp")
            with open(temp_settings, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            temp_settings.replace(self.settings_file)
            return True
        except Exception as e:
            print(f"Error saving {self.settings_file.name}: {e}")
            return False
            print(f"Error saving settings.json: {e}")

settings = Settings()

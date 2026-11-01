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
    def __init__(self):
        self.base_dir = BASE_DIR
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.data = self._load_json()

    def _load_json(self):
        if not SETTINGS_FILE.exists():
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
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings.json: {e}")
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
    def llm_model(self) -> str:
        return self.data.get("ai", {}).get("llm_model", "qwen/qwen3.8-27b")

    @property
    def temperature(self) -> float:
        return self.data.get("ai", {}).get("temperature", 0.1)

    @property
    def sound_feedback(self) -> bool:
        return self.data.get("sound_feedback", True)

    def update_api_key(self, api_key: str):
        """Saves GROQ_API_KEY to runtime environment and .env file."""
        self.groq_api_key = api_key.strip()
        os.environ["GROQ_API_KEY"] = self.groq_api_key
        try:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(f"GROQ_API_KEY={self.groq_api_key}\n")
        except Exception as e:
            print(f"Error saving .env: {e}")

    def update_settings(self, updates: dict):
        """Updates and persists settings.json."""
        self.data.update(updates)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings.json: {e}")

settings = Settings()

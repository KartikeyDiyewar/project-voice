"""
Audio Feedback Utility
Provides subtle system sound cues during recording and pasting.
"""

import threading
import winsound
from config.settings import settings

class SoundFeedback:
    def __init__(self):
        pass

    @property
    def enabled(self) -> bool:
        return settings.sound_feedback

    def _beep_async(self, freqs_and_durations):
        if not self.enabled:
            return
        def _play():
            try:
                for freq, duration in freqs_and_durations:
                    winsound.Beep(freq, duration)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    def play_start(self):
        """Chime when user starts speaking."""
        self._beep_async([(1200, 80)])

    def play_stop(self):
        """Chime when user releases the hotkey."""
        self._beep_async([(800, 60)])

    def play_success(self):
        """Upbeat double chime when text is pasted."""
        self._beep_async([(1400, 50), (1800, 70)])

    def play_error(self):
        """Low warning beep if an error occurs."""
        self._beep_async([(400, 160)])

sound = SoundFeedback()

"""
Audio Feedback Utility (Studio Grade 48 kHz)
Generates high-fidelity, smooth harmonic sound chimes directly in memory.
Synthesized natively at 48,000 Hz with raised-cosine (Hann) acoustic envelopes.

Features:
- Chime Prior (Start): Instant, audible rising cue on hotkey press (Ctrl+Space down)
- Chime After (Finish): Melodic completion chime on text injection (paste)
- Independent customizable toggles: sound_chime_prior and sound_chime_after
- 5 Acoustic themes: Pop (Wispr Flow), Chime (Raycast), Click (Tactile), Synth (Rhodes), Classic
"""

import io
import threading
import wave
import winsound
import numpy as np
from config.settings import settings

def _make_wav(samples: np.ndarray, sample_rate: int = 48000) -> bytes:
    """Encodes float32 samples into standard 16-bit PCM WAV bytes."""
    audio_int16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()

def _apply_hann(signal: np.ndarray, sr: int = 48000) -> np.ndarray:
    """Smooths signal ends with raised-cosine windowing to prevent DAC clicks."""
    n = len(signal)
    att_len = min(int(0.004 * sr), n // 3)
    if att_len > 0:
        signal[:att_len] *= 0.5 * (1.0 - np.cos(np.pi * np.arange(att_len) / att_len))
    rel_len = min(int(0.008 * sr), n // 3)
    if rel_len > 0:
        signal[-rel_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(rel_len) / rel_len))
    return signal

def _synth(freq: float, duration: float, env_type: str = "exp", vol: float = 0.28, sr: int = 48000) -> np.ndarray:
    """Synthesizes smooth, anti-aliased sine audio with natural acoustic decay."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    if env_type == "exp":
        env = np.exp(-t * (4.2 / duration))
        audio = np.sin(2 * np.pi * freq * t)
    elif env_type == "bell":
        env = (1.0 - (t / duration) ** 0.8) * np.exp(-t * (2.8 / duration))
        audio = 0.72 * np.sin(2 * np.pi * freq * t) + 0.28 * np.sin(2 * np.pi * freq * 2.0 * t)
    elif env_type == "click":
        env = np.exp(-t * 240.0)
        audio = np.sin(2 * np.pi * freq * t)
    elif env_type == "synth":
        env = np.exp(-t * (3.5 / duration))
        audio = 0.65 * np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * (freq * 1.5) * t)
    else:
        env = np.ones_like(t)
        audio = np.sin(2 * np.pi * freq * t)

    return _apply_hann((audio * env * vol).astype(np.float32), sr)

def _synth_sweep(f_start: float, f_end: float, duration: float, vol: float = 0.30, sr: int = 48000) -> np.ndarray:
    """Synthesizes smooth rising frequency chirp (ideal for instant listening feedback)."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    freq_t = np.linspace(f_start, f_end, n)
    phase = 2 * np.pi * np.cumsum(freq_t) / sr
    env = np.exp(-t * (3.0 / duration))
    signal = np.sin(phase) * env * vol
    return _apply_hann(signal.astype(np.float32), sr)

class SoundFeedback:
    def __init__(self):
        self._buffers = {}
        self._pre_render_all()

    def _pre_render_all(self):
        sr = 48000

        # 1. Pop Theme (Wispr Flow) - Audible rising chirp on start, double pop on finish
        self._buffers["pop"] = {
            "start": _make_wav(_synth_sweep(480, 780, 0.085, 0.32, sr), sr),
            "stop": _make_wav(_synth(430, 0.04, "exp", 0.24, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(620, 0.035, "exp", 0.26, sr),
                np.zeros(int(sr * 0.015), dtype=np.float32),
                _synth(880, 0.060, "exp", 0.30, sr)
            ]), sr),
            "error": _make_wav(_synth(220, 0.12, "exp", 0.32, sr), sr)
        }

        # 2. Chime Theme (Raycast / Apple) - Warm harmonic bell on start, triple arpeggio on finish
        self._buffers["chime"] = {
            "start": _make_wav(_synth(880, 0.085, "bell", 0.30, sr), sr),
            "stop": _make_wav(_synth(659, 0.05, "bell", 0.22, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(1046, 0.04, "bell", 0.24, sr),
                np.zeros(int(sr * 0.012), dtype=np.float32),
                _synth(1318, 0.04, "bell", 0.26, sr),
                np.zeros(int(sr * 0.012), dtype=np.float32),
                _synth(1568, 0.085, "bell", 0.30, sr)
            ]), sr),
            "error": _make_wav(np.concatenate([
                _synth(440, 0.06, "bell", 0.28, sr),
                _synth(370, 0.09, "bell", 0.28, sr)
            ]), sr)
        }

        # 3. Click Theme (Tactile Minimal) - Crisp tactile switches
        self._buffers["click"] = {
            "start": _make_wav(_synth(1600, 0.03, "click", 0.36, sr), sr),
            "stop": _make_wav(_synth(1100, 0.02, "click", 0.28, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(1400, 0.022, "click", 0.32, sr),
                np.zeros(int(sr * 0.02), dtype=np.float32),
                _synth(1800, 0.025, "click", 0.36, sr)
            ]), sr),
            "error": _make_wav(np.concatenate([
                _synth(350, 0.04, "click", 0.36, sr),
                np.zeros(int(sr * 0.02), dtype=np.float32),
                _synth(300, 0.05, "click", 0.36, sr)
            ]), sr)
        }

        # 4. Synth Theme (Ambient Rhodes)
        self._buffers["synth"] = {
            "start": _make_wav(_synth(550, 0.08, "synth", 0.30, sr), sr),
            "stop": _make_wav(_synth(330, 0.05, "synth", 0.22, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(523, 0.04, "synth", 0.24, sr),
                _synth(659, 0.04, "synth", 0.26, sr),
                _synth(784, 0.04, "synth", 0.26, sr),
                _synth(1046, 0.085, "synth", 0.30, sr)
            ]), sr),
            "error": _make_wav(_synth(200, 0.14, "synth", 0.32, sr), sr)
        }

        # 5. Classic Theme (Clean Electronic Beep)
        self._buffers["classic"] = {
            "start": _make_wav(_synth(920, 0.065, "exp", 0.32, sr), sr),
            "stop": _make_wav(_synth(800, 0.04, "exp", 0.25, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(1200, 0.04, "exp", 0.28, sr),
                np.zeros(int(sr * 0.02), dtype=np.float32),
                _synth(1500, 0.065, "exp", 0.32, sr)
            ]), sr),
            "error": _make_wav(_synth(400, 0.12, "exp", 0.34, sr), sr)
        }

    @property
    def enabled(self) -> bool:
        return settings.sound_feedback

    def _play_wav_async(self, wav_bytes: bytes):
        if not self.enabled or not wav_bytes:
            return
        def _runner():
            try:
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
            except Exception:
                pass
        threading.Thread(target=_runner, daemon=True).start()

    def play_start(self):
        """Plays start-speaking chime on hotkey press (Prior)."""
        if not self.enabled or not settings.sound_chime_prior:
            return
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["start"])

    def play_stop(self):
        """Plays key-release chime."""
        if not self.enabled or not settings.sound_chime_after:
            return
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["stop"])

    def play_success(self):
        """Plays text-injected success chime on finish (After)."""
        if not self.enabled or not settings.sound_chime_after:
            return
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["success"])

    def play_error(self):
        """Plays error chime."""
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["error"])

    def preview(self, theme_name: str, cue_type: str = "start"):
        """Previews chime for a given sound theme immediately."""
        pack = self._buffers.get(theme_name.lower()) or self._buffers["pop"]
        wav = pack.get(cue_type) or pack["start"]
        self._play_wav_async(wav)

sound = SoundFeedback()

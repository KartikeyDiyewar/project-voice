"""
Audio Feedback Utility (Studio Grade 48 kHz)
Generates high-fidelity, smooth harmonic sound chimes directly in memory.
Synthesized natively at 48,000 Hz (Windows WASAPI native mixing rate)
with raised-cosine (Hann) acoustic envelopes to guarantee zero DAC pops or clicks.
Themes available:
1. 'pop'     -> Subtle bubble pop (Wispr Flow style, default)
2. 'chime'   -> Warm harmonic bell chord (Apple / Raycast style)
3. 'click'   -> Crisp tactile haptic click
4. 'synth'   -> Mellow Rhodes ambient tone
5. 'classic' -> Clean electronic tone
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

def _synth(freq: float, duration: float, env_type: str = "exp", vol: float = 0.28, sr: int = 48000) -> np.ndarray:
    """
    Synthesizes smooth, anti-aliased sine audio with natural acoustic decay
    and raised-cosine (Hann) windowing on attack and release to eliminate DAC clicks.
    """
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    if env_type == "exp":
        env = np.exp(-t * (5.0 / duration))
        audio = np.sin(2 * np.pi * freq * t)
    elif env_type == "bell":
        env = (1.0 - (t / duration) ** 0.8) * np.exp(-t * (3.0 / duration))
        # Fundamental + warm harmonic overtone
        audio = 0.72 * np.sin(2 * np.pi * freq * t) + 0.28 * np.sin(2 * np.pi * freq * 2.0 * t)
    elif env_type == "click":
        env = np.exp(-t * 260.0)
        audio = np.sin(2 * np.pi * freq * t)
    elif env_type == "synth":
        env = np.exp(-t * (3.8 / duration))
        audio = 0.65 * np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * (freq * 1.5) * t)
    else:
        env = np.ones_like(t)
        audio = np.sin(2 * np.pi * freq * t)

    signal = (audio * env * vol).astype(np.float32)

    # 4ms Hann smooth attack (prevents startup click)
    attack_len = min(int(0.004 * sr), n_samples // 3)
    if attack_len > 0:
        attack = 0.5 * (1.0 - np.cos(np.pi * np.arange(attack_len) / attack_len))
        signal[:attack_len] *= attack

    # 8ms Hann smooth release fade-out to absolute zero (prevents DAC click on stop)
    release_len = min(int(0.008 * sr), n_samples // 3)
    if release_len > 0:
        release = 0.5 * (1.0 + np.cos(np.pi * np.arange(release_len) / release_len))
        signal[-release_len:] *= release

    return signal

class SoundFeedback:
    def __init__(self):
        # Pre-synthesize all themes on startup for zero-latency (<1ms) playback
        self._buffers = {}
        self._pre_render_all()

    def _pre_render_all(self):
        sr = 48000

        # 1. Pop Theme (Wispr Flow)
        self._buffers["pop"] = {
            "start": _make_wav(_synth(560, 0.05, "exp", 0.26, sr), sr),
            "stop": _make_wav(_synth(430, 0.04, "exp", 0.24, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(620, 0.035, "exp", 0.24, sr),
                np.zeros(int(sr * 0.015), dtype=np.float32),
                _synth(860, 0.055, "exp", 0.28, sr)
            ]), sr),
            "error": _make_wav(_synth(220, 0.12, "exp", 0.30, sr), sr)
        }

        # 2. Chime Theme (Raycast / Apple)
        self._buffers["chime"] = {
            "start": _make_wav(_synth(784, 0.08, "bell", 0.24, sr), sr),
            "stop": _make_wav(_synth(659, 0.06, "bell", 0.22, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(1046, 0.04, "bell", 0.22, sr),
                np.zeros(int(sr * 0.012), dtype=np.float32),
                _synth(1318, 0.04, "bell", 0.24, sr),
                np.zeros(int(sr * 0.012), dtype=np.float32),
                _synth(1568, 0.08, "bell", 0.28, sr)
            ]), sr),
            "error": _make_wav(np.concatenate([
                _synth(440, 0.06, "bell", 0.26, sr),
                _synth(370, 0.09, "bell", 0.26, sr)
            ]), sr)
        }

        # 3. Click Theme (Tactile Minimal)
        self._buffers["click"] = {
            "start": _make_wav(_synth(1600, 0.02, "click", 0.34, sr), sr),
            "stop": _make_wav(_synth(1100, 0.018, "click", 0.30, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(1400, 0.018, "click", 0.30, sr),
                np.zeros(int(sr * 0.02), dtype=np.float32),
                _synth(1800, 0.022, "click", 0.34, sr)
            ]), sr),
            "error": _make_wav(np.concatenate([
                _synth(350, 0.04, "click", 0.34, sr),
                np.zeros(int(sr * 0.02), dtype=np.float32),
                _synth(300, 0.05, "click", 0.34, sr)
            ]), sr)
        }

        # 4. Synth Theme (Ambient Rhodes)
        self._buffers["synth"] = {
            "start": _make_wav(_synth(440, 0.07, "synth", 0.26, sr), sr),
            "stop": _make_wav(_synth(330, 0.05, "synth", 0.22, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(523, 0.04, "synth", 0.22, sr),
                _synth(659, 0.04, "synth", 0.24, sr),
                _synth(784, 0.04, "synth", 0.24, sr),
                _synth(1046, 0.08, "synth", 0.28, sr)
            ]), sr),
            "error": _make_wav(_synth(200, 0.14, "synth", 0.30, sr), sr)
        }

        # 5. Classic Theme (Clean Electronic Beep)
        self._buffers["classic"] = {
            "start": _make_wav(_synth(1000, 0.05, "exp", 0.28, sr), sr),
            "stop": _make_wav(_synth(800, 0.04, "exp", 0.25, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth(1200, 0.04, "exp", 0.26, sr),
                np.zeros(int(sr * 0.02), dtype=np.float32),
                _synth(1500, 0.06, "exp", 0.28, sr)
            ]), sr),
            "error": _make_wav(_synth(400, 0.12, "exp", 0.32, sr), sr)
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
        """Plays start-speaking chime based on active theme."""
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["start"])

    def play_stop(self):
        """Plays key-release chime."""
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["stop"])

    def play_success(self):
        """Plays text-injected success chime."""
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["success"])

    def play_error(self):
        """Plays error chime."""
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["error"])

    def preview(self, theme_name: str):
        """Previews the success chime for a given sound theme immediately."""
        pack = self._buffers.get(theme_name.lower()) or self._buffers["pop"]
        self._play_wav_async(pack["success"])

sound = SoundFeedback()

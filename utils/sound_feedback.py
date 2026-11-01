"""
Audio Feedback Utility (Studio Grade 48 kHz)
Generates high-fidelity, smooth harmonic sound chimes directly in memory.
Synthesized natively at 48,000 Hz with raised-cosine (Hann) acoustic envelopes.

Features:
- Chime Prior (Start): Instant, clearly audible rising cue on hotkey press (Ctrl+Space down)
- Chime After (Finish): Melodic completion chime on text injection (paste)
- Independent customizable toggles: sound_chime_prior and sound_chime_after
- 5 Studio Acoustic themes: Pop (Wispr Flow), Chime (Raycast), Click (Tactile), Synth (Rhodes), Classic
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

def _synth_tone(freq: float, duration: float, vol: float = 0.40, harmonic: float = 0.0, env_mode: str = "smooth", sr: int = 48000) -> np.ndarray:
    """Synthesizes rich, anti-aliased audio with raised-cosine anti-pop envelope."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    audio = np.sin(2 * np.pi * freq * t)
    if harmonic > 0:
        audio = (1.0 - harmonic) * audio + harmonic * np.sin(2 * np.pi * (freq * 1.5) * t)

    if env_mode == "bell":
        env = (1.0 - (t / duration) ** 0.8) * np.exp(-t * (1.8 / duration))
    else:
        att = min(int(0.012 * sr), n // 4)
        rel = min(int(0.045 * sr), n // 2)
        env = np.ones(n, dtype=np.float32)
        if att > 0:
            env[:att] = 0.5 * (1.0 - np.cos(np.pi * np.arange(att) / att))
        if rel > 0:
            env[-rel:] = 0.5 * (1.0 + np.cos(np.pi * np.arange(rel) / rel))

    return (audio * env * vol).astype(np.float32)

def _synth_sweep(f_start: float, f_end: float, duration: float, vol: float = 0.40, sr: int = 48000) -> np.ndarray:
    """Synthesizes smooth rising frequency chirp (instant listening feedback with zero click)."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    freq_t = np.linspace(f_start, f_end, n)
    phase = 2 * np.pi * np.cumsum(freq_t) / sr
    audio = np.sin(phase)
    att = min(int(0.012 * sr), n // 4)
    rel = min(int(0.050 * sr), n // 2)
    env = np.ones(n, dtype=np.float32)
    if att > 0:
        env[:att] = 0.5 * (1.0 - np.cos(np.pi * np.arange(att) / att))
    if rel > 0:
        env[-rel:] = 0.5 * (1.0 + np.cos(np.pi * np.arange(rel) / rel))
    return (audio * env * vol).astype(np.float32)

def _synth_click(duration: float = 0.085, vol: float = 0.42, sr: int = 48000) -> np.ndarray:
    """Synthesizes punchy tactile mechanical switch snap audible on laptop speakers."""
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    audio = 0.55 * np.sin(2 * np.pi * 450 * t) + 0.45 * np.sin(2 * np.pi * 1250 * t)
    att = min(int(0.005 * sr), n // 4)
    rel = min(int(0.045 * sr), n // 2)
    env = np.ones(n, dtype=np.float32)
    if att > 0:
        env[:att] = 0.5 * (1.0 - np.cos(np.pi * np.arange(att) / att))
    if rel > 0:
        env[-rel:] = 0.5 * (1.0 + np.cos(np.pi * np.arange(rel) / rel))
    return (audio * env * vol).astype(np.float32)

class SoundFeedback:
    def __init__(self):
        self._buffers = {}
        self._pre_render_all()

    def _pre_render_all(self):
        sr = 48000

        # 1. Pop Theme (Wispr Flow) - Modern rising chirp on start, double pop on finish
        self._buffers["pop"] = {
            "start": _make_wav(_synth_sweep(520, 820, 0.135, 0.40, sr), sr),
            "stop": _make_wav(_synth_tone(440, 0.070, 0.30, sr=sr), sr),
            "success": _make_wav(np.concatenate([
                _synth_tone(659, 0.065, 0.38, sr=sr),
                np.zeros(int(sr * 0.018), dtype=np.float32),
                _synth_tone(932, 0.110, 0.42, sr=sr)
            ]), sr),
            "error": _make_wav(_synth_tone(220, 0.180, 0.38, sr=sr), sr)
        }

        # 2. Chime Theme (Raycast / Apple) - Warm harmonic bell on start, triple arpeggio on finish
        self._buffers["chime"] = {
            "start": _make_wav(_synth_tone(880, 0.150, 0.38, harmonic=0.28, env_mode="bell", sr=sr), sr),
            "stop": _make_wav(_synth_tone(659, 0.080, 0.28, env_mode="bell", sr=sr), sr),
            "success": _make_wav(np.concatenate([
                _synth_tone(1046, 0.060, 0.34, env_mode="bell", sr=sr),
                _synth_tone(1318, 0.060, 0.36, env_mode="bell", sr=sr),
                _synth_tone(1568, 0.120, 0.40, env_mode="bell", sr=sr)
            ]), sr),
            "error": _make_wav(np.concatenate([
                _synth_tone(440, 0.080, 0.34, env_mode="bell", sr=sr),
                _synth_tone(350, 0.120, 0.36, env_mode="bell", sr=sr)
            ]), sr)
        }

        # 3. Click Theme (Tactile Mechanical) - Substantial tactile switch snap
        self._buffers["click"] = {
            "start": _make_wav(_synth_click(0.085, 0.42, sr), sr),
            "stop": _make_wav(_synth_click(0.050, 0.30, sr), sr),
            "success": _make_wav(np.concatenate([
                _synth_click(0.050, 0.38, sr),
                np.zeros(int(sr * 0.015), dtype=np.float32),
                _synth_click(0.070, 0.42, sr)
            ]), sr),
            "error": _make_wav(_synth_tone(280, 0.120, 0.38, sr=sr), sr)
        }

        # 4. Synth Theme (Ambient Rhodes)
        self._buffers["synth"] = {
            "start": _make_wav(_synth_tone(587, 0.150, 0.38, harmonic=0.32, sr=sr), sr),
            "stop": _make_wav(_synth_tone(392, 0.080, 0.28, sr=sr), sr),
            "success": _make_wav(np.concatenate([
                _synth_tone(523, 0.055, 0.34, sr=sr),
                _synth_tone(659, 0.055, 0.36, sr=sr),
                _synth_tone(880, 0.120, 0.40, harmonic=0.25, sr=sr)
            ]), sr),
            "error": _make_wav(_synth_tone(220, 0.160, 0.36, sr=sr), sr)
        }

        # 5. Classic Theme (Clean Electronic Beep)
        self._buffers["classic"] = {
            "start": _make_wav(_synth_tone(880, 0.120, 0.38, sr=sr), sr),
            "stop": _make_wav(_synth_tone(660, 0.070, 0.28, sr=sr), sr),
            "success": _make_wav(np.concatenate([
                _synth_tone(880, 0.065, 0.36, sr=sr),
                np.zeros(int(sr * 0.015), dtype=np.float32),
                _synth_tone(1320, 0.100, 0.40, sr=sr)
            ]), sr),
            "error": _make_wav(_synth_tone(330, 0.160, 0.36, sr=sr), sr)
        }

    @property
    def enabled(self) -> bool:
        return settings.sound_feedback

    def _play_wav_async(self, wav_bytes: bytes):
        if not self.enabled or not wav_bytes:
            return
        def _runner(payload: bytes):
            try:
                # SND_MEMORY plays buffer synchronously in thread, SND_NODEFAULT suppresses fallback ding
                winsound.PlaySound(payload, winsound.SND_MEMORY | winsound.SND_NODEFAULT)
            except Exception:
                pass
        threading.Thread(target=_runner, args=(wav_bytes,), daemon=True).start()

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
        if not self.enabled:
            return
        theme = settings.sound_theme
        pack = self._buffers.get(theme) or self._buffers["pop"]
        self._play_wav_async(pack["error"])

    def preview(self, theme_name: str, cue_type: str = "start"):
        """Previews chime for a given sound theme immediately."""
        pack = self._buffers.get(theme_name.lower()) or self._buffers["pop"]
        wav = pack.get(cue_type) or pack["start"]
        self._play_wav_async(wav)

sound = SoundFeedback()

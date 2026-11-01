"""
Audio Recording Engine with Pre-roll Ring Buffer & Release Tail
Implements professional dictation audio capture:
- Thread-safe persistent stream with pre-roll ring buffer
- Release tail (~220ms AFTER key-up) so trailing syllables are never clipped
- No digital zeros (prevents Whisper silence hallucinations)
- Gentle peak normalization to -3 dBFS
- Dynamic stream auto-recovery
"""

import collections
import io
import threading
import time
import numpy as np
from scipy.io.wavfile import write
import sounddevice as sd
from config.settings import settings

class AudioRecorder:
    def __init__(self):
        self.sample_rate = settings.sample_rate
        self.channels = settings.channels
        self.is_recording = False
        
        # 350ms pre-roll ring buffer of real room audio
        self.pre_roll_samples = int(0.35 * self.sample_rate)
        self.ring_buffer = collections.deque(maxlen=self.pre_roll_samples)
        
        # Concurrency lock protecting buffers
        self.buffer_lock = threading.Lock()
        
        # Active recording buffer
        self.active_buffer = []
        self.stream = None
        self._start_persistent_stream()

    def _start_persistent_stream(self):
        """Keeps mic stream always warm to avoid 100ms WASAPI open delay."""
        try:
            if self.stream:
                try:
                    self.stream.close()
                except Exception:
                    pass
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Error opening persistent audio stream: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        # Always feed ring buffer with ambient room tone
        flat_data = indata.flatten()
        with self.buffer_lock:
            self.ring_buffer.extend(flat_data)
            if self.is_recording:
                self.active_buffer.append(indata.copy())

    def start(self):
        """Called immediately on hotkey press."""
        # Auto-recover stream if it died or disconnected
        if not self.stream or not self.stream.active:
            self._start_persistent_stream()

        with self.buffer_lock:
            if self.is_recording:
                return
            self.active_buffer = []
            # Thread-safe snapshot of pre-roll
            pre_roll_data = np.array(list(self.ring_buffer), dtype=np.int16)
            if len(pre_roll_data) > 0:
                self.active_buffer.append(pre_roll_data.reshape(-1, 1))
            self.is_recording = True

    def stop(self) -> bytes:
        """Called on hotkey release in a background worker thread."""
        if not self.is_recording:
            return b""

        # Release tail: wait 220ms so final syllable decays naturally
        time.sleep(0.22)

        with self.buffer_lock:
            self.is_recording = False
            if not self.active_buffer:
                return b""
            chunks = list(self.active_buffer)
            self.active_buffer = []

        full_audio = np.concatenate(chunks, axis=0)
        if full_audio.ndim > 1:
            full_audio = full_audio.flatten()

        if len(full_audio) == 0:
            return b""

        # Gate on minimum duration (ignore accidental taps < 350ms total)
        duration = len(full_audio) / self.sample_rate
        if duration < 0.35:
            return b""

        # Gentle Peak Normalization to ~ -3 dBFS (22,000 max) without zero-padding
        max_val = np.max(np.abs(full_audio))
        if 500 < max_val < 18000:
            scale = 22000.0 / max_val
            full_audio = np.clip(full_audio.astype(np.float32) * scale, -32768, 32767).astype(np.int16)

        # Pack into pure in-memory WAV buffer
        wav_io = io.BytesIO()
        write(wav_io, self.sample_rate, full_audio)
        wav_io.seek(0)

        # Save debug WAV in project root safely
        try:
            debug_path = settings.base_dir / "last_dictation.wav"
            write(str(debug_path), self.sample_rate, full_audio)
        except Exception:
            pass

        return wav_io.read()

    @property
    def active(self) -> bool:
        return self.is_recording

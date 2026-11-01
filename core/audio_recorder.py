"""
Audio Recording Engine with Pre-roll Ring Buffer & Release Tail
Implements professional dictation audio capture:
- Pure in-memory RAM audio capture (standard library wave, zero scipy overhead)
- Thread-safe persistent stream with pre-roll ring buffer
- Release tail (~200ms AFTER key-up) so trailing syllables are never clipped
- No digital zeros (prevents Whisper silence hallucinations)
- Gentle peak normalization to -3 dBFS
- Dynamic stream auto-recovery
- True zero-disk storage (honors privacy guarantees)
"""

import collections
import io
import threading
import time
import wave
import numpy as np
import sounddevice as sd
from config.settings import settings

class AudioRecorder:
    def __init__(self):
        self.sample_rate = settings.sample_rate
        self.channels = settings.channels
        self.is_recording = False
        self.is_stopping = False

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
        if status:
            # Non-blocking diagnostic for stream dropouts / buffer overflows
            pass
        flat_data = indata.flatten()
        with self.buffer_lock:
            self.ring_buffer.extend(flat_data)
            if self.is_recording:
                self.active_buffer.append(flat_data.copy())

    def start(self):
        """Called immediately on hotkey press."""
        if not self.stream or not self.stream.active:
            self._start_persistent_stream()

        with self.buffer_lock:
            self.is_stopping = False
            self.active_buffer = []
            # Snapshot pre-roll ambient room tone
            pre_roll_data = np.array(list(self.ring_buffer), dtype=np.int16)
            if len(pre_roll_data) > 0:
                self.active_buffer.append(pre_roll_data)
            self.is_recording = True

    def stop(self) -> bytes:
        """Called on hotkey release in a background worker thread."""
        with self.buffer_lock:
            if not self.is_recording or self.is_stopping:
                return b""
            self.is_stopping = True

        # Release tail: wait 200ms so final syllable decays naturally
        time.sleep(0.20)

        with self.buffer_lock:
            self.is_recording = False
            self.is_stopping = False
            if not self.active_buffer:
                return b""
            chunks = list(self.active_buffer)
            self.active_buffer = []

        full_audio = np.concatenate(chunks, axis=0)
        if len(full_audio) == 0:
            return b""

        # Gate on minimum duration (ignore accidental brief taps < 350ms total)
        duration = len(full_audio) / self.sample_rate
        if duration < 0.35:
            return b""

        # Gentle Peak Normalization to ~ -3 dBFS (22,000 max) without zero-padding
        # Convert to float32 first to safely prevent -32768 int16 absolute value overflow
        audio_float = full_audio.astype(np.float32)
        max_val = np.max(np.abs(audio_float))
        if 500 < max_val < 18000:
            scale = 22000.0 / max_val
            full_audio = np.clip(audio_float * scale, -32768, 32767).astype(np.int16)

        # Pack into pure in-memory WAV buffer (Standard library wave, zero disk I/O)
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)  # Mono for speech STT
            wf.setsampwidth(2)   # 16-bit PCM = 2 bytes per sample
            wf.setframerate(self.sample_rate)
            wf.writeframes(full_audio.tobytes())

        return wav_io.getvalue()

    def close(self):
        """Explicitly stops and releases microphone stream and audio buffers."""
        with self.buffer_lock:
            self.is_recording = False
            self.is_stopping = False
            self.active_buffer.clear()
            self.ring_buffer.clear()
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    @property
    def active(self) -> bool:
        return self.is_recording

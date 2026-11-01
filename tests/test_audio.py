import io
import wave
import numpy as np
import pytest
from core.audio_recorder import AudioRecorder
from config.settings import settings

def test_audio_recorder_zero_disk_leak(tmp_path, monkeypatch):
    """PV-001 Verification: Audio must strictly stay in RAM and never write to disk."""
    debug_wav = settings.base_dir / "last_dictation.wav"
    if debug_wav.exists():
        debug_wav.unlink()

    recorder = AudioRecorder()
    try:
        # Mock active buffer with 1 second of audio
        sample_rate = 16000
        t = np.linspace(0, 1.0, sample_rate, dtype=np.float32)
        sine_wave = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)

        recorder.is_recording = True
        recorder.active_buffer = [sine_wave]

        wav_bytes = recorder.stop()

        # Must return valid WAV in memory
        assert len(wav_bytes) > 0
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == sample_rate

        # Assert no audio files were dumped on disk
        assert not debug_wav.exists(), "Privacy violation: last_dictation.wav found on disk!"
    finally:
        recorder.close()

def test_audio_recorder_minimum_duration():
    """Very brief accidental key taps (<350ms) must be discarded."""
    recorder = AudioRecorder()
    try:
        recorder.is_recording = True
        # 100ms of audio
        recorder.active_buffer = [np.zeros(1600, dtype=np.int16)]
        wav_bytes = recorder.stop()
        assert wav_bytes == b"", "Brief taps under 350ms must return empty bytes."
    finally:
        recorder.close()

def test_audio_normalization_no_int16_overflow():
    """PV-022: Ensure -32768 does not overflow during peak normalization."""
    recorder = AudioRecorder()
    try:
        sample_rate = 16000
        # Include minimum negative 16-bit integer
        audio_with_extremes = np.array([-32768, 0, 32767] * 2000, dtype=np.int16)
        recorder.is_recording = True
        recorder.active_buffer = [audio_with_extremes]
        wav_bytes = recorder.stop()
        assert len(wav_bytes) > 0
    finally:
        recorder.close()

def test_audio_recorder_close():
    """PV-007: close() must cleanly reset buffers and terminate stream."""
    recorder = AudioRecorder()
    recorder.ring_buffer.extend([1, 2, 3])
    recorder.active_buffer.append(np.array([1, 2], dtype=np.int16))
    recorder.close()
    assert len(recorder.ring_buffer) == 0
    assert len(recorder.active_buffer) == 0
    assert recorder.stream is None

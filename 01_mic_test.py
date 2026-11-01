"""
=============================================================================
MILESTONE 1: Audio Capture Engine (01_mic_test.py)
=============================================================================
Aapka concept bilkul sahi tha:
1. Jab aap bolte hain, mic hawa ki vibration ko electrical signals banata hai.
2. sounddevice library Windows sound card se wo signal padhti hai.
3. NumPy library us signal ko ek "Array of Numbers" (digits ki list) bana deti hai.
4. scipy library unhi numbers ko standard .wav audio file mein save karti hai.
=============================================================================
"""

import sys
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np

# Windows console encoding fix for UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. AUDIO CONFIGURATION (Whisper AI ke mutabik settings)
# ---------------------------------------------------------------------------
# Whisper AI model ko 16,000 samples per second pasand hain.
# Matlab har 1 second ke andar mic 16,000 baar aawaz ka voltage check karega!
SAMPLE_RATE = 16000  

# Channels = 1 (Mono).
# Music ke liye Stereo (2 channels: Left + Right) chahiye hota hai.
# Speech recognition ke liye 1 channel (Mono) best aur lightweight hota hai.
CHANNELS = 1  

# Kitne second tak record karna hai:
DURATION = 5  

OUTPUT_FILENAME = "test_recording.wav"

def record_audio():
    print("=" * 60)
    print("🎙️  RECORDING START HONE WALI HAI...")
    print(f"👉 Agle {DURATION} seconds tak mic mein kuch boliye...")
    print("=" * 60)

    # -----------------------------------------------------------------------
    # 2. AUDIO CAPTURE INTO A NUMPY ARRAY
    # -----------------------------------------------------------------------
    # sd.rec() ka kaam hai mic ka nal (stream) kholna aur aawaz capture karna.
    # Total samples = 5 seconds * 16,000 samples/sec = 80,000 numbers!
    # dtype='int16': Har number -32,768 se +32,767 ke beech ka integer hoga.
    audio_data = sd.rec(
        int(DURATION * SAMPLE_RATE), 
        samplerate=SAMPLE_RATE, 
        channels=CHANNELS, 
        dtype='int16'
    )

    # sd.rec() background mein chalta hai. sd.wait() Python ko bolta hai:
    # "Jab tak 5 second ki recording poori na ho jaye, aage mat badho!"
    sd.wait()

    print("\n✅ RECORDING FINISHED!")
    print("=" * 60)

    # -----------------------------------------------------------------------
    # 3. LET'S INSPECT THE "ARRAY OF NUMBERS" (Aapki aawaz ke digits)
    # -----------------------------------------------------------------------
    print(f"📊 Total Numbers Captured: {len(audio_data)} samples")
    print(f"📊 Array Shape: {audio_data.shape} (80,000 rows, 1 channel)")
    print("\n👀 Dekhiye aapki aawaz ke shuruat ke 10 numbers kaise dikhte hain:")
    print(audio_data[:10].flatten())

    # Agar mic ne aawaz pakdi hai toh numbers 0 nahi honge!
    max_volume = np.max(np.abs(audio_data))
    print(f"\n🔊 Max Volume Peak Detected: {max_volume} (Scale: 0 to 32767)")
    if max_volume < 500:
        print("⚠️ Warning: Aawaz bahut dheemi aayi hai ya mic mute hai.")
    else:
        print("🎉 Great! Mic ne aawaz clearly pakdi hai.")

    # -----------------------------------------------------------------------
    # 4. SAVE TO WAV FILE
    # -----------------------------------------------------------------------
    # Ab hum is array of numbers ko ek real .wav file mein convert karte hain.
    write(OUTPUT_FILENAME, SAMPLE_RATE, audio_data)
    print(f"\n💾 Audio file successfully save ho gayi: {OUTPUT_FILENAME}")
    print("=" * 60)

if __name__ == "__main__":
    record_audio()

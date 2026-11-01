"""
=============================================================================
MILESTONE 4: Global Hotkey & Windows Auto-Paste (04_global_dictate.py)
=============================================================================
The Complete Wispr Flow Experience!

Pipeline:
1. User holds HOTKEY (F8 or Right-Alt) anywhere in Windows.
2. Microphone streams audio directly into RAM (io.BytesIO).
3. User releases HOTKEY.
4. Audio bytes sent to Groq Whisper STT (~250ms).
5. Raw text sent to Groq LLM Cleaner for English/Hinglish formatting (~180ms).
6. Polished text copied to Windows Clipboard.
7. Simulated 'Ctrl + V' automatically pastes into the active focused window!
=============================================================================
"""

import io
import os
import sys
import time
import winsound
from dotenv import load_dotenv
from groq import Groq
import numpy as np
from pynput import keyboard
import pyperclip
from scipy.io.wavfile import write
import sounddevice as sd

# Windows UTF-8 output fix
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------------------------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ ERROR: GROQ_API_KEY nahi mili!")
    sys.exit(1)

client = Groq(api_key=api_key)

SAMPLE_RATE = 16000
CHANNELS = 1

# System prompt for smart dictation (English + Hinglish)
SYSTEM_PROMPT = """You are an expert voice-to-text dictation formatter.
Your job is to transform raw spoken speech into clean, well-formatted, natural written text.

CRITICAL RULES:
1. REMOVE filler words, false starts, and stuttering (e.g., 'umm', 'uhh', 'like', 'you know', repeated words).
2. FIX punctuation, capitalization, and formatting automatically.
3. CONVERT spoken numbers or symbols into their natural written form (e.g., 'five pm' -> '5:00 PM', 'question mark' -> '?').
4. PRESERVE the speaker's original language, tone, and exact meaning.
   - If spoken in English, output English.
   - If spoken in Hindi or Hinglish, output natural Hinglish/Hindi.
5. NEVER add conversational replies like 'Sure! Here is the text:'.
   OUTPUT ONLY THE FINAL CLEANED TEXT AND NOTHING ELSE.
"""

# Global State Variables
is_recording = False
audio_buffer = []
stream = None
keyboard_controller = keyboard.Controller()

# Supported Hotkeys: F8 or Right-Alt
TRIGGER_KEYS = {keyboard.Key.f8, keyboard.Key.alt_r}

# ---------------------------------------------------------------------------
# 2. AUDIO STREAM CALLBACK (RAM Mein Record Karna)
# ---------------------------------------------------------------------------
def audio_callback(indata, frames, time_info, status):
    """sounddevice stream har frame par ye function call karta hai."""
    if is_recording:
        audio_buffer.append(indata.copy())

def start_recording():
    global is_recording, audio_buffer, stream
    if is_recording:
        return

    is_recording = True
    audio_buffer = []

    # Subtle audio feedback: Shuruat ka chhota beep
    try:
        winsound.Beep(1200, 80)
    except Exception:
        pass

    print("\n🎙️  [RECORDING STARTED] Speak your mind now...")

    # Non-blocking input stream (direct in RAM)
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
        callback=audio_callback
    )
    stream.start()

def stop_and_process():
    global is_recording, stream
    if not is_recording:
        return

    is_recording = False
    if stream:
        stream.stop()
        stream.close()
        stream = None

    # Subtle release beep
    try:
        winsound.Beep(800, 60)
    except Exception:
        pass

    print("🛑 [RECORDING STOPPED] Processing pipeline in RAM...")

    if not audio_buffer:
        print("⚠️ Koi aawaz record nahi hui.")
        return

    # Sare frames ko ek single NumPy array mein jodo
    full_audio = np.concatenate(audio_buffer, axis=0)

    # Agar aawaz 0.4 second se chhoti ho toh ignore karo (accidental key press)
    duration_sec = len(full_audio) / SAMPLE_RATE
    if duration_sec < 0.4:
        print("⚠️ Bahut chhota keypress tha (ignored).")
        return

    total_start = time.time()

    # 1. RAM ke andar hi WAV bytes banao (Zero disk lag)
    wav_io = io.BytesIO()
    write(wav_io, SAMPLE_RATE, full_audio)
    wav_io.seek(0)
    wav_bytes = wav_io.read()

    # 2. Fast STT: Groq Whisper API
    stt_start = time.time()
    try:
        transcription = client.audio.transcriptions.create(
            file=("dictation.wav", wav_bytes),
            model="whisper-large-v3-turbo",
            response_format="verbose_json"
        )
        raw_text = transcription.text.strip()
    except Exception as e:
        print(f"❌ Whisper Error: {e}")
        return

    stt_time = (time.time() - stt_start) * 1000

    if not raw_text:
        print("⚠️ Kuch sunai nahi diya (silence).")
        return

    print(f"📝 Raw Whisper: \"{raw_text}\" ({stt_time:.0f} ms)")

    # 3. AI Cleanup: Groq Qwen / LLM
    llm_start = time.time()
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.1,
            max_tokens=256
        )
        clean_text = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ LLM Error: {e}, falling back to raw text")
        clean_text = raw_text

    llm_time = (time.time() - llm_start) * 1000
    print(f"✨ AI Cleaned:  \"{clean_text}\" ({llm_time:.0f} ms)")

    # 4. OS Auto-Paste Injection (Clipboard + Virtual Ctrl+V)
    paste_start = time.time()
    
    # Text clipboard pe copy karo
    pyperclip.copy(clean_text)
    time.sleep(0.04)  # Windows clipboard sync ke liye 40ms wait

    # Focused window mein Ctrl + V fire karo
    with keyboard_controller.pressed(keyboard.Key.ctrl):
        keyboard_controller.press('v')
        keyboard_controller.release('v')

    total_time = (time.time() - total_start) * 1000

    # Success double beep
    try:
        winsound.Beep(1400, 50)
        winsound.Beep(1800, 70)
    except Exception:
        pass

    print(f"🚀 [AUTO-PASTED IN ACTIVE WINDOW] Total Latency: {total_time:.0f} ms!")
    print("=" * 60)

# ---------------------------------------------------------------------------
# 3. GLOBAL KEYBOARD HOOK
# ---------------------------------------------------------------------------
active_trigger = None

def on_press(key):
    global active_trigger
    if key in TRIGGER_KEYS and active_trigger is None:
        active_trigger = key
        start_recording()

def on_release(key):
    global active_trigger
    if key == active_trigger:
        active_trigger = None
        stop_and_process()

def main():
    print("=" * 60)
    print("🌟 WISPR FLOW - GLOBAL VOICE DICTATION RUNNING!")
    print("=" * 60)
    print("👉 HOW TO USE:")
    print("   1. Open ANY app (Notepad, Chrome, WhatsApp, VS Code).")
    print("   2. Place your cursor inside the text box.")
    print("   3. HOLD DOWN either [F8] or [Right Alt] key.")
    print("   4. Speak your message in English or Hinglish...")
    print("   5. RELEASE the key.")
    print("   -> Clean text will auto-paste right into your cursor!")
    print("=" * 60)
    print("Press Ctrl+C in this terminal anytime to exit.\n")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()

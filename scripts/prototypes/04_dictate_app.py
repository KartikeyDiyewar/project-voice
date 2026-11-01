"""
=============================================================================
WISPR FLOW DESKTOP (04_dictate_app.py)
=============================================================================
- Clean Always-On-Top Dictation Window.
- Global Hotkeys: Hold [F8] or [Right Ctrl] or [Right Alt].
- OR click the big '🎙️ START RECORDING' button!
- Real-time Visual Status (Recording, Transcribing, Cleaning, Pasting).
- Live Transcript Box showing both Raw Spoken & Polished Text!
- Automatic Windows Keystroke Injection (Ctrl + V).
=============================================================================
"""

import io
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import winsound
from dotenv import load_dotenv
from groq import Groq
import numpy as np
from pynput import keyboard
import pyperclip
from scipy.io.wavfile import write
import sounddevice as sd

# Windows console encoding fix
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ ERROR: GROQ_API_KEY not found in .env!")
    sys.exit(1)

client = Groq(api_key=api_key)

SAMPLE_RATE = 16000
CHANNELS = 1

# Whisper prompt primer (conditions Whisper to output Roman Hinglish instead of English translation)
WHISPER_PROMPT_PRIMER = "Haan bhai, kal subah 10 baje milte hain, meeting karenge aur project discuss karenge. Sab theek hai na?"

SYSTEM_PROMPT = """You are an expert voice dictation formatter for English and Hinglish (Hindi written in Roman/English alphabet).

TASK:
Clean up filler words, remove repetitions, and apply proper punctuation to the spoken transcript.

STRICT RULES:
1. NEVER TRANSLATE HINDI OR HINGLISH TO ENGLISH!
   - If spoken in Hindi/Hinglish, output MUST REMAIN in HINGLISH (Hindi words spelled with English letters).
   - DO NOT translate meaning into English!
   - Example: 'batao kya sun rahe ho' -> 'Batao kya sun rahe ho.' (NEVER 'Tell me what you are hearing')
   - Example: 'kal meeting karte hain' -> 'Kal meeting karte hain.' (NEVER 'Let us meet tomorrow')
   - Example: 'developer, tester aur control card' -> 'Developer, tester aur control card.'
2. NO DEVANAGARI SCRIPT:
   - If input has Devanagari Hindi (e.g. बताओ क्या सुन रहे हो), convert it phonetically into Roman Hinglish ('Batao kya sun rahe ho').
   - NEVER keep Devanagari characters (क, ख, ग).
3. IF ENGLISH:
   - If the speech was spoken in English, output clean English.
4. CLEANUP:
   - Remove filler words ('umm', 'ahh', 'matlab', repeated stutter words).
   - Add proper capitalization, commas, and question marks.
5. OUTPUT ONLY THE FINAL CLEANED TEXT. Do not add any conversational remarks.
"""

# Global State
is_recording = False
audio_buffer = []
stream = None
keyboard_controller = keyboard.Controller()
TRIGGER_KEYS = {keyboard.Key.f8, keyboard.Key.ctrl_r, keyboard.Key.alt_r}

# ---------------------------------------------------------------------------
# 2. AUDIO STREAM
# ---------------------------------------------------------------------------
def audio_callback(indata, frames, time_info, status):
    if is_recording:
        audio_buffer.append(indata.copy())

def start_recording():
    global is_recording, audio_buffer, stream
    if is_recording:
        return

    is_recording = True
    audio_buffer = []

    update_ui_status("🔴 RECORDING... Speak now!", "#dc2626", "Stop Recording")

    try:
        winsound.Beep(1200, 80)
    except Exception:
        pass

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            callback=audio_callback
        )
        stream.start()
    except Exception as e:
        print(f"Mic error: {e}")
        update_ui_status(f"⚠️ Mic Error: {e}", "#dc2626", "Start Recording")

def stop_and_process():
    global is_recording, stream
    if not is_recording:
        return

    is_recording = False
    if stream:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        stream = None

    try:
        winsound.Beep(800, 60)
    except Exception:
        pass

    update_ui_status("⚡ Processing with AI...", "#d97706", "Processing...")
    threading.Thread(target=process_pipeline, daemon=True).start()

def process_pipeline():
    if not audio_buffer:
        update_ui_status("🎙️ Ready (Hold F8 / Right-Ctrl)", "#0f172a", "🎙️ Start Recording")
        return

    full_audio = np.concatenate(audio_buffer, axis=0)
    duration = len(full_audio) / SAMPLE_RATE

    if duration < 0.4:
        update_ui_status("⚠️ Too short (ignored)", "#64748b", "🎙️ Start Recording")
        time.sleep(1)
        update_ui_status("🎙️ Ready (Hold F8 / Right-Ctrl)", "#0f172a", "🎙️ Start Recording")
        return

    # In-memory WAV buffer
    wav_io = io.BytesIO()
    write(wav_io, SAMPLE_RATE, full_audio)
    wav_io.seek(0)
    wav_bytes = wav_io.read()

    # 1. Groq Whisper STT (Primed with Hinglish conversational vocabulary)
    try:
        transcription = client.audio.transcriptions.create(
            file=("speech.wav", wav_bytes),
            model="whisper-large-v3-turbo",
            prompt=WHISPER_PROMPT_PRIMER,
            response_format="verbose_json"
        )
        raw_text = transcription.text.strip()
    except Exception as e:
        update_ui_status(f"❌ Whisper Error: {e}", "#dc2626", "🎙️ Start Recording")
        return

    if not raw_text:
        update_ui_status("⚠️ No speech detected", "#64748b", "🎙️ Start Recording")
        time.sleep(1)
        update_ui_status("🎙️ Ready (Hold F8 / Right-Ctrl)", "#0f172a", "🎙️ Start Recording")
        return

    update_transcript_box(f"[Raw Spoken]:\n{raw_text}\n")

    # 2. Groq Qwen Cleaner (English + Hinglish)
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
        clean_text = raw_text

    update_transcript_box(f"[Raw Spoken]:\n{raw_text}\n\n[✨ AI Cleaned]:\n{clean_text}")

    # 3. Windows Clipboard + Virtual Ctrl+V Auto-Paste
    pyperclip.copy(clean_text)
    time.sleep(0.05)

    with keyboard_controller.pressed(keyboard.Key.ctrl):
        keyboard_controller.press('v')
        keyboard_controller.release('v')

    try:
        winsound.Beep(1400, 50)
        winsound.Beep(1800, 70)
    except Exception:
        pass

    update_ui_status("✅ Pasted into Active Window!", "#16a34a", "🎙️ Start Recording")
    time.sleep(2)
    update_ui_status("🎙️ Ready (Hold F8 / Right-Ctrl)", "#0f172a", "🎙️ Start Recording")

# ---------------------------------------------------------------------------
# 3. GUI WINDOW (Tkinter)
# ---------------------------------------------------------------------------
root = tk.Tk()
root.title("Wispr Flow - Voice Dictation")
root.geometry("460x320+450+150")
root.attributes("-topmost", True)  # Always stay visible on top
root.configure(bg="#f8fafc")

# Header Frame
header = tk.Frame(root, bg="#1e1b4b", padx=16, pady=12)
header.pack(fill="x")

title_label = tk.Label(
    header,
    text="🎙️ Wispr Flow (BYOK Voice Engine)",
    font=("Segoe UI", 13, "bold"),
    fg="white",
    bg="#1e1b4b"
)
title_label.pack(side="left")

# Status Banner
status_label = tk.Label(
    root,
    text="🎙️ Ready (Hold F8 / Right-Ctrl or Click Below)",
    font=("Segoe UI", 11, "bold"),
    fg="#0f172a",
    bg="#e2e8f0",
    pady=10
)
status_label.pack(fill="x", padx=14, pady=10)

# Big Mic Action Button
def on_btn_click():
    if not is_recording:
        start_recording()
    else:
        stop_and_process()

record_btn = tk.Button(
    root,
    text="🎙️ START RECORDING",
    font=("Segoe UI", 12, "bold"),
    bg="#2563eb",
    fg="white",
    activebackground="#1d4ed8",
    activeforeground="white",
    relief="flat",
    pady=8,
    cursor="hand2",
    command=on_btn_click
)
record_btn.pack(fill="x", padx=14, pady=4)

# Preview Text Box
box_label = tk.Label(
    root,
    text="Live Transcript Preview:",
    font=("Segoe UI", 9, "bold"),
    fg="#64748b",
    bg="#f8fafc"
)
box_label.pack(anchor="w", padx=16, pady=(10, 2))

preview_box = tk.Text(
    root,
    height=5,
    font=("Segoe UI", 9),
    bg="white",
    fg="#1e293b",
    relief="solid",
    borderwidth=1,
    padx=8,
    pady=6
)
preview_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
preview_box.insert("1.0", "Bolne par transcript yahan aur aapke Notepad mein dono jagah aayega...")

def update_ui_status(text, color, btn_text):
    def _apply():
        status_label.config(text=text, fg=color)
        record_btn.config(
            text=btn_text,
            bg="#dc2626" if "RECORDING" in text else "#2563eb"
        )
    root.after(0, _apply)

def update_transcript_box(text):
    def _apply():
        preview_box.delete("1.0", tk.END)
        preview_box.insert("1.0", text)
    root.after(0, _apply)

# ---------------------------------------------------------------------------
# 4. KEYBOARD LISTENER
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

threading.Thread(
    target=lambda: keyboard.Listener(on_press=on_press, on_release=on_release).run(),
    daemon=True
).start()

print("🌟 Wispr Flow GUI Ready!")
root.mainloop()

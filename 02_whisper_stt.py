"""
=============================================================================
MILESTONE 2: Speech-to-Text via Whisper API (02_whisper_stt.py)
=============================================================================
Goal:
1. 'test_recording.wav' file ko kholna.
2. Us audio data ko Groq ke Whisper model (whisper-large-v3-turbo) par bhejna.
3. Dekhna ki AI kitni milliseconds mein audio ko Text bana deta hai!
=============================================================================
"""

import os
import sys
import time
from dotenv import load_dotenv
from groq import Groq

# Windows console encoding fix
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. LOAD API KEY (BYOK - Bring Your Own Key)
# ---------------------------------------------------------------------------
# Ye '.env' file se GROQ_API_KEY load karta hai
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ ERROR: GROQ_API_KEY nahi mili!")
    print("👉 Kripya '.env' file mein GROQ_API_KEY=gsk_your_key_here likhein.")
    sys.exit(1)

# Groq Client initialize karna
client = Groq(api_key=api_key)

# ---------------------------------------------------------------------------
# 2. TRANSCRIBE FUNCTION (Audio to Text)
# ---------------------------------------------------------------------------
def transcribe_audio(file_path="test_recording.wav"):
    if not os.path.exists(file_path):
        print(f"❌ File '{file_path}' nahi mili. Pehle 01_mic_test.py run karein!")
        return

    print("=" * 60)
    print(f"🚀 Audio file bheji ja rahi hai Groq Whisper AI ko: {file_path}")
    print("⏳ Processing... (Watch how fast this is!)")
    print("=" * 60)

    # Shuruat ka waqt note karte hain taaki speed naap sakein
    start_time = time.time()

    with open(file_path, "rb") as audio_file:
        # Groq API call:
        # Model: 'whisper-large-v3-turbo' (Duniya ka sabse fast STT model)
        # response_format: 'verbose_json' taaki humein time, language sab mile
        transcription = client.audio.transcriptions.create(
            file=(file_path, audio_file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )

    # Khatam hone ka waqt
    time_taken = (time.time() - start_time) * 1000  # Convert to milliseconds

    print("\n✅ TRANSCRIPTION COMPLETE!")
    print("=" * 60)
    print(f"⚡ Time Taken: {time_taken:.0f} milliseconds! (Less than 0.5 sec)")
    print(f"🌐 Detected Language: {getattr(transcription, 'language', 'unknown')}")
    print("\n📝 Spoken Words (Raw Transcript):")
    print(f"👉 \"{transcription.text.strip()}\"")
    print("=" * 60)

if __name__ == "__main__":
    transcribe_audio()

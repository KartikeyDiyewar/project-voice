"""
=============================================================================
MILESTONE 3: The AI Cleanup & Formatting Layer (03_llm_cleaner.py)
=============================================================================
Goal:
Whisper AI se jo raw text milta hai, usme "umm", "like", repeated words,
aur missing punctuation hoti hai.

Hum Groq ke Llama-3.3-70b model ko use karke ek 'Smart Dictation Prompt'
denge jo text ko ekdum professional, clean aur crisp bana dega!
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

# 1. Load Groq API Key
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ ERROR: GROQ_API_KEY nahi mili!")
    sys.exit(1)

client = Groq(api_key=api_key)

# ---------------------------------------------------------------------------
# 2. THE SECRET PROMPT (Wispr Flow's System Instruction)
# ---------------------------------------------------------------------------
# System prompt LLM ko batata hai ki uska role kya hai aur usko kya rules follow karne hain:
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

def clean_transcript(raw_text: str) -> str:
    """Raw transcript ko LLM ke paas bhej kar clean text wapas leta hai."""
    
    start_time = time.time()

    # Groq Chat Completion Call
    # Model: 'qwen/qwen3.8-27b' (Ultra-fast LLM on Groq)
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text}
        ],
        temperature=0.1,  # Focused output, minimal hallucination
        max_tokens=256
    )

    time_taken = (time.time() - start_time) * 1000  # Milliseconds
    cleaned_text = response.choices[0].message.content.strip()

    return cleaned_text, time_taken

# ---------------------------------------------------------------------------
# 3. TEST CASES (Let's see the transformation!)
# ---------------------------------------------------------------------------
def run_tests():
    print("=" * 70)
    print("🧠 STEP 3: TESTING AI POST-PROCESSING & CLEANUP")
    print("=" * 70)

    # Test Case 1: Jo humne Step 2 mein record kiya tha!
    # "Hello, hello, hello, 123, 123."
    test_1 = "Hello, hello, hello, 123, 123."

    # Test Case 2: Realistic messy dictation with fillers & spoken commands
    test_2 = "umm hey bro like can we like postpone the meeting to tomorrow 5 pm question mark that would be great"

    # Test Case 3: Hinglish messy speech
    test_3 = "matlab haan mai keh raha tha ki kal kal subah 10 baje milte hai office me theek hai"

    samples = [
        ("Aapka Step 2 Recording", test_1),
        ("English with Fillers & 'question mark'", test_2),
        ("Hinglish Casual Speech", test_3)
    ]

    for label, raw in samples:
        print(f"\n--- [{label}] ---")
        print(f"🎙️  RAW WHISPER INPUT : \"{raw}\"")
        
        cleaned, speed = clean_transcript(raw)
        
        print(f"✨ CLEANED AI OUTPUT : \"{cleaned}\"")
        print(f"⚡ Time Taken        : {speed:.0f} ms")

    print("\n" + "=" * 70)
    print("🎉 Notice how clean, punctuated, and natural the output is!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()

"""
Speech-to-Text Module
Pluggable provider for transcribing audio via Groq Whisper.
Enforces Roman Hinglish output and eliminates hallucinations using:
1. language="en" (forces Latin alphabet, prevents Devanagari corruption of English loanwords)
2. Boring Roman-Hinglish prompt with common phonetics (teaches decoder Latin script + Hindi grammar)
3. temperature=0.0
4. verbose_json segment filtering (filters out no-speech / high-compression hallucination segments)
5. Explicit network timeout (10s) to prevent thread hangs
"""

import time
from groq import Groq
from config.settings import settings

class GroqSTTProvider:
    def __init__(self):
        self.client = None
        self.model = settings.stt_model
        # Mundane, mixed-script, complete sentence prompt with common phonetic anchors (pata, zyada, saath mein)
        self.prompt = "Okay toh, mujhe pata hai kal meeting hai, bohot zyada kaam baki hai. Main report bhej dunga, phir saath mein review karenge."
        self.reload_client()

    def reload_client(self):
        """Initializes or reloads the Groq client with the latest API key."""
        if settings.groq_api_key:
            try:
                self.client = Groq(api_key=settings.groq_api_key, timeout=10.0)
            except Exception as e:
                print(f"⚠️ STT Groq client init failed: {e}")
                self.client = None
        else:
            self.client = None

    def transcribe(self, audio_bytes: bytes) -> tuple[str, float]:
        """
        Sends audio bytes to Groq Whisper and returns (raw_text, latency_ms).
        Raises exceptions on network/API failure so the caller can display UI error feedback.
        """
        if not audio_bytes:
            return "", 0.0

        if not self.client:
            self.reload_client()
            if not self.client:
                raise ValueError("Groq API Key is not set. Please configure your key in Project Voice Dashboard.")

        start_time = time.time()

        response = self.client.audio.transcriptions.create(
            file=("speech.wav", audio_bytes),
            model=self.model,
            language="en",
            prompt=self.prompt,
            temperature=0.0,
            response_format="verbose_json"
        )

        latency = (time.time() - start_time) * 1000

        # Filter hallucinated segments
        segments = getattr(response, "segments", None)
        if segments:
            segs = []
            for s in segments:
                no_speech = s.get("no_speech_prob", 0.0) if isinstance(s, dict) else getattr(s, "no_speech_prob", 0.0)
                avg_logprob = s.get("avg_logprob", 0.0) if isinstance(s, dict) else getattr(s, "avg_logprob", 0.0)
                compression = s.get("compression_ratio", 1.0) if isinstance(s, dict) else getattr(s, "compression_ratio", 1.0)
                text = s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")

                # Discard silent hallucination or repetitive looped phrases
                if (no_speech > 0.6 and avg_logprob < -1.0) or compression >= 2.4:
                    continue
                if text:
                    segs.append(text.strip())

            raw_text = " ".join(segs).strip()
        else:
            raw_text = response.text.strip() if hasattr(response, "text") and response.text else ""

        return raw_text, latency

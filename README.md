# 🎙️ Project Voice

> **Sub-Second (<800ms) AI Voice Dictation Engine for Windows (Bring-Your-Own-Key)**  
> Speak naturally in **Roman Hinglish** or **English** anywhere on your PC — auto-cleaned and pasted instantly into your active window.

---

## ✨ Features

- **⚡ Sub-Second Latency (<800ms):** In-memory RAM audio capture paired with Groq LPUs (`whisper-large-v3-turbo` + `qwen/qwen3.8-27b`).
- **🇮🇳 Native Roman Hinglish & English:** Intelligent phonetic correction eliminates Whisper homophone confusions (`ab sab` vs `aap sab`, `chalne lag gaya`, `sandeh`, `avishwas`) with zero unwanted Devanagari script or translation.
- **🖥️ Windows 11 Fluent Dashboard:**
  - Modern obsidian dark-theme control panel with native Per-Monitor DPI scaling and DWM dark titlebar.
  - **Live Microphone Sensitivity Monitor:** Real-time audio volume visualizer with 3-second diagnostic test.
  - **Interactive Dictation Sandbox ("Try It Live"):** Test speech-to-text directly in the dashboard with live millisecond latency telemetry.
- **🚀 Single-Instance Win32 IPC:** Double-clicking the desktop shortcut while the app is running smoothly restores and focuses the Dashboard window (zero duplicate instances).
- **🔕 Silent Background Tray & Boot Auto-Start:** Minimizes cleanly to the taskbar system tray; boots silently on Windows startup via `--tray`.
- **📖 Custom Vocabulary Hook:** Prioritizes project-specific jargon, brand names, and client names (`dictionary.json`).
- **🔑 100% BYOK & Free Forever:** Uses Groq Cloud's free tier (14,400 daily requests). Completely private.

---

## 🏗️ Architecture

```text
Project Voice/
├── config/
│   ├── __init__.py
│   └── settings.py          # Centralized configuration & settings.json parser
│
├── core/
│   ├── __init__.py
│   ├── audio_recorder.py    # Thread-safe in-memory RAM audio capture (16kHz Mono)
│   ├── speech_to_text.py    # Groq Whisper STT (Latin Hinglish phonetic priming)
│   ├── llm_cleaner.py       # Context-aware AI copy-editor (Phonetic repair & formatting)
│   └── injector.py          # Non-destructive clipboard virtual Ctrl+V injection
│
├── docs/                    # Architecture diagrams & design specs
│   └── architecture/
├── scripts/                 # Utility scripts & research prototypes
│   └── prototypes/
├── ui/
│   ├── __init__.py
│   ├── dashboard.py         # Modern sidebar control center & live diagnostics
│   ├── floating_indicator.py# Wispr Flow style glowing pill indicator
│   └── tray.py              # Windows Taskbar System Tray icon & context menu
│
├── utils/
│   ├── __init__.py
│   ├── hotkey_listener.py   # Global multi-key hook with hardware GetAsyncKeyState check
│   └── sound_feedback.py    # Subtle audio cues (start chime, stop chime, paste chime)
│
├── app.py                   # Master Application Controller & Win32 IPC
├── build_exe.bat            # 1-Click PyInstaller compilation script
├── run_app.bat              # Quick developer launcher
├── settings.json            # User preferences & hotkey configuration
├── dictionary.json          # Custom words & jargon list
├── requirements.txt         # Production dependencies
└── .env.example             # Environment template
```

---

## 🚀 Quickstart

### 1. Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.10+
- Free Groq API Key from [console.groq.com/keys](https://console.groq.com/keys)

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/KartikeyDiyewar/project-voice.git
cd project-voice

# Install dependencies
pip install -r requirements.txt

# Configure API Key
cp .env.example .env
# Edit .env and paste your GROQ_API_KEY=gsk_...
```

### 3. Run
```bash
python app.py
```

### 4. Build Standalone EXE
To create a standalone `.exe` that runs without Python installed:
```bash
.\build_exe.bat
```
The output binary will be created in `dist/Project Voice/Project Voice.exe`.

---

## ⌨️ How to Use

1. Click into any application (Notepad, Chrome, WhatsApp, VS Code, Slack, Word).
2. **Press and hold `Ctrl + Space`** (or your custom configured hotkey).
3. A sleek floating pill appears at the bottom-center of your screen: **`● Listening...`**.
4. Speak naturally in English, Hindi, or Hinglish.
5. **Release `Ctrl + Space`**: Project Voice transcribes, copy-edits, and auto-pastes clean text in <800ms!

---

## 🔒 Privacy & Security

- Audio is never saved to disk — recorded entirely in RAM buffers and transmitted via TLS directly to Groq LPUs.
- No remote telemetry or analytics.
- API keys are stored locally on your machine in `.env` and never tracked by Git.

---

## 📄 License
MIT License. Free and open-source.

import json
import os

# Generate tldraw file (.tldr)
tldraw_data = {
    "tldrawFileFormatVersion": 1,
    "schema": {
        "schemaVersion": 2,
        "sequences": {
            "com.tldraw.store": 4,
            "com.tldraw.asset": 1,
            "com.tldraw.camera": 1,
            "com.tldraw.document": 2,
            "com.tldraw.instance": 25,
            "com.tldraw.instance_page_state": 5,
            "com.tldraw.page": 1,
            "com.tldraw.shape": 4
        }
    },
    "records": [
        {"id": "document:document", "typeName": "document", "gridSize": 10, "name": ""},
        {"id": "page:page", "typeName": "page", "name": "Wispr Flow Architecture", "index": "a1"},
        {"id": "camera:page:page", "typeName": "camera", "x": 100, "y": 100, "z": 0.85, "meta": {}},
        
        # Title Card
        {
            "id": "shape:title",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a1",
            "type": "geo",
            "x": 80,
            "y": 60,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 960,
                "h": 120,
                "geo": "rectangle",
                "color": "violet",
                "labelColor": "black",
                "fill": "semi",
                "dash": "solid",
                "size": "l",
                "font": "draw",
                "align": "middle",
                "verticalAlign": "middle",
                "growY": 0,
                "url": "",
                "text": "PROJECT VOICE: WISPR FLOW ARCHITECTURE & ROADMAP\n(BYOK Voice Dictation App for Windows & Mobile)"
            }
        },

        # Step 1: Global Hotkey
        {
            "id": "shape:step1",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a2",
            "type": "geo",
            "x": 80,
            "y": 240,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 280,
                "h": 220,
                "geo": "rectangle",
                "color": "blue",
                "labelColor": "black",
                "fill": "semi",
                "dash": "draw",
                "size": "s",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "url": "",
                "text": "[ 1. GLOBAL HOTKEY ]\n\nTrigger: Press & Hold (e.g. CapsLock / Alt+Space)\n\n• Background listener (pynput / Win32)\n• Works across ANY app (Chrome, VSCode, Slack)\n• On Press -> Start Audio Stream\n• On Release -> Send to AI"
            }
        },

        # Arrow 1 -> 2
        {
            "id": "shape:arrow1",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a3",
            "type": "arrow",
            "x": 360,
            "y": 350,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "dash": "draw",
                "size": "m",
                "fill": "none",
                "color": "black",
                "labelColor": "black",
                "bend": 0,
                "start": {"x": 0, "y": 0},
                "end": {"x": 70, "y": 0},
                "arrowheadStart": "none",
                "arrowheadEnd": "arrow",
                "text": "Audio Data",
                "labelPosition": 0.5,
                "font": "draw"
            }
        },

        # Step 2: In-Memory Audio Buffer
        {
            "id": "shape:step2",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a4",
            "type": "geo",
            "x": 430,
            "y": 240,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 280,
                "h": 220,
                "geo": "rectangle",
                "color": "light-blue",
                "labelColor": "black",
                "fill": "semi",
                "dash": "draw",
                "size": "s",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "url": "",
                "text": "[ 2. AUDIO BUFFER ]\n\nMic Streaming: 16kHz Mono\n\n• Captured via sounddevice\n• In-Memory RAM buffer (io.BytesIO)\n• Zero disk lag (no slow file writes)\n• Converted instantly to WAV"
            }
        },

        # Arrow 2 -> 3
        {
            "id": "shape:arrow2",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a5",
            "type": "arrow",
            "x": 710,
            "y": 350,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "dash": "draw",
                "size": "m",
                "fill": "none",
                "color": "black",
                "labelColor": "black",
                "bend": 0,
                "start": {"x": 0, "y": 0},
                "end": {"x": 70, "y": 0},
                "arrowheadStart": "none",
                "arrowheadEnd": "arrow",
                "text": "WAV Bytes",
                "labelPosition": 0.5,
                "font": "draw"
            }
        },

        # Step 3: Fast STT (Whisper API)
        {
            "id": "shape:step3",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a6",
            "type": "geo",
            "x": 780,
            "y": 240,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 300,
                "h": 220,
                "geo": "rectangle",
                "color": "yellow",
                "labelColor": "black",
                "fill": "semi",
                "dash": "draw",
                "size": "s",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "url": "",
                "text": "[ 3. FAST SPEECH-TO-TEXT ]\n\nModel: Whisper-large-v3-turbo\n\n• Provider: Groq (takes ~200ms!)\n• Or OpenAI Whisper API\n• User uses BYOK (own API key)\n• Returns raw spoken transcript"
            }
        },

        # Arrow 3 -> 4
        {
            "id": "shape:arrow3",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a7",
            "type": "arrow",
            "x": 930,
            "y": 460,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "dash": "draw",
                "size": "m",
                "fill": "none",
                "color": "black",
                "labelColor": "black",
                "bend": 0,
                "start": {"x": 0, "y": 0},
                "end": {"x": 0, "y": 70},
                "arrowheadStart": "none",
                "arrowheadEnd": "arrow",
                "text": "Raw Text",
                "labelPosition": 0.5,
                "font": "draw"
            }
        },

        # Step 4: AI Post-Processing LLM
        {
            "id": "shape:step4",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a8",
            "type": "geo",
            "x": 780,
            "y": 530,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 300,
                "h": 230,
                "geo": "rectangle",
                "color": "orange",
                "labelColor": "black",
                "fill": "semi",
                "dash": "draw",
                "size": "s",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "url": "",
                "text": "[ 4. AI FORMAT & CLEANUP ]\n\nWispr Flow's Secret Sauce!\n\n• LLM: Llama 3.3 70B (Groq) or GPT-4o-mini\n• Removes 'umm', 'aah', repetitions\n• Fixes grammar, punctuation, casing\n• Detects spoken commands (e.g. 'new line')\n• Output: Clean, polished writing"
            }
        },

        # Arrow 4 -> 5
        {
            "id": "shape:arrow4",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "a9",
            "type": "arrow",
            "x": 780,
            "y": 645,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "dash": "draw",
                "size": "m",
                "fill": "none",
                "color": "black",
                "labelColor": "black",
                "bend": 0,
                "start": {"x": 0, "y": 0},
                "end": {"x": -70, "y": 0},
                "arrowheadStart": "none",
                "arrowheadEnd": "arrow",
                "text": "Polished Text",
                "labelPosition": 0.5,
                "font": "draw"
            }
        },

        # Step 5: OS Injection (Auto Paste)
        {
            "id": "shape:step5",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "aa",
            "type": "geo",
            "x": 430,
            "y": 530,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 280,
                "h": 230,
                "geo": "rectangle",
                "color": "green",
                "labelColor": "black",
                "fill": "semi",
                "dash": "draw",
                "size": "s",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "url": "",
                "text": "[ 5. AUTO-PASTE INJECTION ]\n\nWindows Level:\n\n• Copies clean text to Clipboard\n• Simulates Ctrl + V keystroke\n• Target: Currently focused window\n• Text appears instantly inside Slack, Word, Browser, etc.!"
            }
        },

        # Note: BYOK Advantage
        {
            "id": "shape:note_byok",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "ab",
            "type": "note",
            "x": 80,
            "y": 530,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "color": "yellow",
                "size": "s",
                "text": "BYOK KEY ADVANTAGE:\n\n1. 100% Privacy - Audio goes direct to Groq/OpenAI, no middleman server.\n2. Ultra-Cheap / Free - Groq free tier gives 14,400 calls/day.\n3. Latency is <500ms total!",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "fontSizeAdjustment": 0,
                "url": ""
            }
        },

        # Sticky Note: Mobile Difference
        {
            "id": "shape:note_mobile",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "ac",
            "type": "note",
            "x": 80,
            "y": 790,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "color": "light-violet",
                "size": "s",
                "text": "HOW MOBILE DIFFERS:\n\nOn Windows: Global hotkey + virtual Ctrl+V.\nOn Mobile: Android/iOS sandbox blocks background keystroke injection.\nSo mobile Wispr Flow is built as a Custom Keyboard Extension (like Gboard) with a mic button!",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "fontSizeAdjustment": 0,
                "url": ""
            }
        },

        # Step by Step Roadmap Box
        {
            "id": "shape:roadmap",
            "typeName": "shape",
            "parentId": "page:page",
            "index": "ad",
            "type": "geo",
            "x": 430,
            "y": 790,
            "rotation": 0,
            "isLocked": False,
            "opacity": 1,
            "meta": {},
            "props": {
                "w": 650,
                "h": 200,
                "geo": "rectangle",
                "color": "grey",
                "labelColor": "black",
                "fill": "semi",
                "dash": "solid",
                "size": "s",
                "font": "draw",
                "align": "start",
                "verticalAlign": "start",
                "growY": 0,
                "url": "",
                "text": "OUR STEP-BY-STEP LEARNING ROADMAP:\n\nMilestone 1: 01_mic_test.py (Record 5 sec, understand audio buffers)\nMilestone 2: 02_whisper_stt.py (Send to Groq/OpenAI, inspect raw JSON)\nMilestone 3: 03_llm_cleaner.py (Prompt engineering to clean up stuttering)\nMilestone 4: 04_global_dictate.py (Global hotkey + Ctrl+V auto-typing)\nMilestone 5: 05_floating_ui.py (Minimal floating indicator pill + settings)"
            }
        }
    ]
}

# Write .tldr file
with open("whisper_flow_architecture.tldr", "w", encoding="utf-8") as f:
    json.dump(tldraw_data, f, indent=2)

print("Created whisper_flow_architecture.tldr successfully!")

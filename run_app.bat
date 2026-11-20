@echo off
title Project Voice - Desktop Engine
cd /d "%~dp0"
echo ========================================================
echo Starting Project Voice...
echo Default Hotkey: [Ctrl + Space]
echo ========================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause

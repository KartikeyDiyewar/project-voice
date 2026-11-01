@echo off
title Build Project Voice EXE
cd /d "%~dp0"
echo ========================================================
echo Building Standalone Windows Executable for Project Voice...
echo ========================================================

:: Close any running instance to prevent file locks
taskkill /F /IM "Project Voice.exe" >nul 2>nul
timeout /t 1 /nobreak >nul

python -m PyInstaller ^
    --noconsole ^
    --name="Project Voice" ^
    --icon="assets/icon.ico" ^
    --add-data="assets/icon.ico;assets" ^
    --add-data="settings.json;." ^
    --add-data="dictionary.json;." ^
    --collect-all="customtkinter" ^
    --collect-all="darkdetect" ^
    --hidden-import="pystray._win32" ^
    --hidden-import="pynput.keyboard._win32" ^
    --onedir ^
    --clean ^
    --noconfirm ^
    app.py

copy /Y .env.example "dist\Project Voice\.env.example" >nul 2>nul
copy /Y settings.json "dist\Project Voice\settings.json" >nul 2>nul
copy /Y dictionary.json "dist\Project Voice\dictionary.json" >nul 2>nul
xcopy /E /I /Y "assets" "dist\Project Voice\assets" >nul 2>nul

echo.
echo ========================================================
echo SUCCESS: Project Voice.exe is ready!
echo Location: %~dp0dist\Project Voice\Project Voice.exe
echo ========================================================

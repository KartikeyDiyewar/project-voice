"""
Project Voice - Desktop Application Installer & Autostart Manager
Configures the app to run as a permanent, lightweight background utility on Windows:
1. Cleans up any deprecated shortcuts
2. Creates Desktop Shortcuts ('Project Voice' and 'Start_Project_Voice.bat')
3. Adds to Windows Startup (auto-starts on laptop boot / login)
4. Configures execution via pythonw.exe (completely silent, zero black terminal window)
5. Creates 1-click Stop Controller
"""

import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw

# Windows console encoding fix
if sys.stdout is not None and getattr(sys.stdout, "encoding", None) != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PYTHONW_PATH = Path(sys.executable).parent / "pythonw.exe"
if not PYTHONW_PATH.exists():
    PYTHONW_PATH = Path(sys.executable)

PYTHON_EXE_PATH = Path(sys.executable)
APP_PY_PATH = BASE_DIR / "app.py"
ASSETS_DIR = BASE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"

def generate_icon():
    """Generates high-resolution multi-size Windows icon."""
    ASSETS_DIR.mkdir(exist_ok=True)
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Gradient-style blue mic
    draw.rounded_rectangle([44, 18, 84, 76], radius=20, fill="#2563eb")
    draw.arc([30, 42, 98, 92], start=0, end=180, fill="#3b82f6", width=8)
    draw.line([64, 92, 64, 110], fill="#3b82f6", width=8)
    draw.line([42, 110, 86, 110], fill="#3b82f6", width=8)

    img.save(ICON_PATH, format="ICO", sizes=[(128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"✔ Generated App Icon at: {ICON_PATH}")

def create_windows_shortcut(target_path: Path) -> bool:
    """Uses Windows WScript.Shell COM object to create a native .lnk shortcut."""
    ps_command = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{str(target_path)}')
    $Shortcut.TargetPath = '{str(PYTHONW_PATH)}'
    $Shortcut.Arguments = '"{str(APP_PY_PATH)}"'
    $Shortcut.WorkingDirectory = '{str(BASE_DIR)}'
    $Shortcut.IconLocation = '{str(ICON_PATH)},0'
    $Shortcut.Description = 'Project Voice - BYOK Voice Dictation Engine'
    $Shortcut.WindowStyle = 7
    $Shortcut.Save()
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True)
    return target_path.exists()

def install():
    print("=" * 65)
    print("🚀 INSTALLING PROJECT VOICE AS A PERMANENT WINDOWS DESKTOP APP...")
    print("=" * 65)

    # 1. Ensure Icon Exists
    if not ICON_PATH.exists():
        generate_icon()

    # 2. Get Standard Windows Paths
    desktop_dirs = []
    home_dir = Path(os.environ.get("USERPROFILE", ""))
    if (home_dir / "Desktop").exists():
        desktop_dirs.append(home_dir / "Desktop")
    if (home_dir / "OneDrive" / "Desktop").exists():
        desktop_dirs.append(home_dir / "OneDrive" / "Desktop")

    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    # 3. Clean up any old Wispr Flow shortcuts
    for d in desktop_dirs:
        for old_file in ["Wispr Flow.lnk", "Wispr_Flow.bat"]:
            p = d / old_file
            if p.exists():
                try:
                    p.unlink()
                    print(f"🧹 Removed old shortcut: {p}")
                except Exception:
                    pass

    old_startup = startup_dir / "Wispr Flow.lnk"
    if old_startup.exists():
        try:
            old_startup.unlink()
        except Exception:
            pass

    # 4. Create Desktop Shortcuts
    for d in desktop_dirs:
        desktop_shortcut = d / "Project Voice.lnk"
        if create_windows_shortcut(desktop_shortcut):
            print(f"✔ Desktop App Shortcut created: {desktop_shortcut}")

        # Also create a visible console launcher for user testing
        start_bat = d / "Start_Project_Voice.bat"
        with open(start_bat, "w", encoding="utf-8") as f:
            f.write('@echo off\n')
            f.write('title Project Voice - Console Mode\n')
            f.write(f'cd /d "{BASE_DIR}"\n')
            f.write(f'"{PYTHON_EXE_PATH}" app.py\n')
            f.write('pause\n')
        print(f"✔ Desktop Launcher (Console Mode) created: {start_bat}")

        # Also create a 1-click stop script on desktop
        stop_bat = d / "Stop_Project_Voice.bat"
        with open(stop_bat, "w", encoding="utf-8") as f:
            f.write('@echo off\n')
            f.write('echo Stopping Project Voice...\n')
            f.write('powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*app.py*\' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"\n')
            f.write('echo Project Voice stopped successfully.\n')
            f.write('pause\n')

    # Also save stop script in project root
    with open(BASE_DIR / "Stop_Project_Voice.bat", "w", encoding="utf-8") as f:
        f.write('@echo off\n')
        f.write('echo Stopping Project Voice...\n')
        f.write('powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*app.py*\' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"\n')
        f.write('echo Project Voice stopped successfully.\n')
        f.write('pause\n')

    # 5. Create Windows Startup Shortcut (Runs on Boot)
    startup_shortcut = startup_dir / "Project Voice.lnk"
    if create_windows_shortcut(startup_shortcut):
        print(f"✔ Windows Startup Shortcut created: {startup_shortcut}")
        print("   (Project Voice will auto-start quietly on every laptop reboot!)")

    # 6. Kill any old instances to avoid mutex collision
    subprocess.run(
        ["powershell", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True
    )

    # 7. Launch Project Voice now via pythonw.exe (Silent, zero black window)
    print("\n🌟 Launching Project Voice in background (System Tray)...")
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        [str(PYTHONW_PATH), str(APP_PY_PATH)],
        cwd=str(BASE_DIR),
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True
    )

    print("=" * 65)
    print("🎉 PROJECT VOICE SETUP COMPLETE!")
    print("👉 Name updated to: PROJECT VOICE")
    print("👉 Blue microphone icon is active in your System Tray (near clock).")
    print("👉 Hold [Ctrl + Space] anywhere, speak, and release to paste!")
    print("=" * 65)

if __name__ == "__main__":
    install()

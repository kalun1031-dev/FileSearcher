@echo off
cd /d "%~dp0"

if exist "release\FileSearcher.exe" (
    start "" "release\FileSearcher.exe"
    exit /b 0
)

if exist "FileSearcher\FileSearcher.exe" (
    start "" "FileSearcher\FileSearcher.exe"
    exit /b 0
)

where pythonw >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Or download the packaged exe from GitHub Releases:
    echo https://github.com/kalun1031-dev/FileSearcher/releases
    pause
    exit /b 1
)

pythonw main.py
if errorlevel 1 (
    echo Starting with console to show error...
    python main.py
    pause
)

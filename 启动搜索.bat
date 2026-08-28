@echo off
cd /d "%~dp0"

if exist "FileSearcher\FileSearcher.exe" (
    start "" "FileSearcher\FileSearcher.exe"
    exit /b 0
)

where pythonw >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

pythonw main.py
if errorlevel 1 (
    echo Starting with console to show error...
    python main.py
    pause
)

@echo off
REM Build Leo.exe — Windows
REM Requires: pyinstaller (already installed in .venv)

cd /d "%~dp0"

echo ============================================
echo  Building Leo.exe
echo ============================================

.\.venv\Scripts\pyinstaller.exe ^
    --onefile ^
    --windowed ^
    --name Leo ^
    --clean ^
    --noconfirm ^
    leo_desktop.py

echo.
echo ============================================
echo  Done. Check dist\Leo.exe
echo ============================================
pause
@echo off
REM Build LEO desktop app with pywebview + bundled frontend

cd /d "%~dp0"

echo ============================================
echo  Building LEO.exe (pywebview + frontend)
echo ============================================

.\.venv\Scripts\pyinstaller.exe ^
    --onefile ^
    --windowed ^
    --name LeoApp ^
    --add-data "frontend;frontend" ^
    --clean ^
    --noconfirm ^
    leo_app.py

echo.
echo ============================================
echo  Done. Check dist\LeoApp.exe
echo ============================================
pause
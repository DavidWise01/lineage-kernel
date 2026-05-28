@echo off
setlocal
echo Building PCKContinuityShell.exe...
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ first.
  pause
  exit /b 1
)
python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --name PCKContinuityShell pck_continuity_shell.py
echo Done: dist\PCKContinuityShell.exe
pause

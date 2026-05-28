$ErrorActionPreference = "Stop"
python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --name PCKContinuityShell pck_continuity_shell.py
Write-Host "Done: dist\PCKContinuityShell.exe"

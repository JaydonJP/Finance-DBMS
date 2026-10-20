@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" start.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo The demo could not start. See the error above and README.md.
pause
exit /b 1

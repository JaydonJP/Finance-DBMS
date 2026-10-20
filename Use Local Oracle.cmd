@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" configure_oracle.py --local
if errorlevel 1 pause

@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" configure_oracle.py
if errorlevel 1 pause

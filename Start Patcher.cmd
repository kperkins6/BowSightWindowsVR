@echo off
cd /d "%~dp0"
python patcher.py %*
if errorlevel 1 pause

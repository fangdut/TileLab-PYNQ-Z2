@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0host\start_station.ps1"
if errorlevel 1 pause

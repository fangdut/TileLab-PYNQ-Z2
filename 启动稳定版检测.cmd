@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0engineering_delivery_20261027\TileLab_Engineering_V199\start_station.ps1"
if errorlevel 1 pause

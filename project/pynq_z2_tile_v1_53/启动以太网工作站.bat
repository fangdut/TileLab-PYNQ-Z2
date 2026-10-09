@echo off
set "TILE_BOARD_IP=auto"
if not "%~1"=="" set "TILE_BOARD_IP=%~1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0host\start_station.ps1" -Ethernet "%TILE_BOARD_IP%"
if errorlevel 1 pause

@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0engineering_delivery_20261031\TileLab_Engineering_V208\start_conveyor.ps1"
if errorlevel 1 pause

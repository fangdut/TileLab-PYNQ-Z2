# Only after the receiver is paused, disconnected and source is empty.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$state=Invoke-RestMethod -Uri 'http://127.0.0.1:8770/api/state' -TimeoutSec 5
if($state.revision -ne 'V1.5' -or $state.enabled -or $state.busy){throw 'V1.5 receiver must be paused and idle first'}
$stationId=[int](Get-Content -LiteralPath (Join-Path $root 'host/workstation.pid'))
$stationProc=Get-CimInstance Win32_Process -Filter "ProcessId=$stationId"
if($stationProc.CommandLine -notlike '*pynq_z2_tile_v1_5*workstation.py*'){throw 'Unexpected workstation process'}
$displayId=[int](Get-Content -LiteralPath (Join-Path $root 'host/display.pid'))
$displayProc=Get-CimInstance Win32_Process -Filter "ProcessId=$displayId"
if($displayProc.CommandLine -notlike '*pynq_z2_tile_v1_5*hdmi_display.ps1*'){throw 'Unexpected display process'}
Stop-Process -Id $stationId
# Keep the old empty-belt window underneath until the new window is visible.
Set-Content -LiteralPath (Join-Path $root 'host/display.pid') -Value 0
& (Join-Path $root 'host/start_station.ps1') -NoBrowser
$newDisplayId=[int](Get-Content -LiteralPath (Join-Path $root 'host/display.pid'))
Wait-Process -Id $newDisplayId -Timeout 3 -ErrorAction SilentlyContinue
if(!(Get-Process -Id $newDisplayId -ErrorAction SilentlyContinue)){throw 'New HDMI player exited'}
Stop-Process -Id $displayId
Write-Output 'Restarted V1.5 host and source player only; FPGA kept running'

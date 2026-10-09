$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if((Split-Path $root -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'Wrong release'}
$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
if($s.revision -ne 'V1.43' -or $s.enabled -or $s.busy -or $s.pending_operation -or $s.pending_confirmation -or $s.manual_waiting){throw 'Restart requires paused idle V143'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
$taskId=[int](Get-Content -LiteralPath (Join-Path $root 'host/workstation.pid') -Raw)
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
if(!$proc -or $proc.CommandLine -notlike '*pynq_z2_tile_v1_53*workstation.py*'){throw 'Process identity mismatch'}
$handle=Get-Process -Id $taskId
Stop-Process -Id $taskId
if(!$handle.WaitForExit(5000)){throw 'Station process still alive'}
& (Join-Path $root 'host/start_station.ps1') -NoBrowser
Write-Output 'Restarted only the V143 Station; player and board were retained.'

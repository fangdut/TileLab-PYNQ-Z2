$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
if($s.revision -ne 'V1.10'){throw 'Wrong service'}
foreach($body in @('{"op":"display","value":"station_6"}','{"op":"pause"}')){Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body $body | Out-Null}
$deadline=(Get-Date).AddSeconds(15)
do{Start-Sleep -Milliseconds 100;$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state';if((Get-Date)-gt $deadline){throw 'Receiver did not stop'}}while($s.busy)
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
$taskId=[int](Get-Content -LiteralPath (Join-Path $root 'host/workstation.pid') -Raw)
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
if(!$proc -or $proc.CommandLine -notlike '*pynq_z2_tile_v1_53*workstation.py*'){throw 'Process identity mismatch'}
Stop-Process -Id $taskId
& (Join-Path $root 'host/start_station.ps1') -NoBrowser
$deadline=(Get-Date).AddSeconds(10)
do{Start-Sleep -Milliseconds 100;try{$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'}catch{$s=$null};if((Get-Date)-gt $deadline){throw 'HTTP not ready'}}while(!$s)
foreach($body in @('{"op":"recipe","value":"mvtec_hdmi_weak_v16"}','{"op":"display","value":"real_video"}','{"op":"start"}')){Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body $body | Out-Null}
Write-Output 'V1.10 restarted in preview mode.'

$ErrorActionPreference='Stop'
$old='D:\Vivado\pynq_z2_tile_v1_31'
$new=Split-Path $PSScriptRoot -Parent
$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
if($s.revision -ne 'V1.31'){throw 'Expected the validated V1.31 station before switching'}
foreach($body in @('{"op":"display","value":"station_6"}','{"op":"pause"}')){
 Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body $body | Out-Null
}
$deadline=(Get-Date).AddSeconds(15)
do{
 Start-Sleep -Milliseconds 100
 $s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
 if((Get-Date) -gt $deadline){throw 'Old receiver did not become idle'}
}while($s.busy)
if($s.pending_operation){throw 'Finish old pending evidence confirmation before stopping'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
foreach($entry in @(@('workstation.pid','workstation.py'),@('display.pid','hdmi_display.ps1'))){
 $taskId=[int](Get-Content -LiteralPath (Join-Path $old ('host\'+$entry[0])) -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 if($proc){
  if($proc.CommandLine -notlike ('*pynq_z2_tile_v1_31*'+$entry[1]+'*')){throw 'Process identity mismatch'}
  Stop-Process -Id $taskId
 }
}
& (Join-Path $new 'host\start_station.ps1') -NoBrowser
$deadline=(Get-Date).AddSeconds(12)
do{
 Start-Sleep -Milliseconds 150
 try{$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'}catch{$s=$null}
 if((Get-Date) -gt $deadline){throw 'New service did not start'}
}while(!$s -or $s.revision -ne 'V1.32')
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"display","value":"station_6"}' | Out-Null
Write-Output 'V1.32 service/player ready and receiver paused; previous project preserved. Program matching hardware next.'

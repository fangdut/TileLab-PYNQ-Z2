$ErrorActionPreference='Stop'
$old='D:\Vivado\pynq_z2_tile_v1_5'
$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
if($state.revision -ne 'V1.5'){throw 'Expected previous V1.5 station; inspect before stopping'}
foreach($body in @('{"op":"display","value":"station_6"}','{"op":"pause"}')){
 Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body $body | Out-Null
}
$deadline=(Get-Date).AddSeconds(15)
do{
 Start-Sleep -Milliseconds 100
 $state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
 if((Get-Date) -gt $deadline){throw 'Old receiver remained busy'}
}while($state.busy)
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
foreach($entry in @(@('workstation.pid','workstation.py'),@('display.pid','hdmi_display.ps1'))){
 $taskId=[int](Get-Content -LiteralPath (Join-Path $old ('host\'+$entry[0])) -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 if($proc){
  if($proc.CommandLine -notlike ('*pynq_z2_tile_v1_5*'+$entry[1]+'*')){throw 'Process identity mismatch'}
  Stop-Process -Id $taskId
 }
}
Write-Output 'Previous station/display stopped; previous project files preserved.'

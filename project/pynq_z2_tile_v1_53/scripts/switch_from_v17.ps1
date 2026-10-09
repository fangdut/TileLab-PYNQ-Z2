$ErrorActionPreference='Stop'
$old='D:\Vivado\pynq_z2_tile_v1_7'
$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
if($s.revision -ne 'V1.7'){throw 'Expected V1.7 station; inspect current owner before switching'}
foreach($body in @('{"op":"display","value":"station_6"}','{"op":"pause"}')){
 Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body $body | Out-Null
}
$deadline=(Get-Date).AddSeconds(15)
do{
 Start-Sleep -Milliseconds 100
 $s=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
 if((Get-Date) -gt $deadline){throw 'Old receiver remained busy'}
}while($s.busy)
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
foreach($entry in @(@('workstation.pid','workstation.py'),@('display.pid','hdmi_display.ps1'))){
 $taskId=[int](Get-Content -LiteralPath (Join-Path $old ('host\'+$entry[0])) -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 if($proc){
  if($proc.CommandLine -notlike ('*pynq_z2_tile_v1_7*'+$entry[1]+'*')){throw 'Process identity mismatch'}
  Stop-Process -Id $taskId
 }
}
Write-Output 'V1.7 runtime stopped; its project, sources and artifacts preserved.'

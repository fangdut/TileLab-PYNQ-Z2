$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if((Split-Path $root -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'Wrong release root'}
$python='C:/Users/Fang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$audit=Get-Content -LiteralPath (Join-Path $root 'reports/v152/firmware_audit.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if(!$audit.passed -or $audit.version -ne 'V1.52'){throw 'V1.52 firmware audit not passed'}
$sdk=Join-Path $root 'pynq_z2_tile_v1_53.sdk'
foreach($name in @('system.bit','system.xsa')){if(!(Test-Path (Join-Path $sdk $name))){throw "Missing $name"}}
$oldState=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
$oldState | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $root 'reports/v152/pre_program_station.json') -Encoding utf8
if($oldState.revision -ne 'V1.48'){throw "Expected live V1.48 before programming, got $($oldState.revision)"}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"pause"}' | Out-Null
$deadline=(Get-Date).AddSeconds(20)
do {
 Start-Sleep -Milliseconds 100
 $state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
 if((Get-Date) -gt $deadline){throw 'V1.48 receiver did not become idle'}
} while($state.busy)
if($state.pending_operation -or $state.pending_confirmation -or $state.manual_waiting){throw 'Pending operation remains before programming'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
$oldRoot='D:\Vivado\pynq_z2_tile_v1_48'
foreach($entry in @(@('workstation.pid','workstation.py'),@('display.pid','hdmi_display.ps1'))){
 $pidPath=Join-Path $oldRoot ('host\'+$entry[0]);if(!(Test-Path $pidPath)){continue}
 $taskId=[int](Get-Content -LiteralPath $pidPath -Raw);$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 if($proc -and $proc.CommandLine -notlike ('*pynq_z2_tile_v1_48*'+$entry[1]+'*')){throw 'Old process identity mismatch'}
 if($proc){Stop-Process -Id $taskId -Force}
}
& 'D:/2025.2/Vitis/bin/xsdb.bat' (Join-Path $sdk 'program_ethernet.tcl') *> (Join-Path $root 'reports/v152/programming.log')
if($LASTEXITCODE -ne 0){throw 'Programming failed; inspect reports/v152/programming.log'}
if(!(Test-Path (Join-Path $root 'reports/programmed_v152.json'))){throw 'Programming identity proof missing'}
& (Join-Path $root 'host/start_station.ps1') -NoBrowser
if($LASTEXITCODE -ne 0){throw 'V1.52 station start failed'}
& $python -B -X utf8 (Join-Path $root 'scripts/wait_board_ready.py') *> (Join-Path $root 'reports/v152/wait_board_ready.log')
if($LASTEXITCODE -ne 0){throw 'V1.52 board readiness failed'}
Write-Output 'V1.52 programmed and board identity verified; station remains paused.'

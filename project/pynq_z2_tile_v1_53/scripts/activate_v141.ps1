$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if((Split-Path $root -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'Wrong release root'}
$python='C:/Users/Fang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$hardware=Get-Content -LiteralPath (Join-Path $root 'reports/v141/hardware_audit.json') -Raw | ConvertFrom-Json
$firmware=Get-Content -LiteralPath (Join-Path $root 'reports/v141/firmware_audit.json') -Raw | ConvertFrom-Json
if(!$hardware.passed -or !$firmware.passed -or $firmware.firmware_version -ne 76032){throw 'Current release audits not passed'}
$sdk=Join-Path $root 'pynq_z2_tile_v1_53.sdk'
foreach($entry in $hardware.artifacts_sha256.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $sdk $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Hardware artifact changed after audit'}
}
if((Get-FileHash -LiteralPath (Join-Path $sdk 'hdmi_ethernet/build/hdmi_ethernet.elf') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $firmware.elf_sha256){throw 'ELF changed after audit'}
$old='D:\Vivado\pynq_z2_tile_v1_40'
$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
if($state.revision -ne 'V1.40'){throw 'Expected live V1.40; inspect before stopping anything'}
$state | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $root 'reports/v141/pre_program_station.json') -Encoding utf8
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"pause"}' | Out-Null
$deadline=(Get-Date).AddSeconds(20)
do{
 Start-Sleep -Milliseconds 100
 $state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
 if((Get-Date) -gt $deadline){throw 'Old receiver did not become idle'}
}while($state.busy)
if($state.pending_operation -or $state.pending_confirmation -or $state.manual_waiting){throw 'Old receiver has pending work; resolve before reprogramming'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
foreach($entry in @(@('workstation.pid','workstation.py'),@('display.pid','hdmi_display.ps1'))){
 $taskId=[int](Get-Content -LiteralPath (Join-Path $old ('host\'+$entry[0])) -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 if(!$proc -or $proc.CommandLine -notlike ('*pynq_z2_tile_v1_40*'+$entry[1]+'*')){throw 'Old process identity mismatch'}
 Stop-Process -Id $taskId
}
& 'D:/2025.2/Vitis/bin/xsdb.bat' (Join-Path $sdk 'program_ethernet.tcl') *> (Join-Path $root 'reports/v141/programming.log')
if($LASTEXITCODE -ne 0){throw 'Programming failed; inspect programming.log before retry'}
if(!(Test-Path -LiteralPath (Join-Path $root 'reports/programmed_v141.json'))){throw 'Programming identity proof missing'}
& (Join-Path $root 'host/start_station.ps1') -NoBrowser
if($LASTEXITCODE -ne 0){throw 'Station start failed'}
# Station starts paused; wait_board_ready alone owns the board while HDMI source starts.
& $python -B -X utf8 (Join-Path $root 'scripts/wait_board_ready.py')
if($LASTEXITCODE -ne 0){throw 'Board readiness not verified'}
Write-Output 'V1.41 programmed; current boot ready; receiver remains paused.'

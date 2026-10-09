$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if((Split-Path $root -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'Wrong release root'}
$hostProof=Get-Content -LiteralPath (Join-Path $root 'reports/v148/host_validation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if(!$hostProof.passed){throw 'Host regression not passed'}
foreach($entry in $hostProof.source_sha256.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $root $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Host source changed after regression'}
}
$plan=Get-Content -LiteralPath (Join-Path $root 'ITERATION_PLAN.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$sdk=Join-Path $root ((Split-Path $root -Leaf)+'.sdk')
foreach($entry in $plan.inherited_hardware_sha256.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $sdk $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Host-only iteration must retain hardware artifacts'}
}
$old='D:\Vivado\pynq_z2_tile_v1_47'
$program=Get-Content -LiteralPath (Join-Path $old 'reports/programmed_v147.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
if($state.revision -ne 'V1.47' -or $state.board_stats.boot_id -ne $program.boot_id -or $state.board_stats.version -ne 76288){throw 'Expected V147 Station on the verified V142 hardware boot'}
$state | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $root 'reports/v148/pre_switch_station.json') -Encoding utf8
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"pause"}' | Out-Null
$deadline=(Get-Date).AddSeconds(20)
do{
 Start-Sleep -Milliseconds 100
 $state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'
 if((Get-Date) -gt $deadline){throw 'Old receiver did not become idle'}
}while($state.busy)
if($state.pending_operation -or $state.pending_confirmation -or $state.manual_waiting){throw 'Old receiver has pending work'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
foreach($entry in @(@('workstation.pid','workstation.py'),@('display.pid','hdmi_display.ps1'))){
 $taskId=[int](Get-Content -LiteralPath (Join-Path $old ('host\'+$entry[0])) -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 if(!$proc -or $proc.CommandLine -notlike ('*pynq_z2_tile_v1_47*'+$entry[1]+'*')){throw 'Old process identity mismatch'}
 Stop-Process -Id $taskId
}
# Preserve the original programming timestamp and boot. This is a verified
# reuse record, not a claim that V148 downloaded PL or ARM again.
$program | Add-Member -Force -NotePropertyName deployment_method -NotePropertyValue 'Reused unchanged V142 physical boot; no programming in V148'
$program | Add-Member -Force -NotePropertyName source_programming_record -NotePropertyValue (Join-Path $old 'reports/programmed_v147.json')
$program | Add-Member -Force -NotePropertyName source_programming_sha256 -NotePropertyValue ((Get-FileHash -LiteralPath (Join-Path $old 'reports/programmed_v147.json') -Algorithm SHA256).Hash.ToLowerInvariant())
$program | Add-Member -Force -NotePropertyName reuse_verified_at -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'))
$program | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root 'reports/programmed_v148.json') -Encoding utf8
& (Join-Path $root 'host/start_station.ps1') -NoBrowser
$deadline=(Get-Date).AddSeconds(15)
do{
 Start-Sleep -Milliseconds 200
 try{$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state?limit=1'}catch{$state=$null}
 if((Get-Date) -gt $deadline){throw 'New Station did not become ready'}
}while(!$state -or $state.revision -ne 'V1.48')
Write-Output 'V148 host started paused with unchanged V142 hardware/firmware boot.'


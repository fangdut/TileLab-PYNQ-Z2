# Reproduce the final volatile programming and actual hardware acceptance.
param([switch]$SkipProgramming)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$workspace=Join-Path $root 'pynq_z2_tile_v1_5.sdk'
$output=Join-Path $root 'reports/v15'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
if($state.revision -ne 'V1.5' -or $state.enabled -or $state.busy){throw 'Pause the V1.5 receiver before hardware acceptance'}
$digest=(Get-FileHash -LiteralPath (Join-Path $workspace 'system.xsa')).Hash
foreach($relative in @('hdmi_platform/hw/system.xsa','hdmi_platform/export/hdmi_platform/hw/system.xsa')){
 if((Get-FileHash -LiteralPath (Join-Path $workspace $relative)).Hash -ne $digest){throw "Platform hardware mismatch: $relative"}
}
if(!$SkipProgramming){
 & 'D:/2025.2/Vitis/bin/xsdb.bat' (Join-Path $workspace 'program_ethernet.tcl') *> (Join-Path $output 'programming_gate_final.log')
 if($LASTEXITCODE -ne 0){throw 'Programming failed; inspect programming_gate_final.log'}
 Copy-Item -LiteralPath (Join-Path $root 'reports/programmed_v15.json') -Destination (Join-Path $output 'programmed_acceptance.json') -Force
}
$program=Get-Content -LiteralPath (Join-Path $output 'programmed_acceptance.json') -Raw | ConvertFrom-Json
foreach($property in $program.sha256.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $workspace $property.Name)).Hash -ne $property.Value){throw 'Programmed artifact digest mismatch'}
}
# JTAG application startup precedes PHY negotiation and TCP listen readiness.
# Wait for a real response with this boot identity, rather than a fixed sleep.
$ready=$false;$deadline=(Get-Date).AddSeconds(45)
do {
 try {
  $status=Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"status"}' -TimeoutSec 5
  $ready=($status.boot_id -eq $program.boot_id -and $status.version -eq 66816)
 } catch {}
 if(!$ready){Start-Sleep -Milliseconds 500}
} until($ready -or (Get-Date) -gt $deadline)
if(!$ready){throw 'Board TCP did not become ready with the expected V1.5 boot identity'}
Write-Output 'Final V1.5 hardware and firmware programmed'
function Run-Acceptance([string]$name,[string[]]$arguments){
 Write-Output "Starting $name"
 & $python -X utf8 @arguments *> (Join-Path $output ($name+'.log'))
 if($LASTEXITCODE -ne 0){throw "$name failed; inspect its retained log and evidence"}
 Write-Output "PASS $name"
}
try {
 Run-Acceptance 'final_recipe_boundary' @((Join-Path $PSScriptRoot 'board_v15_recipe_boundary.py'))
 Run-Acceptance 'final_real_board' @((Join-Path $PSScriptRoot 'board_v15_real.py'))
 Run-Acceptance 'final_ultrafast' @((Join-Path $PSScriptRoot 'board_v15_continuous.py'),'ultrafast','--seconds','60','--threshold','36')
 Run-Acceptance 'final_real_motion' @((Join-Path $PSScriptRoot 'board_v15_continuous.py'),'real_video','--seconds','120','--threshold','89')
 Run-Acceptance 'final_motion_audit' @((Join-Path $PSScriptRoot 'audit_v15_motion.py'))
 Run-Acceptance 'final_live_delivery' @((Join-Path $PSScriptRoot 'run_v15_live_delivery.py'))
} catch {
 try {Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"display","value":"station_6"}' | Out-Null} catch {}
 throw
}
Write-Output 'Actual hardware acceptance passed; real-photo conveyor and receiver remain running'

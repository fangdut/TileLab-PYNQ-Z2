# SPDX-License-Identifier: MIT
param([Parameter(Mandatory=$true)][string]$Config,[string]$Python)
$ErrorActionPreference='Stop'
$appRoot=$PSScriptRoot
. (Join-Path $appRoot 'runtime.ps1')
$python=Resolve-TileLabPython -Preferred $Python
$configPath=(Resolve-Path -LiteralPath $Config).Path
$bundleRoot=(Resolve-Path -LiteralPath (Join-Path (Split-Path $configPath -Parent) '..\..')).Path
$source=Join-Path $bundleRoot 'project\host\stop_inspect_station'
$station=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8793/api/state'
$flow=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8794/api/state'
if($station.phase -notin @('READY','RELEASED','SEGREGATED','REMOVED','REVIEW_HOLD','GOOD_HOLD','DEFECT_HOLD','CONFLICT_HOLD')){throw 'Wait until the active inference/disposition completes'}
if(!$station.closed_loop.calibrated){throw 'Reference qualification is not valid'}
$stationOwner=(Get-NetTCPConnection -LocalPort 8793 -State Listen).OwningProcess
$flowOwner=(Get-NetTCPConnection -LocalPort 8794 -State Listen).OwningProcess
$stationProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$stationOwner"
$flowProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$flowOwner"
if($stationProcess.CommandLine -notlike ('*'+(Join-Path $appRoot 'station_gateway.py')+'*') -or $stationProcess.CommandLine -notlike ('*'+$configPath+'*')){throw 'Unexpected station owner'}
if($flowProcess.CommandLine -notlike ('*'+(Join-Path $appRoot 'server.py')+'*')){throw 'Unexpected conveyor owner'}
$prep=Join-Path $appRoot ('recording_prep\'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $prep|Out-Null
$station|ConvertTo-Json -Depth 35|Set-Content -LiteralPath (Join-Path $prep 'station_before.json') -Encoding utf8
$flow|ConvertTo-Json -Depth 35|Set-Content -LiteralPath (Join-Path $prep 'flow_before.json') -Encoding utf8
$resume=$station|ConvertTo-Json -Depth 35|ConvertFrom-Json
$pending=if($station.cycle -and !$station.cycle.disposition){$station.cycle.id}else{$null}
$resume|Add-Member -NotePropertyName previous_pending_cycle -NotePropertyValue $pending -Force
$resume|Add-Member -NotePropertyName restart_reason -NotePropertyValue 'Recording preparation: preserve all old records; abandon any held item without inventing a review; begin from idle.' -Force
$resume.cycle=$null;$resume.phase='READY';$resume.stop_requested=$false
$resumeFile=Join-Path $prep 'resume.json'
$resume|ConvertTo-Json -Depth 35|Set-Content -LiteralPath $resumeFile -Encoding utf8
Stop-Process -Id $flowOwner
Stop-Process -Id $stationOwner
$arguments='-X utf8 "{0}" --config "{1}" --station-source "{2}" --resume "{3}"' -f (Join-Path $appRoot 'station_gateway.py'),$configPath,$source,$resumeFile
$service=Start-Process $python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $prep 'gateway_stdout.log') -RedirectStandardError (Join-Path $prep 'gateway_stderr.log')
$service.Id|Set-Content -LiteralPath (Join-Path $appRoot 'gateway_pid.txt')
for($attempt=0;$attempt -lt 25;$attempt++){
    Start-Sleep -Milliseconds 300
    try{$ready=Invoke-RestMethod -TimeoutSec 2 'http://127.0.0.1:8793/api/state';if($ready.phase -eq 'READY' -and $ready.closed_loop.calibrated){break}}catch{}
    $service.Refresh();if($service.HasExited){throw ('Gateway exited; see '+$prep)}
}
if(!$ready -or $ready.phase -ne 'READY'){throw ('Gateway did not become ready; see '+$prep)}
& (Join-Path $appRoot 'start_conveyor.ps1') -Config $configPath -NoWindows
Write-Host ('Recording preparation preserved at '+$prep)

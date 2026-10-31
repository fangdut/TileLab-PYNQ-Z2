# SPDX-License-Identifier: MIT
param([Parameter(Mandatory=$true)][string]$Config,[string]$Python)
$ErrorActionPreference='Stop'
$appRoot=$PSScriptRoot
. (Join-Path $appRoot 'runtime.ps1')
$python=Resolve-TileLabPython -Preferred $Python
$configPath=(Resolve-Path -LiteralPath $Config).Path
$bundleRoot=(Resolve-Path -LiteralPath (Join-Path (Split-Path $configPath -Parent) '..\..')).Path
$source=Join-Path $bundleRoot 'project\host\stop_inspect_station'
if(!(Test-Path -LiteralPath (Join-Path $source 'server.py'))){throw 'Original station source not found'}
$s=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8793/api/state'
if($s.automatic_pass_policy.enabled){Write-Host 'Automatic-pass PC station already running';return}
if($s.phase -notin @('READY','RELEASED','SEGREGATED','REMOVED','REVIEW_HOLD','GOOD_HOLD','DEFECT_HOLD','CONFLICT_HOLD')){throw 'Wait for the current task before upgrading'}
$stationOwner=(Get-NetTCPConnection -LocalPort 8793 -State Listen).OwningProcess
$stationProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$stationOwner"
if($stationProcess.CommandLine -notlike ('*'+(Join-Path $source 'server.py')+'*') -or $stationProcess.CommandLine -notlike ('*'+$configPath+'*')){throw 'Port8793 owner does not match this exact station/config'}
$flowListener=@(Get-NetTCPConnection -LocalPort 8794 -State Listen -ErrorAction SilentlyContinue)
if($flowListener.Count){
    $flowOwner=$flowListener[0].OwningProcess
    $flowProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$flowOwner"
    if($flowProcess.CommandLine -notlike ('*'+(Join-Path $appRoot 'server.py')+'*')){throw 'Port8794 owner is not this conveyor'}
    $f=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8794/api/state'
    if($f.phase -notin @('IDLE','REVIEW')){throw 'Wait for the conveyor to hold before upgrading'}
}
$checkpoint=Join-Path $appRoot 'migration_checkpoint.json'
$s|ConvertTo-Json -Depth 30|Set-Content -LiteralPath $checkpoint -Encoding utf8
# Only verified local project server processes are stopped. Board state and
# frozen deployment files stay in place; the held cycle is revalidated below.
if($flowListener.Count){Stop-Process -Id $flowOwner}
Stop-Process -Id $stationOwner
$arguments='-X utf8 "{0}" --config "{1}" --station-source "{2}" --resume "{3}"' -f (Join-Path $appRoot 'station_gateway.py'),$configPath,$source,$checkpoint
$service=Start-Process $python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $appRoot 'gateway_stdout.log') -RedirectStandardError (Join-Path $appRoot 'gateway_stderr.log')
$service.Id|Set-Content -LiteralPath (Join-Path $appRoot 'gateway_pid.txt')
for($attempt=0;$attempt -lt 30;$attempt++){
    Start-Sleep -Milliseconds 300
    try{$new=Invoke-RestMethod -TimeoutSec 2 'http://127.0.0.1:8793/api/state';if($new.automatic_pass_policy.enabled){Write-Host 'PC automatic-pass policy ready; board deployment preserved';return}}catch{}
    $service.Refresh();if($service.HasExited){break}
}
throw ('PC policy service failed. Original checkpoint is preserved: '+$checkpoint+'. See gateway_stderr.log; no board reload was performed.')

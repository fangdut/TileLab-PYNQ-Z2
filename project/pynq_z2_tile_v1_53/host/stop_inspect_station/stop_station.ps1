param([string]$Bundle=$PSScriptRoot)
$ErrorActionPreference='Stop'
$bundleRoot=(Resolve-Path -LiteralPath $Bundle).Path.Replace('\','/')
$listeners=@(Get-NetTCPConnection -LocalPort 8793 -State Listen -ErrorAction SilentlyContinue)
if (!$listeners.Count) { Write-Host 'Station is already stopped.'; return }
$ids=@($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
if ($ids.Count -ne 1) { throw 'Unexpected listener count.' }
$process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$ids[0])
$command=$process.CommandLine.Replace('\','/')
if (!$command.Contains($bundleRoot+'/project/host/stop_inspect_station/server.py')) { throw 'Another bundle owns this station. Use its own stop script.' }
$state=Invoke-RestMethod -Uri 'http://127.0.0.1:8793/api/state' -TimeoutSec 5
if ($state.phase -notin @('READY','RELEASED','SEGREGATED','REMOVED','FAULT')) { throw 'Finish the current inspection and review before stopping.' }
Stop-Process -Id $ids[0]
Write-Host 'Workstation stopped. Board power and all records were preserved.'

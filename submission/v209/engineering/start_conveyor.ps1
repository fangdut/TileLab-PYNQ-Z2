param([switch]$VerifyOnly,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$bundleRoot=$PSScriptRoot
& (Join-Path $bundleRoot 'start_station.ps1') -Bundle $bundleRoot -NoBrowser -VerifyOnly:$VerifyOnly
if($VerifyOnly){return}
$listener=Get-NetTCPConnection -LocalPort 8793 -State Listen -ErrorAction Stop
$ownerProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+$listener.OwningProcess)
$configMatch=[regex]::Match($ownerProcess.CommandLine,'--config\s+"([^"]+)"')
if(!$configMatch.Success){throw 'Cannot identify the running station configuration'}
$configPath=$configMatch.Groups[1].Value
& (Join-Path $bundleRoot 'project/host/conveyor_station/start_conveyor.ps1') -Config $configPath -NoWindows:$NoBrowser

param([string]$Ethernet='auto',[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if($Ethernet -eq 'auto'){
 $proof=Join-Path $root 'reports/programmed_v153.json'
 $Ethernet='169.254.200.10'
 if(Test-Path -LiteralPath $proof){
  $record=Get-Content -LiteralPath $proof -Raw -Encoding UTF8 | ConvertFrom-Json
  if($record.configured_address -and $record.configured_address -ne 'dhcp'){$Ethernet=$record.configured_address}
 }
}
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if(!(Test-Path -LiteralPath $python)){$python=(Get-Command python -ErrorAction Stop).Source}
$running=$false
try{$s=Invoke-RestMethod -Uri 'http://127.0.0.1:8770/api/state' -TimeoutSec 2;$running=($s.mode -eq 'LIVE_HARDWARE')}catch{}
if($running -and (($Ethernet -and ($s.transport -ne 'ETHERNET_TCP' -or $s.board_address -ne $Ethernet)) -or (!$Ethernet -and $s.transport -eq 'ETHERNET_TCP'))){throw 'Workstation already running with another transport. Close that workstation service before switching.'}
if($running -and $s.revision -ne 'V1.53'){throw 'Port 8770 is running another project version. Stop that service before starting V1.53.'}
if(!$running){
 $stationArgs=@(('"'+(Join-Path $PSScriptRoot 'workstation.py')+'"'))
 if($Ethernet){
  $ip=[System.Net.IPAddress]::Parse($Ethernet)
  if($ip.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork){throw 'IPv4 required'}
  $stationArgs+=@('--ethernet',$ip.ToString())
 }
 $proc=Start-Process -FilePath $python -ArgumentList $stationArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'reports/workstation_service.log') -RedirectStandardError (Join-Path $root 'reports/workstation_service_error.log')
 $proc.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'workstation.pid')
}
$displayAlive=$false;$pidPath=Join-Path $PSScriptRoot 'display.pid'
if(Test-Path -LiteralPath $pidPath){
 $displayId=[int](Get-Content -LiteralPath $pidPath -Raw)
 $displayProc=Get-CimInstance Win32_Process -Filter "ProcessId=$displayId"
 $displayAlive=$displayProc -and $displayProc.CommandLine -like '*hdmi_display.ps1*'
}
if(!$displayAlive){
 Set-Content -LiteralPath (Join-Path $PSScriptRoot 'display_command.txt') -Value ('TILE_CMD_V1 '+[Guid]::NewGuid().ToString('N')+' station_0') -Encoding ascii
 $displayProc=Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $PSScriptRoot 'hdmi_display.ps1')+'"') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'reports/display.log') -RedirectStandardError (Join-Path $root 'reports/display_error.log')
 $displayProc.Id | Set-Content -LiteralPath $pidPath
}
if(!$NoBrowser){Start-Process 'http://127.0.0.1:8770'}

param([string]$Root,[int]$ExpectedPid,[ValidateRange(0,10)][double]$HoldSeconds=0,[ValidateRange(0,60)][double]$AfterSeconds=8,[string]$LogName='render_test')
$ErrorActionPreference='Stop'
$expectedRoot=(Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
if((Resolve-Path -LiteralPath $Root).Path -ne $expectedRoot){throw 'Only this project player may be restarted'}
if($LogName -notmatch '^[a-z0-9_]+$'){throw 'Invalid log name'}
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$ExpectedPid"
if(!$proc -or $proc.CommandLine -notlike ('*'+$Root+'*hdmi_display.ps1*')){throw 'Player identity mismatch'}
Stop-Process -Id $ExpectedPid
$next=Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $Root 'host/hdmi_display.ps1')+'"'),'-DiagnosticHoldSeconds',$HoldSeconds,'-DiagnosticStartAfterSeconds',$AfterSeconds -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Root ('reports/'+$LogName+'.log')) -RedirectStandardError (Join-Path $Root ('reports/'+$LogName+'_error.log'))
$next.Id | Set-Content -LiteralPath (Join-Path $Root 'host/display.pid')
$next.Id

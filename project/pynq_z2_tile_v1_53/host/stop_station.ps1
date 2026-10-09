$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$s=Invoke-RestMethod 'http://127.0.0.1:8770/api/live' -TimeoutSec 3
if($s.revision -ne 'V1.53'){throw 'Unexpected station revision'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"pause"}' | Out-Null
$until=(Get-Date).AddSeconds(25)
do {
 $s=Invoke-RestMethod 'http://127.0.0.1:8770/api/live' -TimeoutSec 3
 if((Get-Date) -gt $until){throw 'Station remains busy; do not terminate in-flight evidence'}
 Start-Sleep -Milliseconds 100
}while($s.busy)
if($s.pending_operation -or $s.pending_confirmation){throw 'Resolve pending confirmation before stopping'}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"disconnect"}' | Out-Null
foreach($name in @('workstation','display')){
 $p=Join-Path $PSScriptRoot ($name+'.pid')
 if(!(Test-Path -LiteralPath $p)){continue}
 $taskId=[int](Get-Content -LiteralPath $p -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
 $scriptName=if($name -eq 'display'){'hdmi_display.ps1'}else{'workstation.py'}
 if($proc -and ($proc.CommandLine -notlike ('*'+$root+'*') -or $proc.CommandLine -notlike ('*'+$scriptName+'*'))){throw 'PID belongs to an unrelated process'}
 if($proc){Stop-Process -Id $taskId -Force}
}

# SPDX-License-Identifier: MIT
param(
    [Parameter(Mandatory=$true)][string]$Config,
    [string]$Python,
    [switch]$NoWindows
)
$ErrorActionPreference='Stop'
$appRoot=$PSScriptRoot
. (Join-Path $appRoot 'runtime.ps1')
$Python=Resolve-TileLabPython -Preferred $Python
$station=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8793/api/state'
if (!$station.closed_loop.enabled) { throw 'Start the V202 closed-loop station first.' }
if (!$station.automatic_pass_policy.enabled) {
    & (Join-Path $appRoot 'upgrade_station.ps1') -Config $Config -Python $Python
    $station=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8793/api/state'
    if(!$station.automatic_pass_policy.enabled){throw 'The automatic-pass policy is not available.'}
}
$listener=@(Get-NetTCPConnection -LocalPort 8794 -State Listen -ErrorAction SilentlyContinue)
if ($listener.Count -eq 0) {
    $argsLine='-X utf8 "{0}" --config "{1}"' -f (Join-Path $appRoot 'server.py'), (Resolve-Path -LiteralPath $Config).Path
    $service=Start-Process -FilePath $Python -ArgumentList $argsLine -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $appRoot 'stdout.log') -RedirectStandardError (Join-Path $appRoot 'stderr.log')
    $service.Id | Set-Content -LiteralPath (Join-Path $appRoot 'server_pid.txt')
    for($attempt=0;$attempt -lt 20;$attempt++) {
        try { $flow=Invoke-RestMethod -TimeoutSec 2 'http://127.0.0.1:8794/api/state'; break } catch { Start-Sleep -Milliseconds 250 }
    }
} else { $flow=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8794/api/state' }
if (!$flow.run) { throw 'Conveyor service did not start, or another application owns port 8794.' }
if ($NoWindows) { Write-Host 'Conveyor: http://127.0.0.1:8794/'; return }
$chrome=$env:TILELAB_CHROME
if(!$chrome){$chrome=Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'}
if (!(Test-Path -LiteralPath $chrome)) { throw 'Chrome not found. Open / and /display in two browser windows.' }
Add-Type -AssemblyName System.Windows.Forms
$external=@([System.Windows.Forms.Screen]::AllScreens | Where-Object {!$_.Primary})
if($external.Count -ne 1) { throw 'Expected one extended display. Service is running; display window was not opened.' }
$bounds=$external[0].Bounds
# These are visible presentation windows explicitly requested for the demo.
$displayArgs=@('--no-first-run','--no-default-browser-check','--disable-background-timer-throttling','--disable-renderer-backgrounding','--force-device-scale-factor=1',('--user-data-dir="'+(Join-Path $appRoot 'browser_display_v207')+'"'),('--window-position='+$bounds.X+','+$bounds.Y),('--window-size='+$bounds.Width+','+$bounds.Height),'--start-fullscreen','--app=http://127.0.0.1:8794/display')
Start-Process -FilePath $chrome -ArgumentList $displayArgs
$operatorArgs=@('--no-first-run','--no-default-browser-check','--force-device-scale-factor=1',('--user-data-dir="'+(Join-Path $appRoot 'browser_operator_v207')+'"'),'--window-position=60,40','--window-size=1440,1050','--app=http://127.0.0.1:8794/')
Start-Process -FilePath $chrome -ArgumentList $operatorArgs
Write-Host 'Operator: http://127.0.0.1:8794/  Display: http://127.0.0.1:8794/display'

# SPDX-License-Identifier: MIT
$ErrorActionPreference='Stop'
$appRoot=$PSScriptRoot
$flow=Invoke-RestMethod -TimeoutSec 5 'http://127.0.0.1:8794/api/state'
if($flow.phase -ne 'IDLE' -or $flow.enabled){throw 'Expected idle recording preparation'}
Add-Type -AssemblyName System.Windows.Forms
$external=@([System.Windows.Forms.Screen]::AllScreens|Where-Object {!$_.Primary})
if($external.Count -ne 1){throw 'Recording windows require one extended display'}
$bounds=$external[0].Bounds
$profiles=@((Join-Path $appRoot 'browser_display_v207'),(Join-Path $appRoot 'browser_operator_v207'))
$roots=Get-CimInstance Win32_Process -Filter "name='chrome.exe'"|Where-Object {
    $line=$_.CommandLine
    $line -and $line -notlike '*--type=*' -and @($profiles|Where-Object {$line.Contains('--user-data-dir="'+$_+'"')}).Count -gt 0
}
# Close only the two project presentation windows, leaving other Chrome use.
$roots|ForEach-Object {Stop-Process -Id $_.ProcessId}
$chrome=$env:TILELAB_CHROME
if(!$chrome){$chrome=Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'}
$displayArgs=@('--no-first-run','--no-default-browser-check','--disable-background-timer-throttling','--disable-renderer-backgrounding','--force-device-scale-factor=1',('--user-data-dir="'+$profiles[0]+'"'),('--window-position='+$bounds.X+','+$bounds.Y),('--window-size='+$bounds.Width+','+$bounds.Height),'--start-fullscreen','--app=http://127.0.0.1:8794/display?filming=1')
Start-Process -FilePath $chrome -ArgumentList $displayArgs
$operatorArgs=@('--no-first-run','--no-default-browser-check','--force-device-scale-factor=1',('--user-data-dir="'+$profiles[1]+'"'),'--window-position=60,40','--window-size=1440,1050','--start-maximized','--app=http://127.0.0.1:8794/?filming=1')
Start-Process -FilePath $chrome -ArgumentList $operatorArgs
Write-Host ('Recording ready; extended monitor '+$bounds.Width+'x'+$bounds.Height+'; queue awaits human start.')

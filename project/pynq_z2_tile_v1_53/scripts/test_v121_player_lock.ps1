$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$playerId=[int](Get-Content -LiteralPath (Join-Path $root 'host/display.pid') -Raw)
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$playerId"
if(!$proc -or $proc.CommandLine -notlike '*pynq_z2_tile_v1_53*hdmi_display.ps1*'){throw 'Wrong player process'}
function State {
 for($n=0;$n -lt 20;$n++){
  try{return [System.IO.File]::ReadAllText((Join-Path $root 'host/player_status.json')) | ConvertFrom-Json}catch [System.IO.IOException]{Start-Sleep -Milliseconds 20}
 }
 throw 'Player telemetry unavailable'
}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"display","value":"real_video"}' | Out-Null
$deadline=(Get-Date).AddSeconds(10)
do{
 Start-Sleep -Milliseconds 100;$before=State
 if((Get-Date) -gt $deadline){throw 'Motion renderer did not start'}
}while($before.source -ne 'real_video' -or $before.rendered_frames -lt 5)
$file=$null
try{
 # Hold the exact command file exclusively, as observed in the real failure.
 $file=[System.IO.File]::Open((Join-Path $root 'host/display_command.txt'),[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
 Start-Sleep -Milliseconds 2200
 $during=State
 if(!(Get-Process -Id $playerId -ErrorAction SilentlyContinue)){throw 'Player exited during file conflict'}
 if($during.source -ne 'real_video' -or $during.rendered_frames -le $before.rendered_frames -or $during.utc -eq $before.utc){throw 'Player stopped rendering during command lock'}
}finally{if($file){$file.Dispose()}}
Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body '{"op":"display","value":"station_6"}' | Out-Null
$deadline=(Get-Date).AddSeconds(8)
do{
 Start-Sleep -Milliseconds 100;$after=State
 if((Get-Date) -gt $deadline){throw 'Player did not accept command after release'}
}while($after.source -ne 'station_6')
$result=[ordered]@{passed=$true;player_id=$playerId;exclusive_lock_ms=2200;rendered_frames_during_lock=($during.rendered_frames-$before.rendered_frames);before=$before;during=$during;after=$after;scope='Actual WPF player and exclusive Windows command-file lock; process survives, frames advance, next source command applies';player_sha256=(Get-FileHash -LiteralPath (Join-Path $root 'host/hdmi_display.ps1') -Algorithm SHA256).Hash.ToLowerInvariant()}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $root 'reports/v132/player_lock.json') -Encoding utf8
$result | ConvertTo-Json -Depth 6

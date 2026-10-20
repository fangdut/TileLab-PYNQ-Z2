param([string]$Python='python',[string]$Board='192.168.33.10',[switch]$Program,[string]$Xsdb='xsdb.bat',[switch]$Demo)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
if(Test-Path -LiteralPath (Join-Path $taskRoot 'project/host/reference_station.py')){$projectRoot=Join-Path $taskRoot 'project'}else{$projectRoot=Split-Path -Parent (Split-Path -Parent $taskRoot)}
$taskRelease=Join-Path $projectRoot 'releases/v167'
if(Test-Path -LiteralPath (Join-Path $projectRoot 'releases/v167_r2/DEPLOYMENT.json')){$taskRelease=Join-Path $projectRoot 'releases/v167_r2'}
if(!(Test-Path -LiteralPath (Join-Path $taskRelease 'DEPLOYMENT.json'))){throw 'Missing sealed V167 deployment bundle'}
if(Test-Path -LiteralPath (Join-Path $taskRoot 'PACKAGE_MANIFEST.json')){
 & $Python -B -X utf8 (Join-Path $projectRoot 'skill/verify_bundle.py') --root $taskRoot --manifest (Join-Path $taskRoot 'PACKAGE_MANIFEST.json')
 if($LASTEXITCODE -ne 0){throw 'Package integrity check failed'}
}
if($Program){
 $taskOutput=Join-Path $projectRoot ('build_local/program_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff'))
 & $Python -B -X utf8 (Join-Path $projectRoot 'scripts/reference_v167/program_release.py') --bundle $taskRelease --xsdb $Xsdb --address $Board --out $taskOutput
 if($LASTEXITCODE -ne 0){throw 'Programming failed; inspect the saved transcript'}
}
Write-Host 'TileLab reference station: http://127.0.0.1:8771'
Write-Host 'Keep this terminal running. Stop with Ctrl+C.'
if($Demo){
 $taskDemo=Join-Path $taskRoot 'demo_player'
 if(!(Test-Path -LiteralPath (Join-Path $taskDemo 'manifest.json'))){throw 'Use the packaged start.ps1 with its demo_player directory'}
 $taskDemo=(Resolve-Path -LiteralPath $taskDemo).Path
 $taskExisting=$false;$taskInstance=Join-Path $taskDemo 'host/player_instance.json'
 if(Test-Path -LiteralPath $taskInstance){
  $taskIdentity=Get-Content -Raw -LiteralPath $taskInstance | ConvertFrom-Json
  $taskProcess=Get-CimInstance Win32_Process -Filter ("ProcessId = "+[int]$taskIdentity.pid)
  if($taskProcess -and $taskProcess.CommandLine -like ('*'+$taskDemo+'*')){$taskExisting=$true}
 }
 if(!$taskExisting){Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $taskDemo 'host/hdmi_display.ps1'),'-Root',$taskDemo) -WindowStyle Hidden | Out-Null;Start-Sleep -Seconds 2}
 & $Python -B -X utf8 (Join-Path $projectRoot 'host/reference_demo_station.py') --ethernet $Board --port 8771 --player $taskDemo
}else{& $Python -B -X utf8 (Join-Path $projectRoot 'host/reference_station.py') --ethernet $Board --port 8771}
if($LASTEXITCODE -ne 0){throw 'Reference station stopped with an error'}

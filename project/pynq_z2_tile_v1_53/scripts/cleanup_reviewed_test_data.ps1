param([switch]$Apply)
# Default: audit only. -Apply permanently removes ONLY the frozen allowlist.
# The agent did NOT execute -Apply: automatic approval rejected bulk deletion.
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
if($root -ne 'D:\Vivado\pynq_z2_tile_v1_5'){throw 'Unexpected project root'}
$planPath=Join-Path $root 'reports\storage_20260926\cleanup_plan.json'
if((Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash -ne '1B60EDAD8E6A007EF1860A49B27F39E1CCA32144C50638479A51471F92FC1E06'){throw 'Cleanup plan changed; review it again'}
$plan=Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if($plan.root -ne $root -or $plan.files.Count -ne 8496 -or $plan.archive_ids_to_remove.Count -ne 3448){throw 'Unexpected allowlist'}
$review=Join-Path $root 'review_records'
$roof=Join-Path $root 'data\ceramics_mendeley\originals'
$approved=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($id in $plan.archive_ids_to_remove){
 if($id -notmatch '^(pl|tile)_[0-9]+_[0-9]+$'){throw 'Invalid archive ID'}
 [void]$approved.Add((Join-Path $review ($id+'.png')))
 [void]$approved.Add((Join-Path $review ($id+'_mask.png')))
}
function Assert-NoReparse([string]$target){
 $cursor=Get-Item -LiteralPath $target -Force
 while($null -ne $cursor){
  if($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Reparse point refused: $($cursor.FullName)"}
  $cursor=if($cursor -is [IO.DirectoryInfo]){$cursor.Parent}else{$cursor.Directory}
 }
}
$remaining=0L;$count=0
foreach($entry in $plan.files){
 $target=[IO.Path]::GetFullPath([string]$entry.path)
 if($entry.category -eq 'repeat_archive'){
  if(!$approved.Contains($target)){throw "Unexpected archive file: $target"}
 }elseif($entry.category -eq 'roof_original'){
  if(!$target.StartsWith($roof+'\',[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($target) -notin @('.jpg','.jpeg','.png')){throw "Unexpected dataset file: $target"}
 }else{throw 'Unknown cleanup category'}
 if(Test-Path -LiteralPath $target){
  Assert-NoReparse $target
  $item=Get-Item -LiteralPath $target -Force
  if($item.PSIsContainer -or $item.Length -ne [long]$entry.bytes){throw "File changed; stop for review: $target"}
  $remaining+=$item.Length;$count++
 }
}
$python=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if(!(Test-Path -LiteralPath $python)){throw 'Bundled Python not found'}
& $python -X utf8 (Join-Path $PSScriptRoot 'cleanup_metadata.py') audit
if($LASTEXITCODE -ne 0){throw 'Archive audit failed'}
Write-Output ("Reviewed remaining files: {0}; {1:N3} GiB. Retain 62 selected events plus all newer events." -f $count,($remaining/1GB))
if(!$Apply){Write-Output 'Audit only. Nothing deleted. Use -Apply yourself to execute the reviewed permanent cleanup.';return}
# Pause and disconnect the matching local service before changing its database.
$state=$null
try{$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state' -TimeoutSec 3}catch{}
if($state){
 if($state.revision -ne 'V1.5'){throw 'Another workstation occupies port 8770'}
 foreach($body in @('{"op":"display","value":"station_6"}','{"op":"pause"}')){
  Invoke-RestMethod 'http://127.0.0.1:8770/api/action' -Method Post -ContentType 'application/json' -Body $body | Out-Null
 }
 $deadline=(Get-Date).AddSeconds(15)
 do{
  Start-Sleep -Milliseconds 200
  $state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
  if((Get-Date) -gt $deadline){throw 'Receiver did not become idle'}
 }while($state.busy)
 $serviceId=[int](Get-Content -LiteralPath (Join-Path $root 'host\workstation.pid') -Raw)
 $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$serviceId"
 if(!$proc -or $proc.CommandLine -notlike '*pynq_z2_tile_v1_5*workstation.py*'){throw 'Service identity mismatch'}
 Stop-Process -Id $serviceId
 Wait-Process -Id $serviceId -ErrorAction SilentlyContinue
}
# Backs up metadata, then prunes ONLY unchanged unreviewed rows. Image deletion
# stays entirely in PowerShell, using validated absolute literal file paths.
& $python -X utf8 (Join-Path $PSScriptRoot 'cleanup_metadata.py') prepare
if($LASTEXITCODE -ne 0){throw 'Database preparation failed; no image deletion attempted'}
$released=0L;$removed=0
foreach($entry in $plan.files){
 $target=[IO.Path]::GetFullPath([string]$entry.path)
 if(Test-Path -LiteralPath $target){
  Assert-NoReparse $target
  $item=Get-Item -LiteralPath $target -Force
  if($item.PSIsContainer -or $item.Length -ne [long]$entry.bytes){throw "File changed during cleanup: $target"}
  Remove-Item -LiteralPath $target -ErrorAction Stop
  $released+=[long]$entry.bytes;$removed++
 }
}
$result=[ordered]@{completed_at=(Get-Date).ToString('s');deleted_files=$removed;released_bytes=$released;metadata_backup='cleanup_metadata_backup.sqlite3';images_are_not_backed_up=$true}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'reports\storage_20260926\cleanup_result.json') -Encoding utf8
Set-Content -LiteralPath (Join-Path $root 'host\storage_policy.json') -Value '{"mode":"preview","max_archive_mib":1024}' -Encoding utf8
Set-Content -LiteralPath (Join-Path $root 'data\ceramics_mendeley\ORIGINALS_REMOVED.txt') -Value 'Bulk originals removed by the reviewed cleanup. Historical metrics, metadata, provenance and download scripts remain; original files must be downloaded again for a full rerun.' -Encoding utf8
& (Join-Path $root 'host\start_station.ps1') -NoBrowser
Write-Output ("Cleanup completed: {0} files, {1:N3} GiB released. Service restarted in preview-only mode." -f $removed,($released/1GB))

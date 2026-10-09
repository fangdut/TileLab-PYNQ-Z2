$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
$source=Join-Path $root 'reports\v126'
$trial=Join-Path $root 'reports\v126_nocopy_trial'
$archive=Join-Path $root 'review_records'
$archiveTarget=Join-Path $trial 'workstation_archive'
# All recursive moves are explicitly contained within this single project.
foreach($candidate in @($source,$trial,$archive,$archiveTarget)){
 $absolute=[IO.Path]::GetFullPath($candidate)
 if(!$absolute.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Move target outside project'}
}
if(Test-Path -LiteralPath $trial){throw 'Trial preservation target already exists'}
$state=Invoke-RestMethod 'http://127.0.0.1:8770/api/state'
if($state.revision -ne 'V1.26' -or $state.busy -or $state.enabled -or $state.pending_operation){throw 'Receiver not safely paused'}
$taskId=[int](Get-Content -LiteralPath (Join-Path $root 'host\workstation.pid') -Raw)
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
if(!$proc -or $proc.CommandLine -notlike '*pynq_z2_tile_v1_53*workstation.py*'){throw 'Service process mismatch'}
Stop-Process -Id $taskId
Wait-Process -Id $taskId -ErrorAction SilentlyContinue
Move-Item -LiteralPath $source -Destination $trial
if(Test-Path -LiteralPath $archive){Move-Item -LiteralPath $archive -Destination $archiveTarget}
New-Item -ItemType Directory -Path $source | Out-Null
foreach($name in @('host_tests.log','prepare_project.log','prepare_project.jou','vitis_build.log','health_native.json','dma_recovery_native.json','native_packed','health_native','recovery_native')){
 Copy-Item -LiteralPath (Join-Path $trial $name) -Destination (Join-Path $source $name) -Recurse
}
$saved=Join-Path $trial 'firmware_snapshot'
New-Item -ItemType Directory -Path $saved | Out-Null
foreach($name in @('network.c','packed_stream.h')){
 Copy-Item -LiteralPath (Join-Path $root ('pynq_z2_tile_v1_53.sdk\ethernet_sources\'+$name)) -Destination $saved
}
Copy-Item -LiteralPath (Join-Path $root 'pynq_z2_tile_v1_53.sdk\hdmi_ethernet\build\hdmi_ethernet.elf') -Destination $saved
Copy-Item -LiteralPath (Join-Path $root 'reports\programmed_v132.json') -Destination $saved
Copy-Item -LiteralPath (Join-Path $root 'scripts\test_packed_stream_native.py') -Destination $saved
& (Join-Path $root 'host\start_station.ps1') -NoBrowser
Write-Output 'Preserved trial firmware, counterexample, reports and archive; fresh receiver remains paused.'

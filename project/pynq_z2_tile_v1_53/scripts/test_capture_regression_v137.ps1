$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if((Split-Path $projectRoot -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'V1.37 regression root required'}
$output=Join-Path $projectRoot 'reports/v137/capture_regression'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$python='C:/Users/Fang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$paths=@('rtl/frame_capture_sg.v','rtl/product_tracker.v','sim/frame_capture_v114_reference.v',
 'sim/tb_capture_crc.sv','sim/tb_capture_equivalence.sv','sim/tb_capture_sg.sv','sim/tb_capture_random_equivalence.sv',
 'scripts/test_capture_crc.tcl','scripts/test_capture_equivalence.tcl','scripts/test_capture_sg.tcl','scripts/test_capture_random_equivalence.tcl',
 'scripts/check_crc_sim.py','scripts/product_gate_no_wave.tcl','scripts/test_capture_regression_v137.ps1','scripts/inject_descriptor_fault.tcl')
$before=[ordered]@{}
foreach($path in $paths){$before[$path]=(Get-FileHash -LiteralPath (Join-Path $projectRoot $path) -Algorithm SHA256).Hash.ToLowerInvariant()}
$jobs=@(
 @{Name='crc';Script='test_capture_crc.tcl';Dir='crc_sim/crc_test.sim/sim_1/behav/xsim';Marker='PASS continuous SG';CRC=$true},
 @{Name='equivalence';Script='test_capture_equivalence.tcl';Dir='equivalence_sim/equivalence_test.sim/sim_1/behav/xsim';Marker='PASS continuous SG';CRC=$true},
 @{Name='sg';Script='test_capture_sg.tcl';Dir='sg_sim/sg_test.sim/sim_1/behav/xsim';Marker='PASS continuous SG';CRC=$false},
 @{Name='random_equivalence';Script='test_capture_random_equivalence.tcl';Dir='random_equivalence_sim/random_equiv.sim/sim_1/behav/xsim';Marker='PASS randomized';CRC=$false}
)
$cases=@();$watch=[Diagnostics.Stopwatch]::StartNew()
Push-Location $output
try {
 foreach($job in $jobs){
  & D:/2025.2/Vivado/bin/vivado.bat -mode batch -source (Join-Path $projectRoot ('scripts/'+$job.Script)) -log (Join-Path $output ($job.Name+'.log')) -journal (Join-Path $output ($job.Name+'.jou')) -notrace
  if($LASTEXITCODE -ne 0){throw ('Vivado regression failed: '+$job.Name)}
  $simdir=Join-Path $projectRoot ('reports/v137/'+$job.Dir)
  $logPath=Join-Path $simdir 'simulate.log';$log=Get-Content -LiteralPath $logPath -Raw
  if($log -match 'Fatal:' -or -not $log.Contains($job.Marker)){throw ('Simulation marker failed: '+$job.Name)}
  $crcProof=$null
  if($job.CRC){
   $crcProof=Join-Path $output ($job.Name+'_crc_summary.json')
   & $python -B -X utf8 (Join-Path $projectRoot 'scripts/check_crc_sim.py') (Join-Path $simdir 'crc_packets.hex') $crcProof
   if($LASTEXITCODE -ne 0){throw ('Independent Python CRC check failed: '+$job.Name)}
  }
  $wdb=@(Get-ChildItem -LiteralPath $simdir -Filter '*.wdb' | Select-Object Name,Length)
  if(@($wdb | Where-Object {$_.Length -gt 1048576}).Count){throw 'Unexpected large waveform generated'}
  $metrics=@($log -split "`n" | Where-Object {$_ -match 'EQUIVALENT_CYCLES=|RANDOM_EQ '})
  $cases+=[ordered]@{name=$job.Name;passed=$true;simulation_log=$logPath;independent_crc_report=$crcProof;metrics=$metrics;waveform_files=$wdb}
 }
} finally {Pop-Location;$watch.Stop()}
foreach($path in $paths){if((Get-FileHash -LiteralPath (Join-Path $projectRoot $path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $before[$path]){throw "Source changed while regression ran: $path"}}
$summary=[ordered]@{passed=$true;revision='V1.37';scope='Default cfg[26]=0 capture regressions, legacy reference retargeted only to descriptor ABI 0x54465337';production_rtl_sha256=$before['rtl/frame_capture_sg.v'];source_sha256=$before;run_seconds=[Math]::Round($watch.Elapsed.TotalSeconds,3);cases=$cases;hardware_executed=$false;legacy_baseline_experiment_modified=$false}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'summary.json') -Encoding utf8
$summary | ConvertTo-Json -Depth 8

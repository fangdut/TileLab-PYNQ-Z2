$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if ((Split-Path $projectRoot -Leaf) -ne 'pynq_z2_tile_v1_53') {throw 'V1.42 validation root required'}
$output=Join-Path $projectRoot 'reports/v142/product_gate_validation'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$paths=@('rtl/frame_capture_sg.v','rtl/product_tracker.v','sim/tb_product_low_gate.sv','scripts/test_product_low_gate.tcl','scripts/product_gate_no_wave.tcl','scripts/test_product_low_gate.ps1')
$before=[ordered]@{}
foreach($path in $paths){$before[$path]=(Get-FileHash -LiteralPath (Join-Path $projectRoot $path) -Algorithm SHA256).Hash.ToLowerInvariant()}
$watch=[Diagnostics.Stopwatch]::StartNew()
Push-Location $output
try {
 & D:/2025.2/Vivado/bin/vivado.bat -mode batch -source (Join-Path $projectRoot 'scripts/test_product_low_gate.tcl') -log (Join-Path $output 'vivado.log') -journal (Join-Path $output 'vivado.jou') -notrace
 if($LASTEXITCODE -ne 0){throw 'Vivado product low-gate simulation failed'}
} finally {Pop-Location;$watch.Stop()}
foreach($path in $paths){if((Get-FileHash -LiteralPath (Join-Path $projectRoot $path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $before[$path]){throw "Source changed while validation ran: $path"}}
$frames=@(Import-Csv -LiteralPath (Join-Path $output 'frames.csv'))
if($frames.Count -ne 57){throw 'Expected 57 module-level input frames'}
$names=@('default_dark_unchanged','default_dip_unchanged','low_dark_one_product','low_dip_one_product','inclusive_luma_boundaries','frame_config_lock')
$expectedStarts=@(0,2,1,1,2,1);$expectedUpdates=@(0,4,4,4,2,1)
$cases=@()
foreach($caseId in 1..6){
 $selected=@($frames | Where-Object {[int]$_.case -eq $caseId})
 $startCount=@($selected | Where-Object {([int]$_.product_flags -band 2) -ne 0}).Count
 $endCount=@($selected | Where-Object {([int]$_.product_flags -band 4) -ne 0}).Count
 $updates=@($selected | Where-Object {([int]$_.product_flags -band 8) -ne 0}).Count
 $cases+= [ordered]@{case_id=$caseId;name=$names[$caseId-1];stimulus_frames=$selected.Count;product_starts=$startCount;product_ends=$endCount;best_updates=$updates;passed=$startCount -eq $expectedStarts[$caseId-1] -and $endCount -eq $expectedStarts[$caseId-1] -and $updates -eq $expectedUpdates[$caseId-1]}
}
$passed=@($cases | Where-Object {-not $_.passed}).Count -eq 0
$summary=[ordered]@{passed=$passed;revision='V1.42';scope='Production frame_capture_sg/product_tracker module simulation with synthetic RGB raster and injected qualified mask/regions';not_validated=@('crack detector accuracy','real photographs','HDMI timing','Vitis runtime','board behavior');run_seconds=[Math]::Round($watch.Elapsed.TotalSeconds,3);source_sha256=$before;frames_checked=57;descriptor_crc_checks=57;descriptor_magic='0x54465337';default_gate_threshold=320;low_gate_threshold=160;cases=$cases;frames='reports/v142/product_gate_validation/frames.csv';simulator_log='reports/v142/product_gate_validation/simulate.log'}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'summary.json') -Encoding utf8
$summary | ConvertTo-Json -Depth 8
if(-not $passed){throw 'Product low-gate validation summary failed'}

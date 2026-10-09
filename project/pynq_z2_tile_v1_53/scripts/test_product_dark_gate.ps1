$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if ((Split-Path $projectRoot -Leaf) -ne 'pynq_z2_tile_v1_53') {throw 'V1.37 experiment root required'}
$output=Join-Path $projectRoot 'reports/v137/product_gate_experiment'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$paths=@('rtl/frame_capture_sg.v','rtl/product_tracker.v','sim/tb_product_dark_gate.sv','scripts/test_product_dark_gate.tcl')
$before=[ordered]@{}
foreach($path in $paths){$before[$path]=(Get-FileHash -LiteralPath (Join-Path $projectRoot $path) -Algorithm SHA256).Hash.ToLowerInvariant()}
$watch=[Diagnostics.Stopwatch]::StartNew()
Push-Location $output
try {
 & D:/2025.2/Vivado/bin/vivado.bat -mode batch -source (Join-Path $projectRoot 'scripts/test_product_dark_gate.tcl') -log (Join-Path $output 'vivado.log') -journal (Join-Path $output 'vivado.jou') -notrace
 if($LASTEXITCODE -ne 0){throw 'Vivado product gate simulation failed'}
} finally {Pop-Location;$watch.Stop()}
foreach($path in $paths){if((Get-FileHash -LiteralPath (Join-Path $projectRoot $path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $before[$path]){throw "Source changed while experiment ran: $path"}}
$frames=@(Import-Csv -LiteralPath (Join-Path $output 'frames.csv'))
if($frames.Count -ne 20){throw 'Expected 20 module-level input frames'}
$cases=@()
foreach($caseId in @(1,2)){
 $selected=@($frames | Where-Object {[int]$_.case -eq $caseId})
 $startCount=@($selected | Where-Object {([int]$_.product_flags -band 2) -ne 0}).Count
 $endCount=@($selected | Where-Object {([int]$_.product_flags -band 4) -ne 0}).Count
 $updates=@($selected | Where-Object {([int]$_.product_flags -band 8) -ne 0}).Count
 $cases+= [ordered]@{case_id=$caseId;name=if($caseId -eq 1){'dark_surface_no_product'}else{'two_frame_brightness_dip_splits_one_product'};stimulus_frames=$selected.Count;injected_qualified_region_frames=@($selected | Where-Object {[int]$_.candidate_pixels -eq 1200}).Count;product_starts=$startCount;product_ends=$endCount;best_updates=$updates;expected_failure_reproduced=if($caseId -eq 1){$startCount -eq 0 -and $endCount -eq 0 -and $updates -eq 0}else{$startCount -eq 2 -and $endCount -eq 2 -and $updates -eq 4}}
}
$passed=@($cases | Where-Object {-not $_.expected_failure_reproduced}).Count -eq 0
$summary=[ordered]@{passed=$passed;meaning='Reproduction experiment passed: both current-product-tracking limitations reproduced, not product acceptance';revision='V1.37';scope='Module simulation of production frame_capture_sg.v and product_tracker.v with synthetic RGB raster and injected mask/region metadata';not_validated=@('crack detector accuracy','real photographs','HDMI timing','Vitis runtime','board behavior');production_rtl_modified=$false;run_seconds=[Math]::Round($watch.Elapsed.TotalSeconds,3);source_sha256=$before;cases=$cases;frames='reports/v137/product_gate_experiment/frames.csv';simulator_log='reports/v137/product_gate_experiment/simulate.log'}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'summary.json') -Encoding utf8
$summary | ConvertTo-Json -Depth 8
if(-not $passed){throw 'Expected failure assertions did not all pass'}

# Original pre-fix test_product_dark_gate.* and recorded proof are preserved.
# V1.37 production RTL now uses ABI 37. Use THIS entry point to replay the old
# ABI 36 baseline from sealed V1.36, never the old entry point against new RTL.
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if((Split-Path $projectRoot -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'V1.37 replay root required'}
$baselineRoot=Join-Path (Split-Path $projectRoot -Parent) 'pynq_z2_tile_v1_36'
$proof=Get-Content -LiteralPath (Join-Path $projectRoot 'reports/v137/product_gate_experiment/summary.json') -Raw | ConvertFrom-Json
if(-not $proof.passed){throw 'Original reproduction proof missing'}
$hashes=[ordered]@{}
foreach($relative in @('rtl/frame_capture_sg.v','rtl/product_tracker.v')){
 $actual=(Get-FileHash -LiteralPath (Join-Path $baselineRoot $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
 if($actual -ne $proof.source_sha256.$relative){throw "Sealed baseline does not match original experiment: $relative"}
 $hashes[$relative]=$actual
}
$tbHash=(Get-FileHash -LiteralPath (Join-Path $projectRoot 'sim/tb_product_dark_gate.sv') -Algorithm SHA256).Hash.ToLowerInvariant()
if($tbHash -ne $proof.source_sha256.'sim/tb_product_dark_gate.sv'){throw 'Original baseline testbench changed'}
$output=Join-Path $projectRoot 'reports/v137/product_gate_baseline_replay'
New-Item -ItemType Directory -Path $output -Force | Out-Null
Push-Location $output
try {
 & D:/2025.2/Vivado/bin/vivado.bat -mode batch -source (Join-Path $projectRoot 'scripts/replay_product_gate_baseline.tcl') -log (Join-Path $output 'vivado.log') -journal (Join-Path $output 'vivado.jou') -notrace
 if($LASTEXITCODE -ne 0){throw 'Baseline replay simulation failed'}
} finally {Pop-Location}
foreach($relative in $hashes.Keys){if((Get-FileHash -LiteralPath (Join-Path $baselineRoot $relative) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hashes[$relative]){throw "Sealed baseline changed during replay: $relative"}}
$frames=@(Import-Csv -LiteralPath (Join-Path $output 'frames.csv'))
if($frames.Count -ne 20){throw 'Incomplete baseline replay'}
$result=[ordered]@{passed=$true;meaning='Replay reproduces original limitations; not product acceptance';scope='Module-level synthetic RGB raster and injected qualified regions';read_only_source_root=$baselineRoot;source_sha256=$hashes;testbench_sha256=$tbHash;frames_checked=20;original_proof='reports/v137/product_gate_experiment/summary.json';output_root=$output}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $output 'summary.json') -Encoding utf8
$result | ConvertTo-Json -Depth 6

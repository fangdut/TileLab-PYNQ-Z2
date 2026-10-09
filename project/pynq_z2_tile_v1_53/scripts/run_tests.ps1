$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runTag = Get-Date -Format 'yyyyMMdd_HHmmss'
$simLog = Join-Path $projectRoot "reports/simulation_$runTag.log"
& 'D:/2025.2/Vivado/bin/vivado.bat' -mode batch -log $simLog -nojournal -source (Join-Path $PSScriptRoot 'simulate.tcl') -tclargs (Join-Path $projectRoot "reports/sim_$runTag")
if ($LASTEXITCODE -ne 0) {throw 'Vivado simulation command failed'}
$testText = Get-Content -LiteralPath $simLog -Raw
foreach ($marker in @('PASS AXIS:', 'PASS WINDOW:', 'PASS SOBEL:', 'PASS GAUSSIAN:', 'PASS PIPELINE V04:', 'PASS CDC:')) {
 if (!$testText.Contains($marker)) {throw "Missing self-check result: $marker"}
}
if ($testText -match '(?m)^(Fatal:|ERROR:)') {throw 'Simulation reported a failure'}
Write-Output 'All V0.4 RTL regression suites passed.'

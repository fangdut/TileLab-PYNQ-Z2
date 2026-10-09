$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$testOutput=Join-Path $projectRoot 'reports/v15/tracker_sim'
New-Item -ItemType Directory -Path $testOutput -Force | Out-Null
Push-Location $testOutput
try {
 & D:/2025.2/Vivado/bin/xvlog.bat --sv (Join-Path $projectRoot 'rtl/product_tracker.v') (Join-Path $projectRoot 'sim/tb_product_tracker_v15.sv')
 if($LASTEXITCODE -ne 0){throw 'xvlog failed'}
 & D:/2025.2/Vivado/bin/xelab.bat tb_product_tracker_v15 -s tracker_v15 --timescale 1ns/1ps
 if($LASTEXITCODE -ne 0){throw 'xelab failed'}
 & D:/2025.2/Vivado/bin/xsim.bat tracker_v15 -runall
 if($LASTEXITCODE -ne 0){throw 'xsim failed'}
 if(!(Select-String -Path xsim.log -Pattern 'PASS V15 product tracker' -Quiet)){throw 'Required PASS marker missing'}
} finally {Pop-Location}

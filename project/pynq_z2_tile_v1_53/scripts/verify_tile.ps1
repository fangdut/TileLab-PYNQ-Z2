param([string]$Python='python',[string]$Vivado='D:/2025.2/Vivado/bin/vivado.bat')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$tag=Get-Date -Format yyyyMMdd_HHmmss
$dest=Join-Path $root ('reports/verify_'+$tag)
New-Item -ItemType Directory -Path $dest | Out-Null
foreach($size in @(32,1280)){
 $height=if($size -eq 32){20}else{720}
 & $Python (Join-Path $PSScriptRoot 'detection_golden.py') $size $height tile
 if($LASTEXITCODE -ne 0){throw 'reference failed'}
 $extra=if($size -eq 1280){@('full')}else{@()}
 $log=Join-Path $dest ('sim_'+$size+'.log')
 & $Vivado -mode batch -log $log -nojournal -source (Join-Path $PSScriptRoot 'test_detection.tcl') -tclargs (Join-Path $dest ('sim_'+$size)) (Join-Path $root ('test_patterns/golden_'+$size)) @extra
 $text=Get-Content -LiteralPath $log -Raw
 if($LASTEXITCODE -ne 0 -or $text -match '(?m)^(ERROR:|Fatal:)' -or !$text.Contains('PASS DETECTION:') -or !$text.Contains('PASS FRAME CRC:')){throw 'RTL regression failed'}
}
& $Python (Join-Path $PSScriptRoot 'test_monitor_native.py')
if($LASTEXITCODE -ne 0){throw 'monitor test failed'}
& $Python (Join-Path $root 'host/test_review.py')
if($LASTEXITCODE -ne 0){throw 'review test failed'}
Write-Output ('PASS Tile offline verification: '+$dest)

param([string]$Python='python',[string]$Vivado='D:/2025.2/Vivado/bin/vivado.bat')
$ErrorActionPreference='Stop'
$root=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$tag=Get-Date -Format yyyyMMdd_HHmmss
$work=Join-Path $root ('reports/regression_'+$tag)
New-Item -ItemType Directory -Path $work | Out-Null
function RunCheck([string]$name,[string]$script,[string[]]$arguments,[string[]]$markers){
 $log=(Join-Path $work ($name+'.log')).Replace('\','/')
 $source=(Join-Path $PSScriptRoot $script).Replace('\','/')
 $arguments=@($arguments | ForEach-Object { $_.Replace('\','/') })
 Push-Location $work
 try { & $Vivado -mode batch -log $log -nojournal -source $source -tclargs @arguments }
 finally {Pop-Location}
 if($LASTEXITCODE -ne 0){throw "$name tool failure"}
 $text=Get-Content -LiteralPath $log -Raw
 if($text -match '(?m)^(ERROR:|Fatal:)'){throw "$name reported error"}
 foreach($marker in $markers){if(!$text.Contains($marker)){throw "$name missing $marker"}}
}
foreach($name in @('brightness','candidate','config','bbox')){
 $marker=switch($name){'brightness'{'PASS BRIGHTNESS UNIT:'} 'candidate'{'PASS CANDIDATE:'} 'config'{'PASS CONFIG:'} 'bbox'{'PASS BBOX:'}}
 RunCheck $name ('test_'+$name+'.tcl') @((Join-Path $work $name)) @($marker)
}
foreach($size in @(@(32,20),@(1280,720))){
 & $Python (Join-Path $PSScriptRoot 'detection_golden.py') $size[0] $size[1]
 if($LASTEXITCODE -ne 0){throw 'NumPy reference generation failed; install numpy for this Python'}
 $name='detection_'+$size[0]
 $arguments=@((Join-Path $work $name),(Join-Path $root ('test_patterns/golden_'+$size[0])))
 $markers=@('PASS DETECTION:','PASS INTEGRATED STATS:','PASS BRIGHTNESS INTEGRATED:','PASS FRAME CRC:')
 if($size[0] -eq 1280){$arguments+=@('full')}else{$markers+=@('PASS RESET:')}
 RunCheck $name 'test_detection.tcl' $arguments $markers
}
Write-Output ('PASS V0.9 regression; logs '+$work)

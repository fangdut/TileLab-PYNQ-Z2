param([Parameter(Mandatory=$true)][int]$BuildProcessId)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if((Split-Path $root -Leaf) -ne 'pynq_z2_tile_v1_53'){throw 'Wrong current root'}
$process=Get-CimInstance Win32_Process -Filter "ProcessId=$BuildProcessId"
if(!$process -or $process.Name -ne 'vivado.exe' -or $process.CommandLine -notlike '*pynq_z2_tile_v1_53/scripts/create_project.tcl*'){throw 'Expected live current-root full-build process'}
$build=Get-Process -Id $BuildProcessId
$end=(Get-Date).AddMinutes(90)
$watch=[ordered]@{process_id=$BuildProcessId;creation_date=$process.CreationDate;command=$process.CommandLine;observed_at=(Get-Date).ToUniversalTime().ToString('o')}
$watch | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'reports/v142/postbuild_wait_identity.json') -Encoding utf8
while(!$build.WaitForExit(30000)){if((Get-Date) -gt $end){throw 'Build observation deadline; no restart attempted'}}
$sdk=Join-Path $root 'pynq_z2_tile_v1_53.sdk'
$plan=Get-Content -LiteralPath (Join-Path $root 'ITERATION_PLAN.json') -Raw | ConvertFrom-Json
foreach($name in @('system.bit','system.xsa')){
 if((Get-FileHash -LiteralPath (Join-Path $sdk $name) -Algorithm SHA256).Hash.ToLowerInvariant() -eq $plan.inherited_hardware_sha256.$name){throw 'Full build did not export new hardware'}
}
$console=Get-Content -LiteralPath (Join-Path $root 'reports/v142/full_build_console.log') -Raw
if($console -match '(?m)^ERROR:'){throw 'Full build reported errors; inspect before proceeding'}
$python='C:/Users/Fang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
foreach($name in @('audit_reset_netlist','audit_max_delay')){
 & 'D:/2025.2/Vivado/bin/vivado.bat' -mode batch -source (Join-Path $PSScriptRoot ($name+'.tcl')) -log (Join-Path $root ('reports/v142/'+$name+'.log')) -journal (Join-Path $root ('reports/v142/'+$name+'.jou')) -notrace *> (Join-Path $root ('reports/v142/'+$name+'_console.log'))
 if($LASTEXITCODE -ne 0){throw ('Routed audit failed: '+$name)}
}
& $python -B -X utf8 (Join-Path $PSScriptRoot 'audit_v142_hardware.py') *> (Join-Path $root 'reports/v142/hardware_audit_console.log')
if($LASTEXITCODE -ne 0){throw 'Hardware audit did not pass'}
chcp 65001 > $null
& 'D:/2025.2/Vitis/bin/vitis.bat' -s (Join-Path $sdk 'build_ethernet.py') *> (Join-Path $root 'reports/v142/vitis_build_console.log')
if($LASTEXITCODE -ne 0){throw 'Vitis process failed'}
# The vendor launcher can exit0 even after Python errors; actual source/import
# and ELF checks are mandatory and are the authority for build acceptance.
& $python -B -X utf8 (Join-Path $PSScriptRoot 'audit_v142_firmware.py') *> (Join-Path $root 'reports/v142/firmware_audit_console.log')
if($LASTEXITCODE -ne 0){throw 'Firmware artifact audit failed'}
Write-Output 'Fresh routed hardware and paired Vitis firmware audits passed. No programming performed here.'

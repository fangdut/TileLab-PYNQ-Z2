param(
    [string]$Bundle = $PSScriptRoot,
    [switch]$NoBrowser,
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$bundleRoot = (Resolve-Path -LiteralPath $Bundle).Path
$deploy = Join-Path $bundleRoot 'project/host/stop_inspect_station/deploy_workstation.py'
$server = Join-Path $bundleRoot 'project/host/stop_inspect_station/server.py'
if (!(Test-Path -LiteralPath $deploy)) { throw 'Run from the extracted engineering bundle, or pass -Bundle.' }
$pythonPath = $env:TILELAB_PYTHON
if (!$pythonPath) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $pythonPath = $bundledPython }
    else { $pythonPath = (Get-Command python -ErrorAction Stop).Source }
}
& $pythonPath -X utf8 $deploy --bundle $bundleRoot --out (Join-Path $bundleRoot 'runtime/unused') --verify-only
if ($LASTEXITCODE -ne 0) { throw 'Bundle or deployment pairing verification failed.' }
if ($VerifyOnly) { return }
$url = 'http://127.0.0.1:8793/'
$closedBundle = Test-Path -LiteralPath (Join-Path $bundleRoot 'profiles/index.json')
$expectedBuild = Get-Content -Raw -LiteralPath (Join-Path $bundleRoot 'verified_hdmi/software/BUILD_RESULT.json') | ConvertFrom-Json
$listener = @(Get-NetTCPConnection -LocalPort 8793 -State Listen -ErrorAction SilentlyContinue)
if ($listener.Count -gt 0) {
    $existing = Invoke-RestMethod -Uri ($url + 'api/state') -TimeoutSec 5
    $modelMatches = $existing.connection.model_crc32 -eq 2781797194
    if ($closedBundle) {
        $allowed = @($expectedBuild.allowed_profiles | ForEach-Object model_crc32)
        $modelMatches = $allowed -contains $existing.connection.model_crc32
        if (!$existing.closed_loop.enabled -or $existing.deployment.elf_sha256 -ne $expectedBuild.elf_sha256) {
            throw 'A different station version owns port8793. Finish its current item and stop it before starting this bundle.'
        }
    }
    if ($existing.connection.pl_identity -ne 385875969 -or !$modelMatches) {
        throw 'Port 8793 is occupied without the expected TileLab configuration. Close that service before deployment.'
    }
    Write-Host ('Existing TileLab station kept running: ' + $url)
    if (!$NoBrowser) { Start-Process $url }
    return
}
& $pythonPath -c 'import numpy; from PIL import Image'
if ($LASTEXITCODE -ne 0) { throw 'Install requirements.txt into TILELAB_PYTHON first.' }
$runtimeParent = Join-Path $bundleRoot 'runtime'
New-Item -ItemType Directory -Path $runtimeParent -Force | Out-Null
$runName = 'run_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8)
$runRoot = Join-Path $runtimeParent $runName
& $pythonPath -X utf8 $deploy --bundle $bundleRoot --out $runRoot
if ($LASTEXITCODE -ne 0) { throw ('Volatile deployment failed. See ' + $runRoot) }
$config = Join-Path $runRoot 'station_config.json'
$arguments = '-X utf8 "{0}" --config "{1}"' -f $server, $config
$service = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $bundleRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runRoot 'server_stdout.log') -RedirectStandardError (Join-Path $runRoot 'server_stderr.log')
$service.Id | Set-Content -LiteralPath (Join-Path $runRoot 'server_pid.txt')
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $state = Invoke-RestMethod -Uri ($url + 'api/state') -TimeoutSec 2
        if ($state.connection.pl_identity -eq 385875969 -and $state.connection.model_crc32 -eq 2781797194 -and (!$closedBundle -or ($state.closed_loop.enabled -and $state.deployment.elf_sha256 -eq $expectedBuild.elf_sha256))) { $ready = $true; break }
    } catch { }
    $service.Refresh()
    if ($service.HasExited) { break }
    Start-Sleep -Milliseconds 500
}
if (!$ready) { throw ('Station did not become ready. Read server logs in ' + $runRoot) }
Write-Host ('TileLab station ready: ' + $url)
Write-Host ('Runtime evidence: ' + $runRoot)
if (!$NoBrowser) { Start-Process $url }

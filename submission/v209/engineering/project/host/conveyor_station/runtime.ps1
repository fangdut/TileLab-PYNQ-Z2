# SPDX-License-Identifier: MIT
function Resolve-TileLabPython {
    param([string]$Preferred)
    if ($Preferred) {
        if (!(Test-Path -LiteralPath $Preferred -PathType Leaf)) { throw 'Specified Python executable does not exist.' }
        return (Resolve-Path -LiteralPath $Preferred).Path
    }
    if ($env:TILELAB_PYTHON) { return Resolve-TileLabPython -Preferred $env:TILELAB_PYTHON }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $localRuntime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $localRuntime) { return $localRuntime }
    throw 'Set TILELAB_PYTHON to a Python executable, or add Python to PATH.'
}

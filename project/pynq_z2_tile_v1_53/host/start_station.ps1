param([string]$Ethernet='169.254.200.10',[string]$Python='python',[int]$Port=8770,[switch]$NoBrowser)
& (Join-Path $PSScriptRoot 'start_single_tile.ps1') @PSBoundParameters
exit $LASTEXITCODE

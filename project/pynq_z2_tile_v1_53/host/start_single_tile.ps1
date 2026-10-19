param([string]$Ethernet='169.254.200.10',[string]$Python='python',[int]$Port=8770,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$station=Join-Path $PSScriptRoot 'single_tile_station.py'
$argsList=@('-B','-X','utf8',$station,'--ethernet',$Ethernet,'--port',$Port)
if(!$NoBrowser){$argsList+='--open'}
& $Python @argsList
exit $LASTEXITCODE

param([string]$Port='COM20',[int]$Seconds=12,[string]$Output='')
$ErrorActionPreference='Stop'
if(!$Output){$Output=Join-Path (Split-Path $PSScriptRoot -Parent) 'reports/board_uart.log'}
if([System.IO.Ports.SerialPort]::GetPortNames() -notcontains $Port){throw "Port $Port missing; available: $([System.IO.Ports.SerialPort]::GetPortNames() -join ', ')"}
$serial=[System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$text=''
try{
 $serial.Open()
 for($i=0;$i -lt $Seconds;$i++){Start-Sleep -Seconds 1;$chunk=$serial.ReadExisting();$text+=$chunk;Write-Output $chunk}
}finally{if($serial.IsOpen){$serial.Close()};$serial.Dispose()}
$text | Set-Content -LiteralPath $Output -Encoding utf8

param([string]$Port='COM20',[int]$Seconds=90,[string]$Output)
$ErrorActionPreference='Stop'
$serial=[System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
try{
 $serial.Open();$until=[DateTime]::UtcNow.AddSeconds($Seconds)
 while([DateTime]::UtcNow -lt $until){
  $chunk=$serial.ReadExisting()
  if($chunk){[System.IO.File]::AppendAllText($Output,$chunk);Write-Output $chunk}
  Start-Sleep -Milliseconds 250
 }
}finally{if($serial.IsOpen){$serial.Close()};$serial.Dispose()}

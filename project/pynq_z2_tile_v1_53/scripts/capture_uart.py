"""Use the Windows serial API without an optional pyserial dependency."""
from pathlib import Path
import subprocess,argparse
r=Path(__file__).resolve().parents[1];ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=int,default=90);ap.add_argument('--port',default='COM20');a=ap.parse_args()
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(r/'scripts/read_uart.ps1'),'-Port',a.port,'-Seconds',str(a.seconds),'-Output',str(r/'reports/v14/uart.log')],check=True)

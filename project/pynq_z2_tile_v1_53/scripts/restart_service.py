"""Reload own paused workstation code without stopping HDMI player or board."""
from pathlib import Path
import sys,subprocess,time,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from board_v18_continuous import action,state,wait_idle
wait_idle();s=state();version='V1.'+R.name.rsplit('_',1)[1]
assert s['revision']==version and not s['pending_operation'] and not s['busy']
p=R/'reports/restart_own_service.ps1'
p.write_text(f'''$ErrorActionPreference='Stop'
$taskId=[int](Get-Content -LiteralPath '{R.as_posix()}/host/workstation.pid' -Raw)
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
if(!$proc -or $proc.CommandLine -notlike '*{R.name}*workstation.py*'){{throw 'Project service identity mismatch'}}
Stop-Process -Id $taskId
''',encoding='utf-8-sig')
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(p)],check=True,creationflags=0x08000000)
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'host/start_station.ps1'),'-NoBrowser'],check=True,creationflags=0x08000000)
end=time.monotonic()+10
while True:
 try:s=state();break
 except OSError:
  if time.monotonic()>end:raise
  time.sleep(.2)
assert s['revision']==version and not s['enabled'] and not s['pending_operation']
print('Own service restarted, receiver remains paused')

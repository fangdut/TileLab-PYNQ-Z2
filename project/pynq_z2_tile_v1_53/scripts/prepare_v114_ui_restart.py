"""Create one real saved/pending event, restart only this project's service."""
from pathlib import Path
import sys,time,json,subprocess,hashlib,shutil,urllib.request
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
from workstation import Records
from board_v18_continuous import action,state,wait_idle
O=R/'reports/v132';proof=O/'ui_restart_before.json'
assert not proof.exists(),'UI restart proof already prepared'
wait_idle();action('display',value='station_6');time.sleep(.5)
c=EventTCP('169.254.200.10')
while c.stats()['depth']:
    _,d,m,_=c.capture(89);c.ack(m[2],d[0])
c.close();action('display',value='real_000');time.sleep(.5)
script=O/'stop_own_service.ps1'
script.write_text("""$ErrorActionPreference='Stop'
$taskId=[int](Get-Content -LiteralPath 'D:/Vivado/pynq_z2_tile_v1_53/host/workstation.pid' -Raw)
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$taskId"
if(!$proc -or $proc.CommandLine -notlike '*pynq_z2_tile_v1_53*workstation.py*'){throw 'Project service identity mismatch'}
Stop-Process -Id $taskId
""",encoding='utf-8-sig')
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)],check=True,creationflags=0x08000000)
for name in ('workstation_service.log','workstation_service_error.log'):
    p=R/'reports'/name
    if p.exists():shutil.copy2(p,O/('before_restart_'+name))
result=subprocess.run([sys.executable,'-X','utf8',str(R/'scripts/board_v114_restart.py'),'--child','before_ack',str(R)],capture_output=True,text=True,timeout=25,creationflags=0x08000000)
(O/'ui_crash_child.log').write_text(result.stdout+result.stderr,encoding='utf-8')
assert result.returncode==73,result.stderr
records=Records(R);pending=records.confirmations.pending();assert pending and len(records.all())==1
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'review_records').glob('*.png')};records.db.close()
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'host/start_station.ps1'),'-NoBrowser'],check=True,creationflags=0x08000000)
end=time.monotonic()+10
while True:
    try:s=state();break
    except OSError:
        if time.monotonic()>end:raise
        time.sleep(.2)
assert s['pending_confirmation'] and not s['enabled'] and s['captures']==0 and not s['error']
proof.write_text(json.dumps(dict(passed=True,pending=pending,hashes=hashes,state=s),ensure_ascii=False,indent=2),encoding='utf-8')
print('Real saved confirmation restored in restarted V1.14 UI; ready for Resume Pending button test',flush=True)

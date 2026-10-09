"""Load finalized recipe wording by restarting only this verified project service."""
from pathlib import Path
import json,time,subprocess,shutil,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from board_v18_continuous import action,state,wait_idle
wait_idle();s=state();assert s['revision']=='V1.24' and not s['pending_operation'] and not s['error']
for name in ('workstation_service.log','workstation_service_error.log'):
 p=R/'reports'/name
 if p.exists():shutil.copy2(p,R/'reports/v132'/('before_publish_'+name))
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'reports/v132/stop_own_service.ps1')],check=True,creationflags=0x08000000)
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'host/start_station.ps1'),'-NoBrowser'],check=True,creationflags=0x08000000)
end=time.monotonic()+10
while True:
 try:s=state();break
 except OSError:
  if time.monotonic()>end:raise
  time.sleep(.2)
assert s['revision']=='V1.24' and not s['pending_operation']
action('storage',mode='preview',max_archive_mib=1024);action('recipe',value='mvtec_hdmi_weak_v124');action('display',value='real_video');action('start')
end=time.monotonic()+10
while True:
 s=state()
 if s['frame'] and s['capture_health']['ready'] and s['stimulus_status']['ready']:break
 if time.monotonic()>end:raise TimeoutError('Published service did not become ready')
 time.sleep(.15)
assert not s['error'] and s['storage']['mode']=='preview' and s['board_stats']['version']==0x11800
(R/'reports/v132/published_service.json').write_text(json.dumps(dict(passed=True,state=s),ensure_ascii=False,indent=2),encoding='utf-8')
print('Published service loaded final recipe, resumed quad preview without new archives')

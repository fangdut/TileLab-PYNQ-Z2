"""Read-only startup gate after JTAG: require matching boot and valid frames."""
from pathlib import Path
import time,json,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
p=json.loads((R/'reports/programmed_v153.json').read_text());start=time.monotonic();attempts=[]
while True:
 c=EventTCP(p.get('configured_address') or '169.254.200.10')
 try:
  s=c.stats();assert s['version']==0x12b00 and s['boot_id']==p['boot_id'],'Unexpected board identity'
  if s['capture_health']['ready']:
   result=dict(passed=True,seconds=time.monotonic()-start,transient_attempts=attempts,state=s)
   (R/'reports/v153/boot_readiness.json').write_text(json.dumps(result,indent=2));print('Matching board boot and complete HDMI frames ready',flush=True);break
  attempts.append(dict(at=time.monotonic()-start,health=s['capture_health']))
 except OSError as e:attempts.append(dict(at=time.monotonic()-start,error=str(e)))
 finally:c.close()
 if time.monotonic()-start>40:raise TimeoutError('Board did not become ready: '+json.dumps(attempts))
 time.sleep(.25)

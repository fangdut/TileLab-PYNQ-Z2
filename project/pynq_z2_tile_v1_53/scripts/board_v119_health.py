"""Real input-gate / S2MM halt faults. Never claims physical HDMI unplug.
The main service displays the health state; a bounded checkpoint permits UI QA.
Any failure or final completion reloads clean BIT+ELF.
"""
from pathlib import Path
import json,sys,time,subprocess,hashlib,shutil
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v132/health_board';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
from workstation import Bridge
from board_v18_continuous import action,state,wait_idle
from board_v119_background import source_ready,until

def execute(cmd,log):
 with log.open('wb') as f:p=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=150,creationflags=0x08000000)
 p.check_returncode()
def ready(path):
 started=time.monotonic();rows=[]
 while time.monotonic()-started<30:
  c=EventTCP('169.254.200.10')
  try:
   s=c.stats();assert s['version']==0x11300
   rows.append(dict(seconds=time.monotonic()-started,stats=s));path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
   if s['capture_health']['ready'] and s['captured']>=3:return s
  except OSError:pass
  finally:c.close()
  time.sleep(.2)
 raise TimeoutError('No healthy complete image stream')
def control(operation,boot,event,out):
 execute(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/control_capture_health.tcl'),str(boot),operation,str(event),str(out/(operation+'.json'))],out/(operation+'.log'))
 return json.loads((out/(operation+'.json')).read_text())
def checkpoint(name,out):
 (O/'stage.json').write_text(json.dumps(dict(stage=name,run_directory=str(out)),indent=2))
 print('UI_CHECKPOINT '+name,flush=True)
 end=time.monotonic()+60
 while time.monotonic()<end and not (out/(name+'.continue')).exists():time.sleep(.1)

def case(name,out):
 wait_idle();action('display',value='station_6');until(lambda:source_ready('station_6'));time.sleep(.5)
 c=EventTCP('169.254.200.10')
 try:
  while c.stats()['depth']:
   _,d,m,_=c.capture(89);c.ack(m[2],d[0])
  action('display',value='real_000');until(lambda:source_ready('real_000'));time.sleep(.5)
  c.compression=False;raw,d,m,ms=c.capture(89);before=c.stats()
  assert before['depth']==1 and before['capture_health']['ready']
  f,png,mask=Bridge.decode_event(raw,d,m,ms)
  (out/'retained.png').write_bytes(png);(out/'retained_mask.png').write_bytes(mask)
  identity=dict(event=d[0],frame=d[2],boot=m[2],descriptor=d,pixel_sha256=hashlib.sha256(raw).hexdigest())
  c.close();injection=control(name,m[2],d[0],out)
  after_fault=c.stats();h=after_fault['capture_health']
  assert h['state']==('STALLED' if name=='pause_input' else 'HALTED'),after_fault
  assert after_fault['boot_id']==m[2] and after_fault['head']==m[4] and after_fault['depth']==1
  for compressed in (False,True):
   c.compression=compressed;again,dd,mm,_=c.capture(89)
   assert again==raw and dd==d and mm[2]==m[2]
   assert all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
  c.close();pre=state();action('storage',mode='preview',max_archive_mib=1024);action('start')
  until(lambda:(state().get('board_stats') or {}).get('head')==d[0] and not state().get('pending_operation'),seconds=10)
  start=state();observations=[];t=time.monotonic()
  while time.monotonic()-t<3:
   s=state();assert s['enabled'] and s['board_connected'] and not s['error']
   assert s['capture_health']['state']==h['state'] and not s['capture_health']['ready']
   assert s['captures']==start['captures'] and s['board_stats']['captured']==after_fault['captured']
   assert s['board_stats']['request']==after_fault['request']
   observations.append(s);time.sleep(.15)
  end=state();delta=end['transport_totals']['received_bytes']-start['transport_totals']['received_bytes']
  duration=time.monotonic()-t;assert 0<delta<20000 and delta%276==0
  assert end['captures']==pre['captures']+1
  result=dict(passed=True,operation=name,identity=identity,before=before,after_fault=after_fault,injection=injection,retained_pixels_equal=True,
              retained_crc_checks=True,host_drained_exactly_one=True,waiting_seconds=duration,status_bytes=delta,status_bytes_per_second=delta/duration,
              no_new_capture_requests=True,observations=observations,final_state=end)
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  checkpoint(name,out)
  wait_idle()
  if name=='pause_input':
   result['resume_control']=control('resume_input',m[2],d[0],out)
   result['after_resume']=ready(out/'resume_ready.json')
   assert result['after_resume']['boot_id']==m[2] and result['after_resume']['head']==d[0]
   raw2,d2,m2,_=c.capture(89)
   assert d2[2]>d[2] and m2[2]==m[2] and all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   result['fresh_frame']=dict(frame=d2[2],event=d2[0],crc=dict(c.last_timing));c.ack(m2[2],d2[0])
   # Stop/resume naturally loses samples; retain counters instead of resetting them.
   result['post_resume_stats']=c.stats()
   (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  return result
 finally:c.close()

def run():
 out=O/str(time.time_ns());out.mkdir();cases=[]
 try:
  ready(out/'initial_ready.json')
  for name in ('pause_input','halt_dma'):
   part=out/name;part.mkdir();cases.append(case(name,part))
 except Exception as e:
  (out/'failure.json').write_text(json.dumps(dict(error=str(e),cases=cases,state=state()),ensure_ascii=False,indent=2),encoding='utf-8');raise
 finally:
  wait_idle();action('display',value='station_6');until(lambda:source_ready('station_6'));time.sleep(.5)
  execute(['cmd.exe','/d','/c',str(W/'program_ethernet.bat')],out/'restore.log')
  restored=ready(out/'clean_ready.json')
  action('display',value='real_video');action('start')
 result=dict(passed=True,cases=cases,clean_restart=restored,run_directory=str(out),scope='Actual PL input gate and S2MM RS halt via guarded JTAG; same-event RAW/RLE retention and live Station status-only wait. No physical HDMI unplug and no automatic DMA recovery claim.')
 (O/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 (O/'stage.json').write_text(json.dumps(dict(stage='complete',run_directory=str(out))))
 print(json.dumps(dict(passed=True,states=[c['after_fault']['capture_health']['state'] for c in cases],clean_boot=restored['boot_id'])),flush=True)
if __name__=='__main__':run()

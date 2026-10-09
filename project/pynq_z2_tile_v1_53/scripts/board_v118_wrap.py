"""Seed an empty queue before DMA, then exercise actual TCP/JTAG around zero."""
from pathlib import Path
import subprocess,json,time,sys,hashlib,zlib,shutil
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v132/wrap_board';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
from workstation import Bridge
from board_v18_continuous import action,state,wait_idle
from board_v118_background import source_ready,until
MASK=0xffffffff
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def execute(cmd,log,timeout=150):
 with log.open('wb') as f:p=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=0x08000000)
 p.check_returncode()
def ready(trace_path=None):
 begun=time.monotonic();end=begun+25;trace=[]
 while True:
  c=EventTCP('169.254.200.10')
  try:
   s=c.stats();assert s['version']==0x11200
   trace.append(dict(seconds=time.monotonic()-begun,boot=s['boot_id'],frames=s['frames'],captured=s['captured'],active=s['active'],error_status=s['error_status']))
   if trace_path:trace_path.write_text(json.dumps(trace,indent=2))
   if s['captured']>=3 and s['active']==1 and s['error_status']==0:return s
   if time.monotonic()>end:raise TimeoutError('TCP is reachable but complete HDMI capture is not ready: '+str(s))
   time.sleep(.2)
  except OSError:
   if time.monotonic()>end:raise
   time.sleep(.2)
  finally:c.close()
def seed(value,out):
 layout=read(R/'reports/v132/queue_debug_layout.json')
 assert layout['elf_sha256']==sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')
 proof=out/'seed.json';assert not proof.exists()
 execute(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/program_queue_seed.tcl'),str(value),str(proof)],out/'seed.log')
 data=read(proof);assert data['seed']==value and data['before'][4:7]==[0,0,0]
 assert data['after'][4:7]==[value,value,0] and data['after'][11]==value and data['after'][64:66]==[value%12]*2
 for key in ('head','tail','last_ack'):assert data['queue_words'][layout[key]//4]==value
 for key in ('read_pos','write_pos'):assert data['queue_words'][layout[key]//4]==value%12
 s=ready(out/'seed_video_ready.json');assert s['boot_id']==data['boot_id'] and s['head']==s['tail']==value and s['depth']==0,s
 data['ready']=s;return data
def restore(out):
 execute(['cmd.exe','/d','/c',str(W/'program_ethernet.bat')],out/'restore_clean.log')
 s=ready(out/'restore_video_ready.json');assert s['head']==0 and s['tail']==0 and s['gaps']==s['invalid']==s['dropped']==s['ack_errors']==0,s
 return s
def prepare_station(out):
 s=state()
 if s['revision']=='V1.17':
  execute(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'scripts/switch_from_v117.ps1')],out/'switch.log')
  execute(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'host/start_station.ps1'),'-NoBrowser'],out/'start.log')
  end=time.monotonic()+10
  while True:
   try:s=state();break
   except OSError:
    if time.monotonic()>end:raise
    time.sleep(.1)
 assert s['revision']=='V1.18'
 wait_idle();action('display',value='station_6');until(lambda:source_ready('station_6'));time.sleep(.5)
def close_jtag(bridge):
 if bridge:
  bridge.close()
  if bridge.proc:bridge.proc.wait(timeout=8)
  if bridge.log:bridge.log.close()
def run():
 out=O/str(time.time_ns());out.mkdir();prepare_station(out);c=None;bridge=None;rows=[];jtag=[];proof=None
 try:
  proof=seed(0xfffffff8,out);base=proof['ready'];c=EventTCP('169.254.200.10');bridge=Bridge(R)
  for i in range(20):
   expected=(0xfffffff9+i)&MASK
   (out/'progress.json').write_text(json.dumps(dict(expected=expected,rows=rows,jtag=jtag),indent=2))
   c.compression=False;raw,d,m,_=c.capture(89);pixel_crc=c.last_timing['pixel_crc32']
   c.compression=True;compact,dd,mm,_=c.capture(89)
   assert raw==compact and d==dd and d[0]==expected and m[4]==((expected-1)&MASK)
   assert all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   slot=(d[1]-0x10100000)//0x400000
   # Cover both the old upper-address failure and the zero-event descriptor.
   need_jtag=expected==0 or (slot>=12 and not any(p['slot']>=12 for p in jtag))
   if need_jtag:
    c.close();key,words=bridge.exchange(('capture','89'))
    assert words[0]=='ok' and len(words)==67
    jd=list(map(int,words[3:43]));jm=list(map(int,words[43:]));path=R/'host/runtime'/f'frame_{key}.bin'
    data=path.read_bytes();assert jd==d and jm[4]==m[4] and data==raw and zlib.crc32(data)==pixel_crc
    saved=out/f'jtag_event_{expected}.bin';shutil.copy2(path,saved);path.unlink()
    jtag.append(dict(event=expected,slot=slot,elapsed_ms=int(words[2]),bytes=len(data),sha256=sha(saved),pixel_crc32=pixel_crc))
   if expected==0:
    bridge.ack(dict(boot_id=m[2],event_id=0));bridge.ack(dict(boot_id=m[2],event_id=0))
   else:c.ack(m[2],expected);c.ack(m[2],expected)
   after=c.stats();assert after['head']==expected and after['depth']==0 and after['ack_errors']==base['ack_errors']
   rows.append(dict(event=expected,frame=d[2],slot=slot,raw_crc32=pixel_crc,bytes_equal=True,after=after))
   print(json.dumps(dict(event=expected,slot=slot,head=after['head'],jtag=need_jtag)),flush=True)
  assert len(jtag)>=2 and any(p['event']==0 for p in jtag) and any(p['slot']>=12 for p in jtag)
  after=c.stats();assert all(after[k]==base[k] for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'))
 except Exception as e:
  (out/'failure.json').write_text(json.dumps(dict(error=str(e),rows=rows,jtag=jtag,proof=proof,failures=c.failures if c else []),indent=2))
  raise
 finally:
  if c:c.close()
  close_jtag(bridge)
  clean=restore(out)
 result=dict(passed=True,events=len(rows),ids=[p['event'] for p in rows],proof=proof,rows=rows,jtag=jtag,clean_restart=clean,run_directory=str(out),
             scope='Actual release ELF seeded at empty queue before DMA; real HDMI frame payloads; event zero JTAG ACK and duplicate ACK, full JTAG/TCP byte equality; deliberate reloads are not normal performance windows')
 (O/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(passed=True,events=len(rows),jtag=jtag,clean_boot=clean['boot_id'])),flush=True)
if __name__=='__main__':run()

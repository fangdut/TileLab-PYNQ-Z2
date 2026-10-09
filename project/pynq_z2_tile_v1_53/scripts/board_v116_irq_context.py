"""Actual board old/new exception-vector controls, then restore a full release."""
from pathlib import Path
import json,subprocess,time,shutil,sys,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_15';W=R/(R.name+'.sdk')
O=R/'reports/v132/irq_context';run=O/'runs'/str(time.time_ns());run.mkdir(parents=True)
sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def execute(command,log,timeout=120):
 with log.open('wb') as f:
  p=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=0x08000000)
 p.check_returncode()
def ready(version):
 end=time.monotonic()+25
 while True:
  c=EventTCP('169.254.200.10')
  try:
   s=c.stats();assert s['version']==version,s;return s
  except OSError:
   if time.monotonic()>end:raise
   time.sleep(.25)
  finally:c.close()
def case(name):
 build=read(O/name/'build.json');assert build['passed']
 assert sha(O/name/'diagnostic.elf')==build['elf_sha256']
 sym=build['symbols'];path=run/(name+'.json')
 execute(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/run_irq_diagnostic.tcl'),name,
          str(sym['irq_result']),str(sym['irq_first_expected']),str(sym['irq_first_observed']),str(path)],run/(name+'.log'))
 raw=read(path);v=raw['result'];assert len(v)==32 and v[0]==0x49525116 and v[1]==2,v
 assert v[2]==v[3]==v[4]==10000 and v[8]==v[9]==0,v
 assert v[13]==1024 and 0<v[14]<v[13]-64 and v[15]==1,v
 assert v[20]&31 in (19,31),'Main was not on the separate supervisor/system stack'
 assert v[21]&31==18,'Handler was not entered through real IRQ mode'
 if name=='baseline':
  assert v[5]==10000 and v[6]==240000 and v[7]==10000 and v[10]==0xffff00ff,v
  a,b=raw['first_expected'],raw['first_observed']
  for j in range(32):
   assert (a[j*2:j*2+2]==b[j*2:j*2+2])==(8<=j<=15),j
 else:assert all(v[k]==0 for k in (5,6,7,8,9,10)),v
 assert v[24]==(name=='candidate') and v[16]>0 and v[17]>=v[16]
 ticks=(v[19]<<32)|v[18]
 result=dict(passed=True,variant=name,expected_state_loss=name=='baseline',iterations=v[3],actual_interrupts=v[4],
             bad_iterations=v[5],register_mismatches=v[6],fpscr_mismatches=v[7],fpexc_mismatches=v[8],timeouts=v[9],
             test_stack_bytes=v[13],stack_high_water_bytes=v[14],bottom_guard_intact=bool(v[15]),
             roundtrip_min_us=v[16]/v[23]*1e6,roundtrip_max_us=v[17]/v[23]*1e6,
             roundtrip_mean_us=ticks/v[3]/v[23]*1e6,raw=raw,build=build)
 print(json.dumps({k:val for k,val in result.items() if k not in ('raw','build')}),flush=True)
 return result
def main():
 # Check both builds before stopping the proven workstation.
 for name in ('baseline','candidate'):assert read(O/name/'build.json')['passed']
 execute(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'scripts/switch_from_v115.ps1')],run/'stop_baseline.log')
 passed=False
 try:
  before=read(B/'reports/programmed_v115.json')
  cases=[case('baseline'),case('candidate')];passed=True
 finally:
  target=R if passed else B;ws=target/(target.name+'.sdk')
  execute(['cmd.exe','/d','/c',str(ws/'program_ethernet.bat')],run/'restore_full_release.log')
  restored=ready(0x11000 if passed else 0x10f00)
  execute(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(target/'host/start_station.ps1'),'-NoBrowser'],run/'restore_station.log')
  (run/'restored.json').write_text(json.dumps(restored,indent=2))
 result=dict(passed=True,baseline=cases[0],candidate=cases[1],board_before=before,restored=restored,run_directory=str(run),
             scope='Actual 10000 GIC SGI interrupts per variant, deliberate ABI-permitted FP clobber; not proof the current Ethernet ISR originally clobbered FP, not nested interrupt/FIQ/abort coverage; same 1024-byte diagnostic stacks, production V1.16 reserves 4096 bytes')
 (O/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print('Actual IRQ negative/positive controls passed; full V1.16 BIT/ELF restored',flush=True)
if __name__=='__main__':main()

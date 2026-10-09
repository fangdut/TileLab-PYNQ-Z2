"""Actual release DMA halts, retained bytes, product boundary and retry budget.
Always restore clean release after diagnostic; never claims physical HDMI loss.
"""
from pathlib import Path
import sys,json,time,subprocess,hashlib
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v132/dma_recovery_board';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from tcp_transport import EventTCP
from workstation import Bridge
from board_v18_continuous import action,state,wait_idle
from board_v120_background import source_ready,until
def dump(path,v):path.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def execute(cmd,log):
 with log.open('wb') as f:p=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=150,creationflags=0x08000000)
 p.check_returncode()
def ready(path):
 begin=time.monotonic();rows=[]
 while time.monotonic()-begin<30:
  c=EventTCP('169.254.200.10')
  try:
   s=c.stats();assert s['version']==0x11400
   rows.append(dict(seconds=time.monotonic()-begin,stats=s));dump(path,rows)
   if s['capture_health']['ready'] and s['captured']>=3:return s
  except OSError:pass
  finally:c.close()
  time.sleep(.2)
 raise TimeoutError('Clean release did not acquire valid HDMI images')
def source(name):
 action('display',value=name);until(lambda:source_ready(name));time.sleep(.35)
def drain(c,out,prefix):
 rows=[]
 for n in range(12):
  if c.stats()['depth']==0:break
  raw,d,m,ms=c.capture(89);f,png,mask=Bridge.decode_event(raw,d,m,ms)
  (out/f'{prefix}_{n}.png').write_bytes(png);(out/f'{prefix}_{n}_mask.png').write_bytes(mask)
  rows.append(dict(event=d[0],frame=d[2],sha256=hashlib.sha256(raw).hexdigest(),descriptor=d));c.ack(m[2],d[0])
 assert c.stats()['depth']==0;dump(out/(prefix+'.json'),rows)
def crc(c):
 result={k:c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')}
 assert all(result.values());return result
def checkpoint(name,out):
 dump(O/'stage.json',dict(stage=name,run_directory=str(out)));print('UI_CHECKPOINT '+name,flush=True)
 end=time.monotonic()+60
 while time.monotonic()<end and not (out/(name+'.continue')).exists():time.sleep(.1)

def case(number,out):
 wait_idle();source('station_6');c=EventTCP('169.254.200.10')
 try:
  drain(c,out,'setup');c.configure(89);time.sleep(.3);assert ((c.stats()['config']>>8)&255)==89
  source('real_000');c.compression=False;raw,d,m,ms=c.capture(89);checks=crc(c);before=c.stats()
  assert before['depth']==1 and before['capture_recovery']['attempts']==number-1 and before['capture_recovery']['state']=='RUNNING'
  f,png,mask=Bridge.decode_event(raw,d,m,ms);(out/'retained.png').write_bytes(png);(out/'retained_mask.png').write_bytes(mask)
  identity=dict(boot=m[2],event=d[0],frame=d[2],product=d[37],sha256=hashlib.sha256(raw).hexdigest(),descriptor=d,crc=checks)
  c.close();execute(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/stop_dma_v120.tcl'),str(m[2]),str(d[0]),str(number-1),str(out/'injection.json')],out/'injection.log')
  after=c.stats();reads=[]
  # Check evidence first, even if the candidate recovery later fails acceptance.
  for compressed in (False,True):
   c.compression=compressed;again,dd,mm,_=c.capture(89)
   assert raw==again and d==dd and mm[2]==m[2]
   reads.append(dict(compressed=compressed,crc=crc(c),sha256=hashlib.sha256(again).hexdigest()))
  result=dict(number=number,before=before,after=after,identity=identity,rereads=reads,injection=json.loads((out/'injection.json').read_text()),retained_bytes_equal=True)
  dump(out/'retention.json',result)
  rec=after['capture_recovery']
  if number<=3:
   assert rec['state']=='RUNNING' and rec['attempts']==rec['successes']==number and rec['failures']==0 and after['capture_health']['ready'],after
   assert rec['waiting_new_product'] and after['boot_id']==m[2]
   c.ack(m[2],d[0]);baseline=c.stats();best_before=baseline['best_updates']
   newraw,nd,nm,_=c.capture(89);newchecks=crc(c)
   assert nd[2]>d[2] and nd[37]==d[37] and nd[8]==3 and nm[2]==m[2]
   c.ack(nm[2],nd[0]);middle=c.stats()
   assert middle['events']==baseline['events'] and middle['best_updates']==best_before and middle['capture_recovery']['waiting_new_product']
   result['mid_product']=dict(frame=nd[2],product=nd[37],crc=newchecks,before=baseline,after=middle)
   if number==1:
    c.close();action('storage',mode='preview',max_archive_mib=1024);action('start')
    until(lambda:state()['captures']>=2 and (state().get('capture_recovery') or {}).get('successes')==1,seconds=8)
    checkpoint('recovered_once',out);wait_idle()
   # An EXIT without a new START must not publish the interrupted old best.
   source('station_6');empty=c.stats();assert empty['depth']==0 and empty['capture_recovery']['waiting_new_product']
   source('real_005');entry=c.stats();assert not entry['capture_recovery']['waiting_new_product'] and entry['current_product_id']!=d[37]
   new_product=entry['current_product_id'];assert new_product
   source('station_6');finished=c.stats();assert finished['depth']==1
   auto,ad,am,ams=c.capture(89);auto_checks=crc(c)
   assert ad[37]==new_product and ad[8]==1 and ad[38]&32 and am[2]==m[2]
   af,apng,amask=Bridge.decode_event(auto,ad,am,ams);(out/'next_product.png').write_bytes(apng);(out/'next_product_mask.png').write_bytes(amask)
   c.ack(am[2],ad[0]);result['next_product']=dict(product=new_product,event=ad[0],frame=ad[2],crc=auto_checks,descriptor=ad)
   result['final_stats']=c.stats()
  else:
   assert rec['state']=='FAILED' and rec['attempts']==rec['successes']==3 and rec['failures']==1 and rec['reason_code']==7 and not after['capture_health']['ready'],after
   c.close();pre=state();action('storage',mode='preview',max_archive_mib=1024);action('start')
   until(lambda:(state().get('board_stats') or {}).get('head')==d[0] and not state().get('pending_operation'),seconds=10)
   first=state();begin=time.monotonic();observations=[]
   while time.monotonic()-begin<3:
    st=state();assert st['board_connected'] and not st['error'] and st['enabled']
    assert st['captures']==first['captures'] and st['capture_recovery']['state']=='FAILED'
    assert st['board_stats']['request']==after['request']
    observations.append(st);time.sleep(.15)
   last=state();assert last['captures']==pre['captures']+1
   received=last['transport_totals']['received_bytes']-first['transport_totals']['received_bytes']
   assert 0<received<20000 and received%276==0
   result['terminal_wait']=dict(first=first,last=last,states=observations,status_bytes=received,seconds=time.monotonic()-begin)
   checkpoint('budget_failed',out);wait_idle();result['final_stats']=c.stats()
  assert result['final_stats']['dropped']==before['dropped'] and result['final_stats']['ack_errors']==before['ack_errors']
  result['passed']=True;dump(out/'result.json',result)
  print(json.dumps(dict(passed=True,attempt=number,state=rec['state'],duration_ms=rec['last_duration_ms'],invalid_delta=result['final_stats']['invalid']-before['invalid'],gaps_delta=result['final_stats']['gaps']-before['gaps'])),flush=True)
  return result
 finally:c.close()

def run():
 out=O/str(time.time_ns());out.mkdir();cases=[]
 try:
  ready(out/'initial_ready.json')
  for number in range(1,5):
   part=out/f'case_{number}';part.mkdir();cases.append(case(number,part))
 except Exception as e:
  dump(out/'failure.json',dict(error=str(e),cases=cases,state=state()));raise
 finally:
  wait_idle();source('station_6')
  execute(['cmd.exe','/d','/c',str(W/'program_ethernet.bat')],out/'restore.log')
  clean=ready(out/'clean_ready.json');assert clean['capture_recovery']['attempts']==0
  action('display',value='real_video');action('start')
 result=dict(passed=True,cases=cases,clean_restart=clean,run_directory=str(out),scope='Actual S2MM run-stop halts with unacknowledged images; three automatic recoveries and fourth bounded refusal; no physical HDMI unplug, DMA reset-stuck injection or power-loss claim')
 dump(O/'summary.json',result);dump(O/'stage.json',dict(stage='complete',run_directory=str(out)))
 print(json.dumps(dict(passed=True,cases=4,clean_boot=clean['boot_id'])),flush=True)
if __name__=='__main__':run()

"""Actual board responses with controlled host delivery barriers.
No fabricated status/pixels: the barrier delays delivery to Station after real
status/image receipt, or before ACK. This is not a claim of link fault injection.
"""
from pathlib import Path
import sys,time,json,threading,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/admission_board';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from workstation import Station,EthernetBridge,Bridge
from tcp_transport import EventTCP
from board_v18_continuous import action,state,wait_idle
from board_v124_background import until,source_ready
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def source_empty():
 action('display',value='station_6');until(lambda:source_ready('station_6'));time.sleep(.35)
class DeferredBridge(EthernetBridge):
 def __init__(self,stage):
  super().__init__('169.254.200.10');self.stage=stage;self.once=True
  self.entered=threading.Event();self.release=threading.Event();self.operations=[]
 def gate(self,stage):
  if self.once and stage==self.stage:
   self.once=False;self.entered.set()
   if not self.release.wait(8):raise TimeoutError('Host delivery barrier was not released')
 def stats(self):
  self.operations.append('stats');result=super().stats();self.gate('stats');return result
 def capture(self,t):
  self.operations.append('capture');result=super().capture(t);self.gate('capture');return result
 def ack(self,f):
  self.operations.append('ack');self.gate('ack');return super().ack(f)
def drain(c,out):
 proofs=[]
 for i in range(12):
  if c.stats()['depth']==0:break
  raw,d,m,ms=c.capture(89);f,png,mask=Bridge.decode_event(raw,d,m,ms)
  (out/f'setup_{i}.png').write_bytes(png);(out/f'setup_{i}_mask.png').write_bytes(mask)
  proofs.append(dict(frame=f,descriptor=d,sha256=hashlib.sha256(raw).hexdigest()));c.ack(m[2],d[0])
 assert c.stats()['depth']==0;dump(out/'setup.json',proofs)
def trial(name,stage,pinned,out):
 out.mkdir();wait_idle();source_empty();c=EventTCP('169.254.200.10');s=None;b=None
 try:
  drain(c,out);c.configure(89);time.sleep(.25);before=c.stats()
  assert before['version']==0x11800 and before['capture_health']['ready']
  raw=d=m=None
  if pinned:
   raw,d,m,ms=c.capture(89);f,png,mask=Bridge.decode_event(raw,d,m,ms)
   assert all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   (out/'pinned.png').write_bytes(png);(out/'pinned_mask.png').write_bytes(mask);before=c.stats();assert before['depth']==1
  else:assert before['depth']==0
  c.close();b=DeferredBridge(stage);s=Station(out,b)
  # A manual request exercises durable save when it is already admitted.
  s.action(dict(op='capture'));assert b.entered.wait(8),'Did not reach real response delivery barrier'
  blocked=s.state();assert blocked['busy'] and blocked['capture_control']['phase']==dict(stats='CHECK',capture='CAPTURE',ack='ACK')[stage]
  if stage=='ack':assert len(s.records.all())==1 and s.records.confirmations.pending()
  s.action(dict(op='pause'));paused=s.state();assert not paused['enabled'];b.release.set()
  until(lambda:not s.busy,seconds=8);after=s.state();assert not after['error'] and not after['enabled'] and not after['manual_waiting']
  counts=(after['captures'],len(b.operations));time.sleep(.25)
  assert counts==(s.captures,len(b.operations)),'A new request started after the worker stopped'
  records=s.records.all();history=s.records.confirmations.history()
  if stage=='stats':
   assert b.operations==['stats'] and not records and after['captures']==0
   assert after['capture_control']['admitted']==0 and after['capture_control']['cancelled_before_capture']==1
  else:
   assert b.operations==['stats','capture','ack','stats'] and len(records)==1 and after['captures']==1
   assert after['capture_control']['admitted']==1 and after['capture_control']['cancelled_before_capture']==0
   assert all(records[0][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   assert records[0]['recovery_generation']==0 and len(history)==1 and history[0]['status']=='ACKNOWLEDGED'
   assert s.records.confirmations.pending() is None
  s.action(dict(op='disconnect'));board_after=c.stats()
  if stage=='stats':
   assert all(board_after[k]==before[k] for k in ('request','head','tail','depth'))
   if pinned:
    reread,dd,mm,_=c.capture(89);assert reread==raw and dd==d and mm[2]==m[2]
    assert all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
    c.ack(m[2],d[0])
  else:
   assert board_after['depth']==0 and board_after['head']==records[0]['event_id']
  assert all(board_after[k]==before[k] for k in ('boot_id','invalid','gaps','dropped','ack_errors','descriptor_crc_errors'))
  result=dict(passed=True,name=name,stage=stage,queued_before=pinned,before=before,blocked=blocked,paused=paused,after=after,board_after=board_after,
   operations=b.operations,records=records,history=history,pinned_reread_equal=bool(pinned),scope='Real board plus controlled host-side response/ACK delivery barrier; no simulated frame or status')
  dump(out/'result.json',result);print(json.dumps(dict(passed=True,name=name,operations=b.operations,captures=after['captures'],cancelled=after['capture_control']['cancelled_before_capture'])),flush=True)
  return result
 except Exception as e:
  dump(out/'failure.json',dict(error=str(e),state=s.state() if s else None,operations=b.operations if b else []));raise
 finally:
  if b:b.release.set()
  if s:s.exit=True;s.worker.join(8);s.records.db.close()
  if b:b.close()
  c.close()
def run():
 run=O/str(time.time_ns());run.mkdir();rows=[]
 try:
  wait_idle();source_empty();started=time.monotonic();ready_rows=[]
  while True:
   probe=EventTCP('169.254.200.10')
   try:
    status=probe.stats();assert status['version']==0x11800
    ready_rows.append(dict(seconds=time.monotonic()-started,stats=status));dump(run/'initial_ready.json',ready_rows)
    if status['capture_health']['ready'] and status['captured']>=3:break
   except OSError:pass
   finally:probe.close()
   if time.monotonic()-started>30:raise TimeoutError('Release did not acquire complete images')
   time.sleep(.2)
  for name,stage,pinned in [('empty_preflight_stop','stats',False),('queued_preflight_stop','stats',True),('admitted_frame_stop','capture',False),('saved_ack_stop','ack',False)]:
   rows.append(trial(name,stage,pinned,run/name))
 finally:action('storage',mode='preview',max_archive_mib=1024);action('display',value='real_video');action('start')
 result=dict(passed=True,cases=rows,run_directory=str(run),scope='Four actual board cases with controlled delivery barriers; user pause before admission cancels, admitted evidence finishes')
 dump(O/'summary.json',result);print('Four actual-board capture admission cases passed',flush=True)
if __name__=='__main__':run()

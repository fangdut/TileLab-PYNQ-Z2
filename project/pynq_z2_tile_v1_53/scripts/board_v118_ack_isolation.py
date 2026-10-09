"""Actual old/new board comparison, including a direct empty-mailbox fault."""
from pathlib import Path
import json,time,struct,zlib,hashlib,argparse
from board_v118_wrap import R,W,read,sha,execute,ready,seed,restore,prepare_station,close_jtag,Bridge
from board_v18_continuous import action,state,wait_idle
from board_v118_background import until
from tcp_transport import EventTCP,MAGIC
O=R/'reports/v132/ack_board';MASK=0xffffffff

def reject(c,boot,event):
 if c.sock is None:c.stats()
 c.sock.sendall(struct.pack('<4I',MAGIC,2,boot,event));raw=c.exact(276);h=struct.unpack('<69I',raw)
 assert h[:4]==(MAGIC,2,0,5) and h[-1]==zlib.crc32(raw[:272]),h[:4]
 return dict(requested_boot=boot,requested_event=event,descriptor=list(h[4:44]),metadata=list(h[44:68]),header_crc_verified=True)

def old_counterexample(out):
 assert state()['revision']=='V1.17';wait_idle();action('display',value='station_6')
 old=R.parent/'pynq_z2_tile_v1_17'
 until(lambda:read(old/'host/player_status.json').get('source')=='station_6');time.sleep(.4)
 c=EventTCP('169.254.200.10')
 try:
  before=c.stats();assert before['version']==0x11100
  while before['depth']:
   _,d,m,_=c.capture(89);c.ack(m[2],d[0]);before=c.stats()
  future=(before['head']+1)&MASK;rejected=reject(c,before['boot_id'],future)
  raw,d,m,_=c.capture(89);assert d[0]==future and m[4]==before['head']
  flags={k:c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')};assert all(flags.values())
  failed=reject(c,m[2],future);after=c.stats();assert after['head']==before['head'] and after['depth']==1
  result=dict(reproduced=True,before=before,premature_response=rejected,valid_response_rejected=failed,after=after,event=future,frame=d[2],pixel_sha256=hashlib.sha256(raw).hexdigest(),crc=flags)
  (out/'old_board_counterexample.json').write_text(json.dumps(result,indent=2));return result
 finally:c.close()

def case(name,out,inject_mailbox=False):
 c=EventTCP('169.254.200.10');jtag=None;rejects=[]
 try:
  before=c.stats();(out/(name+'_before.json')).write_text(json.dumps(before,indent=2));assert before['version']==0x11200 and before['depth']==0
  boot=before['boot_id'];head=before['head'];future=(head+1)&MASK
  c.ack(boot,head);assert c.stats()['ack_errors']==before['ack_errors']
  for request_boot,event in ((boot^1,head),(boot,future),(boot,(head-1)&MASK)):
   proof=reject(c,request_boot,event);assert proof['metadata'][4:7]==[head,head,0] and proof['metadata'][11]==head;rejects.append(proof)
  time.sleep(.1);s=c.stats();assert s['head']==head and s['tail']==head and s['depth']==0
  if inject_mailbox:
   c.close();jtag=Bridge(R)
   try:jtag.ack(dict(boot_id=boot,event_id=future))
   except RuntimeError as e:assert 'no pending event' in str(e);(out/(name+'_jtag_reject.txt')).write_text(str(e))
   else:raise AssertionError('JTAG accepted future ACK on empty queue')
   close_jtag(jtag);jtag=None
   execute(['cmd.exe','/d','/c','D:/2025.2/Vitis/bin/xsdb.bat',str(R/'scripts/inject_empty_ack.tcl'),str(boot),str(out/(name+'_mailbox.json'))],out/(name+'_mailbox.log'))
   injected=read(out/(name+'_mailbox.json'));assert injected['passed'] and injected['requested']==future
   time.sleep(.1)
  else:injected=None
  c.compression=False;raw,d,m,_=c.capture(89);flags={k:c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')};assert all(flags.values())
  assert d[0]==future and m[4]==head and m[11]==head
  for request_boot,event in ((boot,(head+2)&MASK),(boot^1,future),(boot,(head-1)&MASK)):
   proof=reject(c,request_boot,event);assert proof['metadata'][4:7]==[head,future,1] and proof['metadata'][11]==head;rejects.append(proof)
  c.compression=True;again,dd,mm,_=c.capture(89);assert raw==again and d==dd
  if inject_mailbox:
   c.close();jtag=Bridge(R);jtag.ack(dict(boot_id=boot,event_id=future));jtag.ack(dict(boot_id=boot,event_id=future));close_jtag(jtag);jtag=None
  else:c.ack(boot,future)
  after=c.stats();c.ack(boot,future);duplicate=c.stats()
  assert after['head']==future and after['tail']==future and after['depth']==0
  assert after['ack_errors']==before['ack_errors']+len(rejects)+bool(inject_mailbox)
  assert duplicate['ack_errors']==after['ack_errors'] and duplicate['head']==future
  assert all(after[k]==before[k] for k in ('gaps','invalid','dropped','descriptor_crc_errors'))
  result=dict(passed=True,name=name,event=future,before=before,after=after,rejected_requests=rejects,mailbox=injected,jtag_future_rejected=inject_mailbox,valid_ack_transport='JTAG' if inject_mailbox else 'TCP',duplicate_ack=True,pixels_unchanged=True,crc=flags,pixel_sha256=hashlib.sha256(raw).hexdigest())
  (out/(name+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps(dict(passed=True,name=name,event=future,rejections=len(rejects),direct_mailbox=inject_mailbox)),flush=True);return result
 except Exception as e:
  (out/(name+'_failure.json')).write_text(json.dumps(dict(error=str(e),rejected_requests=rejects,failures=c.failures),indent=2));raise
 finally:c.close();close_jtag(jtag)

def drain_setup(out):
 c=EventTCP('169.254.200.10');saved=[]
 try:
  for _ in range(13):
   s=c.stats()
   if not s['depth']:return saved
   if len(saved)==12:raise AssertionError('Setup did not settle to an empty source')
   raw,d,m,_=c.capture(89);assert all(c.last_timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
   p=out/f'setup_event_{d[0]}.bin';p.write_bytes(raw)
   saved.append(dict(event=d[0],boot=m[2],descriptor=d,metadata=m,pixels_sha256=sha(p),file=str(p)))
   (out/'setup_events.json').write_text(json.dumps(saved,indent=2));c.ack(m[2],d[0])
 finally:c.close()

def run():
 ap=argparse.ArgumentParser();ap.add_argument('--baseline-proof',type=Path);args=ap.parse_args()
 fw=read(R/'reports/v132/firmware_audit.json');assert fw['passed'] and fw['elf_sha256']==sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')
 out=O/str(time.time_ns());out.mkdir(parents=True);results=[];old=None
 try:
  if args.baseline_proof:
   source=args.baseline_proof.resolve();assert source.is_relative_to(O.resolve())
   old=read(source);assert old['reproduced'] and old['before']['version']==0x11100 and old['after']['depth']==1
   baseline=R.parent/'pynq_z2_tile_v1_17';program=read(baseline/'reports/programmed_v117.json')
   assert program['boot_id']==old['before']['boot_id']
   for path,digest in program['sha256'].items():assert sha(baseline/(baseline.name+'.sdk')/path)==digest
   old['programming_identity']=program;old['original_proof_path']=str(source)
   (out/'old_board_counterexample.json').write_text(json.dumps(old,indent=2))
  else:old=old_counterexample(out)
 finally:clean=restore(out)
 prepare_station(out);setup=drain_setup(out)
 try:
  results.append(case('ordinary',out))
  seeded=out/'zero_seed';seeded.mkdir();proof=seed(0xffffffff,seeded)
  results.append(case('zero',out,True));assert results[-1]['event']==0
 finally:
  cleanout=out/'final';cleanout.mkdir();clean=restore(cleanout)
 summary=dict(passed=True,old_board=old,cases=results,seed=proof,setup_events=setup,clean_restart=clean,run_directory=str(out),scope='Actual old/new release ELFs; deliberately invalid TCP ACK, debug JTAG guard, one guarded direct ACK-mailbox injection; real HDMI pixels; no physical power-cycle claim')
 (O/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(dict(passed=True,cases=len(results),clean_boot=clean['boot_id'])),flush=True)

if __name__=='__main__':run()

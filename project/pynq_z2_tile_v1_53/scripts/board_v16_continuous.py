"""Exercise actual HDMI/PL/SG/TCP/PNG/SQLite path, preserving every event.
The workstation must be paused. No host detector participates in production.
"""
from pathlib import Path
import sys,time,json,urllib.request,argparse,io,socket,struct,hashlib
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'));sys.path.insert(0,str(R/'models'))
from workstation import EthernetBridge,Records
import recipes
CATALOG=recipes.load(R)
from weak_reference import detect
from regions_reference import regions
BASE='http://127.0.0.1:8770';OUT=R/'reports/v132/continuous';OUT.mkdir(parents=True,exist_ok=True)
def action(op,**kw):
 req=urllib.request.Request(BASE+'/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(req,timeout=20))
def state():return json.load(urllib.request.urlopen(BASE+'/api/state',timeout=10))
def read_player():
 for _ in range(40):
  try:return json.loads((R/'host/player_status.json').read_text(encoding='utf-8-sig'))
  except (PermissionError,FileNotFoundError,json.JSONDecodeError):time.sleep(.025)
 raise TimeoutError('Player status remained unavailable for one second')
def wait_idle():
 action('pause');end=time.monotonic()+10
 while state()['busy']:
  if time.monotonic()>end:raise TimeoutError('Workstation did not pause')
  time.sleep(.05)
 action('disconnect')
def barcode(image):
 a=np.asarray(Image.open(io.BytesIO(image)).convert('RGB'));return sum(int(a[22:38,1018+b*14:1025+b*14].mean()>128)<<b for b in range(16))
def run(mode,seconds,threshold=36):
 wait_idle();action('display',value='station_6');time.sleep(.5)
 bridge=EthernetBridge('169.254.200.10');records=Records(R);rows=[];events=[];checks=[]
 try:
  # Preserve any pending test/event evidence before a new interval.
  while bridge.stats()['depth']:
   f,im,mask=bridge.capture(threshold)
   f.update(recipes.evidence(f,CATALOG))
   if f.get('event_reason') in (1,2):records.save(f,im,mask,'hardware_alarm')
   bridge.ack(f)
  warm,wi,wm=bridge.capture(threshold);bridge.ack(warm)
  if ((warm['config_word']>>8)&255)!=threshold:
   for _ in range(4):
    warm,wi,wm=bridge.capture(threshold);bridge.ack(warm)
    if ((warm['config_word']>>8)&255)==threshold:break
  assert ((warm['config_word']>>8)&255)==threshold
  before=bridge.stats();dbefore=bridge.transport.diagnostics();begun=time.monotonic();action('display',value=mode)
  last=begun;last_print=begun
  while True:
   elapsed_now=time.monotonic()-begun
   # Finish the current physical product before ending a timed test. Abruptly
   # replacing a half-passed tile with an empty image creates a false edge case.
   if elapsed_now>=seconds and bridge.stats()['current_product_id']==0:break
   if elapsed_now>seconds+5:raise TimeoutError('No product gap within five seconds after the test window')
   t=time.monotonic();f,im,mask=bridge.capture(threshold);received=time.monotonic();f.update(recipes.evidence(f,CATALOG));key=None
   if f['event_reason'] in (1,2):
    key=records.save(f,im,mask,'hardware_alarm');events.append(dict(key=key,**f));
    a=np.asarray(Image.open(io.BytesIO(mask)))>0;expected,_=detect(Image.open(io.BytesIO(im)),threshold=threshold);rr=regions(expected)
    check=dict(key=key,mask_mismatch=int(np.count_nonzero(a!=expected)),boxes_match=f['boxes']==rr['boxes'],areas_match=f['region_areas']==rr['areas'],full=f.get('selection_full_tile',False))
    checks.append(check)
   bridge.ack(f);ended=time.monotonic()
   rows.append(dict(frame_id=f['frame_id'],event_id=f['event_id'],product_id=f.get('product_id'),reason=f['event_reason'],barcode=barcode(im),receive_ms=(received-t)*1000,cycle_ms=(ended-t)*1000,interval_ms=(ended-last)*1000,**{k:f[k] for k in ('request_ms','header_wait_ms','payload_ms','payload_MB_s','goodput_MB_s','total_request_ms','retry_count','reconnects')}))
   last=ended
   if ended-last_print>15:
    print(json.dumps(dict(mode=mode,seconds=round(ended-begun,1),frames=len(rows),saved=len(events),status=bridge.stats())),flush=True);last_print=ended
  player_end=read_player()
  action('display',value='station_6');time.sleep(.2)
  while bridge.stats()['depth']:
   f,im,mask=bridge.capture(threshold)
   f.update(recipes.evidence(f,CATALOG))
   if f['event_reason'] in (1,2):events.append(dict(key=records.save(f,im,mask,'hardware_alarm'),**f))
   bridge.ack(f)
  after=bridge.stats();dafter=bridge.transport.diagnostics();elapsed=time.monotonic()-begun
  # The final drain belongs to the same run. Verify and attribute those images
  # too, instead of silently excluding a last product from the acceptance.
  verified={c['key'] for c in checks}
  for e in events:
   if e['key'] in verified:continue
   im=(R/'review_records'/(e['key']+'.png')).read_bytes()
   mask=(R/'review_records'/(e['key']+'_mask.png')).read_bytes()
   a=np.asarray(Image.open(io.BytesIO(mask)))>0;expected,_=detect(Image.open(io.BytesIO(im)),threshold=(e['config_word']>>8)&255);rr=regions(expected)
   checks.append(dict(key=e['key'],mask_mismatch=int(np.count_nonzero(a!=expected)),boxes_match=e['boxes']==rr['boxes'],areas_match=e['region_areas']==rr['areas'],full=e.get('selection_full_tile',False)))
  intervals=np.array([r['interval_ms'] for r in rows]);capture_delta=after['captured']-before['captured']
  product_ids=[e['product_id'] for e in events if e.get('selection')=='FPGA_PRODUCT_BEST_FRAME']
  passed=after['gaps']==before['gaps'] and after['invalid']==before['invalid'] and after['dropped']==before['dropped'] and not after['error_status'] and len(set(product_ids))==len(product_ids) and all(c['mask_mismatch']==0 and c['boxes_match'] and c['areas_match'] and c['full'] for c in checks) and len(events)>0 and intervals.max()<1000
  result=dict(mode=mode,threshold=threshold,warmup_ms=warm['transfer_ms'],requested_window_seconds=seconds,stop_policy='Wait for the current product to leave the hardware gate, then clear source and drain',seconds=elapsed,before=before,after=after,diag_before=dbefore,diag_after=dafter,raw_capture_fps=capture_delta/elapsed,host_captures=len(rows),saved_events=len(events),products_completed=dafter['raw'][16]-dbefore['raw'][16],max_interval_ms=float(intervals.max()),p99_interval_ms=float(np.percentile(intervals,99)),unique_product_ids=len(set(product_ids)),checks=checks,events=events,rows=rows,passed=bool(passed))
  result['player_at_end']=player_end
  (OUT/f'{mode}_{int(seconds)}s.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
  print(json.dumps({k:v for k,v in result.items() if k not in ('checks','events','rows','diag_before','diag_after')}),flush=True)
  if not passed:raise AssertionError('Continuous acceptance did not pass; evidence retained')
 except Exception as e:
  (OUT/f'failure_{mode}_{time.time_ns()}.json').write_text(json.dumps(dict(error=str(e),rows=rows,events=events,checks=checks,transport=bridge.transport.failures),indent=2));raise
 finally:action('display',value='station_6');bridge.close();records.db.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['video','fast','ultrafast','real_video']);ap.add_argument('--seconds',type=float,default=60);ap.add_argument('--threshold',type=int,default=36);a=ap.parse_args();run(a.mode,a.seconds,a.threshold)

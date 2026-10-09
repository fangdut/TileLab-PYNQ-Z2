"""Real board acceptance. Service must be idle and HDMI player running."""
from pathlib import Path
import json,time,urllib.request,sys,io,os
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from valley_reference import detect
from regions_reference import regions
BASE='http://127.0.0.1:8770';OUT=Path(os.environ.get('TILE_TEST_OUTPUT',str(R/'reports/board_acceptance')));OUT.mkdir(parents=True,exist_ok=True)
def get(p):return urllib.request.urlopen(BASE+p,timeout=10).read()
def state():return json.loads(get('/api/state'))
def action(op,**kw):return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'}),timeout=60))
def shot():
 before=state()['captures'];action('capture');end=time.monotonic()+100
 while time.monotonic()<end:
  s=state()
  if s['error']:raise RuntimeError(s['error'])
  if s['captures']>before and not s['busy']:return s
  time.sleep(.1)
 raise TimeoutError('board capture')
def check(s,label,expected_boxes=None):
 f=s['frame'];raw=get('/api/image');mask=get('/api/image?mask=1');im=Image.open(io.BytesIO(raw));actual=np.asarray(Image.open(io.BytesIO(mask)))>0
 expected,_=detect(im,threshold=(f['config_word']>>8)&255);rr=regions(expected);diff=int(np.count_nonzero(actual!=expected))
 passed=diff==0 and f['boxes']==rr['boxes'] and f['region_areas']==rr['areas'] and f['region_overflow']==rr['overflow']
 if expected_boxes is not None:passed=passed and len(f['boxes'])==expected_boxes
 (OUT/f'{label}_original.png').write_bytes(raw);(OUT/f'{label}_mask.png').write_bytes(mask)
 row=dict(label=label,hardware=f,reference=rr,mask_mismatch_pixels=diff,passed=passed);print(json.dumps(row),flush=True)
 if not passed:raise AssertionError(json.dumps(row))
 return row
def static():
 action('pause');action('threshold',value=36);rows=[]
 for i,n in enumerate([0,1,0,1,2,0]):
  action('display',value=f'station_{i}');time.sleep(1)
  shot();s=shot();rows.append(check(s,f'station_{i}',n));(OUT/'static_results.json').write_text(json.dumps(rows,indent=2))
 print('V13 BOARD STATIC PASS: six scenes, exact masks and FPGA multi-region coordinates',flush=True)
def pressure(controlled=False):
 action('pause');action('display',value='station_0');time.sleep(.4)
 while action('status')['depth']:shot()
 before=action('status');positions=[]
 if controlled:
  for i in range(16):
   action('display',value='station_4');time.sleep(.6)
   action('display',value='station_0');time.sleep(.6)
 else:
  action('display',value='burst');deadline=time.monotonic()+45
  while time.monotonic()<deadline:
   try:ps=json.loads((R/'host/player_status.json').read_text(encoding='utf-8-sig'))
   except (OSError,ValueError):time.sleep(.1);continue
   positions.append(ps)
   if ps['source']=='burst' and ps['position_seconds']>=9.5:break
   time.sleep(.1)
  else:raise TimeoutError('Player never reached end of sixteen-event sequence')
 action('display',value='station_0');time.sleep(.5);after=action('status')
 (OUT/'pressure_player_timeline.json').write_text(json.dumps(positions,indent=2))
 result=dict(input='STATIC_SWITCH_600MS' if controlled else 'VIDEO_100MS',before=before,after=after,event_delta=after['events']-before['events'],dropped_delta=after['dropped']-before['dropped'])
 result_path=OUT/('queue_capacity_counts.json' if controlled else 'pressure_counts.json')
 result_path.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 if result['event_delta']!=16 or after['depth']!=12 or result['dropped_delta']!=4:raise AssertionError('Short-event/full-queue acceptance failed')
 rows=[]
 for i in range(12):rows.append(check(shot(),f'queue_capacity_{i}' if controlled else f'queued_{i}',2));(OUT/('queue_capacity_results.json' if controlled else 'queued_results.json')).write_text(json.dumps(rows,indent=2))
 final=action('status');result['final']=final;result['passed']=final['depth']==0 and final['ack_errors']==0
 result_path.write_text(json.dumps(result,indent=2));assert result['passed'];print('V13 QUEUE PASS: 16 events, 12 held, four explicit drops, all held masks/boxes intact and acknowledged; input='+result['input'],flush=True)
if __name__=='__main__':
 if '--queue' in sys.argv:pressure(controlled=True)
 elif '--pressure' in sys.argv:pressure()
 else:static()

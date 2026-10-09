"""A/B normal preview versus frozen view with real hardware events."""
from pathlib import Path
import sys,json,time,io
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'));sys.path.insert(0,str(R/'models'))
from workstation import Records,EthernetBridge
from tcp_transport import EventTCP
from weak_reference import detect
from regions_reference import regions
from board_v18_continuous import action,state,wait_idle,barcode
OUT=R/'reports/v132';OUT.mkdir(exist_ok=True)
def until(fn,seconds=8):
 end=time.monotonic()+seconds
 while not fn():
  if time.monotonic()>end:raise TimeoutError('Background acceptance condition not reached')
  time.sleep(.05)
def source_ready(value):
 try:return json.loads((R/'host/player_status.json').read_text(encoding='utf-8-sig')).get('source')==value
 except (OSError,ValueError):return False
def phase(name,frozen,seconds):
 action('display',value='station_6');action('freeze_preview',enabled=frozen);action('storage',mode='preview',max_archive_mib=1024);action('start')
 until(lambda:(state().get('board_stats') or {}).get('depth')==0 and state()['board_connected']);time.sleep(.3)
 store=Records(R);previous={r['id'] for r in store.all()};before=state();rows=[];action('storage',mode='archive',max_archive_mib=1024)
 action('display',value='real_video');begun=time.monotonic()
 try:
  while True:
   s=state();elapsed=time.monotonic()-begun
   assert not s['error'],s['error']
   rows.append(dict(seconds=elapsed,captures=s['captures'],transport=s['transport_totals'],stats=s['board_stats']))
   if elapsed>=seconds and s['board_stats']['current_product_id']==0:break
   if elapsed>seconds+5:raise TimeoutError('No end-of-product gap')
   time.sleep(.1)
  action('display',value='station_6');time.sleep(.5);until(lambda:state()['board_stats']['depth']==0)
  action('pause');until(lambda:not state()['busy']);after=state();records=[r for r in store.all() if r['id'] not in previous];checks=[]
  timeline=json.loads((R/'data/real_tiles/video_manifest.json').read_text())['timeline']
  for e in records:
   im=(R/'review_records'/(e['id']+'.png')).read_bytes();mask=np.asarray(Image.open(R/'review_records'/(e['id']+'_mask.png')))>0
   expected,_=detect(Image.open(io.BytesIO(im)),threshold=89);rr=regions(expected);code=barcode(im)
   tile=[t for t in timeline[code]['visible'] if t['x']<=640<t['x']+500] if code<len(timeline) else []
   checks.append(dict(key=e['id'],product=e['product_id'],mask_mismatch=int(np.count_nonzero(mask!=expected)),boxes_match=e['boxes']==rr['boxes'],areas_match=e['region_areas']==rr['areas'],full=e['selection_full_tile'],source_code=code,source_crack=len(tile)==1 and tile[0]['label']=='crack',center_error=abs(tile[0]['x']+250-640) if len(tile)==1 else None))
  assert all(e['pixel_crc_verified'] and e['header_crc_verified'] and e['descriptor_crc_verified'] for e in records);assert len(records)==seconds//6 and len({e['product_id'] for e in records})==len(records)
  assert all(c['mask_mismatch']==0 and c['boxes_match'] and c['areas_match'] and c['full'] and c['source_crack'] and c['center_error']<=32 for c in checks)
  assert all(after['board_stats'][k]==before['board_stats'][k] for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'))
  received=after['transport_totals']['received_bytes']-before['transport_totals']['received_bytes'];duration=(rows[-1]['seconds']+.5)
  captures=after['captures']-before['captures'];products=after['board_stats']['products_completed']-before['board_stats']['products_completed']
  if frozen:assert captures==len(records),'Frozen mode unexpectedly requested preview frames'
  result=dict(passed=True,name=name,frozen=frozen,seconds=duration,requested_seconds=seconds,received_bytes=received,received_bytes_per_second=received/duration,host_captures=captures,saved=len(records),products=products,checks=checks,records=records,before=before,after=after,rows=rows)
  (OUT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({k:v for k,v in result.items() if k not in ('checks','records','before','after','rows')}),flush=True);return result
 except Exception as e:
  (OUT/f'failure_{name}_{time.time_ns()}.json').write_text(json.dumps(dict(error=str(e),rows=rows,state=state()),ensure_ascii=False,indent=2),encoding='utf-8');raise
 finally:action('pause');action('storage',mode='preview',max_archive_mib=1024);action('display',value='station_6');store.db.close()

def run():
 wait_idle();action('display',value='station_6');until(lambda:source_ready('station_6'));time.sleep(.5)
 c=EventTCP('169.254.200.10');before=c.stats();assert before['version']==0x10f00
 while c.stats()['depth']:
  _,d,m,_=c.capture(89);c.ack(m[2],d[0])
 trials=[]
 for threshold,enhance in [(123,False),(89,True)]:
  b=c.stats();c.configure(threshold,enhance);time.sleep(.3);a=c.stats()
  assert a['request']==b['request'] and a['head']==b['head'] and a['tail']==b['tail']
  assert ((a['config']>>8)&255)==threshold and bool(a['config']&(1<<24))==enhance
  trials.append(dict(threshold=threshold,enhance=enhance,before=b,after=a))
 c.close();(OUT/'configure_without_capture.json').write_text(json.dumps(dict(passed=True,trials=trials),indent=2))
 action('recipe',value='mvtec_hdmi_weak_v16')
 preview=phase('normal_preview_24s',False,24)
 frozen=phase('frozen_background_60s',True,60)
 reduction=100*(1-frozen['received_bytes_per_second']/preview['received_bytes_per_second'])
 assert reduction>=90,'Expected large savings from suppressing idle preview frames'
 result=dict(passed=True,received_rate_reduction_percent=reduction,normal=dict(seconds=preview['seconds'],received_bytes=preview['received_bytes'],captures=preview['host_captures'],saved=preview['saved']),frozen=dict(seconds=frozen['seconds'],received_bytes=frozen['received_bytes'],captures=frozen['host_captures'],saved=frozen['saved']),scope='TCP application bytes received, including status and ACK headers; excludes link/TCP/IP headers. Same repeating input, different timed windows, no claim of 60 fps desktop preview.')
 (OUT/'background_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 action('freeze_preview',enabled=False);action('display',value='real_video');action('start')
if __name__=='__main__':run()

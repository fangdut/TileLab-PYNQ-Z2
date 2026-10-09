"""Exercise the real Station worker/API/archive path, not only EventTCP."""
from pathlib import Path
import sys,time,json,urllib.request,io
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'));sys.path.insert(0,str(R/'models'))
from workstation import Records
from weak_reference import detect
from regions_reference import regions
from board_v18_continuous import action,state,wait_idle,barcode
OUT=R/'reports/v132';OUT.mkdir(exist_ok=True)
def run():
 wait_idle();action('display',value='station_6');action('recipe',value='mvtec_hdmi_weak_v16');action('storage',mode='preview',max_archive_mib=1024);action('start')
 end=time.monotonic()+8
 while True:
  s=state()
  if s.get('frame') and s['applied_threshold']==89 and (s.get('board_stats') or {}).get('depth')==0:break
  if time.monotonic()>end:raise TimeoutError('Warmup did not produce configured frame')
  time.sleep(.1)
 records=Records(R);old={r['id'] for r in records.all()};before=s['board_stats'];before_count=s['captures'];rows=[];keys=set()
 action('storage',mode='archive',max_archive_mib=1024);action('display',value='real_video');begin=time.monotonic()
 try:
  while True:
   s=state();elapsed=time.monotonic()-begin
   assert not s['error'],s['error']
   assert s['capture_health']['ready'] and not s['capture_health']['stale'],s['capture_health']
   if elapsed>=60 and s['board_stats']['current_product_id']==0:break
   if elapsed>65:raise TimeoutError('No product gap at test end')
   f=s.get('frame')
   if f:
    key=str(f['frame_id'])+'_'+f['acquired_at']
    if key not in keys:
     try:
      with urllib.request.urlopen('http://127.0.0.1:8770/api/image?frame='+urllib.parse.quote(key),timeout=2) as stream:im=stream.read()
     except urllib.error.HTTPError as e:
      if e.code==404:continue # receiver legitimately advanced >3 frames
      raise
     rows.append(dict(frame_id=f['frame_id'],barcode=barcode(im),interval_ms=0,at=time.monotonic()-begin));keys.add(key)
   time.sleep(.06)
  action('display',value='station_6');time.sleep(.5)
  deadline=time.monotonic()+5
  while state()['board_stats']['depth']:
   if time.monotonic()>deadline:raise TimeoutError('Evidence queue did not drain')
   time.sleep(.1)
  action('pause')
  while state()['busy']:time.sleep(.03)
  last=state();after=last['board_stats'];events=[r for r in records.all() if r['id'] not in old];checks=[]
  for e in events:
   im=(R/'review_records'/(e['id']+'.png')).read_bytes();mask=np.asarray(Image.open(R/'review_records'/(e['id']+'_mask.png')))>0
   expected,_=detect(Image.open(io.BytesIO(im)),threshold=89);rr=regions(expected)
   checks.append(dict(key=e['id'],product=e['product_id'],frame=e['frame_id'],barcode=barcode(im),mask_mismatch=int(np.count_nonzero(mask!=expected)),boxes_match=e['boxes']==rr['boxes'],areas_match=e['region_areas']==rr['areas'],full=e['selection_full_tile']))
  assert all(e['pixel_crc_verified'] and e['header_crc_verified'] and e['descriptor_crc_verified'] for e in events);assert len(events)==10 and len({e['product_id'] for e in events})==10
  assert all(c['mask_mismatch']==0 and c['boxes_match'] and c['areas_match'] and c['full'] for c in checks)
  assert all(after[k]==before[k] for k in ('gaps','dropped','invalid','ack_errors','descriptor_crc_errors'))
  assert not last['pending_operation'] and not last['recovery']['active'] and not last['error']
  image_bytes=sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
  assert last['storage']['image_bytes']==image_bytes
  result=dict(passed=True,seconds=elapsed,before=before,after=after,host_captures=last['captures']-before_count,saved=len(events),records=events,checks=checks,rows=rows,final_state=last)
  (OUT/'station_continuous.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps(dict(passed=True,seconds=elapsed,host_captures=result['host_captures'],saved=len(events),captures_delta=after['captured']-before['captured'],products=after['products_completed']-before['products_completed'],image_bytes=image_bytes)),flush=True)
 except Exception as e:
  (OUT/f'station_failure_{time.time_ns()}.json').write_text(json.dumps(dict(error=str(e),rows=rows,state=state()),ensure_ascii=False,indent=2),encoding='utf-8');raise
 finally:action('pause');action('storage',mode='preview',max_archive_mib=1024);action('display',value='station_6');records.db.close()
if __name__=='__main__':run()

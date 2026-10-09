"""Real board validation: preview never auto-archives, then bounded auto-store."""
from pathlib import Path
import json,time,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import board_v13_acceptance as t
T=R/'reports/storage_20260926'
def idle():
 t.action('pause');deadline=time.monotonic()+10
 while t.state()['busy']:
  if time.monotonic()>deadline:raise TimeoutError('receiver busy')
  time.sleep(.05)
def png_bytes():return sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
def run():
 idle();t.action('display',value='station_6');t.action('recipe',value='mvtec_hdmi_v15')
 t.action('storage',mode='preview',max_archive_mib=1024)
 t.action('start');time.sleep(1);idle()
 before=t.action('status');initial=t.state();size=png_bytes()
 t.action('display',value='real_video');t.action('start');time.sleep(36)
 # Stop the source while the receiver still drains the event queue.
 t.action('display',value='station_6');time.sleep(1);idle()
 after=t.action('status');end=t.state()
 preview=dict(before=before,after=after,initial_records=initial['records_total'],final_records=end['records_total'],image_bytes_before=size,image_bytes_after=png_bytes(),captures=end['captures']-initial['captures'],not_archived=end['storage']['not_archived_events']-initial['storage']['not_archived_events'])
 preview['passed']=preview['captures']>100 and preview['not_archived']>=5 and preview['initial_records']==preview['final_records'] and preview['image_bytes_before']==preview['image_bytes_after'] and all(after[k]==before[k] for k in ('gaps','invalid','dropped')) and not end['error']
 (T/'live_preview.json').write_text(json.dumps(preview,ensure_ascii=False,indent=2),encoding='utf-8')
 assert preview['passed']
 # A brief explicit archive-mode check retains just two new product events.
 limit=max(1024,(end['storage']['used_bytes']//1048576)+32)
 t.action('storage',mode='archive',max_archive_mib=limit)
 initial=t.state();t.action('display',value='real_video');t.action('start');deadline=time.monotonic()+25
 while time.monotonic()<deadline:
  time.sleep(.25);s=t.state()
  if s['error']:raise AssertionError(s['error'])
  if s['records_total']>=initial['records_total']+2:break
 t.action('display',value='station_6');time.sleep(.7);idle();end=t.state()
 archive=dict(initial_records=initial['records_total'],final_records=end['records_total'],new_records=end['records_total']-initial['records_total'],error=end['error'])
 archive['passed']=2<=archive['new_records']<=3 and not archive['error']
 (T/'live_archive.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2),encoding='utf-8')
 assert archive['passed']
 t.action('storage',mode='preview',max_archive_mib=1024)
 t.action('display',value='real_video');t.action('start')
 print(json.dumps(dict(preview=preview,archive=archive,final='Live preview only; automatic images are not saved'),ensure_ascii=False))
try:run()
except Exception:
 t.action('display',value='station_6');idle();raise

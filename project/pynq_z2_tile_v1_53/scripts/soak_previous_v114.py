"""Ten-minute V1.14 baseline during V1.15 build. No archive writes."""
from pathlib import Path
import time,json,urllib.request
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/baseline_v114_soak.json'
def state():
 with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=3) as f:return json.load(f)
def action(op,**kw):
 with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8770/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'}),timeout=3) as f:return json.load(f)
assert not O.exists();before=state()
assert before['revision']=='V1.14' and before['enabled'] and before['stimulus']=='real_video' and before['storage']['mode']=='preview'
rows=[];begin=time.monotonic();frozen=False
action('freeze_preview',enabled=False)
try:
 while True:
  s=state();elapsed=time.monotonic()-begin
  assert s['revision']=='V1.14' and not s['error'] and s['enabled'] and s['board_connected']
  assert s['board_stats']['version']==0x10e00 and s['board_stats']['boot_id']==before['board_stats']['boot_id']
  assert s['storage']['mode']=='preview' and s['storage']['image_bytes']==before['storage']['image_bytes']
  assert s['records_total']==before['records_total'] and s['storage']['auto_saved']==before['storage']['auto_saved']
  assert all(s['board_stats'][k]==before['board_stats'][k] for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'))
  assert s['board_stats']['captured']==s['board_stats']['descriptor_verified_frames']
  assert all(s['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
  rows.append(dict(seconds=elapsed,frozen=frozen,captures=s['captures'],stats=s['board_stats'],bytes=s['transport_totals']['received_bytes']))
  if elapsed>=600:break
  if elapsed>=300 and not frozen:
   action('freeze_preview',enabled=True);frozen=True
   print('V1.14 baseline: first 5 minutes passed; continuing 5 minutes with frozen preview',flush=True)
  time.sleep(.5)
 assert s['board_stats']['frames']-before['board_stats']['frames']>=elapsed*59
 result=dict(passed=True,release_tested='V1.14',scope='Prior-release 5 min normal preview + 5 min frozen background during V1.15 build; preview storage deliberately does not archive events; not V1.15 endurance or physical camera validation',seconds=elapsed,before=before,after=s,rows=rows,new_images=0,new_records=0)
 O.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(dict(passed=True,release='V1.14',seconds=elapsed,frames=s['board_stats']['frames']-before['board_stats']['frames'],host_captures=s['captures']-before['captures'],new_images=0)),flush=True)
except Exception as e:
 (O.parent/'baseline_v114_soak_failure.json').write_text(json.dumps(dict(error=str(e),rows=rows,state=state()),ensure_ascii=False,indent=2),encoding='utf-8');raise
finally:action('freeze_preview',enabled=before['preview_frozen'])

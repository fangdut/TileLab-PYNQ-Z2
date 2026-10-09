"""Five-minute prior-release baseline during V1.14 build; not V1.14 proof."""
from pathlib import Path
import time,json,urllib.request
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/baseline_v113_soak.json'
def state():
    with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=3) as f:return json.load(f)
def action(op,**kw):
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8770/api/action',data=json.dumps(dict(op=op,**kw)).encode(),headers={'Content-Type':'application/json'}),timeout=3) as f:return json.load(f)
assert not O.exists()
s=state();assert s['revision']=='V1.13' and s['enabled'] and s['stimulus']=='real_video' and s['storage']['mode']=='preview'
before=s;rows=[];begin=time.monotonic();action('freeze_preview',enabled=True)
try:
    while True:
        s=state();elapsed=time.monotonic()-begin
        assert s['revision']=='V1.13' and not s['error'] and s['enabled']
        assert s['storage']['mode']=='preview' and s['storage']['image_bytes']==before['storage']['image_bytes']
        assert s['records_total']==before['records_total'] and s['storage']['auto_saved']==before['storage']['auto_saved']
        assert all(s['board_stats'][k]==before['board_stats'][k] for k in ('gaps','invalid','dropped','ack_errors'))
        rows.append(dict(seconds=elapsed,captures=s['captures'],stats=s['board_stats'],bytes=s['transport_totals']['received_bytes']))
        if elapsed>=300:break
        time.sleep(.5)
    assert s['board_stats']['frames']-before['board_stats']['frames']>=elapsed*59
    result=dict(passed=True,release_tested='V1.13',scope='Prior-release baseline during V1.14 build; preview mode deliberately does not archive events',seconds=elapsed,before=before,after=s,rows=rows,new_images=0,new_records=0)
    O.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,release='V1.13',seconds=elapsed,frames=s['board_stats']['frames']-before['board_stats']['frames'],host_event_captures=s['captures']-before['captures'],new_images=0)),flush=True)
finally:action('freeze_preview',enabled=False)

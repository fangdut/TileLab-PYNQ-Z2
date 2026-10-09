"""Actual unchanged V1.29 server, isolated fixtures; reproduce stale overwrite."""
from pathlib import Path
import sys,json,threading,urllib.request,hashlib
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_29';O=R/'reports/v132/review_baseline';O.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(B/'host'))
from workstation import Station,ThreadingHTTPServer,handler
import test_workstation as fixtures
station=Station(O,fixtures.DummyBridge());server=ThreadingHTTPServer(('127.0.0.1',0),handler(station));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
def post(payload):
    req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/review',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as f:return dict(status=f.status,body=json.load(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
try:
    f,im,mask=fixtures.FrameTests().decode(fixtures.FrameTests().packet());key=station.records.save(f,im,mask,'isolated_protocol_test')
    observed_a=station.records.all()[0];observed_b=station.records.all()[0]
    first=post(dict(id=key,review='confirmed_crack',note='Window A: checked crack'))
    second=post(dict(id=key,review='false_alarm',note='Window B: old page overwrote A'))
    final=station.records.all()[0]
    assert observed_a==observed_b and first['status']==second['status']==200 and final['note']=='Window B: old page overwrote A'
    manifest=json.loads((B/'DELIVERY_MANIFEST.json').read_text());assert sha(B/'host/workstation.py')==manifest['source_sha256']['host/workstation.py']
    result=dict(counterexample_reproduced=True,baseline='V1.29',baseline_source_sha256=sha(B/'host/workstation.py'),first=first,second=second,final=final,scope='Two logical clients of unchanged V1.29 HTTP API; isolated artificial fixture only. No production review or board was changed.')
    (O/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='final'}))
finally:station.exit=True;station.worker.join(2);server.shutdown();server.server_close();station.records.db.close()

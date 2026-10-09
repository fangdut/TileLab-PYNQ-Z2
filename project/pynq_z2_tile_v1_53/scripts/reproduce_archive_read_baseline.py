"""Read-only baseline code; bounded isolated evidence copy retained for audit."""
from pathlib import Path
import sys,json,threading,urllib.request,hashlib,io
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_28';O=R/'reports/v132/archive_baseline';O.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(B/'host'))
from workstation import Station,ThreadingHTTPServer,handler
from test_workstation import FrameTests,DummyBridge
from PIL import Image
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
station=Station(O,DummyBridge());server=ThreadingHTTPServer(('127.0.0.1',0),handler(station));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    f,original,mask=FrameTests().decode(FrameTests().packet());key=station.records.save(f,original,mask,'isolated_protocol_test')
    (O/'original_before.png').write_bytes(original);p=station.records.file(key);p.write_bytes(original+b'TILE_TEST_TRAILING_CORRUPTION')
    Image.open(io.BytesIO(p.read_bytes())).load()
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/image?id={key}') as response:
        body=response.read();status=response.status;cache=response.headers.get('Cache-Control')
    recorded=station.records.all()[0]['image_sha256'];received=hashlib.sha256(body).hexdigest()
    assert status==200 and recorded!=received and body==p.read_bytes()
    manifest=json.loads((B/'DELIVERY_MANIFEST.json').read_text());assert sha(B/'host/workstation.py')==manifest['source_sha256']['host/workstation.py']
    result=dict(counterexample_reproduced=True,baseline='V1.28',baseline_source_sha256=sha(B/'host/workstation.py'),http_status=status,cache_control=cache,image_still_decodable=True,stored_sha256=recorded,received_sha256=received,
        scope='Only an isolated artificial protocol fixture was changed. Existing project evidence and board were untouched.')
    (O/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:station.exit=True;station.worker.join(2);server.shutdown();server.server_close();station.records.db.close()

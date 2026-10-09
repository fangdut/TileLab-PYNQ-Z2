"""Bounded isolated UI server using copies of validated real board evidence."""
from pathlib import Path
import sys,json,hashlib,time,threading
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_28';O=R/'reports/v132/archive_ui';O.mkdir(parents=True,exist_ok=False)
(O/'host').mkdir();(O/'pristine').mkdir();sys.path.insert(0,str(R/'host'))
from workstation import Station,ThreadingHTTPServer,handler
class NoCapture:
    def capture(self,*args):raise RuntimeError('Isolated archive test server does not capture live hardware')
    def close(self):pass
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((B/'reports/v128/station_continuous.json').read_text());assert source['passed'];station=Station(O,NoCapture());fixtures=[]
for row in source['records'][:2]:
    key=row['id'];image=(B/'review_records'/(key+'.png')).read_bytes();mask=(B/'review_records'/(key+'_mask.png')).read_bytes()
    assert hashlib.sha256(image).hexdigest()==row['image_sha256'] and hashlib.sha256(mask).hexdigest()==row['mask_sha256']
    saved=station.records.save(row,image,mask,'copied_real_board_test');assert saved==key
    station.records.update(saved,'needs_recheck','自动化复核测试副本；原工程证据未修改')
    (O/'pristine'/(key+'.png')).write_bytes(image);(O/'pristine'/(key+'_mask.png')).write_bytes(mask)
    fixtures.append(dict(id=key,frame_id=row['frame_id'],product_id=row['product_id'],image_sha256=row['image_sha256'],mask_sha256=row['mask_sha256'],source_project=str(B)))
meta=dict(source_manifest_sha256=sha(B/'DELIVERY_MANIFEST.json'),scope='Copies of real V1.28 board evidence. No physical capture at this isolated server. Original project and evidence are never changed.',fixtures=fixtures)
(O/'fixture.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
server=ThreadingHTTPServer(('127.0.0.1',8771),handler(station));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();print('http://127.0.0.1:8771 isolated archive verification',flush=True)
try:
    deadline=time.monotonic()+1200
    while time.monotonic()<deadline and not (O/'stop.request').exists():time.sleep(.2)
finally:
    station.exit=True;station.worker.join(2);server.shutdown();server.server_close();station.records.db.close();print('Isolated test server closed',flush=True)

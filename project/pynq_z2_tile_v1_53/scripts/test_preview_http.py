"""Actual HTTP API/HTML integration while acquisition remains stopped."""
from pathlib import Path
import json,sys,tempfile,threading,urllib.request,urllib.error,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v134';sys.path.insert(0,str(R/'host'))
from workstation import Station,EthernetBridge,ThreadingHTTPServer,handler
with tempfile.TemporaryDirectory(prefix='tile_preview_http_') as root:
    station=Station(root,EthernetBridge('169.254.200.10'))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(station));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    base=f'http://127.0.0.1:{server.server_port}';rows=[]
    def state():
        with urllib.request.urlopen(base+'/api/state',timeout=3) as f:return json.load(f)
    def action(value):
        req=urllib.request.Request(base+'/api/action',data=json.dumps(dict(op='preview_rate',value=value)).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=3) as f:return json.load(f)
    try:
        s=state();assert s['revision']=='V1.34' and s['preview_rate_fps']==2 and s['preview_rate_supported']
        with urllib.request.urlopen(base,timeout=3) as f:html=f.read()
        assert html==(R/'host/workstation.html').read_bytes() and b'id="previewRate"' in html
        for value in (5,0,2):
            action(value);s=state();assert s['preview_rate_fps']==value
            assert not s['enabled'] and s['captures']==0 and not s['board_connected']
            rows.append(dict(rate=value,confirmed=True,captures=0,board_connected=False))
        for bad in (True,3,'5',None):
            try:action(bad)
            except urllib.error.HTTPError as error:assert error.code==400
            else:raise AssertionError('Invalid preview rate accepted')
            assert state()['preview_rate_fps']==2
        assert station.bridge.transport.requests_sent==0
        result=dict(passed=True,html_sha256=hashlib.sha256(html).hexdigest(),rates=rows,invalid_values_rejected=4,board_requests=0,scope='Actual HTTP API and served HTML; no browser rendering or physical board connection',browser_visual_check=dict(performed=False,reason='CUA browser inventory failed with nodeRepl.fetch request failed'))
        (O/'preview_http.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
    finally:
        station.exit=True;station.worker.join(3);server.shutdown();server.server_close();worker.join(3);station.bridge.close();station.records.db.close()

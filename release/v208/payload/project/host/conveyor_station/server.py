# SPDX-License-Identifier: MIT
"""Photo conveyor -> browser frame capture -> existing V202 FPGA station.

Only the existing station talks to the board. This application orchestrates
motion, checks captured pixels, displays the PL overlay, and records review.
"""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, quote
import argparse, datetime, hashlib, io, json, threading, time, uuid
from PIL import Image

HERE = Path(__file__).resolve().parent
IDLE = {'READY', 'RELEASED', 'SEGREGATED', 'REMOVED'}
HOLDS = {'REVIEW_HOLD', 'GOOD_HOLD', 'DEFECT_HOLD', 'CONFLICT_HOLD'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class StationAPI:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.opener = build_opener(ProxyHandler({}))

    def request(self, path, body=None, headers=None):
        req = Request(self.base+path, data=body, headers=headers or {})
        read_state = body is None and path == '/api/state'
        # Only idempotent state reads may retry. Uploads, inference requests,
        # reviews and disposition are never blindly replayed after a timeout.
        for attempt in range(5 if read_state else 1):
            try:
                with self.opener.open(req, timeout=2 if read_state else 25) as response:
                    return response.read()
            except HTTPError as error:
                raise ValueError(json.loads(error.read()).get('error', str(error))) from error
            except (URLError, OSError):
                if not read_state or attempt == 4:
                    raise
                time.sleep(.15)

    def state(self):
        return json.loads(self.request('/api/state'))

    def action(self, op, **fields):
        s = self.state()
        body = dict(session=s['session'], revision=s['revision'], op=op, **fields)
        return json.loads(self.request('/api/action', json.dumps(body).encode(),
                                      {'Content-Type': 'application/json'}))


from flow import Conveyor

class LocalHTTPServer(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True

def handler(flow):
    class Handler(BaseHTTPRequestHandler):
        def send(self, value, mime='application/json; charset=utf-8', code=200):
            raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            try:
                path=urlparse(self.path).path
                if path in ['/','/display']:
                    return self.send((HERE/'app.html').read_bytes(),'text/html; charset=utf-8')
                if path=='/app.js':
                    return self.send((HERE/'app.js').read_bytes(),'application/javascript; charset=utf-8')
                if path=='/api/state':
                    return self.send(flow.snapshot())
                if path.startswith('/photo/'):
                    row=flow.catalog[path.rsplit('/',1)[1]]
                    raw=Path(row['file']).read_bytes()
                    if sha(raw)!=row['sha256']: raise ValueError('照片校验失败')
                    return self.send(raw,'image/png')
                if path=='/image':
                    return self.send(flow.api.request(self.path),'image/png')
                self.send({'error':'not found'},code=404)
            except Exception as error:
                self.send({'error':str(error)},code=409)

        def do_POST(self):
            try:
                if self.headers.get('Origin') not in [None,'http://'+self.headers.get('Host','')]:
                    raise ValueError('跨域操作已拒绝')
                length=int(self.headers.get('Content-Length','0'))
                limit=10*1024*1024 if self.path=='/api/capture' else 12000
                if not 0<length<=limit: raise ValueError('请求大小无效')
                raw=self.rfile.read(length)
                if len(raw)!=length: raise ValueError('截帧传输不完整')
                if self.path=='/api/action':
                    return self.send(flow.action(json.loads(raw)))
                if self.path=='/api/capture':
                    return self.send(flow.capture(self.headers.get('X-Capture-Token'),raw))
                self.send({'error':'not found'},code=404)
            except Exception as error:
                self.send({'error':str(error)},code=409)

        def log_message(self, fmt, *args):
            if self.command!='GET': super().log_message(fmt,*args)
    return Handler


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--station',default='http://127.0.0.1:8793')
    p.add_argument('--port',type=int,default=8794)
    p.add_argument('--store',type=Path,default=HERE/'runtime')
    a=p.parse_args()
    server=LocalHTTPServer(('127.0.0.1',a.port),BaseHTTPRequestHandler)
    config=json.loads(a.config.read_text(encoding='utf8'))
    cat=(a.config.parent/config['catalog']).resolve()
    rows=json.loads(cat.read_text(encoding='utf8'))
    catalog={}
    for row in rows:
        if row.get('profile_id_hint')=='texture':
            row['file']=str((cat.parent/row['file']).resolve())
            catalog[row['id']]=row
    store=a.store/('run_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
    flow=Conveyor(StationAPI(a.station),catalog,store)
    server.RequestHandlerClass=handler(flow)
    def monitor():
        while True:
            try: flow.tick()
            except Exception as error:
                with flow.lock:
                    if flow.phase!='FAULT': flow.fail(error)
            time.sleep(.2)
    threading.Thread(target=monitor,daemon=True).start()
    print(json.dumps(dict(url=f'http://127.0.0.1:{a.port}',store=str(store)),ensure_ascii=False),flush=True)
    server.serve_forever()


if __name__=='__main__': main()

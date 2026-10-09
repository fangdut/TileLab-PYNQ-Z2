"""Local review application. It displays supplied boxes and never runs detection.

Current input is explicitly OFFLINE_REFERENCE. Board frame transport is pending.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
import argparse,json,mimetypes,threading,hashlib,shutil,webbrowser

ROOT=Path(__file__).resolve().parents[1]
VALID_REVIEW={'pending','confirmed_crack','false_alarm'}

class Store:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.dir=self.root/'review_records';self.dir.mkdir(exist_ok=True)
        self.path=self.dir/'reviews.json';self.lock=threading.Lock()
        self.items={r['id']:r for r in json.loads((self.root/'data/manifest.json').read_text())['items']}
        self.reviews=json.loads(self.path.read_text(encoding='utf8')) if self.path.exists() else {}
    def save(self):
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(self.reviews,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(self.path)
    def capture(self,key):
        if key not in self.items:raise ValueError('Unknown sample')
        row=self.items[key]
        if not row['alarm']:return dict(saved=False,reason='No candidate alarm')
        with self.lock:
            if key not in self.reviews:
                image=self.root/'data'/row['image'];dest=self.dir/(key+'.png');shutil.copy2(image,dest)
                self.reviews[key]=dict(id=key,review='pending',note='',provenance='OFFLINE_REFERENCE',
                    frame_id=key,boxes=row['boxes'],image_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
                self.save()
        return dict(saved=True,record=self.reviews[key])
    def update(self,key,status,note):
        if key not in self.reviews or status not in VALID_REVIEW or not isinstance(note,str) or len(note)>2000:raise ValueError('Invalid review')
        with self.lock:
            self.reviews[key].update(review=status,note=note);self.save()
        return self.reviews[key]

def handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send_json(self,obj,status=200):
            data=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            u=urlparse(self.path)
            if u.path=='/api/state':return self.send_json(dict(mode='OFFLINE_REFERENCE',board_connected=False,
                capture_transport='NOT_IMPLEMENTED',items=list(store.items.values()),reviews=list(store.reviews.values())))
            if u.path=='/api/export':return self.send_json(dict(origin='OFFLINE_REFERENCE',records=list(store.reviews.values())))
            if u.path=='/':p=ROOT/'host/index.html'
            elif u.path=='/player':p=ROOT/'host/player.html'
            elif u.path=='/image':
                key=parse_qs(u.query).get('id',[''])[0]
                if key not in store.items:return self.send_json({'error':'Unknown image'},404)
                p=store.root/'data'/store.items[key]['image']
            elif u.path=='/video':
                name=parse_qs(u.query).get('name',[''])[0]
                allowed={'hdmi_stationary_SYNTHETIC_720p60.mp4','hdmi_motion_CHALLENGE_720p60.mp4','hdmi_photo_AI_SYNTHETIC_720p60.mp4'}
                if name not in allowed:return self.send_json({'error':'Unknown video'},404)
                p=store.root/'data'/name
            else:return self.send_json({'error':'Not found'},404)
            if not p.is_file():return self.send_json({'error':'Missing local asset'},404)
            total=p.stat().st_size;start,end=0,total-1;status=200
            rang=self.headers.get('Range','')
            if rang:
                import re
                m=re.fullmatch(r'bytes=(\d+)-(\d*)',rang)
                if not m:return self.send_json({'error':'Invalid range'},416)
                start=int(m[1]);end=min(int(m[2]) if m[2] else end,end)
                if start>end:return self.send_json({'error':'Invalid range'},416)
                status=206
            self.send_response(status);self.send_header('Content-Type',mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{total}')
            self.end_headers()
            try:
                with p.open('rb') as f:
                    f.seek(start);left=end-start+1
                    while left:
                        b=f.read(min(65536,left));self.wfile.write(b);left-=len(b)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):
            try:
                origin=self.headers.get('Origin')
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>8192:raise ValueError('Invalid body size')
                # Drain only a bounded body before closing a rejected request.
                # Windows can otherwise reset the socket before 403 arrives.
                self.connection.settimeout(2);payload=self.rfile.read(n)
                if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:return self.send_json({'error':'Local origin required'},403)
                body=json.loads(payload)
                if self.path=='/api/capture':result=store.capture(body['id'])
                elif self.path=='/api/review':result=store.update(body['id'],body['review'],body.get('note',''))
                else:return self.send_json({'error':'Not found'},404)
                self.send_json(result)
            except (ValueError,KeyError,TypeError) as e:self.send_json({'error':str(e)},400)
    return Handler

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8768);ap.add_argument('--open',action='store_true');args=ap.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(Store()))
    url=f'http://127.0.0.1:{args.port}';print(f'{url} | OFFLINE_REFERENCE | hardware image transport pending',flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()

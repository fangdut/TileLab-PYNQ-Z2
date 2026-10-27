"""Local operator interface. All inference uses the physical FPGA backend."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import argparse
import json
import re
from controller import FPGABackend, Station

HERE = Path(__file__).resolve().parent


def handler(station):
    class Handler(BaseHTTPRequestHandler):
        def send(self, value, content='application/json; charset=utf-8', code=200):
            raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode('utf8')
            self.send_response(code)
            self.send_header('Content-Type', content)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            try:
                url = urlparse(self.path)
                if url.path == '/':
                    return self.send((HERE/'app.html').read_bytes(), 'text/html; charset=utf-8')
                if url.path == '/api/state':
                    return self.send(station.state())
                if url.path == '/image':
                    args = parse_qs(url.query)
                    ident = args.get('cycle', [''])[0]
                    name = args.get('kind', ['input'])[0]
                    if not re.fullmatch('[a-f0-9]{32}', ident) or name not in ['input', 'overlay', 'mask']:
                        raise ValueError('Invalid image request')
                    folder = station.store/'cycles'/ident
                    file = folder/'source.png' if name == 'input' else folder/'fpga'/(name+'.png')
                    raw = file.read_bytes()
                    return self.send(raw, 'image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg')
                self.send(dict(error='Not found'), code=404)
            except Exception as error:
                self.send(dict(error=str(error)), code=400)

        def do_POST(self):
            try:
                if self.headers.get('Origin') not in [None, 'http://'+self.headers.get('Host', '')]:
                    raise ValueError('Cross-origin action rejected')
                size = int(self.headers.get('Content-Length', '0'))
                if self.path == '/api/upload':
                    if not 0 < size <= 10*1024*1024:
                        raise ValueError('图片文件必须小于10MB')
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError('图片上传不完整')
                    return self.send(station.add_image(raw,
                        unquote(self.headers.get('X-File-Name', 'local_photo'))))
                if self.path != '/api/action':
                    return self.send(dict(error='Not found'), code=404)
                if not 0 < size <= 4096:
                    raise ValueError('Invalid request size')
                self.send(station.action(json.loads(self.rfile.read(size))))
            except Exception as error:
                self.send(dict(error=str(error)), code=409)

        def log_message(self, fmt, *args):
            if self.command != 'GET' or not self.path.startswith('/api/state'):
                super().log_message(fmt, *args)
    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path)
    for key in ['catalog', 'profile', 'program', 'hardware', 'store']:
        p.add_argument('--'+key, type=Path)
    p.add_argument('--board', default='192.168.33.10')
    p.add_argument('--port', type=int, default=8793)
    a = p.parse_args()
    if a.config:
        config = json.loads(a.config.read_text(encoding='utf8'))
        for key in ['catalog', 'profile', 'program', 'hardware', 'store']:
            if getattr(a, key) is None:
                setattr(a, key, (a.config.parent/config[key]).resolve())
        a.board = config.get('board', a.board)
        a.port = config.get('port', a.port)
    for key in ['catalog', 'profile', 'program', 'hardware', 'store']:
        if getattr(a, key) is None:
            p.error('--'+key+' or --config is required')
    # A fixed endpoint refuses a second instance before it can talk to the board.
    server = ThreadingHTTPServer(('127.0.0.1', a.port), BaseHTTPRequestHandler)
    try:
        rows = json.loads(a.catalog.read_text(encoding='utf8'))
        for row in rows:
            row['file'] = str((a.catalog.parent/row['file']).resolve())
        backend = FPGABackend(a.board, a.profile, a.program, a.hardware)
        station = Station(backend, rows, a.store)
        station.connection = backend.check()
        server.RequestHandlerClass = handler(station)
        print(json.dumps(dict(url=f'http://127.0.0.1:{a.port}',
            scope='PHYSICAL_FPGA_STOP_INSPECT_PHOTO_DEMONSTRATOR',
            connection=station.connection), ensure_ascii=False), flush=True)
        server.serve_forever(poll_interval=.25)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()

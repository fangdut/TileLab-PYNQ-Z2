"""Single-fixture workstation. Detection remains in PL, never in this server."""
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse
import argparse,json,webbrowser
import workstation
from single_tile_profile import load,validate_wire_contract,validate_frame
ROOT=Path(__file__).resolve().parents[1]

class SingleTileBridge(workstation.EthernetBridge):
    def __init__(self,address,root=ROOT):
        super().__init__(address);self.profile=load(root);self.transport.single_tile_contract=self.profile
        self.enhance=True;self.passes=4;self.low_gate=False;self.wide_weak=self.ridge=self.pixel_boost=True
    def _request(self,threshold):
        request=self.request_parameters(threshold)
        if (request.threshold,request.enhance,request.passes,request.low_gate,request.wide_weak,request.ridge,request.wide_line,request.directional_growth,request.pixel_boost)!=(90,True,4,False,True,True,False,False,True):raise ValueError('单片版本使用冻结配方；不能在运行中切换阈值或算法')
    def _ensure_peer(self):
        # Public transport flag validation runs before its socket preflight.
        # Bootstrap cold clients using read-only status, then still recheck
        # the profile on the exact mutation socket inside EventTCP._exchange.
        if self.transport.peer_version!=self.profile['firmware_version']:self.stats()
    def configure(self,threshold):self._request(threshold);self._ensure_peer();return super().configure(threshold)
    def capture(self,threshold):
        self._request(threshold);self._ensure_peer();frame,image,mask=super().capture(threshold);validate_frame(self.profile,frame,mask);return frame,image,mask
    def stats(self):
        stats=super().stats();_,d,m=self.call(self.transport.exchange,6,0);contract=validate_wire_contract(self.profile,d,m)
        if contract['boot_id']!=stats['boot_id']:raise ValueError('Board restarted during status read; retry status')
        return dict(stats,single_tile=contract)

class SingleTileStation(workstation.Station):
    def __init__(self,root=ROOT,bridge=None):
        if bridge is None:raise ValueError('Single-tile station requires a hardware Ethernet bridge; use offline CLI for software experiments')
        self.single_profile=load(root);super().__init__(root=root,bridge=bridge)
        with self.lock:
            recipe=next((r for r in self.recipe_catalog if r['id']=='single_tile_v164_integer_boost'),None)
            if recipe is None:raise ValueError('Missing single-tile recipe')
            self.recipe_catalog=[recipe];self.recipe_id=recipe['id'];self.threshold=90
            self.bridge.passes=4
            self.preview_policy=workstation.PreviewPolicy(2)
    def action(self,body):
        if body.get('op')=='threshold':raise ValueError('单片检测参数已冻结；更换花色或材质须单独标定和验证')
        if body.get('op')=='recipe' and body.get('value')!=self.single_profile['recipe_id']:raise ValueError('Only the fixed single-tile recipe is available')
        allowed={'station_6'}|{f'real_{i:03}' for i in list(range(17))+list(range(35,68))}
        if body.get('op')=='display' and body.get('value') not in allowed:raise ValueError('单片演示只开放17张裂纹、33张正常静态照片及空视野；其他缺陷和墙面需单独验证')
        return super().action(body)
    def live_state(self):
        value=super().live_state();value.update(revision='V1.64',inspection_scope='single_tile',single_tile_profile=self.single_profile,accuracy_qualified=False,limitations='单片固定视野工程候选；彩绘/多材质高准确率尚未通过独立验证。无报警表示ROI未发现候选，仍需人工复核。');return value

def handler(station):
    Base=workstation.handler(station)
    class Handler(Base):
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/':return self.send((station.root/'host/single_tile.html').read_bytes(),'text/html; charset=utf-8')
            if path=='/api/benchmark':
                p=station.root/'reports/v164/QUALIFICATION.json'
                if not p.is_file():return self.send(dict(qualified=False,scope='Single-tile qualification pending; historical board results are not substituted'),code=503)
                return self.send(json.loads(p.read_text(encoding='utf-8')))
            if path=='/benchmark':return self.send((station.root/'host/single_tile_validation.html').read_bytes(),'text/html; charset=utf-8')
            if path.startswith('/validation/'):
                name=path[len('/validation/'):]
                allowed={'':'validation.html','QUALIFICATION.json':'QUALIFICATION.json','OOF_HISTORICAL_ACQUIRED.json':'OOF_HISTORICAL_ACQUIRED.json','OOF_STIMULUS.json':'OOF_STIMULUS.json'}
                if name not in allowed:return self.send(dict(error='Unknown validation artifact'),code=404)
                file=station.root/'reports/v164'/allowed[name]
                if not file.is_file():return self.send(dict(error='Current validation artifact is unavailable'),code=503)
                return self.send(file.read_bytes(),'text/html; charset=utf-8' if name=='' else 'application/json; charset=utf-8')
            if path=='/api/benchmark-image':return self.send(dict(error='Use the source-linked current validation report; legacy board photos are historical'),code=410)
            return super().do_GET()
    return Handler

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ethernet',required=True,help='Private IPv4 board address');ap.add_argument('--port',type=int,default=8770);ap.add_argument('--open',action='store_true');args=ap.parse_args();station=SingleTileStation(bridge=SingleTileBridge(args.ethernet));server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(station));url=f'http://127.0.0.1:{args.port}';print(url+' | TileLab V1.64 single-tile hardware station',flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:station.exit=True;station.live_cache.close();station.bridge.close();server.server_close()
if __name__=='__main__':main()

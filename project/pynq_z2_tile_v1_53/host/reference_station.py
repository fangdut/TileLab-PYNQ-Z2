"""Single-tile per-pattern calibration workstation using real FPGA scores."""
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
import argparse,datetime,hashlib,io,json,re,sys,uuid
import numpy as np
from PIL import Image
import workstation
from reference_capture import Capture
from reference_frame_tcp import inspect as hardware_inspect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/reference_tile'))
import reference_tile as base
import reference_v166 as v166
import frame_v167

class Station:
    def __init__(self,address,store):
        self.address=address;self.capture=Capture(address);self.store=Path(store);self.store.mkdir(parents=True,exist_ok=True)
        self.calibrations=self.store/'calibrations';self.calibrations.mkdir(exist_ok=True);self.last=None
        self.loaded_implementation=frame_v167.implementation()
    def save(self,path,data):workstation.atomic(path,data)
    def json(self,path,value):self.save(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    def acquire(self,folder):
        frame,png,_=self.capture.capture();folder.mkdir(parents=True,exist_ok=False)
        self.save(folder/'input.png',png);self.json(folder/'capture.json',frame)
        self.capture.ack(frame);self.json(folder/'ack.json',dict(boot_id=frame['boot_id'],event_id=frame['event_id'],acknowledged=True))
        with Image.open(io.BytesIO(png)) as im:array=np.array(im.convert('RGB'))
        return frame,array
    def action(self,body):
        if frame_v167.implementation()!=self.loaded_implementation:raise ValueError('算法源码已变化，请重新启动工作站并重新标定')
        pattern=body.get('pattern','')
        if not re.fullmatch('[A-Za-z0-9_-]{1,64}',pattern):raise ValueError('花色编号请使用1–64个字母、数字、下划线或减号')
        op=body.get('op');identifier=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]
        if op=='calibrate':
            if body.get('declared_good') is not True:raise ValueError('标定前需要确认当前是该花色的完整良品')
            folder=self.store/'captures'/identifier;frame,array=self.acquire(folder)
            quality,_,_,_=frame_v167.prepare(array,array)
            if quality['status']!='PREPARED':raise ValueError('参照画面缺少可用定位信息：'+quality['reason'])
            target=self.calibrations/pattern/identifier
            record=frame_v167.calibrate(folder/'input.png',pattern,target)
            record=dict(bundle=target.relative_to(self.store).as_posix(),bundle_sha256=record['bundle_sha256'],capture=folder.relative_to(self.store).as_posix(),capture_identity=frame)
            self.json(self.calibrations/pattern/'active.json',record);self.last=dict(status='CALIBRATED',pattern=pattern,reference=record,preview=str(folder/'input.png'))
        elif op=='inspect':
            active=json.loads((self.calibrations/pattern/'active.json').read_text(encoding='utf8'));bundle=self.store/active['bundle']
            # Reuse the frozen bundle integrity checks without running its
            # software detector: validate all identities before acquisition.
            record=json.loads((bundle/'calibration.json').read_text(encoding='utf8'));digest=record.pop('bundle_sha256')
            if record['schema']!=3 or digest!=active['bundle_sha256'] or hashlib.sha256(base.canonical(record)).hexdigest()!=digest or record['material_id']!=pattern or record['implementation_sha256']!=frame_v167.implementation() or record['policy']!=frame_v167.policy() or base.sha(bundle/'reference.png')!=record['reference_sha256']:raise ValueError('良品参照完整性或算法版本不匹配，请重新标定')
            reference=base.read_frame(bundle/'reference.png');folder=self.store/'inspections'/identifier;frame,current=self.acquire(folder/'capture')
            result,paired,aligned,_=frame_v167.prepare(reference,current);result.update(pattern=pattern,calibration_sha256=digest,capture=frame)
            mask=None
            if paired is not None:
                words,proof=hardware_inspect(self.address,paired,result['photometric'],frame['pixel_crc32'],zlib_crc(reference))
                self.save(folder/'scores.u32',words.astype('<u4').tobytes());result,mask=frame_v167.finish(result,words,proof)
            base.save_result(folder/'result',result,mask,aligned)
            self.last=dict(result,record=folder.relative_to(self.store).as_posix(),preview=str(folder/'result/overlay.png') if mask is not None else str(folder/'capture/input.png'))
        else:raise ValueError('Unknown operation')
        self.json(self.store/'last.json',self.last);return self.last
    def state(self):
        return dict(board=self.capture.status(),patterns=sorted(p.name for p in self.calibrations.iterdir() if p.is_dir()),last=self.last,partition='电脑配准与区域筛选；FPGA完成全幅归一化和像素差分',accuracy_qualified=False)
def zlib_crc(a):
    import zlib
    return zlib.crc32(a.tobytes())
def handler(station):
    class Handler(BaseHTTPRequestHandler):
        def send(self,data,content='application/json; charset=utf-8',code=200):
            raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            try:
                if self.path=='/':return self.send((ROOT/'host/reference_station.html').read_bytes(),'text/html; charset=utf-8')
                if self.path=='/api/state':return self.send(station.state())
                if urlparse(self.path).path=='/preview' and station.last:return self.send(Path(station.last['preview']).read_bytes(),'image/png')
                self.send(dict(error='Not found'),code=404)
            except Exception as e:self.send(dict(error=str(e)),code=503)
        def do_POST(self):
            try:
                if self.path!='/api/action':return self.send(dict(error='Not found'),code=404)
                if self.headers.get('Origin') not in (None,'http://'+self.headers.get('Host','')):raise ValueError('Cross-origin actions rejected')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=4096:raise ValueError('Invalid action length')
                self.send(station.action(json.loads(self.rfile.read(n))))
            except Exception as e:self.send(dict(error=str(e)),code=400)
    return Handler
def main():
    p=argparse.ArgumentParser();p.add_argument('--ethernet',required=True);p.add_argument('--port',type=int,default=8771);p.add_argument('--store',type=Path,default=ROOT/'host/runtime/reference_v167');a=p.parse_args();s=Station(a.ethernet,a.store);server=HTTPServer(('127.0.0.1',a.port),handler(s));print(f'http://127.0.0.1:{a.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()

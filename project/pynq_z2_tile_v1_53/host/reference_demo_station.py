"""Optional clearly labeled synthetic HDMI demonstration around the core UI."""
from pathlib import Path
from http.server import HTTPServer
import argparse,hashlib,json,time,uuid
import reference_station as core
import workstation
class Demo(core.Station):
    def __init__(self,address,store,player):
        super().__init__(address,store);self.player=Path(player).resolve();self.catalog=json.loads((self.player/'manifest.json').read_text())['rows']
        if len(self.catalog)!=24 or {r['style'] for r in self.catalog}!={'floral','geometry','stripes','woodlike','grain','plain'}:raise ValueError('Expected the fixed24-image procedural demo catalog')
    def show(self,row):
        path=self.player/'data/reference_v167'/(row['source']+'.png')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['image_sha256']:raise ValueError('Demo source image changed')
        nonce=uuid.uuid4().hex;workstation.atomic(self.player/'host/display_command.txt',f"TILE_CMD_V1 {nonce} {row['source']}\n".encode());deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            try:state=json.loads((self.player/'host/player_status.json').read_text())
            except (OSError,json.JSONDecodeError):state={}
            if state.get('source')==row['source'] and state.get('request_id')==nonce and not state.get('error'):time.sleep(.45);return
            time.sleep(.05)
        raise TimeoutError('HDMI演示播放器未采用本次图像，请检查第二屏和播放器进程')
    def demo(self,body):
        style=body.get('style');kind=body.get('kind')
        if kind not in ('good','line','invalid_pose'):raise ValueError('Unknown demo case')
        reference=next((r for r in self.catalog if r['style']==style and r['kind']=='reference'),None);current=next((r for r in self.catalog if r['style']==style and r['kind']==kind),None)
        if reference is None or current is None:raise ValueError('Unknown demo pattern')
        self.show(reference);self.action(dict(op='calibrate',pattern=style,declared_good=True));self.show(current);result=self.action(dict(op='inspect',pattern=style));result['demo_scope']='PROCEDURAL_HDMI_REPLAY_NOT_REAL_TILE_NOT_CAMERA';return result
def handler(station):
    Base=core.handler(station)
    class Handler(Base):
        def do_GET(self):
            if self.path!='/':return super().do_GET()
            page=(core.ROOT/'host/reference_station.html').read_text(encoding='utf8')
            page=page.replace('</style>',(core.ROOT/'host/reference_demo.css').read_text(encoding='utf8')+'</style>',1).replace('TileLab · 单片良品参照检测','TileLab · 单片参照检测',1)
            controls='''<section style="background:#fff4db;padding:16px;border-radius:10px;margin:16px 0"><strong>一键上板演示：程序生成图像经真实 HDMI 回放，非实体瓷砖或相机实拍</strong><br><select id="demoStyle" style="font:inherit;padding:10px"><option value="floral">花卉彩绘</option><option value="geometry">几何彩绘</option><option value="stripes">条纹</option><option value="woodlike">木纹模拟</option><option value="grain">颗粒纹理模拟</option><option value="plain">纯色</option></select><button onclick="demo('good')">良品演示</button><button onclick="demo('line')">人工细线演示</button><button onclick="demo('invalid_pose')">位姿拒判演示</button></section>'''
            page=page.replace('<div id="status">',controls+'<div id="status">',1)
            script='''<script>async function demo(kind){document.querySelectorAll('button').forEach(b=>b.disabled=true);box.textContent='正在显示良品、完成标定并由 FPGA 检测演示图像…';try{let r=await fetch('/api/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({style:document.querySelector('#demoStyle').value,kind})}),d=await r.json();if(!r.ok)throw Error(d.error);box.textContent=d.status==='REJECTED_INPUT'?'演示结果：输入拒判，请复核':d.alarm?'演示结果：发现人工表面变化候选':'演示结果：未发现变化候选，仍需复核';detail.textContent=JSON.stringify(d,null,2);preview.src='/preview?'+Date.now();preview.hidden=false;document.querySelector('#pattern').value=document.querySelector('#demoStyle').value}catch(e){box.textContent='演示失败：'+e.message}finally{document.querySelectorAll('button').forEach(b=>b.disabled=false)}}</script>'''
            page=page.replace('</html>',script+'</html>');return self.send(page.encode(),'text/html; charset=utf-8')
        def do_POST(self):
            if self.path!='/api/demo':return super().do_POST()
            try:
                if self.headers.get('Origin') not in (None,'http://'+self.headers.get('Host','')):raise ValueError('Cross-origin actions rejected')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=4096:raise ValueError('Invalid action length')
                return self.send(station.demo(json.loads(self.rfile.read(n))))
            except Exception as error:return self.send(dict(error=str(error)),code=400)
    return Handler
def main():
    p=argparse.ArgumentParser();p.add_argument('--ethernet',required=True);p.add_argument('--player',required=True,type=Path);p.add_argument('--port',type=int,default=8771);p.add_argument('--store',type=Path,default=core.ROOT/'host/runtime/reference_v167');a=p.parse_args();station=Demo(a.ethernet,a.store,a.player);server=HTTPServer(('127.0.0.1',a.port),handler(station));print(f'http://127.0.0.1:{a.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()

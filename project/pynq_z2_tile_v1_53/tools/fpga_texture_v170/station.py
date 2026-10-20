"""Local board workstation. All detection uses TCP 9136 -> FPGA PL."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
import argparse,base64,hashlib,json,shutil,threading,time,uuid
from board_client import Board

PAGE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>TileLab V170 · FPGA 整数实拍检测</title>
<style>body{margin:0;background:#0e1720;color:#e4edf5;font:16px system-ui}main{max-width:1200px;margin:auto;padding:36px}h1{margin-bottom:8px}.muted{color:#9bb0bf}b{color:#6ae0bb}section{background:#182632;border:1px solid #2c4354;border-radius:16px;padding:24px;margin-top:20px}button,select,input{font:inherit;padding:12px;border-radius:8px;border:0;margin:5px}button{background:#6ae0bb;cursor:pointer}button:disabled{opacity:.4}select{max-width:65%}.photos{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%;border-radius:12px}pre{white-space:pre-wrap;font:14px monospace;line-height:1.7}#verdict{font-size:28px}</style>
<main><h1>TileLab V170 <b>FPGA 整数实拍检测</b></h1><p class="muted">电脑读图与显示 → 网线传输 → Zynq-7020 PL 完整推理 → 原尺寸缺陷掩码</p>
<section><b>板端推理 · 无 CPU/GPU 检测回退</b><p>PL 执行缩放、归一化、卷积网络、特征投影、正常特征比较、评分及判定。ARM 仅负责传输与控制。</p><p class="muted">当前为整数硬件候选；核内耗时与网线往返耗时分别记录。连续 HDMI 视频尚待验证。样图来自 MVTec AD Tile 实拍数据；当前证据限于该材质，尚未验证任意彩绘或多材质。</p>
<select id="samples"></select><button id="go" onclick="start(false)">发送实拍图到 FPGA</button><br><input type="file" accept="image/png,image/jpeg" id="file"><button id="upload" onclick="start(true)">检测上传图片</button><p class="muted">上传原图须不超过 1024×1024。缩放在 FPGA 内完成。</p></section>
<section><div id="status">等待请求</div><p id="verdict"></p><div class="photos"><div><p>原始实拍图片</p><img id="original"></div><div><p>FPGA 返回掩码叠加</p><img id="overlay"></div></div><pre id="proof"></pre></section>
<p class="muted">来源：<a href="https://www.mvtec.com/company/research/datasets/mvtec-ad" style="color:#6ae0bb">MVTec AD</a> · CC BY-NC-SA 4.0。离线历史测试集结果不能替代板端验收。</p></main>
<script>
async function refresh(){let s=await(await fetch('/api/state')).json();document.querySelector('#status').textContent=s.message;document.querySelector('#go').disabled=s.busy;document.querySelector('#upload').disabled=s.busy;if(s.result){let r=s.result;document.querySelector('#verdict').textContent=r.pl_image_alarm?'FPGA 判定：异常':'FPGA 判定：正常';document.querySelector('#original').src='/result/'+s.job+'/input.png';document.querySelector('#overlay').src='/result/'+s.job+'/overlay.png';document.querySelector('#proof').textContent=JSON.stringify({执行位置:'FPGA PL',板端身份:'0x'+r.pl_identity.toString(16),完成网络步骤:r.pl_completed_steps,板端峰值:r.pl_peak,板端阈值:r.pl_threshold,缺陷像素:r.pl_mask_pixels,核内计算秒:r.pl_engine_seconds,网线请求耗时秒:r.wall_seconds,硬件完成帧号:r.pl_frame_sequence,模型校验:r.model_sha256,输入校验:r.rgb_crc32,结果校验:r.result_crc32},null,2);}else{document.querySelector('#verdict').textContent='';document.querySelector('#overlay').removeAttribute('src');document.querySelector('#proof').textContent='';}}
async function start(upload){let body={id:document.querySelector('#samples').value};if(upload){let f=document.querySelector('#file').files[0];if(!f){alert('请选择图片');return;}let data=await new Promise((ok,no)=>{let r=new FileReader();r.onload=()=>ok(r.result.split(',')[1]);r.onerror=no;r.readAsDataURL(f)});body={name:f.name,data};document.querySelector('#original').src=URL.createObjectURL(f);}else{document.querySelector('#original').src='/image/'+body.id;}let r=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)alert(await r.text());await refresh();}
fetch('/api/samples').then(r=>r.json()).then(samples=>{for(let s of samples){let o=document.createElement('option');o.value=s.id;o.textContent=s.label+' · '+s.id;document.querySelector('#samples').appendChild(o)};document.querySelector('#original').src='/image/'+samples[0].id});setInterval(refresh,2000);refresh();
</script></html>'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--port',type=int,default=8789);p.add_argument('--board',default='192.168.33.10');p.add_argument('--initial-evidence',type=Path);a=p.parse_args()
    samples={v['id']:v for v in json.loads((a.dataset/'manifest.json').read_text())['images'] if v['role']=='test'}
    state=dict(busy=False,message='等待请求：仅使用板端推理',job=None,result=None);lock=threading.Lock();a.out.mkdir(parents=True,exist_ok=True)
    if a.initial_evidence:
        initial=json.loads((a.initial_evidence/'evidence.json').read_text(encoding='utf8'))
        if initial['scope']!='BOARD_FULL_PL_INFERENCE' or hashlib.sha256((a.initial_evidence/'raw_result.bin').read_bytes()).hexdigest()!=initial['result_sha256']:raise ValueError('Invalid initial evidence')
        job=uuid.uuid4().hex;folder=a.out/job;folder.mkdir()
        for name in ('input.png','mask.png','overlay.png','evidence.json'):shutil.copy2(a.initial_evidence/name,folder/name)
        state.update(job=job,result=initial,message='已完成的真实上板结果（历史记录）；可发送新图片重新检测')
    def process(spec,job):
        try:
            if 'data' in spec:
                raw=base64.b64decode(spec['data'],validate=True)
                if len(raw)>8388608:raise ValueError('图片文件过大')
                path=a.out/(job+'.upload');path.write_bytes(raw)
            else:path=a.dataset/samples[spec['id']]['file']
            state.update(message='正在连接 FPGA，并校验或上传模型；电脑未执行检测')
            board=Board(a.board);model=board.upload(a.model)
            state.update(message='FPGA PL 正在执行完整网络，请等待；网络断开会报错')
            result=board.infer(path,a.out/job,model)
            state.update(message='已收到并校验 FPGA 推理结果',job=job,result=result)
        except Exception as error:state.update(message='板端检测失败：'+str(error),job=None,result=None)
        finally:state['busy']=False;lock.release()
    class Handler(BaseHTTPRequestHandler):
        def send(self,data,kind='application/json; charset=utf-8',status=200):
            if isinstance(data,str):data=data.encode('utf8')
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/':return self.send(PAGE,'text/html; charset=utf-8')
            if path=='/api/state':return self.send(json.dumps(state,ensure_ascii=False))
            if path=='/api/samples':return self.send(json.dumps([dict(id=v['id'],label=v['label']) for v in samples.values()]))
            if path.startswith('/image/') and path.split('/')[-1] in samples:return self.send((a.dataset/samples[path.split('/')[-1]]['file']).read_bytes(),'image/png')
            parts=path.split('/')
            if len(parts)==4 and parts[1]=='result' and len(parts[2])==32 and all(c in '0123456789abcdef' for c in parts[2]) and parts[3] in ('input.png','mask.png','overlay.png','evidence.json'):
                f=a.out/parts[2]/parts[3]
                if f.is_file():return self.send(f.read_bytes(),'image/png' if f.suffix=='.png' else 'application/json')
            self.send('Not found','text/plain',404)
        def do_POST(self):
            if self.path!='/api/start':return self.send('Not found','text/plain',404)
            n=int(self.headers.get('Content-Length','0'))
            if n<1 or n>12000000:return self.send('Invalid upload size','text/plain',400)
            try:spec=json.loads(self.rfile.read(n))
            except Exception:return self.send('Invalid request','text/plain',400)
            if not lock.acquire(blocking=False):return self.send('FPGA busy','text/plain',409)
            job=uuid.uuid4().hex;state.update(busy=True,message='准备板端检测',result=None)
            threading.Thread(target=process,args=(spec,job),daemon=True).start();self.send('{"started":true}')
    print(f'FPGA-only station http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

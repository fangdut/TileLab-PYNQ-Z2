"""Render the source-bound development/board report; keep failures visible."""
from pathlib import Path
import argparse,base64,html,io,json,zipfile
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]

def data(im):
    im=im.convert('RGB');im.thumbnail((500,500));b=io.BytesIO();im.save(b,format='JPEG',quality=88);return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();out=ROOT/'reports/v166';s=json.loads((out/'MECHANISM_FINAL.json').read_text());status=json.loads((out/'STATUS.json').read_text());board=json.loads((out/'BOARD_REPLAY.json').read_text())
    groups=s['groups'];table=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [k,r['cases'],r['alarms'],r['rejected'],r['minimum_pixel_coverage']])+ '</tr>' for k,r in groups.items())
    selected=[r for r in s['rows'] if r['id'] in s['failures'] or (r['pixel_coverage'] is not None and r['pixel_coverage']<.85)]
    wanted=['floral_normal_jpeg92','geometry_normal_jpeg92','stripes_normal_jpeg92','floral_normal_2','stripes_normal_3','floral_line_0','floral_line_2','geometry_line_w3_bright0_edge1','plain_color_line_w1']
    selected+= [r for r in s['rows'] if r['id'] in wanted and r not in selected]
    selected.sort(key=lambda r:(r['id'] not in s['failures'],r['pixel_coverage'] is None,r['pixel_coverage'] if r['pixel_coverage'] is not None else 1.))
    cards=[];contact=Image.new('RGB',(1200,330*((len(selected)+3)//4)),(245,247,250));draw=ImageDraw.Draw(contact)
    for i,row in enumerate(selected):
        folder=a.work/'audit01'/row['id'];current=Image.open(folder/'current.png').crop((390,110,890,610));overlay=Image.open(folder/'overlay.png') if (folder/'overlay.png').exists() else current
        tag='FAIL' if row['id'] in s['failures'] else ('LOW COVERAGE' if row['pixel_coverage'] is not None and row['pixel_coverage']<.8 else 'DEVELOPMENT CASE')
        cards.append('<article><h3>'+html.escape(row['id'])+'</h3><p>'+tag+' · alarm='+str(row['alarm'])+' · GT coverage='+str(row['pixel_coverage'])+'</p><div class="pair"><figure><img src="'+data(current)+'"><figcaption>程序构造输入</figcaption></figure><figure><img src="'+data(overlay)+'"><figcaption>V166离线候选</figcaption></figure></div></article>')
        thumb=overlay.convert('RGB').resize((300,300));x=(i%4)*300;y=(i//4)*330;contact.paste(thumb,(x,y));draw.text((x+5,y+303),row['id'],fill=(20,25,35))
    contact.save(out/'contact.jpg',quality=90)
    with zipfile.ZipFile(out/'board_captures.zip') as z:
        hardware=[]
        for name in ['real_000','real_008','real_035','real_050']:
            im=Image.open(io.BytesIO(z.read(name+'/original.png')));mask=Image.open(io.BytesIO(z.read(name+'/pl_mask.png')))
            hardware.append('<article><h3>'+name+' · 实际HDMI回读</h3><div class="pair"><figure><img src="'+data(im.crop((390,110,890,610)))+'"><figcaption>真实板端采集的公开照片画面</figcaption></figure><figure><img src="'+data(mask.crop((390,110,890,610)))+'"><figcaption>V164 PL掩码；不是V166参照结果</figcaption></figure></div></article>')
    document='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V166 · 验收进度与实板证据</title><style>body{font:16px/1.65 "Microsoft YaHei",system-ui,sans-serif;background:#f1f4f8;color:#182335;margin:0}main{max-width:1160px;margin:auto;padding:32px}h1{line-height:1.3}h2{margin-top:40px}.notice{background:#fff0d9;border-left:5px solid #d27b00;padding:20px}article{background:white;padding:20px;margin:20px 0;border-radius:10px}table{width:100%;border-collapse:collapse;background:white;font-size:13px}td,th{text-align:left;border-bottom:1px solid #dde3ed;padding:10px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0}img{width:100%;max-width:500px}figcaption{color:#536173}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:18px}a{color:#1254a3}</style><main><h1>TileLab V166：验收进度与实板证据</h1><div class="notice"><b>尚未达到整体验收标准。</b>完整V166参照视频通路未接入板端，同花色独立真实良品／裂纹配对仍为0。合成用例、旧开发图片和算术硬件自检分别列示，不能代替目标材料真实准确率。</div><h2>本轮结果</h2><p>72个构造正常用例均无误报、无拒判；60个人工明暗线用例中检出59个，12个纯颜色线均检出，但最低像素覆盖仅69.84%。下面首先展示失败与低覆盖用例。全部用例均参与了开发调试，不是盲测。</p><table><tr><th>组别</th><th>数量</th><th>报警</th><th>拒判</th><th>最小GT覆盖</th></tr>'''+table+'''</table><h2>失败、覆盖不足与关键对照</h2>'''+''.join(cards)+'''<h2>实际板端回放</h2><p>50张已有开发图片经电脑HDMI、PYNQ-Z2 PL、DDR、以太网实际回读，掩码、报警及区域框与独立整数参考逐项一致，帧／描述符／传输CRC均通过。17张裂纹报警、33张正常无报警；图片参与过开发与模型训练，且输入为屏幕显示照片，因此不能称为真实光学或独立目标材料准确率。</p>'''+''.join(hardware)+'''<h2>硬件算术自检与当前状态</h2><p>算术自检仅覆盖配对窗口计算。它不包含窗口生成、参照DDR读取、在线对齐、光照估计及区域逻辑，不能写成整机V166算法已上板。自检镜像与视频镜像分别留证，视频工程在测试后恢复。</p><pre>'''+html.escape(json.dumps(status,ensure_ascii=False,indent=2))+'''</pre><h2>验收条件与证据</h2><p>每个支持材质／花色至少100块独立裂纹砖、400块独立良品砖；召回Wilson95%下限≥95%，误报、拒判及其合计Wilson95%上限≤1%，每张裂纹GT覆盖≥80%。这是工程目标，不是比赛官方奖项门槛。</p><p><a href="QUALIFICATION.json">验收结论与阻断项</a> · <a href="MECHANISM_FINAL.json">174个逐用例结果</a> · <a href="BOARD_REPLAY.json">50张实际板端回放记录</a> · <a href="board_captures.zip">板端原图／掩码与元数据</a> · <a href="METRIC_BOARD_PROOF.json">窗口算术上板证据</a> · <a href="metric_readback.txt">实际自检读回</a></p><p>板端回放照片源自原仓库MVTec数据，延续原数据CC BY-NC-SA 4.0许可及来源说明；程序构造纹理／线条不冒充真实瓷砖。<a href="../../DATA_PROVENANCE_V164.md">数据来源</a></p></main></html>'''
    (out/'reference_report.html').write_text(document,encoding='utf8');print(json.dumps(dict(selected_cases=len(selected),hardware_examples=4,html_bytes=len(document.encode()),accuracy_qualified=False)))

if __name__=='__main__':main()

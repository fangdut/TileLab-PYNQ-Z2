"""Render a bounded scientific comparison of offline predictions, no board I/O."""
from pathlib import Path
import argparse,base64,html,io,json,sys
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'models'),str(R/'scripts')]
from evaluate_ridge_v154 import cohort,load,sha
from directional_mean_reference import detect

def uri(a):
    stream=io.BytesIO();Image.fromarray(a).save(stream,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    if args.out.exists():raise FileExistsError(args.out)
    data=json.loads((R/'reports/v154/selected_profile_01/summary.json').read_text())
    old={(r['dataset'],r['id']):r for r in data['rows'] if r['variant']=='accepted_v152'}
    new={(r['dataset'],r['id']):r for r in data['rows'] if r['variant']=='mean_v154'}
    positives=[k for k in new if k[0]=='mvtec_acquired_development' and new[k]['label']=='crack']
    positives.sort(key=lambda k:new[k]['tp']-old[k]['tp'],reverse=True)
    selected={positives[i] for i in (0,4,8,16)}
    normal=max((k for k in new if k[0]=='mvtec_acquired_normal_calibration'),key=lambda k:new[k]['fp'])
    external=max((k for k in new if k[0]=='mcs2_source_development' and not new[k]['alarm']),key=lambda k:new[k]['fn'])
    selected|={normal,external};sections=[]
    for ds,sid,label,p,truth,m in cohort():
        key=(ds,sid)
        if key not in selected:continue
        rgb=load(p);baseline=detect(rgb,enabled=False);candidate=detect(rgb,enabled=True)
        arrays=[rgb[110:610,390:890],(truth[110:610,390:890]*255).astype(np.uint8),
                (baseline[110:610,390:890]*255).astype(np.uint8),(candidate[110:610,390:890]*255).astype(np.uint8)]
        cards=''.join('<figure><img src="'+uri(a)+'" loading="lazy"><figcaption>'+title+'</figcaption></figure>'
                      for a,title in zip(arrays,['历史实采 RGB／外部源图','标注裂纹','旧版：离线重算','新候选：离线重算']))
        a,b=old[key],new[key]
        sections.append('<section><h2>'+html.escape(ds+' / '+sid)+'</h2><p>标签：'+html.escape(label)+
            '；报警 '+str(a['alarm'])+' → '+str(b['alarm'])+'；TP '+str(a['tp'])+' → '+str(b['tp'])+
            '；FP '+str(a['fp'])+' → '+str(b['fp'])+'；FN '+str(a['fn'])+' → '+str(b['fn'])+
            '。图片显示 500×500 材料区域；统计按完整输入帧计算。</p><div class="grid">'+cards+'</div></section>')
    body='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TileLab V1.54 候选算法对比</title><style>body{font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;margin:auto;max-width:1440px;padding:28px;color:#173046;background:#f6f8fb}h1{line-height:1.3}section{background:white;padding:20px;margin:24px 0;border-radius:12px;border:1px solid #dbe3ec}h2{font-size:19px;overflow-wrap:anywhere}.notice{padding:16px;background:#fff3cf;border-left:5px solid #d99400}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}figure{margin:0}img{display:block;width:100%;image-rendering:auto;background:#111}figcaption{font-weight:600;text-align:center;margin-top:6px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;border:1px solid #dbe3ec;text-align:left}@media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}a{color:#1762a5}</style>
<h1>TileLab V1.54 · 方向均值增强候选</h1>
<p class="notice">本页展示离线算法对比。瓷砖 RGB 来自历史 HDMI 实采；新候选掩码由离线参考模型计算，尚非新实板验收结果。开发数据已经用于选型，不能当作独立工业测试。</p>
<table><tr><th>同批历史开发数据</th><th>旧版</th><th>新候选</th></tr><tr><td>像素召回</td><td>28.20%</td><td>41.53%</td></tr><tr><td>像素精确率</td><td>98.36%</td><td>97.48%</td></tr><tr><td>裂纹图报警</td><td>17/17</td><td>17/17</td></tr><tr><td>正常图报警</td><td>0/33；标定组 0/230</td><td>0/33；标定组 0/230</td></tr></table>
<p>展示样本按新增 TP 排序选取第 1、5、9、17 张，并加入正常标定图中候选像素最多的一张及一张仍漏检的大理石图。样本选择不是随机盲测。四张图点击／浏览器缩放可检查细节；每个掩码中白色表示候选像素。</p>
'''
    body+=''.join(sections)+'''<footer><p>图像来源：Bergmann 等，MVTec AD tile，CC BY-NC-SA 4.0；Vrochidou 等，MCS2 RGB，CC BY 4.0。像素精确率不等于产品检测准确率；跨材质能力仍不足。</p><p><a href="https://www.mvtec.com/research-teaching/datasets/mvtec-ad">MVTec 原始来源</a> · <a href="https://github.com/MachineLearningVisionRG/mcs2-dataset">MCS2 原始来源</a></p></footer></html>'''
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(body,encoding='utf-8')
    print(json.dumps(dict(file=str(args.out),examples=len(sections),bytes=args.out.stat().st_size,scope='offline_development_visualization')))
if __name__=='__main__':main()

"""Self-contained scientific comparison; fixed masks verified against evaluation hashes."""
from pathlib import Path
import sys,json,base64,io,html,hashlib,argparse
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'models'),str(R/'scripts')]
from evaluate_support_v155 import old_cohort,source_cohort
from support_profiles_v155 import compute_features,mask_from_features
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
if args.out.exists():raise FileExistsError(args.out)
data={s:json.loads((R/f'reports/v155/eval_{s}_frozen01/summary.json').read_text()) for s in ['old','development','reserved']}
allrows=[x for d in data.values() for x in d['rows']];lookup={(x['dataset'],x['id'],x['variant']):x for x in allrows}
old=[x for x in data['old']['rows'] if x['dataset']=='mvtec_acquired_development' and x['label']=='crack' and x['variant']=='sensitive']
old.sort(key=lambda x:x['tp']-lookup[(x['dataset'],x['id'],'v154')]['tp'],reverse=True)
selected={(old[i]['dataset'],old[i]['id']) for i in [0,8,16]}
for ds,cls,alarm in [('hfenet_reserved','normal',False),('hfenet_reserved','normal',True),('visuceram_reserved','body_crack',True),('visuceram_reserved','glaze_crack',False),('visuceram_reserved','normal',True)]:
 row=next(x for x in allrows if x['dataset']==ds and x['label']==cls and x['variant']=='sensitive' and x['alarm']==alarm and not x['label_contradiction']);selected.add((ds,row['id']))
def uri(a):
 out=io.BytesIO();Image.fromarray(a).save(out,format='PNG');return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()
sections=[]
for item in list(old_cohort())+list(source_cohort('reserved')):
 key=item['dataset'],item['id']
 if key not in selected:continue
 rgb=item['rgb'];a=rgb.astype(np.int32);gray=(77*a[:,:,0]+150*a[:,:,1]+29*a[:,:,2])>>8
 keep=np.zeros(gray.shape,bool);keep[80:640,80:1200]=True;features=compute_features(gray)
 crop=(slice(232,488),slice(80,1200)) if key[0].startswith('hfenet') else (slice(110,610),slice(390,890))
 arrays=[rgb[crop]];captions=['真实源图／历史实采'];stats=[]
 if item['truth'] is not None:arrays.append((item['truth'][crop]*255).astype(np.uint8));captions.append('原像素标注')
 for variant,title in [('v154','V1.54'),('conservative','V1.55 稳健'),('sensitive','V1.55 高敏')]:
  mask=mask_from_features(features,keep,variant);row=lookup[(*key,variant)]
  assert hashlib.sha256(np.packbits(mask.ravel(),bitorder='little').tobytes()).hexdigest()==row['mask_sha256']
  arrays.append((mask[crop]*255).astype(np.uint8));captions.append(title+' · '+('报警' if row['alarm'] else '未报警'))
  stats.append(title+': '+(f"TP {row['tp']} / FP {row['fp']} / FN {row['fn']}" if row['tp'] is not None else f"候选像素 {row['pixels']}，框 {len(row['boxes'])}"))
 cards=''.join('<figure><img loading="lazy" src="'+uri(a)+'"><figcaption>'+c+'</figcaption></figure>' for a,c in zip(arrays,captions))
 boxes='；该来源只有框标注，不计算像素召回率。' if key[0].startswith('visuceram') else ''
 sections.append('<section><h2>'+html.escape(' / '.join(key))+'</h2><p>标签：'+item['label']+boxes+'</p><p>'+html.escape('；'.join(stats))+'</p><div class="grid">'+cards+'</div></section>')
body='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.55 算法与新图片检验</title>
<style>body{max-width:1500px;margin:auto;padding:28px;color:#173046;background:#f6f8fb;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}section{background:white;border:1px solid #dbe3ec;border-radius:12px;padding:20px;margin:24px 0}h1{line-height:1.4}h2{font-size:18px;overflow-wrap:anywhere}.notice{padding:18px;background:#fff1cd;border-left:5px solid #d99400}.grid{display:flex;flex-wrap:wrap;gap:12px}figure{margin:0;flex:1 1 230px;max-width:500px}img{display:block;width:100%;background:#111}figcaption{font-weight:600;text-align:center}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;border:1px solid #dbe3ec;text-align:left}a{color:#1762a5}</style>
<h1>TileLab V1.55 · 两档可选算法与新图片检验</h1>
<p class="notice">结论：原材质的裂纹像素召回提高；新材质正常图误报仍较高。60% 召回／95% 精确率并保持旧正常组零报警的目标尚未实现。所有结果为离线参考模型，非新实板验收；现有默认配方不变。</p>
<p>稳健档增加 7 点方向均值、法向偏移 4 的宽线响应，强／弱阈值 60／30，四级邻域支持。高敏档保留 V1.54 种子，用四方向线状资格限制延伸，最多八级。运算在 PL 中实现，主机只控制参数、传输与展示。</p>
<table><tr><th>已参与选型的 50 张历史 HDMI 图</th><th>V1.54</th><th>V1.55 稳健</th><th>V1.55 高敏</th></tr><tr><td>裂纹像素召回</td><td>41.53%</td><td>43.23%</td><td>52.56%</td></tr><tr><td>像素精确率</td><td>97.48%</td><td>97.39%</td><td>95.24%</td></tr><tr><td>正常图报警</td><td>0/33</td><td>0/33</td><td>0/33</td></tr><tr><td>另 230 张历史正常标定图报警</td><td>0/230</td><td>0/230</td><td>2/230</td></tr></table>
<h2>新来源留出组：冻结参数后一次统一评估</h2>
<table><tr><th>来源与指标</th><th>V1.54</th><th>稳健</th><th>高敏</th></tr><tr><td>HFENet 正常瓷砖条带报警</td><td>15/128</td><td>15/128</td><td>16/128</td></tr><tr><td>VisuCeram 正常卫生陶瓷报警</td><td>17/39</td><td>17/39</td><td>19/39</td></tr><tr><td>VisuCeram 坯体裂纹：至少一个框 IoU≥0.25</td><td>19/40</td><td>20/40</td><td>21/40</td></tr><tr><td>VisuCeram 釉面裂纹：至少一个框 IoU≥0.25</td><td>10/40</td><td>10/40</td><td>13/40</td></tr></table>
<p>新选入 546 张真实源图：288 张开发、258 张留出。HFENet 是工业相机瓷砖条带，其缺陷类别为印刷缺陷，不能当裂纹真值。VisuCeram 是卫生陶瓷，不能当平面瓷砖；只有框标注。40 张留出“正常”中有 1 张同时带裂纹标注，排除后分母为 39。图像按 SHA256、像素哈希与旋转／镜像感知哈希分组去重；缺少实体编号，不能证明不同实物／不同产线独立。</p>
<p>下面特意包括新增检出、增益较小、正常误报与裂纹漏报。历史样本按高敏新增 TP 排序选第 1、9、17 张；新来源按预先列出的类别／报警条件取首张。这些图用于解释结果，不是随机抽样准确率。白色表示候选像素，图片为源图的材料区域；统计按完整 1280×720 帧。</p>
'''+''.join(sections)+'''
<section><h2>下一轮优先级</h2><p>优先压制纹理与陶瓷轮廓造成的误报，再继续延伸弱裂纹。需要在新的开发数据中研究材质标定、表面有效区、纹理方向一致性与可解释的置信拒识，另设未使用的验证组；本轮留出组已经曝光，后续只能作为回归集。避免继续单纯降低阈值或增加支持级数。</p></section>
<footer><p>来源：<a href="https://github.com/RobotvisionLab/HFENet">HFENet 作者仓库</a> · <a href="https://github.com/Md-Ali-Azad/VisuCeram">VisuCeram 作者仓库</a> · <a href="https://www.mvtec.com/research-teaching/datasets/mvtec-ad">MVTec AD</a>。HFENet 仓库 MIT，链接的图像档案未附独立授权声明，本地研究留存，不代表可公开再分发；VisuCeram 作者仓库 Apache-2.0；MVTec AD CC BY-NC-SA 4.0。没有使用 P 图裂纹充当真实缺陷证据。</p></footer></html>'''
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(body,encoding='utf-8')
print(json.dumps(dict(path=str(args.out),examples=len(sections),bytes=args.out.stat().st_size,mask_hashes_verified=True)))

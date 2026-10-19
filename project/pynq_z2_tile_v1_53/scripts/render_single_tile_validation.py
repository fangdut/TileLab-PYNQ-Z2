"""Render both exposed input domains, retaining failures and full-tile evidence."""
from pathlib import Path
import argparse,base64,hashlib,html,io,json
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]

def thumbnail(path):
    with Image.open(path) as im:
        im=im.convert('RGB').crop((390,110,890,610));im.thumbnail((250,250));b=io.BytesIO();im.save(b,format='JPEG',quality=83)
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--acquired',required=True,type=Path);ap.add_argument('--stimulus',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    original={};reports={}
    for name,path in [('historical_acquired',a.acquired),('stimulus',a.stimulus)]:
        raw=(path/'summary.json').read_bytes();report=json.loads(raw);report['input_kind']=name
        # Input kind was implicit in the first stimulus run; label that evidence
        # explicitly and retain the exact source-summary digest.
        report['source_summary_sha256']=hashlib.sha256(raw).hexdigest()
        original[name]=path;reports[name]=report
        (a.out/('OOF_'+name.upper()+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    acquired=reports['historical_acquired'];stimulus=reports['stimulus'];by={name:{r['index']:r for r in report['rows']} for name,report in reports.items()}
    def stats(r):return f"{r['localized_crack_detections']}/{r['image_positive']} | {r['normal_false_alarms']}/{r['image_negative']} | {r['pixel_precision']:.2%} | {r['pixel_recall']:.2%} | 最弱 {r['worst_crack_pixel_recall']:.2%}"
    summary=dict(release='V1.64',qualified=False,requested_materials=['painted','multiple_materials'],accuracy_qualified=False,current_board_accepted=False,independent_material_validation_count=0,profile_sha256=acquired['profile_sha256'],blockers=['Painted/multiple-material single-tile accuracy is unqualified; no independent target-material test set','Historical calibrated HDMI captures and original input photos produce materially different results','Weakest crack coverage remains2.684%; image-level detection must not conceal under-segmentation','No V164 physical board/optical validation','Per-pattern good-reference option is pending user selection; not implemented'],proposed_future_acceptance_gates=dict(scope='Per supported material, independent source-grouped evaluation, frozen operating point',positive_images_at_least=100,negative_images_at_least=400,image_recall_wilson95_lower_at_least=.95,image_fpr_wilson95_upper_at_most=.01,small_crack_coverage_guard_required=True),development_replays={name:{k:v for k,v in r.items() if k!='rows'} for name,r in reports.items()})
    (a.out/'QUALIFICATION.json').write_text(json.dumps(summary,indent=2)+'\n')
    table=''
    for name,label in [('historical_acquired','历史 HDMI 实采图'),('stimulus','原始 HDMI 输入照片')]:
        r=reports[name];table+=f"<tr><td>{label}</td><td>{r['localized_crack_detections']}/{r['image_positive']}</td><td>{r['normal_false_alarms']}/{r['image_negative']}</td><td>{r['pixel_precision']:.2%}</td><td>{r['pixel_recall']:.2%}</td><td>{r['worst_crack_pixel_recall']:.2%}</td></tr>"
    failure_ids=[r['index'] for r in stimulus['rows'] if (r['truth'] and not r['localized_alarm']) or (r['label']=='good' and r['alarm'])]
    weakest=sorted((r for r in acquired['rows'] if r['truth']),key=lambda r:r['tp']/r['truth'])[:3]
    order=list(dict.fromkeys(failure_ids+[r['index'] for r in weakest]+[r['index'] for r in acquired['rows']]))
    cards=[]
    for index in order:
        parts=[]
        for name,label in [('historical_acquired','历史实采'),('stimulus','原始输入')]:
            row=by[name][index];cov=f"裂纹像素 {row['tp']/row['truth']:.2%}" if row['truth'] else f"正常图 FP 像素 {row['fp']}"
            verdict='有候选报警' if row['alarm'] else '无候选报警'
            parts.append(f'<figure><img loading="lazy" alt="{label} 单片 {index:03} 掩码和框" src="{thumbnail(original[name]/f"sample_{index:03}/overlay.png")}"><figcaption>{label} · {verdict}<br>{cov}</figcaption></figure>')
        row=by['stimulus'][index];mark='原始输入失败案例' if index in failure_ids else '完整单片回归'
        cards.append(f'<article><h3>#{index:03} · {"裂纹" if row["truth"] else "正常"} <small>{mark}</small></h3><div class="pair">'+''.join(parts)+'</div></article>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.64 单片验证</title><style>body{font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif;background:#f3f6f7;color:#17343d;margin:0}main{max-width:1200px;margin:auto;padding:28px}h1{margin:8px 0}.flag{background:#fff2cf;border:1px solid #dcba62;padding:18px;border-radius:12px}table{border-collapse:collapse;width:100%;background:white;margin:20px 0;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:12px;border-bottom:1px solid #dae4e6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}article{background:white;border:1px solid #d5e0e3;border-radius:12px;padding:16px}h3{font-size:16px;margin:0 0 10px}small{font-size:11px;color:#98631c}.pair{display:flex;gap:12px}figure{margin:0;flex:1;min-width:0}img{width:100%;height:auto;border-radius:7px}figcaption{font-size:12px;color:#4f6871}a{color:#007b78}.scroll{overflow:auto}code{overflow-wrap:anywhere}</style><main><p>TileLab · V1.64 · 单片工程候选</p><h1>工程可以复现，高准确率仍需解决</h1><div class="flag"><b>彩绘／多材质未通过准确率验收；没有本次实板验收。</b><br>同一批17张裂纹、33张正常图的两种输入呈现，不是100张独立样本。全部属于反复暴露的开发集 OOF。无报警仍需人工复核。</div><div class="scroll"><table><tr><th>输入</th><th>裂纹定位图数</th><th>正常图误报</th><th>像素精确率</th><th>像素召回率</th><th>最弱覆盖</th></tr>'''+table+'''</table></div><p>当前完整500×500表面 ROI：[390,110]—[889,609]。未缩边，GT共94,043像素，ROI外GT为0。红色表示候选掩码与合格区域框，青色为完整检测边界。下面只裁出完整单片用于显示，统计来自原720p画面。框内有真实裂纹掩码交点才计为定位检出。</p><p>历史实采图已经通过此前HDMI链路；原始输入照片尚未通过那条链路。差异表明现有检测器依赖已标定成像条件，不能直接宣称任意照片、彩绘或多材质均适用。最弱裂纹覆盖2.68%，也不能被17/17整图定位掩盖。</p><p><a href="QUALIFICATION.json">当前资格状态</a> · <a href="OOF_HISTORICAL_ACQUIRED.json">历史实采逐图JSON</a> · <a href="OOF_STIMULUS.json">原始输入逐图JSON</a> · <a href="../../DATA_PROVENANCE_V164.md">数据来源与许可</a></p><h2>先看失败，再看全部50张</h2><div class="grid">'''+''.join(cards)+'''</div><p>来源：原仓库 MVTec AD tile／CC BY-NC-SA4.0。没有新增真实相机实验，没有新增模型训练，合成裂纹不计真实准确率。</p></main></html>'''
    (a.out/'validation.html').write_text(page,encoding='utf8');print(json.dumps(dict(report=str((a.out/'validation.html').resolve()),image_pairs=len(cards),failure_indices=failure_ids,qualified=False)))

if __name__=='__main__':main()

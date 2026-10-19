"""Publish bounded mechanism evidence, explicitly separating real and synthetic."""
from pathlib import Path
import argparse,base64,hashlib,html,io,json,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]

def thumb(path,crop=False):
    with Image.open(path) as im:
        im=im.convert('RGB')
        if crop:im=im.crop((390,110,890,610))
        im.thumbnail((190,190));b=io.BytesIO();im.save(b,format='JPEG',quality=85)
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--initial',required=True,type=Path);ap.add_argument('--final',required=True,type=Path);ap.add_argument('--stress',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    initial=json.loads((a.initial/'summary.json').read_text());final=json.loads((a.final/'summary.json').read_text());stress=json.loads((a.stress/'summary.json').read_text());declaration=json.loads((a.final/'declaration.json').read_text())
    for name,digest in declaration['source_sha256'].items():
        if hashlib.sha256((ROOT/'tools/reference_tile'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Final algorithm differs from executed benchmark: '+name)
    for source,name in [(a.initial/'summary.json','MECHANISM_INITIAL.json'),(a.initial/'declaration.json','INITIAL_PROTOCOL.json'),(a.final/'summary.json','MECHANISM_FINAL.json'),(a.final/'declaration.json','FINAL_PROTOCOL.json'),(a.stress/'summary.json','CROSS_INSTANCE_STRESS.json')]:shutil.copy2(source,a.out/name)
    normal=final['cohorts']['PROCEDURAL_NORMAL_CAPTURE_SIMULATION'];line=final['cohorts']['PROCEDURAL_ARTIFICIAL_LINE'];bad=final['cohorts']['PROCEDURAL_REJECT_OR_REVIEW_STRESS'];identity=final['cohorts']['REAL_GOOD_PHOTO_IDENTITY_DIAGNOSTIC_NOT_ACCURACY']
    status=dict(version='V1.65-reference-prototype',reference_mode_authorized=True,new_classifier_training=False,scope='Offline good-reference prototype and experimental paired-pixel RTL only',accuracy_qualified=False,board_integrated=False,current_deployed_hardware='V1.64 unchanged',real_good_crack_pairs=0,independent_real_material_validation_count=0,policy_sha256=final['policy_sha256'],normal_synthetic=normal,artificial_lines=line,reject_stress=bad,real_identity_diagnostics=identity,real_cross_instance_stress={k:v for k,v in stress.items() if k!='rows'},remaining_failure_cases=final['failed_cases'],limitations=['JPEG color-edge artifacts:2 candidate alarms and1 rejection in6 constructed JPEG inputs','All32 different real good tiles were rejected against one unmatched category reference; not a zero-FPR result','No real same-pattern good/crack pairs; no actual optical validation','Registration, reference DDR transport, frame identity pairing and regional logic are not integrated into the FPGA release','Difference candidates can also be stain, dirt or glaze changes; not semantic crack classification'])
    (a.out/'STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
    cards=[];rows=sorted((r for r in final['rows'] if r['style']!='mvtec'),key=lambda r:(r['mechanism_expectation_met'],r['id']))
    for row in rows:
        d=a.final/row['id'];pictures=[]
        for name,label,crop in [('reference.png','构造良品参照',True),('current.png','构造采集输入',True),('overlay.png','对齐后候选结果',False)]:
            if (d/name).is_file():pictures.append(f'<figure><img loading="lazy" src="{thumb(d/name,crop)}" alt="{html.escape(label)}"><figcaption>{label}</figcaption></figure>')
            else:pictures.append('<figure class="reject">拒绝判定<br>没有输出检测掩码</figure>')
        label='人工线条' if row['truth_pixels'] else '构造正常扰动' if 'NORMAL' in row['cohort'] else '无效输入压力'
        outcome='拒判' if row['alarm'] is None else '有变化候选' if row['alarm'] else '无变化候选'
        recall=f" · 人工GT像素覆盖 {row['pixel_recall']:.1%}" if row['pixel_recall'] is not None else ''
        cards.append(f'<article><h3>{html.escape(row["id"])}</h3><p>{label} · <b>{outcome}</b>{recall}<br>{html.escape(row.get("reason", ""))}</p><div class="triplet">'+''.join(pictures)+'</div></article>')
    before=initial['cohorts']['PROCEDURAL_NORMAL_CAPTURE_SIMULATION'];checks=''.join(f'<li>{html.escape(x)}</li>' for x in final['failed_cases'])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TileLab V1.65 良品参照原型</title><style>body{margin:0;background:#f2f6f6;color:#193842;font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1260px;margin:auto;padding:26px}h1{margin:8px 0}.notice{padding:18px;background:#fff1ce;border:1px solid #d9b75e;border-radius:12px}.metrics{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.metrics div{flex:1;min-width:170px;padding:16px;background:white;border:1px solid #d2e2e4;border-radius:12px}.metrics b{display:block;font-size:25px}table{border-collapse:collapse;background:white;width:100%;margin:18px 0}td,th{text-align:left;padding:11px;border-bottom:1px solid #dae5e7}.scroll{overflow:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(510px,1fr));gap:16px}article{padding:15px;background:white;border:1px solid #d6e3e5;border-radius:12px}h3{font-size:14px;overflow-wrap:anywhere;margin:0}article p{font-size:12px;color:#506c75}.triplet{display:flex;gap:8px}figure{margin:0;flex:1;min-width:0}img{width:100%;border-radius:6px}figcaption{font-size:11px}.reject{background:#fff4d8;padding:20px 5px;text-align:center;color:#916418;font-size:12px}a{color:#007d78}code{overflow-wrap:anywhere}@media(max-width:600px){main{padding:14px}.grid{grid-template-columns:1fr}}</style><main><p>TileLab · V1.65 · 按花色良品参照</p><h1>抵消既有花纹，保留新增变化</h1><div class="notice"><b>离线原型＋独立整数RTL验证；尚未接入V164板端。</b><br>真实同花色良品／裂纹配对为0，没有真实准确率验收。人工细线、采集扰动和真实图片自对照分开统计。拒判不会记成正常，也不会被删出分母。</div><div class="metrics"><div>构造正常扰动<b>2 报警 / 36</b>另有1次拒判，33次无候选</div><div>人工细线用例<b>24 / 24</b>均触发定位候选，非真实裂纹检出率</div><div>逐像素RTL向量<b>8,192</b>整数、背压、复位及边带一致</div><div>真实配对验收<b>尚未完成</b>当前准确率资格仍为false</div></div><h2>三类结果必须分开看</h2><div class="scroll"><table><tr><th>用例</th><th>数量</th><th>候选报警</th><th>拒判</th><th>无候选</th></tr>'''
    for label,r in [('构造正常采集扰动',normal),('人工细线',line),('错参照／位移／旋转／曝光／遮挡压力',bad),('原有真实良品图自对照（只查流程）',identity)]:page+=f'<tr><td>{label}</td><td>{r["cases"]}</td><td>{r["alarms"]}</td><td>{r["rejected"]}</td><td>{r["no_candidate"]}</td></tr>'
    page+=f'<tr><td>真实不同良品跨实例压力（花纹与姿态未验证匹配）</td><td>{stress["cases"]}</td><td>{stress["candidate_alarms"]}</td><td>{stress["rejected"]}</td><td>{stress["no_candidate"]}</td></tr></table></div>'
    page+=f'<p>同一套构造正常扰动，直接差分有23次报警；初版参照算法有{before["alarms"]}次报警、{before["rejected"]}次拒判；修正位移峰值采样和双线性重采样模型后为2次报警、1次拒判。高／低阈值仍为18／9。用例已反复调试，是开发机制验证，不能用来宣称独立准确率。</p>'
    page+='''<p><b>剩余失败均为JPEG用例：</b>6个JPEG扰动中有2次误报、1次拒判、3次无候选。其余30个构造正常用例无候选、无拒判；这是同一开发试验的分项，不能替代真实验证。</p><ul>'''+checks+'''</ul><p><b>“同材质”不等于“空间花纹匹配”。</b>使用一张原有MVTec正常照片，直接比较另32张正常照片，32张全部拒判。随机石纹、木纹或不同布局不能直接套同一像素参照。需要先检查同花色良品间变化范围，不能把拒判包装成零误报。</p><h2>已实现与尚待接入</h2><p>已实现：不可覆盖的按花色标定包、文件与代码指纹、完整500×500 ROI、小位移对齐、整体RGB光照补偿、边缘容差、变化区域、质量拒判。差分只判断表面变化，污渍、灰尘和釉面变化也可能报警，不能自动证明是裂纹。</p><p>独立RTL仅做成对RGB像素的Q8光照补偿和差分，3级弹性流水线。孤立综合约135 LUT、295寄存器、3 DSP、0 BRAM；不是完整系统资源或布线时序结果。完整参照加容差表约1,000,000字节，需要DDR参照流与帧身份配对；当前V164下载包没有这些模块。</p><p><a href="STATUS.json">状态</a> · <a href="MECHANISM_FINAL.json">逐用例结果</a> · <a href="FINAL_PROTOCOL.json">执行前协议与源指纹</a> · <a href="MECHANISM_INITIAL.json">初版失败记录</a> · <a href="CROSS_INSTANCE_STRESS.json">真实跨实例压力</a></p><h2>全部90个构造用例（失败优先）</h2><p>图片均为程序生成的工程夹具，不是真实彩绘裂纹照片。显示完整500×500表面，不缩边；青色／红色只是绘图说明。真实自对照33张仅列在JSON中，避免将重复原图误当独立实验。</p><div class="grid">'''+''.join(cards)+'''</div></main></html>'''
    (a.out/'reference_report.html').write_text(page,encoding='utf8');print(json.dumps(dict(cards=len(cards),report=str((a.out/'reference_report.html').resolve()),accuracy_qualified=False)))

if __name__=='__main__':main()

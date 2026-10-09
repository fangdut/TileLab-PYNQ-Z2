"""Seal attribution evidence; explicitly not a new deployed product."""
from pathlib import Path
import datetime,hashlib,json,os,urllib.request
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_50';P=R.parent/'pynq_z2_tile_v1_48'
O=R/'reports/v151';W=R/(R.name+'.sdk')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def check(p,h):assert sha(p)==h,('Changed',str(p))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def files(root):
    for parent,ds,ns in os.walk(root,followlinks=False):
        ds[:]=[n for n in ds if n not in ('__pycache__','runtime','review_records') and not (Path(parent)/n).is_symlink() and not (Path(parent)/n).is_junction()]
        for n in ns:
            p=Path(parent)/n
            if not p.is_symlink():yield p
def main():
    assert not (R/'DELIVERY_MANIFEST.json').exists(),'Never rewrite a sealed version'
    plan=load(R/'ITERATION_PLAN.json');assert plan['version']=='V1.51'
    check(B/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);check(plan['backup'],plan['backup_sha256'])
    for base in (B,P):
        m=load(base/'DELIVERY_MANIFEST.json')
        for group in ('source_sha256','proof_sha256'):
            for n,h in m[group].items():check(base/n,h)
    for n,h in plan['inherited_hardware_sha256'].items():check(W/n,h)
    for folder in ('rtl','constraints','ip_repo'):
        for q in files(R/folder):check(q,sha(B/q.relative_to(R)))
    for q in (W/'ethernet_sources').iterdir():
        if q.is_file():check(q,sha(B/(B.name+'.sdk')/'ethernet_sources'/q.name))
    d=load(O/'miss_diagnostic/declaration.json');r=load(O/'miss_diagnostic/result.json')
    check(O/'miss_diagnostic/declaration.json',r['declaration_sha256'])
    for n,h in d['inputs'].items():check(n,h)
    assert r['completed'] and r['baseline_reproduced'] and not r['production_changed'] and not r['board_tested']
    assert len(load(O/'miss_diagnostic/items.json'))==50
    assert r['counts']['fn']==69242 and sum(r['categories'].values())==69242
    units=load(O/'diagnostic_unit.json');assert units['passed'] and units['tests']==6
    for n,h in units['source_sha256'].items():check(R/n,h)
    with urllib.request.urlopen('http://127.0.0.1:8770/api/live',timeout=8) as response:live=json.load(response)
    assert live['revision']=='V1.48' and live['enabled'] and not live['error']
    assert live['storage']['mode']=='preview' and live['board_stats']['version']==0x12a00
    save(O/'live_station_unchanged.json',live)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();status='OFFLINE_MISS_ATTRIBUTION_COMPLETED_NOT_DEPLOYED'
    summary=dict(passed=True,version='V1.51',status=status,deployable=False,completed_at=now,
        scope='Historical diagnostic verified; no candidate improvement or board validation claim',
        live_product='V1.48',hardware_revision='V1.42',unit_tests=6,regression_images=50,
        result_sha256=sha(O/'miss_diagnostic/result.json'),findings=r['categories'],
        next_step='Evaluate one wider-scale weak feature anchored to unchanged strong seeds; keep production unchanged until gates pass')
    save(O/'validation_summary.json',summary)
    plan.update(phase=status,scope='OFFLINE_DIAGNOSTIC_ONLY',deployable=False,live_station='V1.48 remains active')
    save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase=status,all_test_sessions_completed=True,next_step=summary['next_step']))
    (R/'README.md').write_text('''# TileLab V1.51 · 漏检归因

**诊断记录，不是新发布的检测版本。实际运行 V1.48，PL/ARM 保持 V1.42。**

先核对并备份 V1.50，再用 50 张历史开发帧复现基准：17 张裂纹报警、33 张正常不报警，裂纹像素 TP=24801、FP=339、FN=69242。6 项归因与边界测试通过。

漏检按固定顺序分为互斥类别：48445 个（约 70%）响应不超过弱阈值；11554 个离强种子超过四级传播范围；28 个在范围内但没有可行弱连接路径；9215 个受三个邻居的支持规则限制。ROI 外为零。该顺序会影响归因解释，不能把各项看成独立消融实验。

现有框覆盖 70.63% 的标注裂纹像素；这不等于像素召回率（26.37%），大框也可能提高覆盖率。四级、单邻居的乐观连接上限为 34016 个真阳性，不含误报和硬件成本约束，不能当作新产品结果。

下一轮只评估一条方案：保持强种子和阈值不变，给弱像素增加更宽尺度的双侧灰度响应。先过正常图门槛，再比较收益及精度；不满足则不进入 RTL。未改变板上算法，没有重新综合或烧录。历史数据反复用于开发，不能用于宣称工厂准确率。

细项与输入哈希在 reports/v151/miss_diagnostic。没有复制原图，也未增加连续截图存档。正式报告留待多轮迭代后统一编写。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for q in files(R/folder):
            if q.suffix not in ('.pid','.log','.pyc','.wdb') and q.name not in ('player_status.json','player_instance.json','display_command.txt'):source[q.relative_to(R).as_posix()]=sha(q)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for q in W.iterdir():
        if q.is_file() and q.suffix in ('.py','.tcl','.bat'):source[q.relative_to(R).as_posix()]=sha(q)
    proofs={R/'README.md',R/'ITERATION_PLAN.json'};proofs.update(q for q in files(O) if q.suffix in ('.json','.txt','.log','.csv','.png'))
    save(R/'DELIVERY_MANIFEST.json',dict(version='V1.51',status=status,deployable=False,created_at=now,
        baseline=str(B),baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
        artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=source,
        proof_sha256={q.relative_to(R).as_posix():sha(q) for q in sorted(proofs)},validation=summary,report='README.md'))
    p=R.parent/'TileLab_进度与回退.md';s=p.read_text(encoding='utf-8');a=s.index('## 尚在进行');b=s.index('## 回退和空间')
    s=s[:a]+f'| V1.51 | 漏检分层归因；诊断完成，当前仍运行 V1.48 | {status} | [记录]({R.as_posix()}/README.md) |\n\n## 尚在进行\n\nV1.51 诊断完成，下一轮先备份，再评估保留强种子的较宽尺度弱响应。当前实板产品仍为 V1.48。\n\n'+s[b:];p.write_text(s,encoding='utf-8')
    print(json.dumps(dict(passed=True,status=status,deployable=False,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

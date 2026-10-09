"""Seal a rejected offline candidate, explicitly not a deployed product release."""
from pathlib import Path
import argparse,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v150';W=R/(R.name+'.sdk');B=R.parent/'pynq_z2_tile_v1_49';P=R.parent/'pynq_z2_tile_v1_48';BOUND={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    p=Path(p);BOUND[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def check(p,h):assert sha(p)==h,('Changed file',str(p));BOUND[str(p)]=h
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def files(root):
    for parent,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[n for n in dirs if n not in ('__pycache__','runtime','review_records') and not (Path(parent)/n).is_symlink() and not (Path(parent)/n).is_junction()]
        for name in names:
            p=Path(parent)/name
            if not p.is_symlink():yield p
def main():
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');args=p.parse_args();plan=load(R/'ITERATION_PLAN.json')
    assert plan['version']=='V1.50' and Path(plan['baseline'])==B;check(B/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);baseline=load(B/'DELIVERY_MANIFEST.json')
    for group in ('source_sha256','proof_sha256'):
        for n,h in baseline[group].items():check(B/n,h)
    production=load(P/'DELIVERY_MANIFEST.json')
    for group in ('source_sha256','proof_sha256'):
        for n,h in production[group].items():check(P/n,h)
    check(plan['backup'],plan['backup_sha256'])
    for n,h in plan['inherited_hardware_sha256'].items():check(W/n,h)
    for folder in ('rtl','constraints','ip_repo'):
        for q in files(R/folder):check(q,sha(B/q.relative_to(R)))
    for q in (W/'ethernet_sources').iterdir():
        if q.is_file():check(q,sha(B/(B.name+'.sdk')/'ethernet_sources'/q.name))
    unit=load(O/'candidate_unit.json');assert unit['passed'] and unit['tests']==7
    for n,h in unit['source_sha256'].items():check(R/n,h)
    result=load(O/'band_candidate/result.json');decl=load(O/'band_candidate/declaration.json');check(O/'band_candidate/declaration.json',result['declaration_sha256'])
    for n,item in decl['input_files'].items():check(n,item['sha256'])
    gate=load(O/'band_candidate/normal_gate.json');regression=load(O/'band_candidate/regression.json')
    assert gate['passed'] and gate['images_checked']==230 and len(gate['items'])==230
    assert len(regression['items'])==50 and result['completed'] and result['status']=='REGRESSION_REJECTED'
    assert not result['production_changed'] and not result['board_tested'] and not result['candidate_eligible_for_isolated_rtl']
    assert result['checks']['baseline_reproduced'] and not result['checks']['recall_gain_met'] and result['checks']['precision_floor_met']
    assert regression['summary']==result['summary'];old,new=result['summary']['baseline'],result['summary']['candidate'];assert new['tp']-old['tp']==33
    live=load(O/'live_station_unchanged.json');assert live['revision']=='V1.48' and live['enabled'] and not live['error'] and live['storage']['mode']=='preview' and live['board_stats']['version']==0x12a00
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    status='OFFLINE_CANDIDATE_REJECTED_NOT_DEPLOYED';now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary=dict(passed=True,version='V1.50',status=status,completed_at=now,scope='Experiment completed and rejection verified; not product or board validation',deployable=False,
        live_product='V1.48',live_root=str(P),hardware_revision='V1.42',normal_images=230,regression_images=50,unit_tests=7,candidate_eligible=False,
        added_true_pixels=new['tp']-old['tp'],added_false_pixels=new['fp']-old['fp'],pixel_recall_gain_percentage_points=100*(new['pixel_recall']-old['pixel_recall']),
        result_sha256=sha(O/'band_candidate/result.json'),declaration_sha256=sha(O/'band_candidate/declaration.json'),limits=['Historical development material, not independent factory accuracy','No RTL change, synthesis, programming or candidate board test'],
        decision='Reject: less than the predeclared 1 percentage point recall gain; preserve the live V1.48 product')
    save(O/'validation_summary.json',summary);plan.update(phase=status,deployable=False,live_station='V1.48 remains active; candidate not promoted');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase=status,all_test_sessions_completed=True,next_step='Backup this experimental record. Live remains V1.48. Diagnose where false negatives lie relative to seeds, score bands and weak connectivity before choosing another hardware rule.'))
    (R/'README.md').write_text(f"""# TileLab V1.50 · 低对比度连接实验

**未发布、未烧录；实际运行产品仍为 V1.48，FPGA/Vitis 为 V1.42。**

保持阈值 90/45 的原增长规则，为响应值 35～45 的像素增加严格通路：3×3 内至少 3 个已接受邻居，并包含一对相对方向的已接受邻居。固定为四级传播。规则与验收门槛在读取实验图像前已声明。

7 项几何与有界传播测试通过；230 张历史正常图与 33 张正常回归图仍无报警，17 张裂纹图仍全部报警。但是，只比基准多识别 33 个标注裂纹像素，同时增加 1 个非裂纹像素。召回提升约 {summary['pixel_recall_gain_percentage_points']:.4f} 个百分点，仍未达到预设 1 个百分点门槛，拒绝进入 RTL。

`reports/v150/band_candidate/declaration.json` 保存规则与输入哈希，`result.json` 保存拒绝结论。没有修改实时检测算法，没有重跑综合或烧录。实验数据已长期用于开发，不能当成工厂盲测准确率。

V1.49 的细线规则与本版严格低对比度桥接都收益很小，下一步先定位漏检像素究竟是响应过低、缺少强种子，还是受连接范围限制；用这些测量选择下一种硬件方案。继续保留旧工程，正式报告在多轮后统一整理。
""",encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for q in files(R/folder):
            if q.suffix not in ('.pid','.log','.pyc','.wdb') and q.name not in ('player_status.json','player_instance.json','display_command.txt'):source[q.relative_to(R).as_posix()]=sha(q)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for q in W.iterdir():
        if q.is_file() and q.suffix in ('.py','.tcl','.bat'):source[q.relative_to(R).as_posix()]=sha(q)
    proofs={R/'README.md',R/'ITERATION_PLAN.json'};proofs.update(q for q in files(O) if q.suffix in ('.json','.log','.txt','.png','.py','.csv'))
    save(R/'DELIVERY_MANIFEST.json',dict(version='V1.50',status=status,deployable=False,created_at=now,baseline=str(B),baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
        artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=source,proof_sha256={q.relative_to(R).as_posix():sha(q) for q in sorted(proofs)},validation=summary,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');text=text.replace('## 尚在进行',f'| V1.50 | 离线低对比度候选：收益不足，未进入 RTL，实际仍运行 V1.48 | {status} | [记录]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    a=text.index('## 尚在进行');b=text.index('## 回退和空间');text=text[:a]+'## 尚在进行\n\nV1.50 离线候选已拒绝并封存，当前实板产品仍为 V1.48。下一轮先备份，再测量强种子、响应阈值和连接范围分别限制了多少漏检像素，避免继续无依据地修改规则。\n\n'+text[b:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,status=status,deployable=False,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

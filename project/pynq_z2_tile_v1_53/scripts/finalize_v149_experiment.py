"""Seal a rejected offline candidate, explicitly not a deployed product release."""
from pathlib import Path
import argparse,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v149';W=R/(R.name+'.sdk');B=R.parent/'pynq_z2_tile_v1_48';BOUND={}
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
    assert plan['version']=='V1.49' and Path(plan['baseline'])==B;check(B/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);baseline=load(B/'DELIVERY_MANIFEST.json')
    for group in ('source_sha256','proof_sha256'):
        for n,h in baseline[group].items():check(B/n,h)
    check(plan['backup'],plan['backup_sha256'])
    for n,h in plan['inherited_hardware_sha256'].items():check(W/n,h)
    for folder in ('rtl','constraints','ip_repo'):
        for q in files(R/folder):check(q,sha(B/q.relative_to(R)))
    for q in (W/'ethernet_sources').iterdir():
        if q.is_file():check(q,sha(B/(B.name+'.sdk')/'ethernet_sources'/q.name))
    unit=load(O/'candidate_unit.json');assert unit['passed'] and unit['tests']==8
    for n,h in unit['source_sha256'].items():check(R/n,h)
    result=load(O/'line_candidate/result.json');decl=load(O/'line_candidate/declaration.json');check(O/'line_candidate/declaration.json',result['declaration_sha256'])
    for n,item in decl['input_files'].items():check(n,item['sha256'])
    gate=load(O/'line_candidate/normal_gate.json');regression=load(O/'line_candidate/regression.json')
    assert gate['passed'] and gate['images_checked']==230 and len(gate['items'])==230
    assert len(regression['items'])==50 and result['completed'] and result['status']=='REGRESSION_REJECTED'
    assert not result['production_changed'] and not result['board_tested'] and not result['candidate_eligible_for_isolated_rtl']
    assert result['checks']['baseline_reproduced'] and not result['checks']['recall_gain_met'] and result['checks']['precision_floor_met']
    assert regression['summary']==result['summary'];old,new=result['summary']['baseline'],result['summary']['candidate'];assert new['tp']-old['tp']==6
    live=load(O/'live_station_unchanged.json');assert live['revision']=='V1.48' and live['enabled'] and not live['error'] and live['storage']['mode']=='preview' and live['board_stats']['version']==0x12a00
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    status='OFFLINE_CANDIDATE_REJECTED_NOT_DEPLOYED';now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary=dict(passed=True,version='V1.49',status=status,completed_at=now,scope='Experiment completed and rejection verified; not product or board validation',deployable=False,
        live_product='V1.48',live_root=str(B),hardware_revision='V1.42',normal_images=230,regression_images=50,unit_tests=8,candidate_eligible=False,
        added_true_pixels=new['tp']-old['tp'],added_false_pixels=new['fp']-old['fp'],pixel_recall_gain_percentage_points=100*(new['pixel_recall']-old['pixel_recall']),
        result_sha256=sha(O/'line_candidate/result.json'),declaration_sha256=sha(O/'line_candidate/declaration.json'),limits=['Historical development material, not independent factory accuracy','No RTL change, synthesis, programming or candidate board test'],
        decision='Reject: less than the predeclared 1 percentage point recall gain; preserve the live V1.48 product')
    save(O/'validation_summary.json',summary);plan.update(phase=status,deployable=False,live_station='V1.48 remains active; candidate not promoted');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase=status,all_test_sessions_completed=True,next_step='Backup this experimental record before another predeclared candidate; live baseline stays V1.48. Consider stricter geometry only in the lower-contrast band, given prior V137 precision rejection.'))
    (R/'README.md').write_text(f'''# TileLab V1.49 · 离线候选实验

**未发布、未烧录。实际运行产品仍为 V1.48，FPGA/Vitis 仍为 V1.42。**

在高/低阈值 90/45 和四级传播不变时，为细线补充“相对方向都有弱响应、至少一端已接受、3×3 弱响应不超过 5 点”的连接规则。先固定规则与门槛，再校验 230 张历史正常实采图；通过后才解码 50 张历史开发回归图（17 裂纹、33 正常）。8 项几何与有界传播测试通过。

正常图仍为 0/230、0/33 报警，裂纹帧仍为 17/17 报警。但只增加 6 个标注裂纹像素和 3 个非裂纹像素，像素召回仅增加约 {summary['pixel_recall_gain_percentage_points']:.4f} 个百分点，未达到预设的 1 个百分点提升门槛，因此拒绝进入 RTL。不能把“实验运行完成”称作“算法改进成功”。

记录：`reports/v149/line_candidate/declaration.json` 固定输入和规则；`result.json` 保存拒绝结论。所有输入和模型哈希已复核，原生产工程和板端文件未变。没有为此重跑综合或烧录，没有将离线 Python 模型放入实时检测链路。

下一步：考虑仅对更低对比度像素增加更严格的方向约束；此前 V1.37 直接降低低阈值虽有召回收益，但精度不足，不能原样采用。历史图已用于开发，不属于独立盲测。正式报告仍留待多轮后统一整理。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for q in files(R/folder):
            if q.suffix not in ('.pid','.log','.pyc','.wdb') and q.name not in ('player_status.json','player_instance.json','display_command.txt'):source[q.relative_to(R).as_posix()]=sha(q)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for q in W.iterdir():
        if q.is_file() and q.suffix in ('.py','.tcl','.bat'):source[q.relative_to(R).as_posix()]=sha(q)
    proofs={R/'README.md',R/'ITERATION_PLAN.json'};proofs.update(q for q in files(O) if q.suffix in ('.json','.log','.txt','.png','.py','.csv'))
    save(R/'DELIVERY_MANIFEST.json',dict(version='V1.49',status=status,deployable=False,created_at=now,baseline=str(B),baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
        artifacts_sha256=plan['inherited_hardware_sha256'],source_sha256=source,proof_sha256={q.relative_to(R).as_posix():sha(q) for q in sorted(proofs)},validation=summary,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');text=text.replace('## 尚在进行',f'| V1.49 | 离线细线候选：收益不足，未进入 RTL，实际仍运行 V1.48 | {status} | [记录]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    a=text.index('## 尚在进行');b=text.index('## 回退和空间');text=text[:a]+'## 尚在进行\n\nV1.49 离线候选已拒绝并封存，当前实板产品仍为 V1.48。下一轮先备份实验记录，再对低对比度连接约束进行一次有明确门槛的比较。\n\n'+text[b:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,status=status,deployable=False,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

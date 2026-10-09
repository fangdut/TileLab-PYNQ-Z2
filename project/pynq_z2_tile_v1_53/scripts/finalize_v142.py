"""Bind V142 regression/build/physical evidence. --check-only does not write."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,zipfile
R=Path(__file__).resolve().parents[1];O=R/'reports/v142';W=R/(R.name+'.sdk')
VERSION='V1.42';STATUS='BOARD_REGRESSION_PASSED_INVALID_OBSERVATION_TRACKER';BOUND={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(p,d):
    p=Path(p).resolve();assert sha(p)==d,('Changed file',str(p));BOUND[str(p)]=d
def load(p):
    p=Path(p).resolve();BOUND[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def hashes(root,items):
    assert items
    for n,d in items.items():check(Path(root)/n,d)
def passed(p):
    v=load(p);assert v['passed'] is True,str(p);return v
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ref(p):return dict(path=p.relative_to(R).as_posix(),sha256=sha(p))
def files(root):
    for parent,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d not in ('__pycache__','runtime','review_records') and not (Path(parent)/d).is_symlink() and not (Path(parent)/d).is_junction()]
        for name in names:
            p=Path(parent)/name
            if not p.is_symlink():yield p

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    assert R.name=='pynq_z2_tile_v1_53'
    plan=load(R/'ITERATION_PLAN.json');assert plan['version']==VERSION
    b=Path(plan['baseline']);assert b.name=='pynq_z2_tile_v1_41'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json')
    assert old['validation']['passed'];check(plan['backup'],plan['backup_sha256'])
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    hashes(R,load(O/'build_inputs.json')['source_sha256'])
    changed=[p.relative_to(R).as_posix() for folder in ('rtl','constraints','ip_repo')
             for p in (R/folder).rglob('*') if p.is_file() and sha(p)!=sha(b/p.relative_to(R))]
    assert changed==['rtl/product_tracker.v'],changed
    warnings=load(O/'synthesis_warning_comparison.json');assert warnings['same_warning_multiset'];hashes(Path(),warnings['source_sha256'])
    hardware=passed(O/'hardware_audit.json');firmware=passed(O/'firmware_audit.json')
    hashes(R,hardware['source_sha256']);hashes(R/'reports',hardware['reports_sha256'])
    hashes(O,hardware['implemented_clock_evidence_sha256']);hashes(W,hardware['artifacts_sha256'])
    hashes(W/'ethernet_sources',firmware['source_sha256']);hashes(R,firmware['build_config_sha256'])
    check(R/'scripts/audit_v142_firmware.py',firmware['audit_script_sha256'])
    assert firmware['firmware_version']==0x12a00 and firmware['new_bit_xsa_elf']
    artifacts={n:sha(W/n) for n in (*hardware['artifacts_sha256'],'hdmi_ethernet/build/hdmi_ethernet.elf')}
    assert artifacts['hdmi_ethernet/build/hdmi_ethernet.elf']==firmware['elf_sha256']
    for n in ('system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'):assert artifacts[n]!=plan['inherited_hardware_sha256'][n]
    with zipfile.ZipFile(W/'system.xsa') as z:
        assert [hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith('.bit')]==[artifacts['system.bit']]
    base=passed(O/'tracker_invalid_baseline/summary.json')
    assert base['negative_baseline_reproduced'] and base['hardware_used'] is False
    for n,d in base['source_sha256'].items():check((b if n.startswith('rtl/') else R)/n,d)
    hashes(O/'tracker_invalid_baseline',base['proof_sha256'])
    fixed=passed(O/'tracker_invalid_fixed/summary.json');hashes(R,fixed['source_sha256']);hashes(O/'tracker_invalid_fixed',fixed['proof_sha256'])
    assert fixed['fixed_policy_validated'] and len(fixed['observations'])==20 and fixed['source_unchanged']
    assert [int(v['product_id']) for v in fixed['observations']]==[0,1,1,1,1,1,1,1,1,1,1,1,0,2,2,2,2,2,0,3]
    assert sum(bool(int(v['region_status'],16)&0x80000000) for v in fixed['observations'])==7
    integration=passed(O/'tracker_capture_invalid/summary.json');hashes(R,integration['source_sha256_after']);hashes(O/'tracker_capture_invalid',integration['proof_sha256'])
    assert integration['packets']==integration['decisions']==7 and integration['invalid_packets']==2
    assert integration['crc_checks']==14 and integration['product_ids']==[1,1,1,1,1,1,2]
    porch=passed(O/'porch_fixed/summary.json');hashes(R,porch['source_sha256']);hashes(O/'porch_fixed',porch['proof_sha256'])
    assert porch['full_packets']==12 and porch['invalid_packets']==0 and porch['packet_sequences']==list(range(1,13))
    boundary=passed(O/'scheduling_boundaries/summary.json');hashes(R,boundary['source_sha256_after']);hashes(O/'scheduling_boundaries',boundary['proof_sha256'])
    assert boundary['epochs']==22 and boundary['packets']==14 and boundary['invalid_packets']==1
    regression=passed(O/'capture_regression/summary.json');hashes(R,regression['source_sha256'])
    assert len(regression['cases'])==4 and all(c['passed'] for c in regression['cases'])
    for c in regression['cases']:
        assert 'Fatal:' not in Path(c['simulation_log']).read_text()
        check(c['simulation_log'],sha(c['simulation_log']))
        if c['independent_crc_report']:passed(c['independent_crc_report'])
    oracle=load(O/'legacy_oracle_change.json')
    assert len(oracle['changes'])==3
    for row in oracle['changes']:
        check(b/row['path'],row['before']);check(R/row['path'],row['after'])
        assert row['old_expected']==3 and row['new_expected']==2
    gate=passed(O/'product_gate_validation/summary.json');hashes(R,gate['source_sha256']);assert gate['frames_checked']==57
    native=passed(O/'firmware_native_summary.json');hashes(W/'ethernet_sources',native['source_sha256']);hashes(O,native['proof_sha256'])
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v142_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==384 and host['archive_implementation_ast_unchanged']
    program=load(R/'reports/programmed_v142.json');hashes(W,program['sha256']);boot=program['boot_id']
    assert load(O/'boot_readiness.json')['passed']
    dense=passed(O/'dense_board/summary.json');hashes(R,dense['source_sha256'])
    assert dense['programming']['record']==program and len(dense['status_windows'])==3 and len(dense['captures'])==6
    assert 'BGR24_MASK1' in dense['actual_codecs'] and not any(dense['error_deltas'].values())
    assert dense['static_product_identity']['passed'] and dense['static_product_identity']['empty_ends_product']
    for row in dense['captures']:
        if row['files_sha256']:hashes(O/'dense_board',row['files_sha256'])
        assert row['check']['passed'] and row['check']['mask_mismatch']==0 and row['check']['regions_match']
        assert row['frame']['boot_id']==boot and row['frame']['firmware_version']==0x12a00
    real=passed(O/'real_board/summary.json');hashes(Path(),real['source_sha256'])
    assert real['startup_programmed_proof']['record']==program and real['samples']==real['pixel_exact']==50
    assert not any(real['error_deltas'].values()) and real['counts']['crack']['alarms']==17 and real['counts']['good']['alarms']==0
    for row in real['items']:
        assert row['passed'];stem=f"real_{row['index']:03d}"
        check(O/'real_board'/f'{stem}_original.png',row['image_sha256']);check(O/'real_board'/f'{stem}_mask.png',row['mask_sha256'])
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256'])
    assert motion['programming']['record']==program and not any(motion['error_deltas'].values())
    assert motion['manual_saved_and_confirmed'] and motion['new_manual_archives']==1 and motion['final_enabled']
    evidence=motion['manual_evidence'];assert evidence['check']['passed']
    for label,name in evidence['files'].items():check(O/'motion_board'/name,evidence['sha256'][label])
    if args.check_only:
        print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['Invalid-frame lifecycle faults are validated by RTL injection, not a new physical HDMI fault-injection experiment.',
        'Board tests verify normal dense/photo/motion regressions with the fresh hardware and firmware.',
        'No blind factory dataset or camera; historical development photos do not establish factory accuracy.',
        'Unknown intervals freeze tracking; different products crossing during unobserved gaps cannot be distinguished without another sensor.',
        'No new human monitor confirmation; finite queue capacity and disk power-loss consistency remain limitations.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        firmware_version=0x12a00,boot_id=boot,wns_ns=hardware['wns_ns'],resources=hardware['resources'],limits=limits,industrial_acceptance=False)
    for key,folder in [('negative','tracker_invalid_baseline'),('fixed','tracker_invalid_fixed'),('capture_fault','tracker_capture_invalid'),
                       ('porch','porch_fixed'),('boundaries','scheduling_boundaries'),('dense_board','dense_board'),('real_board','real_board'),('motion_board','motion_board')]:summary[key]=ref(O/folder/'summary.json')
    for key in ('hardware','firmware','host'):summary[key]=ref(O/(key+('_validation' if key=='host' else '_audit')+'.json'))
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD',scope='PL_INVALID_OBSERVATION_TRACKING',hardware='Fresh V1.42 routed BIT/XSA and rebuilt paired ARM0x12a00; normal physical regressions passed, fault policy proved in RTL simulation')
    save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V142',all_build_sessions_completed=True,board_boot=boot,
        live_station='V1.42 real_video preview-only2fps with packed capability',next_step='Backup sealed V142 before next incremental improvement'))
    fps=[round(x['captured_fps'],2) for x in dense['status_windows']]
    (R/'README.md').write_text(f'''# TileLab V1.42

状态：{STATUS}。

修复无效采集帧错误地结束或新建瓷砖编号的问题。FPGA 对无效观察保留产品编号、离场计数和最佳帧评分，同时返回处理完成信号，让无效包正常退出，避免卡死采集。有效观察的门禁、最佳帧排序和两次有效空场结束规则保持不变。无效期间若有多块实物经过，仅凭缺失图像无法还原身份，这仍需要额外传感器或明确的失联策略。

专项仿真先复现旧版误切编号，再验证 20 次状态观察，其中 7 次无效观察均未修改跟踪状态。真实采集模块注入两张截断帧，7 包、7 次决策全部结束，原瓷砖保持编号，14 次 CRC 校验通过。另通过 12 张完整 720p 联合仿真、22 周期调度边界、57 帧门禁及原有随机/CRC 回归，384 项主机测试和固件原生协议测试。截断帧故障验证属于 RTL 仿真，没有宣称在 HDMI 实板上注入了相同故障。

重新综合布线，WNS={hardware['wns_ns']:+.3f} ns，CDC 和复位审计通过。像素 74.25 MHz、AXI 100 MHz、参考 200 MHz 均保持不变。新 BIT/XSA 与配套 ELF 在 `{W.name}`，仍以该目录作为 Vitis 工作区。Vitis 计算职责保持 DMA、队列、传输，本版仅更新版本号和启动说明。

实板空场/高密度/空场三个窗口采集率为 {fps} 帧/秒；6 次取图覆盖 {', '.join(dense['actual_codecs'])}，图像/掩码/区域及 CRC 一致；50 张历史照片回归全部通过（17 张裂纹报警，33 张正常无报警），不代表独立工厂准确率。15 秒连续移动预览与 1 次人工存档、确认流程通过，无新增队列/CRC/无效帧错误。当前仅预览，避免大量自动积累截图。

上一版 `{b.as_posix()}` 保留，备份 `{Path(plan['backup']).as_posix()}`。完整测试证据索引为 `reports/v142/validation_summary.json`，多轮迭代后再统一生成正式报告。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v142.json'}
    proofs.update(R/'reports'/n for n in hardware['reports_sha256'])
    proofs.update(Path(p) for p in BOUND if Path(p).is_relative_to(O))
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.rpt','.csv','.py','.html') and not any(part.endswith('.sim') or part=='project' for part in p.relative_to(O).parts))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),
        baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
        hardware_revision='Fresh V1.42 PL / paired ARM0x12a00',artifacts_sha256=artifacts,source_sha256=source,
        proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新实板回归：**V1.42**。无效帧不再误切瓷砖编号，专项 RTL 故障测试及新硬件正常实板回归通过。逐版仅保留简要变更和证据，多轮后统一报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.42 | 无效观察冻结产品跟踪；新 PL/ARM | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.42 已封存。下一轮先备份，再复现可验证问题。候选方向包括保存确认时限、断电一致性、有限队列和长失联后的身份处理；检测泛化需独立真实材质验证。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

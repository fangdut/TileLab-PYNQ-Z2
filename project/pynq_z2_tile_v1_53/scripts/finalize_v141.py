"""Validate and seal this iteration. No build, board or archive DB operations.
--check-only performs read/hash checks without writes.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,zipfile
R=Path(__file__).resolve().parents[1];O=R/'reports/v141';W=R/(R.name+'.sdk')
BOUND={};VERSION='V1.41';STATUS='BOARD_VALIDATED_PENDING_FRAME_SCHEDULING'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(p,d):
    p=Path(p).resolve();assert sha(p)==d,('Changed source/proof',str(p));BOUND[str(p)]=d
def load(p):
    p=Path(p).resolve();BOUND[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def hashes(root,values):
    assert values
    for n,d in values.items():check(Path(root)/n,d)
def passed(p):
    d=load(p);assert d['passed'] is True,str(p);return d
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
    b=Path(plan['baseline']);assert b.name=='pynq_z2_tile_v1_40'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json')
    assert old['validation']['passed'];check(plan['backup'],plan['backup_sha256'])
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    inputs=load(O/'build_inputs.json');hashes(R,inputs['source_sha256'])
    warnings=load(O/'synthesis_warning_comparison.json');assert warnings['same_warning_multiset']
    hashes(Path(),warnings['source_sha256'])
    hardware=passed(O/'hardware_audit.json');firmware=passed(O/'firmware_audit.json')
    hashes(R,hardware['source_sha256']);hashes(R/'reports',hardware['reports_sha256'])
    hashes(O,hardware['implemented_clock_evidence_sha256']);hashes(W,hardware['artifacts_sha256'])
    hashes(W/'ethernet_sources',firmware['source_sha256']);hashes(R,firmware['build_config_sha256'])
    check(R/'scripts/audit_v141_firmware.py',firmware['audit_script_sha256'])
    assert firmware['firmware_version']==0x12900 and firmware['new_bit_xsa_elf']
    artifacts={n:sha(W/n) for n in (*hardware['artifacts_sha256'],'hdmi_ethernet/build/hdmi_ethernet.elf')}
    assert artifacts['hdmi_ethernet/build/hdmi_ethernet.elf']==firmware['elf_sha256']
    for n in ('system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'):assert artifacts[n]!=plan['inherited_hardware_sha256'][n]
    with zipfile.ZipFile(W/'system.xsa') as z:
        assert [hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith('.bit')]==[artifacts['system.bit']]
    base=passed(O/'porch_baseline/summary.json');fixed=passed(O/'porch_fixed/summary.json')
    assert base['negative_baseline_reproduced'] and base['full_packets']==8
    for n,d in base['source_sha256'].items():check((b if n.startswith('rtl/') else R)/n,d)
    hashes(O/'porch_baseline',base['proof_sha256'])
    hashes(R,fixed['source_sha256']);hashes(O/'porch_fixed',fixed['proof_sha256'])
    assert fixed['fixed_schedule_validated'] and fixed['full_packets']==12 and fixed['invalid_packets']==0 and fixed['packet_sequences']==list(range(1,13))
    boundary=passed(O/'scheduling_boundaries/summary.json');hashes(R,boundary['source_sha256_after']);hashes(O/'scheduling_boundaries',boundary['proof_sha256'])
    assert boundary['epochs']==22 and boundary['packets']==14 and boundary['invalid_packets']==1
    regression=passed(O/'capture_regression/summary.json');hashes(R,regression['source_sha256'])
    assert len(regression['cases'])==4 and all(c['passed'] for c in regression['cases'])
    for c in regression['cases']:
        assert 'Fatal:' not in Path(c['simulation_log']).read_text()
        check(c['simulation_log'],sha(c['simulation_log']))
        if c['independent_crc_report']:passed(c['independent_crc_report'])
    gate=passed(O/'product_gate_validation/summary.json');hashes(R,gate['source_sha256']);assert gate['frames_checked']==57
    region=load(O/'region_full_inputs.json');hashes(R,region['source_sha256'])
    log=O/'region_full_sim/region_full_test.sim/sim_1/behav/xsim/simulate.log'
    text=log.read_text();assert 'Fatal:' not in text and 'REGION PASS' in text;check(log,sha(log))
    native=passed(O/'firmware_native_summary.json');hashes(W/'ethernet_sources',native['source_sha256']);hashes(O,native['proof_sha256'])
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v141_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==384 and host['archive_implementation_ast_unchanged']
    prior=passed(O/'host_validation_before_status_text.json')
    for n,d in prior['source_sha256'].items():
        check(O/'host_validation_before_status_text.html' if n=='host/benchmark.html' else R/n,d)
    program=load(R/'reports/programmed_v141.json');hashes(W,program['sha256']);boot=program['boot_id']
    ready=load(O/'boot_readiness.json');assert ready['passed']
    dense=passed(O/'dense_board/summary.json');hashes(R,dense['source_sha256'])
    assert dense['programming']['record']==program and len(dense['status_windows'])==3 and len(dense['captures'])==6
    assert 'BGR24_MASK1' in dense['actual_codecs'] and not any(dense['error_deltas'].values())
    for row in dense['captures']:
        hashes(O/'dense_board',row['files_sha256']) if row['files_sha256'] else None
        assert row['check']['passed'] and row['check']['mask_mismatch']==0 and row['check']['regions_match']
        assert row['frame']['boot_id']==boot and row['frame']['firmware_version']==0x12900
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
    limits=['No new blind factory dataset or camera acquisition; photos are historical development regression.',
      'Algorithm accuracy/material generalization is unchanged; this iteration repairs packet scheduling.',
      'If downstream blocking extends beyond first DE, a complete input frame can be skipped; finite buffering is not an unlimited lossless guarantee.',
      'No new human monitor observation; physical evidence uses board counters and acquired RGB/mask/CRC.',
      'Finite queue capacity, material-specific presence thresholds, and PNG/SQLite power-loss atomicity remain.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      baseline_negative=ref(O/'porch_baseline/summary.json'),fixed_raster=ref(O/'porch_fixed/summary.json'),
      boundaries=ref(O/'scheduling_boundaries/summary.json'),hardware=ref(O/'hardware_audit.json'),firmware=ref(O/'firmware_audit.json'),
      host=ref(O/'host_validation.json'),dense_board=ref(O/'dense_board/summary.json'),real_board=ref(O/'real_board/summary.json'),motion_board=ref(O/'motion_board/summary.json'),
      firmware_version=0x12900,boot_id=boot,wns_ns=hardware['wns_ns'],resources=hardware['resources'],limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD',scope='PL_PENDING_FRAME_SCHEDULING',hardware='Fresh V1.41 routed BIT/XSA and rebuilt paired ARM firmware 0x12900, tested on board')
    save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V141',all_build_sessions_completed=True,board_boot=boot,
        live_station='V1.41 real_video preview-only 2fps, packed capability enabled',
        next_step='Backup sealed V1.41 before next version; see next_iteration_candidate.json for source-only hypothesis'))
    fps=[round(x['captured_fps'],2) for x in dense['status_windows']]
    (R/'README.md').write_text(f'''# TileLab V1.41

状态：{STATUS}。

修复了高密度区域计算跨越下一次 VS 时，采集误判旧帧无效并漏掉下一帧的问题。现在记住 VS 启动机会，等待旧帧结果和最后一个传输字真正完成，在首个有效像素之前启动新帧。若已经错过首像素，则跳过整帧，避免把半帧保存成正常截图。像素时钟仍为 74.25 MHz，AXI 100 MHz，参考时钟 200 MHz；未改裂纹算法或协议格式。

证据：真实 720p 时序的联合仿真中，旧版 12 帧只出 8 包、其中 4 包无效；修正版连续 12 包全部有效，并通过独立 CRC。另有 22 个帧周期的堵塞/参数/复位/使能边界测试、57 帧产品门禁回归、原有 CRC/随机回归、384 项主机测试及前端测试。重新综合布线、时序/CDC/复位审计通过，WNS={hardware['wns_ns']:+.3f} ns。

实板空场→高密度噪声→空场三个状态窗口的有效采集率分别为 {fps} 帧/秒，无新增无效帧或序号缺口。6 次高密度图片取回均与参考掩码及区域结果相同，三重 CRC 通过，实际覆盖 {', '.join(dense['actual_codecs'])}；50 张历史真实照片逐像素回归全部通过（17 张裂纹报警，33 张正常无报警）。这些是开发回归，不代表独立工厂准确率或最坏网络性能。

FPGA 完成像素检测、区域、产品跟踪与流式采集；Vitis 保持 DMA/队列/传输职责，本版只更新配对版本号和启动说明。新 BIT/XSA、ELF 位于 `{W.name}`，该目录仍是 Vitis 工作区。测试明细为 `reports/v141/validation_summary.json`，正式报告留到多轮迭代后统一整理。

另有 15 秒真实照片连续移动预览验证，通过 1 次人工截图的持久保存、图像校验和板端确认；预览没有自动增加存档。当前恢复连续移动预览。局限：无限长堵塞下仍会整帧跳过；真实材质泛化、有限队列和断电存档一致性还需改善。上一版在 `{b.as_posix()}`，已备份至 `{Path(plan['backup']).as_posix()}`。没有批量自动积累业务截图。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v141.json'}
    proofs.update(R/'reports'/n for n in hardware['reports_sha256'])
    proofs.update(Path(p) for p in BOUND if Path(p).is_relative_to(O))
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.rpt','.csv','.py','.html') and not any(part.endswith('.sim') or part=='project' for part in p.relative_to(O).parts))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),
      baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
      hardware_revision='Fresh V1.41 PL / paired ARM 0x12900',artifacts_sha256=artifacts,
      source_sha256=source,proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},
      validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新实板回归：**V1.41**。已修复高密度采集跨 VS 误判，实际验证 packed 传输及 50 张历史照片。逐版仅保留简要变更和证据，批量后统一报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.41 | 高密度采集跨 VS 调度修复；新 PL/ARM | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.41 已封存。后续继续按备份、复现、修改、测试逐版改进。待评估整条保存/确认流程时限、有限队列处理与断电一致性，弱裂纹泛化仍需独立真实材质验证。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,status=STATUS,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

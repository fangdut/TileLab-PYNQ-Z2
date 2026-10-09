"""Verify provenance and seal V145; no programming or board control."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v145';W=R/(R.name+'.sdk');BOUND={}
VERSION='V1.45';STATUS='BOARD_VALIDATED_INDEPENDENT_LIVE_ARCHIVE_REFRESH'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    p=Path(p).resolve();BOUND[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def check(p,h):assert sha(p)==h,('Changed file',str(p));BOUND[str(Path(p).resolve())]=h
def hashes(root,mapping):
    for n,h in mapping.items():check(Path(root)/n,h)
def passed(p):
    value=load(p);assert value['passed'] is True,str(p);return value
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def files(root):
    for parent,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d not in ('__pycache__','runtime','review_records') and not (Path(parent)/d).is_symlink() and not (Path(parent)/d).is_junction()]
        for name in names:
            p=Path(parent)/name
            if not p.is_symlink():yield p
def ref(p):return dict(path=p.relative_to(R).as_posix(),sha256=sha(p))
def evidence(value,folder,key):
    e=value[key];assert e['check']['passed']
    for label,name in e['files'].items():check(O/folder/name,e['sha256'][label])
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    assert R.name=='pynq_z2_tile_v1_53';plan=load(R/'ITERATION_PLAN.json');assert plan['version']==VERSION
    b=Path(plan['baseline']);bw=b/(b.name+'.sdk');assert b.name=='pynq_z2_tile_v1_44'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json');assert old['validation']['passed']
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    check(plan['backup'],plan['backup_sha256'])
    for folder in ('rtl','constraints','ip_repo'):
        for p in files(R/folder):check(p,sha(b/p.relative_to(R)))
    for p in (W/'ethernet_sources').iterdir():
        if p.is_file():check(p,sha(bw/'ethernet_sources'/p.name))
    hashes(W,plan['inherited_hardware_sha256'])
    negative=passed(O/'state_wait_baseline/summary.json');assert negative['negative_baseline_reproduced'] and negative['state_blocked_during_png_publish'] and negative['source_unchanged']
    for n,h in negative['source_sha256'].items():check(O/'state_wait_baseline'/Path(n).name,h)
    check(R/'scripts/reproduce_v145_state_wait.py',negative['script_sha256'])
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v145_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==402 and host['archive_implementation_ast_unchanged']
    for key in ('review_ui','preview_ui','inventory_ui','status_ui','tcp_load','storage_process','native_stimulus'):assert host[key]['passed']
    hashes(R,host['status_ui']['source_sha256']);assert len(host['status_ui']['cases'])==8
    activation=load(O/'activation_result.json');assert activation['exit_code']==0;check(R/'scripts/activate_v145.ps1',activation['script_sha256'])
    program=load(R/'reports/programmed_v145.json');hashes(W,program['sha256']);boot=program['boot_id']
    previous=load(b/'reports/programmed_v144.json');check(program['source_programming_record'],program['source_programming_sha256'])
    assert program['sha256']==previous['sha256'] and boot==previous['boot_id']
    assert datetime.datetime.fromisoformat(program['programmed_at'])==datetime.datetime.fromisoformat(previous['programmed_at'])
    board=passed(O/'live_state_board/summary.json');hashes(R,board['source_sha256']);assert board['programming']['record']==program
    assert len(board['live_observations'])==9 and len(board['archive_observations'])==8
    assert all(v['status']==200 and v['milliseconds']<1000 and v['response']['capture_control']['phase']=='SAVE' for v in board['live_observations'])
    assert all(v['status']==503 and v['response']['code']=='ARCHIVE_BUSY' for v in board['archive_observations'])
    assert board['after_archive']['status']==200 and board['pause_while_writer_reserved']['milliseconds']<1000
    assert board['one_admitted_frame_saved'] and board['no_extra_capture'] and board['final_paused'] and board['post_commit_confirmation']
    assert not any(board['error_deltas'].values()) and len(board['history'])==1;evidence(board,'live_state_board','saved_evidence')
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256']);assert motion['programming']['record']==program
    assert not any(motion['error_deltas'].values()) and motion['new_manual_archives']==1 and motion['manual_saved_and_confirmed'] and motion['final_enabled']
    evidence(motion,'motion_board','manual_evidence')
    browser=passed(O/'browser_qa.json');hashes(R,browser['source_sha256']);check(O/'browser_archive.png',browser['screenshot_sha256'])
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['Timing is one bounded physical contention experiment, not a hard real-time upper bound.',
        'Live still reads player status files; storage configuration and other control actions can perform synchronous work.',
        'Legacy /api/state, review and export can wait for disk. Archive scans and saves still share the Records lock.',
        'Client timeout cannot cancel server filesystem work; concurrent archive requests are refused until the current lock holder exits.',
        'Hardware/firmware remain V142; no new detector accuracy or industrial acceptance claim.',
        'A manual request may retrieve an older queued event. The first contention-test image was an earlier HDMI desktop scene, not the current moving tile; motion-test image was a tile.',
        'Browser displayed 11 historical queue drops since boot; both bounded board tests added zero.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),hardware_revision='Reused sealed V1.42 PL/ARM through V1.44',
        firmware_version=0x12a00,boot_id=boot,host_tests=402,status_ui_cases=8,negative=ref(O/'state_wait_baseline/summary.json'),host=ref(O/'host_validation.json'),
        live_state_board=ref(O/'live_state_board/summary.json'),motion_board=ref(O/'motion_board/summary.json'),browser=ref(O/'browser_qa.json'),
        live_max_ms=board['live_max_ms'],pause_ms=board['pause_while_writer_reserved']['milliseconds'],writer_held_seconds=board['writer_held_seconds'],limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD_HOST_ONLY',hardware='Unchanged V142 PL/ARM0x12a00; actual archive contention, independent live status and moving preview passed');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V145',all_test_sessions_completed=True,board_boot=boot,live_station='V1.45 real_video preview-only2fps, packed capability; two manual archives',
        next_step='Backup before next iteration; inspect archive category semantics and remaining synchronous storage configuration path'))
    (R/'README.md').write_text(f'''# TileLab V1.45

状态：{STATUS}。

网页将实时采集状态与存档列表分开请求。存图时仍可更新保存阶段和暂停状态；存档忙碌立即返回繁忙提示，保留并标记旧快照，防止积压等待请求。筛选改变和控制操作会使旧响应失效，列表不能覆盖新的控制状态。盘点占用、快照时间与当前存储配置分别处理。

原版真实 HTTP 隔离测试复现了完整状态读取等待 PNG 写入。修复后 402 项 Python 回归、48 项 JavaScript 用例以及 TCP/进程故障回归通过。实板持有实际数据库写锁约 {summary['writer_held_seconds']:.2f} 秒，9 次实时状态查询最长约 {summary['live_max_ms']:.0f} ms，暂停约 {summary['pause_ms']:.0f} ms；释放后只保存并确认已接收帧。15 秒照片运动输入测试、一次额外保存与原图/掩码/CRC 校验通过，无新增采集、丢失或确认错误。网页已实际检查，两张验收存档可按筛选显示。

这是主机端改进，FPGA 与 Vitis 仍使用 V1.42 的 BIT/XSA/ELF（固件 `0x12a00`），未重新烧录。完整硬件工作区仍为 `D:/Vivado/pynq_z2_tile_v1_42`。入口 `host/start_station.ps1`；验证索引 `reports/v145/validation_summary.json`。已备份 `{Path(plan['backup']).as_posix()}`。

边界：新实时接口仍读取播放器状态文件，配置存储等操作仍可能同步等待；本版不承诺所有磁盘情况下的响应上限。旧完整状态、复核与导出可能等待存档。客户端超时不能取消服务器文件操作，但新存档接口不会在存档锁后无限累积等待请求。首次争用截图是之前排队的 HDMI 桌面画面；后续运动验收截图是瓷砖。页面历史丢失计数 11 未清零，本版两段测试增量均为零。

旧工程保持完整。仅新增两张业务验收截图，平时仅预览，避免长时间运行累积截图。按用户偏好，多版之后集中生成正式报告。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v145.json'}
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.csv','.py','.ps1','.html','.sqlite3'))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),baseline_manifest_sha256=plan['baseline_manifest_sha256'],
        backup=plan['backup'],backup_sha256=plan['backup_sha256'],artifacts_sha256=plan['inherited_hardware_sha256'],hardware_revision='Sealed V142 inherited unchanged',
        source_sha256=source,proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新电脑端及实板流程回归：**V1.45**。采集状态与存档独立刷新，402 项主机回归及实板争用/移动保存通过；硬件沿用 V1.42。多轮后统一正式报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.45 | 实时状态与存档独立刷新；402 项回归和实板争用验证 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间');text=text[:i]+'## 尚在进行\n\nV1.45 已封存。下一轮先备份，检查存档分类语义及同步存储配置等待；继续保持检测位于 FPGA。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

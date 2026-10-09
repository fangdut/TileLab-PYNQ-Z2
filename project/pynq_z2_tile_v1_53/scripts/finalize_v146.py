"""Verify provenance and seal V146; no programming or board control."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v146';W=R/(R.name+'.sdk');BOUND={}
VERSION='V1.46';STATUS='BOARD_VALIDATED_RESPONSIVE_STORAGE_CONFIGURATION'
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
    b=Path(plan['baseline']);bw=b/(b.name+'.sdk');assert b.name=='pynq_z2_tile_v1_45'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json');assert old['validation']['passed']
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    check(plan['backup'],plan['backup_sha256'])
    for folder in ('rtl','constraints','ip_repo'):
        for p in files(R/folder):check(p,sha(b/p.relative_to(R)))
    for p in (W/'ethernet_sources').iterdir():
        if p.is_file():check(p,sha(bw/'ethernet_sources'/p.name))
    hashes(W,plan['inherited_hardware_sha256'])
    negative=passed(O/'storage_control_baseline/summary.json');assert negative['negative_baseline_reproduced'] and negative['pause_blocked_during_policy_write'] and negative['source_unchanged']
    for n,h in negative['source_sha256'].items():check(O/'storage_control_baseline'/Path(n).name,h)
    check(R/'scripts/reproduce_v146_storage_control.py',negative['script_sha256'])
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v146_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==409 and host['archive_implementation_ast_unchanged']
    for key in ('review_ui','preview_ui','inventory_ui','status_ui','tcp_load','storage_process','native_stimulus'):assert host[key]['passed']
    hashes(R,host['status_ui']['source_sha256']);assert len(host['status_ui']['cases'])==8
    activation=load(O/'activation_result.json');assert activation['exit_code']==0;check(R/'scripts/activate_v146.ps1',activation['script_sha256'])
    program=load(R/'reports/programmed_v146.json');hashes(W,program['sha256']);boot=program['boot_id']
    previous=load(b/'reports/programmed_v145.json');check(program['source_programming_record'],program['source_programming_sha256'])
    assert program['sha256']==previous['sha256'] and boot==previous['boot_id']
    assert datetime.datetime.fromisoformat(program['programmed_at'])==datetime.datetime.fromisoformat(previous['programmed_at'])
    board=passed(O/'storage_control_board/summary.json');hashes(R,board['source_sha256']);assert board['programming']['record']==program
    assert len(board['live_observations'])==10
    assert all(v['milliseconds']<1000 and v['response']['capture_control']['phase']=='STORAGE' for v in board['live_observations'])
    assert [v['op'] for v in board['actions'][:3]]==['pause','start','pause']
    assert all(v['status']==200 and v['milliseconds']<1000 for v in board['actions'][:3])
    assert all(v['status']==400 for v in board['actions'][3:])
    assert board['no_capture_before_commit'] and board['no_capture_after_final_pause'] and board['final_paused'] and board['policy_restored_exactly']
    assert not any(board['error_deltas'].values())
    assert board['committed_policy']==dict(mode='archive',max_archive_mib=32)
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256']);assert motion['programming']['record']==program
    assert not any(motion['error_deltas'].values()) and motion['new_manual_archives']==1 and motion['manual_saved_and_confirmed'] and motion['final_enabled']
    evidence(motion,'motion_board','manual_evidence')
    browser=passed(O/'browser_qa.json');hashes(R,browser['source_sha256']);check(O/'browser_workstation.png',browser['screenshot_sha256'])
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['One bounded contention experiment, not a hard real-time response or disk-completion guarantee.',
        'Configuration temporarily prevents new capture admission; the FPGA detector continues independently.',
        'Pause affects capture intent, not an already admitted settings write. A successful write still applies after Pause.',
        'Player status reads and HDMI command publication still involve synchronous filesystem work.',
        'PL/ARM remain V142; archive review/export can still wait for storage; power-loss testing and factory blind accuracy are separate work.',
        'The page shows 11 historical dropped events since board boot; both bounded tests added zero.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),hardware_revision='Reused sealed V1.42 PL/ARM through V1.45',
        firmware_version=0x12a00,boot_id=boot,host_tests=409,status_ui_cases=8,negative=ref(O/'storage_control_baseline/summary.json'),host=ref(O/'host_validation.json'),
        storage_control_board=ref(O/'storage_control_board/summary.json'),motion_board=ref(O/'motion_board/summary.json'),browser=ref(O/'browser_qa.json'),
        live_max_ms=board['live_max_ms'],pause_ms=max(v['milliseconds'] for v in board['actions'][:3] if v['op']=='pause'),writer_held_seconds=board['writer_held_seconds'],limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD_HOST_ONLY',hardware='Unchanged V142 PL/ARM0x12a00; actual storage-configuration contention, Pause/Start ordering and moving preview passed');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V146',all_test_sessions_completed=True,board_boot=boot,live_station='V1.46 real_video preview-only2fps, packed capability; one manual archive',
        next_step='Backup before next iteration; review synchronous display command publication and prioritise a measurable detector/transport improvement'))
    (R/'README.md').write_text(f"""# TileLab V1.46

状态：{STATUS}。

存储配置不再持有控制锁等待容量检查和文件写入。检查期间先预留操作，暂停新取图；新设置写入成功后才同时发布新的内存策略和容量上限。失败保留旧配置。暂停、开始及实时状态查询继续响应，最终采用最近一次采集意图。网页显示“正在检查和保存存储设置”，忙碌时禁用重复提交。

隔离的真实 HTTP 测试复现了旧版慢配置写入阻塞暂停。修复后 409 项 Python 回归、48 项 JavaScript 用例、TCP 与进程故障回归通过，包含配置失败、超容量、数据库写超时、重复请求及暂停—开始—再暂停。

实板连接的工作站配置期间，实际存档数据库由独立连接持有写锁约 {summary['writer_held_seconds']:.3f} 秒。10 次实时状态查询最长约 {summary['live_max_ms']:.0f} ms；控制操作顺序得到保留，配置前后没有意外取图。释放后新设置正确落盘，再恢复仅预览 1024 MiB 上限。随后完成 15 秒真实照片运动输入、1 张手动存档、图像/掩码及 CRC 校验，无新增采集或确认错误。默认自动证据列表可能不显示手动样本，可切换“全部记录”。

本版修改电脑端控制流程；FPGA 和 Vitis 沿用 V1.42，固件 `0x12a00`，未重新烧录。完整硬件工作区仍在 `D:/Vivado/pynq_z2_tile_v1_42`。入口 `host/start_station.ps1`；证据 `reports/v146/validation_summary.json`。旧版备份 `{Path(plan['backup']).as_posix()}`。

边界：暂停不会取消已开始的配置写入；这是采集意图暂停，配置成功仍然生效。配置过程中暂缓主机取图，板端检测继续且队列容量有限。本次有界争用测试不代表最坏响应时间；HDMI 输入命令和播放器状态读取仍有同步文件访问。掉电耐久性与工厂盲测精度尚不能由这些测试证明。页面保留本次板卡启动以来 11 条历史丢失计数，两段验收测试无新增。

保持旧工程和回退备份，只保存一张业务验收截图。按照用户偏好，多版后集中生成正式报告。
""",encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v146.json'}
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.csv','.py','.ps1','.html','.sqlite3'))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),baseline_manifest_sha256=plan['baseline_manifest_sha256'],
        backup=plan['backup'],backup_sha256=plan['backup_sha256'],artifacts_sha256=plan['inherited_hardware_sha256'],hardware_revision='Sealed V142 inherited unchanged',
        source_sha256=source,proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新电脑端及实板流程回归：**V1.46**。存储配置期间控制保持响应，409 项主机回归及实板配置争用/移动保存通过；硬件沿用 V1.42。多轮后统一正式报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.46 | 存储配置不阻塞暂停；409 项回归和实板配置争用验证 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间');text=text[:i]+'## 尚在进行\n\nV1.46 已封存。下一轮先备份，评估输入命令同步等待，并优先选择可测量的检测或传输改进；继续保持检测位于 FPGA。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

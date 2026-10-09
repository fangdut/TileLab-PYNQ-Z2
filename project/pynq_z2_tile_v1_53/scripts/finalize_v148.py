"""Verify provenance and seal V148; no programming or board control."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v148';W=R/(R.name+'.sdk');BOUND={}
VERSION='V1.48';STATUS='BOARD_VALIDATED_PLAYER_TELEMETRY_CONTROL_ISOLATION'
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
    b=Path(plan['baseline']);bw=b/(b.name+'.sdk');assert b.name=='pynq_z2_tile_v1_47'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json');assert old['validation']['passed']
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    check(plan['backup'],plan['backup_sha256'])
    for folder in ('rtl','constraints','ip_repo'):
        for p in files(R/folder):check(p,sha(b/p.relative_to(R)))
    for p in (W/'ethernet_sources').iterdir():
        if p.is_file():check(p,sha(bw/'ethernet_sources'/p.name))
    hashes(W,plan['inherited_hardware_sha256'])
    negative=passed(O/'player_read_baseline/summary.json');assert negative['negative_baseline_reproduced'] and negative['pause_blocked_during_player_read'] and negative['source_unchanged']
    for n,h in negative['source_sha256'].items():check(O/'player_read_baseline'/Path(n).name,h)
    check(R/'scripts/reproduce_v148_player_read.py',negative['script_sha256'])
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v148_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==419 and host['archive_implementation_ast_unchanged']
    for key in ('review_ui','preview_ui','inventory_ui','status_ui','display_ui','tcp_load','storage_process','native_stimulus'):assert host[key]['passed']
    hashes(R,host['status_ui']['source_sha256']);assert len(host['status_ui']['cases'])==8
    hashes(R,host['display_ui']['source_sha256']);assert len(host['display_ui']['cases'])==5
    activation=load(O/'activation_result.json');assert activation['exit_code']==0;check(R/'scripts/activate_v148.ps1',activation['script_sha256'])
    program=load(R/'reports/programmed_v148.json');hashes(W,program['sha256']);boot=program['boot_id']
    previous=load(b/'reports/programmed_v147.json');check(program['source_programming_record'],program['source_programming_sha256'])
    assert program['sha256']==previous['sha256'] and boot==previous['boot_id']
    assert datetime.datetime.fromisoformat(program['programmed_at'])==datetime.datetime.fromisoformat(previous['programmed_at'])
    board=passed(O/'player_read_board/summary.json');hashes(R,board['source_sha256']);assert board['programming']['record']==program
    assert len(board['observations'])>=8 and board['capture_delta_during_denial']>=2
    assert all(v['milliseconds']<1000 and v['response']['stimulus_status']['state']=='PLAYER_INSTANCE_UNAVAILABLE' and not v['response']['stimulus_status']['ready'] and v['response']['capture_health']['ready'] for v in board['observations'])
    assert board['pause_during_read_denial']['status']==200 and board['pause_during_read_denial']['milliseconds']<1000
    assert board['final_paused'] and board['identity_confirmation_recovered'] and board['marker_unchanged']
    assert not any(board['error_deltas'].values())
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256']);assert motion['programming']['record']==program
    assert not any(motion['error_deltas'].values()) and motion['new_manual_archives']==1 and motion['manual_saved_and_confirmed'] and motion['final_enabled']
    evidence(motion,'motion_board','manual_evidence')
    browser=passed(O/'browser_qa.json');hashes(R,browser['source_sha256']);check(O/'browser_workstation.png',browser['screenshot_sha256'])
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['Slow-read blocking is an isolated injected-delay test; the physical test uses actual Windows read denial, not stalled disk I/O.',
        'Player status HTTP requests may still wait for files or the separate telemetry lock. No asynchronous cache or hard latency bound is claimed.',
        'Input publication can wait for serialized telemetry metadata after its file has changed; capture control remains independent.',
        'Player adoption and board capture health are distinct; missing local identity does not prove HDMI has failed.',
        'PL/ARM remain V142; no new detector accuracy or industrial acceptance claim.',
        'Page retains historical queue drops=11; bounded board tests added zero.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),hardware_revision='Reused sealed V1.42 PL/ARM through V1.47',
        firmware_version=0x12a00,boot_id=boot,host_tests=419,status_ui_cases=8,negative=ref(O/'player_read_baseline/summary.json'),host=ref(O/'host_validation.json'),
        player_read_board=ref(O/'player_read_board/summary.json'),motion_board=ref(O/'motion_board/summary.json'),browser=ref(O/'browser_qa.json'),
        live_max_ms=board['live_max_ms'],pause_ms=board['pause_during_read_denial']['milliseconds'],read_denied_seconds=board['held_seconds'],limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD_HOST_ONLY',hardware='Unchanged V142 PL/ARM0x12a00; actual player identity read denial with continuing capture and moving preview passed');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V148',all_test_sessions_completed=True,board_boot=boot,live_station='V1.48 real_video preview-only2fps, packed capability; one manual archive',
        next_step='Backup before next iteration; evaluate one predeclared thin-crack connectivity candidate offline; no algorithm deployment unless normal-image and precision gates pass'))
    (R/'README.md').write_text(f"""# TileLab V1.48

状态：{STATUS}。

播放器状态文件的读取改用独立锁，在采集控制锁之外执行；并发读取仍按顺序访问播放器进度状态，输入命令更新请求元数据也遵循同一顺序。文件等待不再妨碍暂停、开始以及图像采集、保存和确认。

隔离环境注入慢播放器状态读取，复现并修复了旧版暂停被阻塞的问题。419 项 Python 回归、53 项 JavaScript 用例及 TCP/进程故障回归通过，包括等待期间取图保存完成、暂停—开始—再暂停、并发读取串行、发布命令等待元数据及异常后释放锁。

实板工作站用 Windows 共享句柄拒绝读取播放器身份文件约 {summary['read_denied_seconds']:.3f} 秒，期间新采集 {board['capture_delta_during_denial']} 帧，页面状态明确区分身份未确认和板端采集正常。释放句柄后恢复原请求身份确认，文件保持不变；暂停约 {summary['pause_ms']:.0f} ms 返回，无新增采集或确认错误。注意：这是读取被拒绝测试，不是物理磁盘慢读实验。另完成 15 秒连续移动和一张手动证据保存，原图、掩码及 CRC 通过。

FPGA/Vitis 沿用 V1.42（固件 `0x12a00`），本版没有重新烧录。完整硬件工作区仍在 `D:/Vivado/pynq_z2_tile_v1_42`；入口 `host/start_station.ps1`；证据 `reports/v148/validation_summary.json`。旧版备份 `{Path(plan['backup']).as_posix()}`。

剩余边界：状态 HTTP 请求本身仍可能等待播放器文件或独立读锁，当前并非异步遥测缓存；已发布的输入命令也可能等待请求元数据更新完成，但不会因此占住采集控制锁。不保证任意文件系统故障下的延迟上限。历史板端丢失计数 11 保留，本版两段测试增量为零。仅预览持续运行，业务库新增一张验收截图。

这组控制路径修复封存后，下一步回到细弱裂纹的连接规则，先在已有开发数据上比较误报和漏检，通过明确门槛后才考虑修改 FPGA。按用户偏好，正式报告在多个版本后集中整理。
""",encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v148.json'}
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.csv','.py','.ps1','.html','.sqlite3'))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),baseline_manifest_sha256=plan['baseline_manifest_sha256'],
        backup=plan['backup'],backup_sha256=plan['backup_sha256'],artifacts_sha256=plan['inherited_hardware_sha256'],hardware_revision='Sealed V142 inherited unchanged',
        source_sha256=source,proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新电脑端及实板流程回归：**V1.48**。播放器状态读取与采集控制分离，419 项主机回归及实板读取拒绝/移动保存通过；硬件沿用 V1.42。多轮后统一正式报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.48 | 播放器读取不占用采集控制锁；419 项回归及实板读取拒绝验证 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间');text=text[:i]+'## 尚在进行\n\nV1.48 已封存。下一轮先备份，先离线比较一种细弱裂纹连接规则；达到正常图像误报和精度门槛才考虑进入 FPGA 验证；继续保持检测位于 FPGA。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

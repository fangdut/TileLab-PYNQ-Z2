"""Verify provenance and seal V147; no programming or board control."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v147';W=R/(R.name+'.sdk');BOUND={}
VERSION='V1.47';STATUS='BOARD_VALIDATED_INDEPENDENT_SOURCE_PUBLICATION'
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
    b=Path(plan['baseline']);bw=b/(b.name+'.sdk');assert b.name=='pynq_z2_tile_v1_46'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json');assert old['validation']['passed']
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    check(plan['backup'],plan['backup_sha256'])
    for folder in ('rtl','constraints','ip_repo'):
        for p in files(R/folder):check(p,sha(b/p.relative_to(R)))
    for p in (W/'ethernet_sources').iterdir():
        if p.is_file():check(p,sha(bw/'ethernet_sources'/p.name))
    hashes(W,plan['inherited_hardware_sha256'])
    negative=passed(O/'display_control_baseline/summary.json');assert negative['negative_baseline_reproduced'] and negative['pause_blocked_during_command_publish'] and negative['source_unchanged']
    for n,h in negative['source_sha256'].items():check(O/'display_control_baseline'/Path(n).name,h)
    check(R/'scripts/reproduce_v147_display_control.py',negative['script_sha256'])
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v147_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==414 and host['archive_implementation_ast_unchanged']
    for key in ('review_ui','preview_ui','inventory_ui','status_ui','display_ui','tcp_load','storage_process','native_stimulus'):assert host[key]['passed']
    hashes(R,host['status_ui']['source_sha256']);assert len(host['status_ui']['cases'])==8
    hashes(R,host['display_ui']['source_sha256']);assert len(host['display_ui']['cases'])==5
    activation=load(O/'activation_result.json');assert activation['exit_code']==0;check(R/'scripts/activate_v147.ps1',activation['script_sha256'])
    program=load(R/'reports/programmed_v147.json');hashes(W,program['sha256']);boot=program['boot_id']
    previous=load(b/'reports/programmed_v146.json');check(program['source_programming_record'],program['source_programming_sha256'])
    assert program['sha256']==previous['sha256'] and boot==previous['boot_id']
    assert datetime.datetime.fromisoformat(program['programmed_at'])==datetime.datetime.fromisoformat(previous['programmed_at'])
    board=passed(O/'display_control_board/summary.json');hashes(R,board['source_sha256']);assert board['programming']['record']==program
    assert len(board['live_observations'])==4
    assert all(v['milliseconds']<1000 and v['response']['display_pending'] is not None for v in board['live_observations'])
    assert board['pause_during_publish']['status']==200 and board['pause_during_publish']['milliseconds']<1000
    assert board['second_publish_rejected']['status']==400 and board['publication']['status']==200
    assert board['final_paused'] and board['no_unrequested_capture'] and board['old_command_preserved_until_release'] and board['exact_new_request_adopted']
    assert not any(board['error_deltas'].values())
    assert board['adopted_input']['request_id']==board['publication']['response']['request_id']
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256']);assert motion['programming']['record']==program
    assert not any(motion['error_deltas'].values()) and motion['new_manual_archives']==1 and motion['manual_saved_and_confirmed'] and motion['final_enabled']
    evidence(motion,'motion_board','manual_evidence')
    browser=passed(O/'browser_qa.json');hashes(R,browser['source_sha256']);check(O/'browser_workstation.png',browser['screenshot_sha256'])
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['Bounded actual Windows file-sharing contention, not a guarantee against arbitrary filesystem stalls.',
        'Only one source command may publish at a time. A second request is rejected until publication finishes.',
        'Pause changes capture intent; it does not cancel a source command already being written.',
        'Command publication, player adoption and physical HDMI reception remain distinct confirmations.',
        'Player status reads still occur synchronously; no claim of fully nonblocking filesystem telemetry.',
        'PL/ARM remain V142; no new detector accuracy or factory acceptance claim.',
        'Historical board queue drop count is 11; both bounded tests added zero.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),hardware_revision='Reused sealed V1.42 PL/ARM through V1.46',
        firmware_version=0x12a00,boot_id=boot,host_tests=414,status_ui_cases=8,negative=ref(O/'display_control_baseline/summary.json'),host=ref(O/'host_validation.json'),
        display_control_board=ref(O/'display_control_board/summary.json'),motion_board=ref(O/'motion_board/summary.json'),browser=ref(O/'browser_qa.json'),
        live_max_ms=board['live_max_ms'],pause_ms=board['pause_during_publish']['milliseconds'],writer_held_seconds=board['writer_held_seconds'],limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD_HOST_ONLY',hardware='Unchanged V142 PL/ARM0x12a00; actual Windows source-command sharing contention and moving preview passed');save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V147',all_test_sessions_completed=True,board_boot=boot,live_station='V1.47 real_video preview-only2fps, packed capability; one manual archive',
        next_step='Backup before next iteration; review remaining synchronous player-status reads; inspect detector/transport opportunities after control-path reliability work'))
    (R/'README.md').write_text(f"""# TileLab V1.47

状态：{STATUS}。

HDMI 测试素材命令在控制锁之外发布。文件暂被占用时，暂停和实时状态不再等待文件替换；已在运行的取图可继续。单一发布者保护命令临时文件，重复切换返回等待提示。网页单独显示正在写入的请求，原输入的播放器确认不会被误认为新输入已采用。

旧版通过真实 Windows 共享句柄阻止文件替换，复现了暂停等待。修复后 414 项 Python 回归、53 项 JavaScript 用例及 TCP/进程故障回归通过，覆盖发布失败、重复发布、输入身份和发布期间取图。

实板连接的工作站上，真实文件占用约 {summary['writer_held_seconds']:.3f} 秒，实时状态最长约 {summary['live_max_ms']:.0f} ms；暂停约 {summary['pause_ms']:.0f} ms 返回。占用期间旧命令保持不变，第二次切换被拒绝；释放后播放器采用了准确的新请求编号，没有意外取图。另完成 15 秒连续移动照片输入和一张手动保存，原图/掩码和 CRC 通过，无新增传输或确认错误。

本版修改电脑端，FPGA 与 Vitis 继续沿用 V1.42（固件 `0x12a00`），未重新烧录。完整硬件工作区在 `D:/Vivado/pynq_z2_tile_v1_42`。入口 `host/start_station.ps1`，证据 `reports/v147/validation_summary.json`。备份 `{Path(plan['backup']).as_posix()}`。

边界：暂停不会取消已经开始的输入命令；命令写入成功、播放器采用、物理 HDMI 有效是三个不同确认层次。播放器状态文件读取仍是同步访问；本次实验不是任意磁盘故障下的响应上限。页面历史丢失计数 11 保留，本版实板验收没有增加。默认仅预览，业务库只增加一张验收截图。

按用户习惯，正式报告在多个版本之后集中整理；本版仅保留说明、备份和测试证据。
""",encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v147.json'}
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.csv','.py','.ps1','.html','.sqlite3'))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),baseline_manifest_sha256=plan['baseline_manifest_sha256'],
        backup=plan['backup'],backup_sha256=plan['backup_sha256'],artifacts_sha256=plan['inherited_hardware_sha256'],hardware_revision='Sealed V142 inherited unchanged',
        source_sha256=source,proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新电脑端及实板流程回归：**V1.47**。输入命令发布不阻塞采集控制，414 项主机回归及实板文件争用/移动保存通过；硬件沿用 V1.42。多轮后统一正式报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.47 | HDMI 命令发布不阻塞暂停；414 项回归和实板文件争用验证 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间');text=text[:i]+'## 尚在进行\n\nV1.47 已封存。下一轮先备份，评估播放器状态读取的同步等待，并选择可测量的检测或传输改进；继续保持检测位于 FPGA。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

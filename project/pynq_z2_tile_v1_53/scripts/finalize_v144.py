"""Seal V144 control responsiveness; never build, program or operate the board."""
from pathlib import Path
import argparse,ast,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v144';W=R/(R.name+'.sdk');BOUND={}
STATUS='BOARD_VALIDATED_PAUSE_DURING_ARCHIVE_SAVE';VERSION='V1.44'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(p,d):
    p=Path(p).resolve();assert sha(p)==d,('Changed file',str(p));BOUND[str(p)]=d
def load(p):
    p=Path(p).resolve();BOUND[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def hashes(root,items):
    for n,d in items.items():check(Path(root)/n,d)
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
def station_method(p,name):
    cls=next(n for n in ast.parse(p.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='Station')
    return ast.dump(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    assert R.name=='pynq_z2_tile_v1_53'
    plan=load(R/'ITERATION_PLAN.json');assert plan['version']==VERSION
    b=Path(plan['baseline']);bw=b/(b.name+'.sdk');assert b.name=='pynq_z2_tile_v1_43'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json')
    check(plan['backup'],plan['backup_sha256']);assert old['validation']['passed']
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    for folder in ('rtl','constraints','ip_repo'):
        for p in files(R/folder):check(p,sha(b/p.relative_to(R)))
    for p in (W/'ethernet_sources').iterdir():
        if p.is_file():check(p,sha(bw/'ethernet_sources'/p.name))
    hashes(W,plan['inherited_hardware_sha256'])
    negative=passed(O/'pause_save_baseline/summary.json')
    assert negative['negative_baseline_reproduced'] and negative['pause_blocked_before_storage_release'] and negative['source_unchanged']
    for name,digest in negative['source_sha256'].items():check(O/'pause_save_baseline/source_before.py' if name=='host/workstation.py' else R/name,digest)
    for name in ('loop','action'):assert station_method(O/'pause_save_baseline/source_before.py',name)==station_method(b/'host/workstation.py',name)
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v144_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==397 and host['archive_implementation_ast_unchanged']
    for key in ('review_ui','preview_ui','inventory_ui','tcp_load','storage_process','native_stimulus'):assert host[key]['passed']
    program=load(R/'reports/programmed_v144.json');hashes(W,program['sha256']);boot=program['boot_id']
    previous=load(b/'reports/programmed_v143.json');check(program['source_programming_record'],program['source_programming_sha256'])
    assert program['sha256']==previous['sha256'] and boot==previous['boot_id']
    assert datetime.datetime.fromisoformat(program['programmed_at'])==datetime.datetime.fromisoformat(previous['programmed_at'])
    board=passed(O/'save_pause_board/summary.json');hashes(R,board['source_sha256']);assert board['programming']['record']==program
    assert board['pause_while_writer_reserved']['status']==200 and board['pause_while_writer_reserved']['milliseconds']<1000
    assert board['busy_diagnostic_rejected']['status']==400 and board['one_admitted_frame_saved'] and board['no_extra_capture'] and board['final_paused']
    assert board['post_commit_confirmation'] and not any(board['error_deltas'].values()) and len(board['history'])==1
    evidence=board['saved_evidence'];assert evidence['check']['passed']
    for label,path in evidence['files'].items():check(O/'save_pause_board'/path,evidence['sha256'][label])
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256']);assert motion['programming']['record']==program
    assert not any(motion['error_deltas'].values()) and motion['manual_saved_and_confirmed'] and motion['new_manual_archives']==1 and motion['final_enabled']
    evidence=motion['manual_evidence'];assert evidence['check']['passed']
    for label,path in evidence['files'].items():check(O/'motion_board'/path,evidence['sha256'][label])
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['Physical contention result is one bounded experiment, not a worst-case disk/control latency guarantee.',
        'Pause stops new admissions; an already admitted frame still completes saving and ACK, and disk completion itself is not preempted.',
        'Archive/state reads can still wait for a writer; no claim that every UI request is nonblocking.',
        'Storage-setting changes are rejected while an operation is busy; retry after completion.',
        'PL/ARM remain V142; detector generalization, finite queues and power-loss durability remain separate limitations.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        hardware_revision='Reused sealed V1.42 PL/ARM through V1.43',firmware_version=0x12a00,boot_id=boot,host_tests=397,
        negative=ref(O/'pause_save_baseline/summary.json'),host=ref(O/'host_validation.json'),
        save_pause_board=ref(O/'save_pause_board/summary.json'),motion_board=ref(O/'motion_board/summary.json'),
        pause_ms=board['pause_while_writer_reserved']['milliseconds'],writer_held_seconds=board['writer_held_seconds'],limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD_HOST_ONLY',hardware='Unchanged V142 PL/ARM0x12a00; physical capture, Pause during SQLite writer contention and moving preview passed')
    save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V144',all_test_sessions_completed=True,board_boot=boot,
        live_station='V1.44 real_video preview-only2fps with packed capability; two bounded manual archives',
        next_step='Backup before next incremental version; full state/archive HTTP responses can still wait for Records lock'))
    (R/'README.md').write_text(f'''# TileLab V1.44

状态：{STATUS}。

修复存图期间暂停请求被控制锁阻塞的问题。图片发布与数据库事务使用存档自己的锁；暂停新采集可以先返回，已经接收的帧仍完整保存后才确认板端事件。忙碌期间修改存储模式会要求等待，避免当前存图策略发生竞争。

原代码的真实 HTTP 隔离测试复现了暂停必须等待 PNG 发布。修复后 397 项主机回归通过，包含图片/掩码慢写、数据库写竞争、保存失败、满额转预览，以及暂停—开始—再暂停的最新意图检查。

实板测试持有实际存档数据库写锁约 {summary['writer_held_seconds']*1000:.0f} ms，收到 FPGA 图像后，暂停约 {summary['pause_ms']:.0f} ms 返回；释放写锁后仅保存并确认已接收的一帧，原图、掩码、三重 CRC 和确认历史一致，无新增传输/确认错误。此为有界实验，不代表任意磁盘故障下的最坏响应时间。另通过 15 秒连续移动预览和一次人工保存验证，已恢复仅预览 2 fps，业务库共两条验收截图。

FPGA/Vitis 继续复用 V1.42 的 BIT/XSA/ELF（ARM `0x12a00`），本版没有重新烧录。完整硬件工作区仍为 `D:/Vivado/pynq_z2_tile_v1_42`。本版电脑入口 `host/start_station.ps1`，证据索引 `reports/v144/validation_summary.json`。旧版备份 `{Path(plan['backup']).as_posix()}`。

局限：列表、完整状态读取仍可能等待存档锁；暂停不取消已经开始的文件写入，也不承诺文件系统完成时限。后续评估快速控制状态与存档列表分开刷新。正式报告在多轮迭代后统一整理。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v144.json'}
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.csv','.py','.sqlite3'))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),
        baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
        artifacts_sha256=plan['inherited_hardware_sha256'],hardware_revision='Sealed V142 inherited unchanged',source_sha256=source,
        proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新电脑端及实板流程回归：**V1.44**。慢存图期间暂停响应修复，397 项测试和实际数据库争用/移动保存通过；硬件沿用 V1.42。多轮后统一正式报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.44 | 存图期间暂停及时响应；397 项回归及实板争用测试 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.44 已封存。下一轮先备份，评估完整状态和存档列表读取在写入期间的等待；继续保持检测位于 FPGA。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

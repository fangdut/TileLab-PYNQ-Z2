"""Seal the host-only confirmation fix against frozen source/board evidence."""
from pathlib import Path
import argparse,datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v143';W=R/(R.name+'.sdk');BOUND={}
STATUS='BOARD_VALIDATED_ATOMIC_CONFIRMATION_SETTLEMENT';VERSION='V1.43'
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
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    assert R.name=='pynq_z2_tile_v1_53'
    plan=load(R/'ITERATION_PLAN.json');assert plan['version']==VERSION
    b=Path(plan['baseline']);bw=b/(b.name+'.sdk');assert b.name=='pynq_z2_tile_v1_42'
    check(b/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256']);old=load(b/'DELIVERY_MANIFEST.json')
    check(plan['backup'],plan['backup_sha256']);assert old['validation']['passed']
    for group in ('source_sha256','proof_sha256'):hashes(b,old[group])
    for folder in ('rtl','constraints','ip_repo'):
        for p in files(R/folder):check(p,sha(b/p.relative_to(R)))
    for p in (W/'ethernet_sources').iterdir():
        if p.is_file():check(p,sha(bw/'ethernet_sources'/p.name))
    hashes(W,plan['inherited_hardware_sha256'])
    negative=passed(O/'settle_baseline/summary.json');assert negative['negative_baseline_reproduced'] and negative['source_unchanged']
    check(b/'host/confirmation_journal.py',negative['source_sha256']['host/confirmation_journal.py'])
    check(R/'scripts/reproduce_settle_race.py',negative['source_sha256']['scripts/reproduce_settle_race.py'])
    check(O/'settle_baseline/isolated.sqlite3',negative['database_sha256'])
    assert negative['settled_event_ids']==[1,1] and negative['new_pending_after_old_settlement'] is None
    host=passed(O/'host_validation.json');hashes(R,host['source_sha256']);check(R/'scripts/validate_v143_host.py',host['validation_script_sha256'])
    assert host['unit_tests']['count']==391 and host['archive_implementation_ast_unchanged']
    for key in ('review_ui','preview_ui','inventory_ui','tcp_load','storage_process','native_stimulus'):assert host[key]['passed']
    crash=passed(O/'settle_process/summary.json');hashes(R,crash['source_sha256']);assert crash['source_unchanged'] and len(crash['cases'])==4
    for row in crash['cases']:
        assert row['passed'] and row['exit_code']==73 and row['retry_history_count']==1
        check(O/'settle_process'/(row['phase']+'.sqlite3'),row['database_sha256'])
    program=load(R/'reports/programmed_v143.json');hashes(W,program['sha256']);boot=program['boot_id']
    previous=load(b/'reports/programmed_v142.json');check(program['source_programming_record'],program['source_programming_sha256'])
    assert program['sha256']==previous['sha256'] and boot==previous['boot_id']
    assert datetime.datetime.fromisoformat(program['programmed_at'])==datetime.datetime.fromisoformat(previous['programmed_at'])
    activation=passed(O/'activation_verified.json');check(R/'reports/programmed_v143.json',activation['programming_record_sha256'])
    check(R/'scripts/activate_v143.ps1',activation['activation_script_sha256'])
    motion=passed(O/'motion_board/summary.json');hashes(R,motion['source_sha256']);assert motion['programming']['record']==program
    assert not any(motion['error_deltas'].values()) and motion['manual_saved_and_confirmed'] and motion['new_manual_archives']==1
    evidence=motion['manual_evidence'];assert evidence['check']['passed']
    for name,path in evidence['files'].items():check(O/'motion_board'/path,evidence['sha256'][name])
    restart=passed(O/'station_restart/summary.json');hashes(R,restart['source_sha256']);assert restart['programming']['record']==program
    assert restart['image_check']['passed'] and restart['archive_bytes_identical'] and restart['unchanged_board_boot']
    assert restart['record_count']==restart['completion_history_count']==1 and restart['no_extra_capture_while_paused'] and restart['final_enabled']
    attempt=load(O/'station_restart_launcher_pipe_attempt/observed_failure.json');assert attempt['passed'] is False
    check(O/'station_restart_launcher_pipe_attempt/test_v143_station_restart_before.py',attempt['source_sha256'])
    if args.check_only:print(json.dumps(dict(passed=True,writes=False,verified_files=len(BOUND))));return
    limits=['Independent SQLite connections and process exit tests are isolated fault injection, not physical disk power-loss tests.',
        'Actual board test covers normal moving input, one saved frame/ACK and Station service restart; no physical board reset.',
        'PL/ARM remain sealed V142, firmware0x12a00. No new hardware or detector improvement claimed.',
        'Finite queues, long unobserved physical-product gaps and real-material detector generalization remain limitations.']
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        hardware_revision='Reused sealed V1.42 PL/ARM',firmware_version=0x12a00,boot_id=boot,host_tests=391,
        negative=ref(O/'settle_baseline/summary.json'),host=ref(O/'host_validation.json'),process_recovery=ref(O/'settle_process/summary.json'),
        motion_board=ref(O/'motion_board/summary.json'),station_restart=ref(O/'station_restart/summary.json'),limits=limits,industrial_acceptance=False)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD_HOST_ONLY',scope='HOST_ATOMIC_CONFIRMATION_SETTLEMENT',hardware='Reused unchanged sealed V142 PL/ARM0x12a00; same physical boot verified during V143 host workflow tests')
    save(R/'ITERATION_PLAN.json',plan)
    save(O/'continuation.json',dict(phase='SEALED_V143',all_test_sessions_completed=True,board_boot=boot,
        live_station='V1.43 real_video preview-only2fps, packed capability; one manual archive',
        next_step='Backup before next incremental version; assess control response during slow evidence writes'))
    (R/'README.md').write_text(f'''# TileLab V1.43

状态：{STATUS}。

电脑端修复了多连接同时完成截图确认时，旧操作删除新待确认记录的问题。读取身份、写入完成历史、删除待确认记录现在处于同一个 SQLite 写事务内。异常会整体回滚；调用者已有事务时拒绝执行，避免误提交别人的工作。

先用原代码复现：事件 1 的旧确认删掉事件 2 的新待确认记录，并生成两条事件 1 历史。修复后 391 项主机测试通过；四个阶段强制退出进程，重启后状态完整、重试仅保留一条完成历史。这属于程序进程退出验证，不等于硬盘断电验证。

实板连续移动预览和一次人工截图、确认通过。重启工作站服务后，原图、掩码、CRC、存档身份与完成历史一致，暂停状态下没有新取图，没有新增存档，开发板启动身份保持不变。重启测试第一次因启动器输出管道被后台程序继承而等待，已保留失败记录并修复测试脚本，重测通过。

FPGA 和 Vitis 的业务代码没有改变，复用 V1.42 的 BIT/XSA/ELF（ARM 版本 `0x12a00`），本版没有重新烧录。完整 Vivado/Vitis 构建工作区仍保留在 `{b.as_posix()}`；本版电脑程序入口 `host/start_station.ps1`，已恢复连续移动、仅预览、2 fps 取图。仅保留 1 条人工验收截图，避免持续自动积累数据。

测试索引 `reports/v143/validation_summary.json`。旧版备份 `{Path(plan['backup']).as_posix()}`。逐版只保留简短记录和证据，多轮后统一正式报告。后续优先评估慢磁盘存图期间的控制响应，检测材质泛化仍需独立数据验证。
''',encoding='utf-8')
    source={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for p in files(R/folder):
            if p.suffix not in ('.pid','.log','.pyc','.wdb') and p.name not in ('player_status.json','player_instance.json','display_command.txt'):source[p.relative_to(R).as_posix()]=sha(p)
    source['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.tcl','.bat'):source[p.relative_to(R).as_posix()]=sha(p)
    proofs={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v143.json'}
    proofs.update(p for p in files(O) if p.suffix in ('.json','.log','.png','.txt','.csv','.py','.sqlite3'))
    save(R/'DELIVERY_MANIFEST.json',dict(version=VERSION,status=STATUS,created_at=summary['completed_at'],baseline=str(b),
        baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup=plan['backup'],backup_sha256=plan['backup_sha256'],
        artifacts_sha256=plan['inherited_hardware_sha256'],hardware_revision='Sealed V142 inherited unchanged',source_sha256=source,
        proof_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(proofs)},validation=summary,limits=limits,report='README.md'))
    index=R.parent/'TileLab_进度与回退.md';text=index.read_text(encoding='utf-8');i=text.index('更新：');j=text.index('## 当前产品')
    text=text[:i]+f'更新：{summary["completed_at"]}\n\n最新电脑端及实板流程回归：**V1.43**。确认写事务并发修复，391 项主机测试、退出恢复与实际保存/服务重启通过；硬件沿用 V1.42。多轮后统一正式报告。\n\n'+text[j:]
    text=text.replace('## 尚在进行',f'| V1.43 | 确认写事务、并发隔离与退出恢复；复用 V142 PL/ARM | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i=text.index('## 尚在进行');j=text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.43 已封存。下一轮先备份，评估慢存储操作是否阻塞暂停控制；继续区分隔离故障注入与实板验收。\n\n'+text[j:];index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(passed=True,version=VERSION,source_files=len(source),proof_files=len(proofs))))
if __name__=='__main__':main()

"""Check existing V1.39 evidence, then seal a concise host-only iteration.

Never builds, programs hardware, starts a service, or opens the archive database.
--check-only performs reads/hashes only and writes no files or directories.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import argparse
import ast
import datetime
import hashlib
import json
import os
import zipfile

R=Path(__file__).resolve().parents[1];O=R/'reports/v139';W=R/(R.name+'.sdk')
VERSION='V1.39';FIRMWARE=0x12500;STATUS='BOARD_VALIDATED_EXCLUSIVE_DIAGNOSTIC_RESERVATION'
ERRORS=('gaps','invalid','dropped','ack_errors','descriptor_crc_errors')
CRCS=('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')
BOUND={}


def require(value,message):
    if not value:raise RuntimeError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def checked(path,digest):
    path=Path(path).resolve();actual=sha(path)
    require(actual==digest,'Changed evidence/source: '+str(path));BOUND[str(path)]=actual
def load(path):
    path=Path(path).resolve();data=path.read_bytes();BOUND[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data.decode('utf-8-sig'))
def hashes(root,values):
    require(values,'Empty hash evidence')
    for name,digest in values.items():checked(Path(root)/name,digest)
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def inside(root,name):
    path=(Path(root)/name).resolve();require(path.is_relative_to(Path(root).resolve()),'Evidence path escapes directory')
    return path
def files(root):
    for parent,directories,names in os.walk(root,followlinks=False):
        directories[:]=[name for name in directories if name not in ('__pycache__','runtime','review_records')
                       and not (Path(parent)/name).is_symlink() and not (Path(parent)/name).is_junction()]
        for name in names:
            path=Path(parent)/name
            if not path.is_symlink():yield path
def passed(value,name):require(value.get('passed') is True,name+' did not pass')
def stats(value,boot):
    require(value['version']==FIRMWARE and value['boot_id']==boot and value['error_status']==0,'Wrong board identity or active error')
def reference(path):return dict(path=path.relative_to(R).as_posix(),sha256=sha(path))


def inherited(plan):
    baseline=Path(plan['baseline']);require(baseline.name=='pynq_z2_tile_v1_38','Wrong baseline')
    checked(baseline/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256'])
    old=load(baseline/'DELIVERY_MANIFEST.json')
    require(old['version']=='V1.38' and old['validation']['passed'] is True,'Baseline is not sealed/passed V1.38')
    for group in ('source_sha256','proof_sha256'):hashes(baseline,old[group])
    checked(Path(plan['backup']),plan['backup_sha256'])
    for name in ('rtl','constraints','ip_repo','models','ethernet_sources'):
        current=W/name if name=='ethernet_sources' else R/name
        previous=baseline/(baseline.name+'.sdk')/name if name=='ethernet_sources' else baseline/name
        require(current.is_dir() and previous.is_dir(),'Missing inherited source directory')
        a={p.relative_to(current).as_posix():p for p in files(current)}
        b={p.relative_to(previous).as_posix():p for p in files(previous)}
        require(set(a)==set(b),'Inherited file inventory changed: '+name)
        for key,path in a.items():checked(path,sha(b[key]))
    artifacts=plan['inherited_hardware_sha256'];hashes(W,artifacts)
    require(set(artifacts)=={'system.bit','system.xsa','system.ltx','hdmi_ethernet/build/hdmi_ethernet.elf'},'Incomplete inherited artifact plan')
    require(all(old['artifacts_sha256'][k]==v for k,v in artifacts.items()),'Inherited binaries differ from sealed V1.38')
    audit=load(O/'inheritance_audit.json');passed(audit,'Inheritance audit')
    require(audit['revision']==VERSION,'Wrong inheritance audit revision')
    hashes(R,audit['source_sha256']);hashes(baseline,audit['baseline_source_sha256'])
    hashes(W,audit['artifacts_sha256']);hashes(R/'reports',audit['reports_sha256'])
    checked(R/'scripts/audit_v139_inheritance.py',audit['audit_script_sha256'])
    require(audit['artifacts_sha256']==artifacts and audit['unchanged_source_files']==len(audit['source_sha256'])
            and audit['baseline_manifest_sha256']==plan['baseline_manifest_sha256'] and audit['backup_sha256']==plan['backup_sha256'],'Binary audit/plan mismatch')
    with zipfile.ZipFile(W/'system.xsa') as archive:
        bits=[hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.lower().endswith('.bit')]
    require(bits==[artifacts['system.bit']],'XSA embedded bit differs')
    checked(W/'ps7_init.tcl',sha(baseline/(baseline.name+'.sdk')/'ps7_init.tcl'))
    def records(path):
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        return ast.dump(next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Records'))
    require(records(R/'host/workstation.py')==records(baseline/'host/workstation.py'),'Archive implementation changed')
    return baseline,audit,artifacts


def host_checks():
    host=load(O/'host_validation.json');passed(host,'Host regression')
    unit=host['unit_tests'];passed(unit,'Unit regression')
    require(host['version']==VERSION and unit['count']>=365 and not unit['failures'] and not unit['errors'],'Incomplete host suite')
    hashes(R,host['source_sha256'])
    checked(R/'scripts/validate_v139_host.py',host['validation_script_sha256'])
    for name,minimum in (('review_ui',19),('preview_ui',11),('inventory_ui',10)):
        value=host[name];passed(value,name)
        require(value['tests']>=minimum and len(value['cases'])==value['tests'] and all(c['passed'] is True for c in value['cases']),'Incomplete UI regression')
        if 'html_sha256' in value:checked(R/'host/workstation.html',value['html_sha256'])
    checked(R/'host/review_session.js',host['review_ui']['session_source_sha256'])
    require(host['archive_implementation_ast_unchanged'] is True,'Missing archive AST proof')
    tcp=host['tcp_load'];passed(tcp,'Loopback TCP');hashes(R,tcp['source_sha256'])
    require(load(O/'preview_tcp_load/summary.json')==tcp,'Loopback embedded/output mismatch')
    require({c['preview_rate_fps'] for c in tcp['cases']}=={0,2,5} and all(c['passed'] is True and c['all_headers_and_pixels_crc_validated'] is True and c['all_saved_events_committed_before_ack'] is True for c in tcp['cases']),'Loopback integrity/ACK regression incomplete')
    process=host['storage_process'];passed(process,'Storage process regression')
    require(load(O/'storage_rollback_process/summary.json')==process and all(c['passed'] is True for c in process['cases']),'Storage process output mismatch/failure')
    mapping={'baseline/workstation.py':R.parent/'pynq_z2_tile_v1_34/host/workstation.py',
             'current/workstation.py':R/'host/workstation.py','current/archive_inventory.py':R/'host/archive_inventory.py',
             'test_script':R/'scripts/test_storage_rollback_process.py'}
    require(set(process['source_sha256'])==set(mapping),'Unexpected storage proof inputs')
    for key,path in mapping.items():checked(path,process['source_sha256'][key])
    native=host['native_stimulus'];passed(native,'Native player regression')
    require(native['actual_renderer_compiled'] is True and native['player_script_syntax'] is True,'Native player not compiled/parsed')
    require(load(O/'native_stimulus/summary.json')==native,'Native player embedded/output mismatch')
    snapshot=load(O/'recipe_snapshot_summary.json');passed(snapshot,'Atomic request tests')
    require(snapshot['tests']>=12 and len(snapshot['test_ids'])==snapshot['tests'] and snapshot['failures']==snapshot['errors']==0,'Snapshot coverage incomplete')
    hashes(R,snapshot['source_sha256'])
    negative=snapshot['negative_controls']
    require({c['negative_control'] for c in negative}=={'capture','configure'} and all(c['old']==[90,True,4,False] and c['new']==[36,True,2,True] and c['observed']==[90,True,2,True] for c in negative),'Mixed-tuple negative baseline not reproduced')
    diagnostic=load(O/'diagnostic_reservation_summary.json');passed(diagnostic,'Diagnostic reservation tests')
    require(diagnostic['tests']>=10 and len(set(diagnostic['test_ids']))==diagnostic['tests']
            and diagnostic['failures']==diagnostic['errors']==0,'Diagnostic coverage incomplete')
    hashes(R,diagnostic['source_sha256'])
    require(set(diagnostic['source_sha256'])=={'host/workstation.py','host/test_diagnostic_reservation.py'},'Wrong diagnostic test inputs')
    previous=R.parent/'pynq_z2_tile_v1_38'
    negative=load(previous/'reports/v138/next_iteration_analysis/status_lock_negative.json')
    passed(negative,'Blocked-status negative baseline')
    require(negative['revision']=='V1.38' and negative['negative_reproduced'] is True
            and negative['lock_acquirable_nonblocking_while_stats_blocked'] is False
            and negative['pause_pending_before_stats_release'] is True and negative['pause_completed_after_release'] is True
            and negative['stats_calls']==1 and negative['captures']==0,'Missing status-lock negative baseline')
    hashes(previous,negative['source_sha256'])
    checked(previous/'reports/v138/next_iteration_analysis/reproduce_status_lock.py',negative['script_sha256'])
    review=None
    if (O/'independent_diagnostic_review.json').exists():
        review=load(O/'independent_diagnostic_review.json');passed(review,'Independent source review');hashes(R,review['source_sha256'])
        require(review['revision']==VERSION and not review['actionable_findings'] and review['checks']
                and all(v is True for v in review['checks'].values()),'Unresolved independent review findings')
        checked(O/'diagnostic_reservation_summary.json',review['specialist_test_proof_sha256'])
        checked(previous/'host/workstation.py',review['baseline_workstation_sha256'])
        prepared=review['prepared_validation_script']
        require(prepared['ast_checked'] is True and prepared['reviewer_executed'] is False,'Incorrect independent script review scope')
        checked(inside(R,prepared['path']),prepared['sha256'])
    followup=O/'next_iteration_analysis/receive_deadline_negative.json'
    if followup.exists():
        value=load(followup);passed(value,'Slow-progress negative analysis')
        require(value['revision']==VERSION and value['negative_reproduced'] is True,'Invalid next-iteration negative analysis')
        hashes(R,value['source_sha256'])
        checked(followup.with_name('reproduce_receive_deadline.py'),value['script_sha256'])
    return host,snapshot,diagnostic,review


def board_checks(artifacts):
    program=load(R/'reports/programmed_v139.json');ready=load(O/'boot_readiness.json');passed(ready,'Board readiness')
    require(program['active_application']=='hdmi_ethernet' and type(program['boot_id']) is int,'Missing Ethernet programming proof')
    boot=program['boot_id'];stats(ready['state'],boot);hashes(W,program['sha256'])
    require(set(program['sha256'])=={'system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'} and all(artifacts[k]==v for k,v in program['sha256'].items()),'Programming proof differs from inherited artifacts')
    local=load(O/'diagnostics_loopback/summary.json');verify_loopback(local)
    board=load(O/'diagnostics_board/summary.json');verify_board_schema(board,boot,program)
    return program,ready,local,board


def run_proof(value,mode):
    passed(value,mode+' diagnostic test')
    require(value['revision']==VERSION and value['mode']==mode and value['sources_unchanged'] is True,'Wrong diagnostic test identity or changed source')
    hashes(R,value['source_sha256'])
    required={'scripts/board_v139_diagnostics.py','host/workstation.py','host/tcp_transport.py','host/recipes.py','host/recipes.json'}
    require(required.issubset(value['source_sha256']),'Diagnostic source binding incomplete')
    run=inside(O/('diagnostics_'+mode),value['run_directory'])
    require(load(run/'summary.json')==value,'Diagnostic latest/run summary mismatch')
    keys=('source_sha256','startup_programmed_proof') if mode=='board' else ('source_sha256',)
    require(load(run/'provenance.json')=={key:value[key] for key in keys},'Diagnostic startup provenance mismatch')
    return run


def pixel_check(value,boot,firmware):
    passed(value,'Complete image/CRC consistency')
    require(value['boot_id']==boot and value['firmware_version']==firmware
            and all(value[key] is True for key in ('complete_720p_frame','crc3','reconstructed_pixel_crc_matches','candidate_count_matches')),
            'Image identity, CRC or candidate-count check failed')
    for key in ('image_sha256','mask_sha256'):
        require(isinstance(value[key],str) and len(value[key])==64,'Missing checked PNG digest')


def verify_loopback(value):
    run_proof(value,'loopback')
    require(all(value[key] is True for key in ('pause_completed_before_status_release','start_intent_queued_without_capture',
            'release_kept_latest_pause','manual_saved_before_ack','status_header_crc_verified','temporary_business_files_removed')),
            'Delayed-socket diagnostic/control/ACK check failed')
    require(value['reserved_phase_observed']=='DIAGNOSTIC' and value['requests_sent_before_release']==1
            and value['competing_socket_bytes_before_release'] is False and value['pending_confirmation'] is False,
            'Missing exclusive diagnostic connection proof')
    require(set(value['rejected_during_diagnostic'])=={'capture','status','disconnect','resume_pending'}
            and all(value['rejected_during_diagnostic'].values()),'Missing conflicting-control rejection')
    require(0<=value['pause_http_ms']<500 and 0<=value['start_http_ms']<500 and value['diagnostic_delay_seconds']>0,
            'Delayed-socket response check exceeded bound')
    require(value['protocol_fixture_version']==0x12000 and value['transport']['reconnects']==0
            and value['transport']['acks']==1 and value['transport']['requests']>1,'Unexpected loopback fixture transport')
    require(set(value['ports'])=={'http','tcp'} and all(0<int(port)<=65535 and port!=8770 for port in value['ports'].values()),
            'Loopback did not use isolated ports')
    pixel_check(value['manual_frame_check'],value['manual_frame_check']['boot_id'],value['protocol_fixture_version'])


def verify_board_schema(board,boot,program):
    run=run_proof(board,'board')
    require(board['firmware_version']==FIRMWARE and board['boot_id']==boot,'Wrong physical test identity')
    require(board['programmed_artifacts_unchanged'] is True and not board['cleanup_errors'],'Changed programmed artifacts or failed cleanup')
    startup=board['startup_programmed_proof']
    require(Path(startup['path']).resolve()==(R/'reports/programmed_v139.json').resolve() and startup['record']==program,'Physical programming record mismatch')
    checked(R/'reports/programmed_v139.json',startup['marker_sha256']);hashes(W,startup['artifact_sha256'])
    require(startup['artifact_sha256']==program['sha256'],'Startup artifact/marker mismatch')
    for name in ('before','after'):stats(board[name],boot)
    errors={key:(board['after'][key]-board['before'][key])&0xffffffff for key in ERRORS}
    require(board['error_deltas']==errors and not any(errors.values()),'Physical error deltas nonzero or inconsistent')
    control=board['final_control']
    require(board['after']['depth']==0 and all(not control[key] for key in ('enabled','busy','manual_waiting','pending_operation','pending_confirmation'))
            and control['capture_control']['phase']=='IDLE','Board queue/control/pending ACK not drained')
    require(board['manual_saved_and_confirmation_completed'] is True,'Manual save/confirmation not complete')
    windows=board['windows'];require(len(windows)==3 and {row['index'] for row in windows}=={0,1,2},'Missing bounded physical windows')
    statuses=[]
    for row in windows:
        require(row['captures']>=2 and row['live_pair_retained'] is True and row['paused_stays_stopped'] is True,'Capture or post-Pause stop failed')
        statuses.extend(row['status_requests'])
    require(all(row['outcome'] in ('accepted','busy_rejected') for row in statuses),'Unexpected physical status outcome')
    accepted=sum(row['outcome']=='accepted' for row in statuses)
    rejected=sum(row['outcome']=='busy_rejected' for row in statuses)
    require(accepted==board['status_accepted'] and accepted>=3 and rejected==board['status_busy_rejected'],'Physical status count mismatch')
    pauses=board['pause_measurements']
    require(len(pauses)==3 and {row['window'] for row in pauses}=={0,1,2},'Missing physical Pause observations')
    for row in pauses:
        require(0<=row['pause_http_ms']<1500 and row['pause_and_inflight_completion_ms']>=row['pause_http_ms']
                and row['concurrent_status_outcome'] in ('accepted','busy_rejected') and type(row['status_thread_overlap']) is bool,
                'Physical Pause observation failed')
    require(board['status_during_manual']['outcome'] in ('accepted','busy_rejected'),'Unexpected status/manual outcome')
    require(len(board['live_evidence'])==3 and len(board['manual_evidence'])==1,'Missing bounded retained PNG evidence')
    for value in board['live_evidence']+board['manual_evidence']:
        frame=value['frame'];check=value['check'];pixel_check(check,boot,FIRMWARE)
        require(frame['boot_id']==boot and frame['firmware_version']==FIRMWARE and frame['width']==1280 and frame['height']==720
                and all(frame[key] is True for key in CRCS),'Physical frame identity/dimensions/CRC failed')
        require(frame['frame_id']==check['frame_id'] and frame['event_id']==check['event_id'],'PNG check/frame mismatch')
        require(value['sha256']=={'original':check['image_sha256'],'mask':check['mask_sha256']},'PNG digest/check mismatch')
        for kind in ('original','mask'):checked(inside(run,value['files'][kind]),value['sha256'][kind])
    manual=board['manual_evidence'][0];frame=manual['frame']
    require(frame['id']==board['manual_record_id'] and frame['reason']=='manual'
            and frame['image_sha256']==manual['sha256']['original'] and frame['mask_sha256']==manual['sha256']['mask'],
            'Manual record/PNG/archive digest mismatch')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    require(R.name=='pynq_z2_tile_v1_53' and not R.is_symlink() and not R.is_junction(),'Wrong project root')
    plan=load(R/'ITERATION_PLAN.json');require(plan['version']==VERSION,'Wrong iteration plan')
    baseline,audit,artifacts=inherited(plan);host,snapshot,diagnostic,review=host_checks();program,ready,local,board=board_checks(artifacts)
    index=R.parent/'TileLab_进度与回退.md';old_index=index.read_text(encoding='utf-8')
    require(all(marker in old_index for marker in ('更新：','## 当前产品','## 尚在进行','## 回退和空间')),'Progress index layout changed')
    if args.check_only:
        print(json.dumps(dict(version=VERSION,passed=True,writes=False,verified_files=len(BOUND),unit_tests=host['unit_tests']['count'])));return
    limits=['Pause promptly updates host intent; an already admitted request must still complete or fail before the exclusive bridge is released.',
            'Only the local fixture deliberately withholds a reply. Physical thread overlap is not proof of a blocked board response.',
            'Physical HTTP timings are observations with clock/scheduler granularity, not real-time guarantees or throughput measurements.',
            'PL/ARM/model artifacts remain byte-identical to sealed V1.37 via V1.38; no new detector accuracy, RTL or 50-photo result is claimed.',
            'The board run uses repeated synthetic moving tiles, not independent factory samples or a new human HDMI-output visual confirmation.',
            'Idle receive timeout still permits impractically long requests under continued slow progress; total request deadlines remain a follow-up candidate.',
            'Finite board queues, material-specific brightness gates, crack generalization and PNG/SQLite power-loss boundaries remain.']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=now,
                 scope='Exclusive diagnostics outside the Station control lock; unchanged V1.37 FPGA/ARM; delayed-loopback and bounded physical regression',
                 host_validation=reference(O/'host_validation.json'),unit_tests=host['unit_tests'],
                 frontend_tests=sum(host[k]['tests'] for k in ('review_ui','preview_ui','inventory_ui')),
                 recipe_snapshot=dict(**reference(O/'recipe_snapshot_summary.json'),tests=snapshot['tests']),
                 diagnostic_reservation=dict(**reference(O/'diagnostic_reservation_summary.json'),tests=diagnostic['tests']),
                 diagnostic_loopback=dict(**reference(O/'diagnostics_loopback/summary.json'),
                    pause_completed_before_status_release=local['pause_completed_before_status_release'],
                    no_competing_socket_request=not local['competing_socket_bytes_before_release']),
                 inheritance=reference(O/'inheritance_audit.json'),programming=reference(R/'reports/programmed_v139.json'),
                 boot_readiness=reference(O/'boot_readiness.json'),board_test=dict(performed=True,boot_id=program['boot_id'],firmware_version=FIRMWARE,
                    **reference(O/'diagnostics_board/summary.json'),windows=len(board['windows']),
                    captures_in_windows=sum(row['captures'] for row in board['windows']),
                    status_accepted=board['status_accepted'],status_busy_rejected=board['status_busy_rejected'],
                    manual_archives=len(board['manual_evidence']),pause_http_ms=[row['pause_http_ms'] for row in board['pause_measurements']],
                    error_deltas=board['error_deltas']),
                 independent_review=reference(O/'independent_diagnostic_review.json') if review else None,limits=limits)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD',hardware='Byte-identical sealed V1.37 PL/ARM via V1.38; V1.39 host diagnostic reservation, delayed-loopback and physical regression passed')
    save(R/'ITERATION_PLAN.json',plan)
    (R/'README.md').write_text(f'''# TileLab V1.39

状态：{STATUS}。

本版修复读取板端状态时网络等待占用电脑端控制锁、导致暂停按钮一起等待的问题。现在先在短锁内预留连接，再到锁外读取状态，结束或异常时释放预留。暂停/开始可以及时更新意图；等待期间工作线程不会同时使用该连接，抓拍、再次诊断和断开会明确拒绝。待确认图像、待补读状态和已排队人工操作优先处理。保留旧桥接口、先存档后确认及 V1.38 完整配方快照。

验证：{host['unit_tests']['count']} 项主机、{summary['frontend_tests']} 项前端通过，其中包含 {diagnostic['tests']} 项诊断互斥专项和 {snapshot['tests']} 项配方快照专项。真实本机 HTTP/TCP 延迟夹具确认暂停在状态回复放行前完成、连接无竞争请求、释放后人工存档先于确认。实板完成 3 个观察窗口、{summary['board_test']['captures_in_windows']} 次窗口内取图、{board['status_accepted']} 次诊断成功及 {board['status_busy_rejected']} 次明确忙拒绝；保留 3 对预览 PNG 和 1 对人工存档 PNG，完整图像、三项 CRC 声明/校验和重建像素校验一致，错误计数增量为零。详情见 `reports/v139/validation_summary.json`。

暂停立即更新意图不等于中止已准入传输；后者仍需完成或失败。只有本机夹具刻意延迟回复，实板并发线程有重叠也不能证明板端长时间等待。HTTP 耗时受时钟粒度影响，零读数不代表零延迟，不构成实时上限承诺。

FPGA、ARM/Vitis、参考算法及 BIT/XSA/ELF 经 V1.38 继承封存 V1.37，逐字节一致，仍由 FPGA 在线检测；本版没有重做 50 图或 RTL 测试，不宣称提高裂纹精度。合成移动素材不等于工厂独立样本，未新增人工外接屏幕目视确认。下一步优先研究接收总时限：目前空闲超时无法约束持续少量进展的慢回复。有限队列、弱裂纹泛化及 PNG/数据库断电边界仍需改进。

打开 `{R.name}.xpr`；Vitis 工作区 `{W.name}`。回退工程 `{baseline.as_posix()}`，备份 `{Path(plan['backup']).as_posix()}`。本版仅保留简短摘要，批量后统一报告。
''',encoding='utf-8')
    sources={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for path in files(R/folder):
            if path.suffix not in ('.pid','.log','.pyc','.wdb') and path.name not in ('player_status.json','player_instance.json','display_command.txt'):
                sources[path.relative_to(R).as_posix()]=sha(path)
    sources['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for path in W.iterdir():
        if path.is_file() and path.suffix in ('.py','.tcl','.bat'):sources[path.relative_to(R).as_posix()]=sha(path)
    proof_paths={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v139.json'}
    proof_paths.update(R/'reports'/name for name in audit['reports_sha256'])
    proof_paths.update(path for path in files(O) if path.suffix in ('.json','.log','.png','.txt','.rpt','.py'))
    proofs={path.relative_to(R).as_posix():sha(path) for path in sorted(proof_paths)}
    for path in (R/'ITERATION_PLAN.json',O/'validation_summary.json'):BOUND[str(path.resolve())]=sha(path)
    manifest=dict(version=VERSION,status=STATUS,created_at=now,baseline=str(baseline),baseline_manifest_sha256=plan['baseline_manifest_sha256'],
                  backup=plan['backup'],backup_sha256=plan['backup_sha256'],hardware_revision='Byte-identical sealed V1.37 PL/ARM',
                  artifacts_sha256=artifacts,inherited_artifacts_sha256=artifacts,source_sha256=sources,proof_sha256=proofs,
                  executed_input_output_sha256=BOUND,validation=summary,report='README.md',limits=limits,
                  hash_scope='Executed proof inputs are checked against saved hashes; the finalizer is sealed as current source, not claimed as a prior test execution.')
    save(R/'DELIVERY_MANIFEST.json',manifest)
    i,j=old_index.index('更新：'),old_index.index('## 当前产品')
    text=old_index[:i]+f'更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新实板验收：**V1.39**。状态诊断等待移出控制锁并预留独占连接，延迟本机夹具及实板回归通过；PL/ARM 沿用 V1.37。只保存逐版摘要，批量后统一报告。\n\n'+old_index[j:]
    text='\n'.join(line for line in text.split('\n') if not line.startswith('| V1.39 |'))
    text=text.replace('## 尚在进行',f'| V1.39 | 状态诊断独占连接、暂停响应与延迟夹具/实板回归 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i,j=text.index('## 尚在进行'),text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.39 已封存。后续继续按小步、备份、故障复现和实板验证迭代；优先研究接收总时限，避免持续少量进展的慢回复长期占用连接。未登记证据的断电恢复、材质泛化和传输负载仍待改善。低门禁仅为材质标定，弱阈值 TL34 候选仍维持拒绝。\n\n'+text[j:]
    index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(version=VERSION,status=STATUS,boot_id=program['boot_id'],unit_tests=host['unit_tests']['count'],source_files=len(sources),proof_files=len(proofs))))


if __name__=='__main__':main()

"""Check existing V1.40 evidence, then seal a concise host-only iteration.

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

R=Path(__file__).resolve().parents[1];O=R/'reports/v140';W=R/(R.name+'.sdk')
VERSION='V1.40';FIRMWARE=0x12500;STATUS='BOARD_VALIDATED_DEADLINES_WITH_DENSE_INPUT_LIMIT'
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
    baseline=Path(plan['baseline']);require(baseline.name=='pynq_z2_tile_v1_39','Wrong baseline')
    checked(baseline/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256'])
    old=load(baseline/'DELIVERY_MANIFEST.json')
    require(old['version']=='V1.39' and old['validation']['passed'] is True,'Baseline is not sealed/passed V1.39')
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
    require(all(old['artifacts_sha256'][k]==v for k,v in artifacts.items()),'Inherited binaries differ from sealed V1.39')
    audit=load(O/'inheritance_audit.json');passed(audit,'Inheritance audit')
    require(audit['revision']==VERSION,'Wrong inheritance audit revision')
    hashes(R,audit['source_sha256']);hashes(baseline,audit['baseline_source_sha256'])
    hashes(W,audit['artifacts_sha256']);hashes(R/'reports',audit['reports_sha256'])
    checked(R/'scripts/audit_v140_inheritance.py',audit['audit_script_sha256'])
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
    checked(R/'scripts/validate_v140_host.py',host['validation_script_sha256'])
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
    previous=R.parent/'pynq_z2_tile_v1_39'
    negative=load(previous/'reports/v139/next_iteration_analysis/receive_deadline_negative.json')
    passed(negative,'Slow-progress negative baseline')
    require(negative['revision']=='V1.39' and negative['negative_reproduced'] is True,'Missing slow-progress negative baseline')
    hashes(previous,negative['source_sha256'])
    checked(previous/'reports/v139/next_iteration_analysis/reproduce_receive_deadline.py',negative['script_sha256'])
    deadline=load(O/'deadline_summary.json');passed(deadline,'Logical-request deadline tests')
    require(deadline['tests']>=19 and len(set(deadline['test_ids']))==deadline['tests']
            and deadline['failures']==deadline['errors']==0,'Deadline coverage incomplete')
    require(unit['count']>=365+deadline['tests'],'New deadline tests missing from full regression')
    hashes(R,deadline['source_sha256'])
    review=load(O/'independent_deadline_review.json');passed(review,'Independent deadline review')
    hashes(R,review['source_sha256']);hashes(previous,review['baseline_source_sha256'])
    require(review['revision']==VERSION and not review['actionable_findings'] and review['checks']
            and all(v is True for v in review['checks'].values()),'Unresolved independent review findings')
    checked(O/'deadline_summary.json',review['specialist_test_proof_sha256'])
    require(review['specialist_tests']==deadline['tests'],'Independent review/test count mismatch')
    return host,snapshot,diagnostic,deadline,review



def board_checks(artifacts):
    program=load(R/'reports/programmed_v140.json');ready=load(O/'boot_readiness.json');passed(ready,'Board readiness')
    require(program['active_application']=='hdmi_ethernet' and type(program['boot_id']) is int,'Missing Ethernet programming proof')
    boot=program['boot_id'];stats(ready['state'],boot);hashes(W,program['sha256'])
    require(set(program['sha256'])=={'system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'} and all(artifacts[k]==v for k,v in program['sha256'].items()),'Programming proof differs from inherited artifacts')
    local=load(O/'deadline_loopback/summary.json');verify_loopback(local)
    board=load(O/'deadline_board/summary.json');verify_board_schema(board,boot,program)
    noise=noise_checks()
    return program,ready,local,board,noise


def pixel_check(value,boot,firmware):
    passed(value,'Complete image/CRC consistency')
    require(value['boot_id']==boot and value['firmware_version']==firmware
            and all(value[key] is True for key in ('complete_720p_frame','crc3','reconstructed_pixel_crc_matches','candidate_count_matches')),
            'Image identity, CRC or candidate-count check failed')
    for key in ('image_sha256','mask_sha256'):
        require(isinstance(value[key],str) and len(value[key])==64,'Missing checked PNG digest')


def verify_loopback(value):
    passed(value,'Real TCP slow-progress deadline fixture');hashes(R,value['source_sha256'])
    require(set(value['source_sha256'])=={'host/tcp_transport.py','scripts/test_deadline_loopback.py'},'Wrong loopback inputs')
    require(value['control_timeout_seconds']==.3 and value['idle_timeout_seconds']==.35 and 0<int(value['port'])<=65535
            and value['port']!=8770,'Wrong isolated shortened-budget fixture')
    require(value['exception_type']=='RequestDeadlineExceeded' and .25<=value['first_request_elapsed_seconds']<.8
            and 16<=value['first_received_bytes']<272 and value['automatic_reconnects']==0,'Slow progress did not terminate within fixture bound')
    require(value['server_observed_close'] is True and not value['server_errors'] and value['no_ack_request'] is True,'Loopback close/ACK check failed')
    intervals=value['server_send_intervals_seconds']
    require(len(intervals)>=2 and all(0<=gap<.35 for gap in intervals),'Fixture stopped making positive progress')
    require(.08<=value['second_request_elapsed_seconds']<.5 and value['second_header_crc_verified'] is True
            and value['second_boot_id']==17,'Fresh request did not obtain independent budget')
    require(value['requests']==[[0x544c5033,3,0,0],[0x544c5033,3,0,0]],'Unexpected loopback request or ACK')
    failures=value['first_failures']
    require(len(failures)==1 and failures[0]['op']==3 and failures[0]['bytes_received']==value['first_received_bytes']
            and 'deadline' in failures[0]['error'].lower(),'Missing deadline diagnostic evidence')


def verify_board_schema(board,boot,program):
    passed(board,'Physical deadline normal-link regression')
    require(board['revision']==VERSION and board['firmware_version']==FIRMWARE and board['boot_id']==boot,'Wrong physical test identity')
    require(board['sources_unchanged'] is True and board['programmed_artifacts_unchanged'] is True
            and not board['cleanup_errors'],'Changed sources/artifacts or failed cleanup')
    require(board['high_density_stress_passed'] is False,'Known dense-input stress failure must remain explicit')
    hashes(R,board['source_sha256'])
    require({'scripts/board_v140_deadline.py','scripts/board_v140_diagnostics.py','host/workstation.py','host/tcp_transport.py'}.issubset(board['source_sha256']),
            'Incomplete physical source binding')
    run=inside(O/'deadline_board',board['run_directory'])
    require(load(run/'summary.json')==board,'Physical latest/run summary mismatch')
    require(load(run/'provenance.json')=={key:board[key] for key in ('source_sha256','startup_programmed_proof')},'Physical startup provenance mismatch')
    startup=board['startup_programmed_proof']
    require(Path(startup['path']).resolve()==(R/'reports/programmed_v140.json').resolve() and startup['record']==program,'Physical programming record mismatch')
    checked(R/'reports/programmed_v140.json',startup['marker_sha256']);hashes(W,startup['artifact_sha256'])
    require(startup['artifact_sha256']==program['sha256'],'Startup artifact/marker mismatch')
    profiles={'default':dict(recipe='mvtec_hdmi_weak_v124',threshold=90,passes=4,low_gate=False),
              'low_gate':dict(recipe='synthetic_dark_v137',threshold=36,passes=2,low_gate=True)}
    require(board['profiles']==profiles,'Wrong physical recipe matrix')
    codecs={'raw':{'RAW32'},'rle':{'WORD_RLE','RAW32'},'packed':{'BGR24_MASK1','WORD_RLE','RAW32'}}
    expected={(p,m,c) for p in profiles for m in codecs for c in ('fresh','reused')}
    cases=board['cases']
    require(len(cases)==12 and {(c['profile'],c['mode'],c['connection']) for c in cases}==expected,'Incomplete physical request matrix')
    record_ids=set()
    for row in cases:
        p=profiles[row['profile']];value=row['evidence'];frame=value['frame'];check=value['check']
        require(row['source']=='station_0','Normal-link acceptance must use the documented station_0 fixture')
        pixel_check(check,boot,FIRMWARE)
        require(row['capture_budget_seconds']==8 and 0<=row['capture_elapsed_ms']<8000
                and row['capture_elapsed_ms']==frame['total_request_ms'] and row['capture_margin_ms']==8000-row['capture_elapsed_ms'],
                'Invalid physical request budget/timing')
        require(row['manual_saved_and_confirmation_completed'] is True and row['paused_after_capture'] is True,'Manual save/confirmation not complete')
        require(frame['boot_id']==boot and frame['firmware_version']==FIRMWARE and frame['width']==1280 and frame['height']==720
                and all(frame[key] is True for key in CRCS),'Physical frame identity/dimensions/CRC failed')
        require(frame['reason']=='manual' and frame['retry_count']==0 and frame['wire_codec'] in codecs[row['mode']],'Unexpected capture reason/retry/codec')
        require(frame['recipe_id']==p['recipe'] and frame['applied_threshold']==p['threshold'] and frame['weak_passes']==p['passes']
                and frame['low_gate_enabled'] is p['low_gate'],'Physical captured recipe attribution mismatch')
        cfg=frame['config_word']
        require(((cfg>>8)&255,bool(cfg&(1<<24)),4 if cfg&(1<<25) else 2,bool(cfg&(1<<26)))==
                (p['threshold'],True,p['passes'],p['low_gate']),'Physical captured config mismatch')
        require(frame['frame_id']==check['frame_id'] and frame['event_id']==check['event_id'],'PNG check/frame mismatch')
        require(value['sha256']=={'original':check['image_sha256'],'mask':check['mask_sha256']}
                and frame['image_sha256']==check['image_sha256'] and frame['mask_sha256']==check['mask_sha256'],'PNG/check/archive digest mismatch')
        for kind in ('original','mask'):checked(inside(run,value['files'][kind]),value['sha256'][kind])
        record_ids.add(frame['id'])
    require(len(record_ids)==board['new_manual_archives']==12,'Manual archive count/identity mismatch')
    actual=sorted({row['evidence']['frame']['wire_codec'] for row in cases})
    require(board['actual_wire_codecs']==actual and board['packed_codec_exercised'] is ('BGR24_MASK1' in actual),
            'Actual codec coverage misreported')
    controls=board['controls']
    require(len(controls)==6 and {(c['profile'],c['mode']) for c in controls}=={(p,m) for p in profiles for m in codecs},'Missing control request matrix')
    require(all(c['control_budget_seconds']==3 and 0<=c['http_elapsed_ms']<3000 for c in controls),'Control request observation exceeded bound')
    for name in ('before','after'):stats(board[name],boot)
    errors={key:(board['after'][key]-board['before'][key])&0xffffffff for key in ERRORS}
    require(board['error_deltas']==errors and not any(errors.values()),'Physical error deltas nonzero or inconsistent')
    require(board['after']['depth']==0 and all(not board['final_control'][key] for key in
            ('enabled','busy','manual_waiting','pending_operation','pending_confirmation')),'Board queue/control/pending ACK not drained')


def noise_checks():
    path=O/'noise_probe/status_only_physical.json';value=load(path)
    require(value['host_captures_before']==value['host_captures_after'],'Noise probe performed host image capture')
    samples=value['samples']
    require([row['source'] for row in samples]==['station_6','transport_noise','station_6'],'Wrong noise probe control sequence')
    boot=samples[0]['before']['boot_id']
    for row in samples:
        for name in ('before','after'):stats(row[name],boot)
        delta={key:(row['after'][key]-row['before'][key])&0xffffffff for key in row['delta']}
        require(delta==row['delta'],'Noise probe counter mismatch')
    require(samples[1]['delta']['captured']==0 and samples[1]['delta']['invalid']>0 and samples[1]['delta']['frames']>0,
            'Documented dense-noise failure is missing')
    require(all(row['delta']['captured']>0 and row['delta']['invalid']==0 for row in (samples[0],samples[2])),
            'Noise probe normal-source controls did not recover')
    snapshots={sha(p):p for p in (O/'deadline_board').glob('attempt*_script.py')}
    attempts=[]
    for attempt_path in sorted((O/'deadline_board').glob('run_*/summary.json')):
        old=load(attempt_path)
        if old['passed'] is not False:continue
        require(old['revision']==VERSION and old.get('error'),'Incomplete failed-attempt evidence')
        digest=old['source_sha256']['scripts/board_v140_deadline.py']
        require(digest in snapshots,'Missing historical script for failed physical attempt')
        checked(snapshots[digest],digest)
        attempts.append(dict(**reference(attempt_path),historical_script=reference(snapshots[digest]),error=old['error']))
    require(len(attempts)>=2,'The known failed stress attempts must remain in evidence')
    return dict(**reference(path),boot_id=boot,status='KNOWN_DENSE_NOISE_CAPTURE_FAILURE',
                noise_delta=samples[1]['delta'],host_image_requests=0,failed_attempts=attempts,
                provenance='Preserved inline physical status observations; no saved pre-execution probe-script hash is claimed.',
                interpretation='Valid frames stop and invalid frames increase under dense noise even without host image requests; precise PL/firmware root cause remains unresolved.')



def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    require(R.name=='pynq_z2_tile_v1_53' and not R.is_symlink() and not R.is_junction(),'Wrong project root')
    plan=load(R/'ITERATION_PLAN.json');require(plan['version']==VERSION,'Wrong iteration plan')
    baseline,audit,artifacts=inherited(plan);host,snapshot,diagnostic,deadline,review=host_checks();program,ready,local,board,noise=board_checks(artifacts)
    index=R.parent/'TileLab_进度与回退.md';old_index=index.read_text(encoding='utf-8')
    require(all(marker in old_index for marker in ('更新：','## 当前产品','## 尚在进行','## 回退和空间')),'Progress index layout changed')
    if args.check_only:
        print(json.dumps(dict(version=VERSION,passed=True,writes=False,verified_files=len(BOUND),unit_tests=host['unit_tests']['count'])));return
    limits=['Budgets apply to a single EventTCP exchange, including its retry and low-gate preflight; they do not bound an entire capture/save/ACK/status workflow.',
            'Default control/image budgets are 3/8 seconds. CPU decoding/CRC is not preempted; results completing too late are rejected.',
            'An ACK may reach the board before its reply times out; durable pending identity remains for reconciliation.',
            'Virtual-clock fault injection and any local socket fixture timings are separate from physical normal-link observations.',
            'Observed board margins are not worst-case network or OS scheduling guarantees, and no physical disconnection was injected.',
            'Dense full-frame noise fails board capture even with no host image requests. This known unresolved stress failure is not covered by normal-link acceptance.',
            'Packed is a capability request; firmware may choose a smaller legal codec. packed_codec_exercised records actual BGR24_MASK1 coverage, not merely the requested mode.',
            'PL/ARM/model artifacts remain byte-identical to sealed V1.37 via V1.39; no new detector accuracy, RTL or 50-photo result is claimed.',
            'Two repeated synthetic static profiles are not independent factory samples or a new human HDMI-output visual confirmation.',
            'Finite board queues, material-specific gates, crack generalization and PNG/SQLite power-loss boundaries remain.']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=now,
                 scope='Bounded logical TCP request budget across retry and low-gate preflight; unchanged FPGA/ARM; fault injection and normal-link physical regression',
                 host_validation=reference(O/'host_validation.json'),unit_tests=host['unit_tests'],
                 frontend_tests=sum(host[k]['tests'] for k in ('review_ui','preview_ui','inventory_ui')),
                 recipe_snapshot=dict(**reference(O/'recipe_snapshot_summary.json'),tests=snapshot['tests']),
                 diagnostic_reservation=dict(**reference(O/'diagnostic_reservation_summary.json'),tests=diagnostic['tests']),
                 logical_deadline=dict(**reference(O/'deadline_summary.json'),tests=deadline['tests'],default_control_seconds=3,default_image_seconds=8),
                 deadline_loopback=dict(**reference(O/'deadline_loopback/summary.json'),shortened_control_seconds=local['control_timeout_seconds'],
                    observed_expiry_seconds=local['first_request_elapsed_seconds'],fresh_request_succeeded=local['second_header_crc_verified']),
                 inheritance=reference(O/'inheritance_audit.json'),programming=reference(R/'reports/programmed_v140.json'),
                 boot_readiness=reference(O/'boot_readiness.json'),board_test=dict(performed=True,boot_id=program['boot_id'],firmware_version=FIRMWARE,
                    **reference(O/'deadline_board/summary.json'),cases=len(board['cases']),controls=len(board['controls']),
                    new_manual_archives=board['new_manual_archives'],
                    capture_elapsed_ms=[row['capture_elapsed_ms'] for row in board['cases']],
                    min_capture_margin_ms=min(row['capture_margin_ms'] for row in board['cases']),
                    actual_codecs=board['actual_wire_codecs'],packed_codec_exercised=board['packed_codec_exercised'],error_deltas=board['error_deltas']),
                 known_noise_failure=noise,industrial_acceptance=False,
                 independent_review=reference(O/'independent_deadline_review.json'),limits=limits)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD',hardware='Byte-identical sealed V1.37 PL/ARM via V1.39; V1.40 host logical deadlines, fault injection and physical normal-link regression passed')
    save(R/'ITERATION_PLAN.json',plan)
    (R/'README.md').write_text(f'''# TileLab V1.40

状态：{STATUS}。

**已知未通过项：高密度全屏噪声输入会使板端有效采集停止、无效帧增加，本版尚未修复。** 不取图、只读状态的实板观察中，噪声输入期间有效采集增量为 0、无效帧增加 {noise['noise_delta']['invalid']}；切回正常空场后恢复。原始记录及两次失败测试、历史脚本和日志完整保留。V1.40 的通过范围是正常输入下的 TCP 总预算和数据完整性回归，不是工业通用验收；下一版优先定位该问题。

本版为单次 TCP 逻辑请求增加总时间预算：控制请求默认 3 秒，取图请求默认 8 秒。原先持续收到少量字节会反复延长等待；现在连接、发送、分段接收、重试退避和低亮度门禁的能力查询共同使用一次预算，不因进展或重连重新计时。首帧原有 2 秒空闲容忍仍保留，但受 8 秒总预算约束。

超时会关闭连接并抛出明确错误，不将半张图保存或确认。若图像已保存、ACK 已发送而回复超时，会保留待确认身份，之后对账，避免丢掉已有证据。解码和 CRC 计算不能被强制抢占，但计算完成后已过时的结果不会作为成功帧返回。总预算针对一次网络请求，不是包括存档和多次 ACK/状态请求的整个工作流程上限。

验证：{host['unit_tests']['count']} 项主机、{summary['frontend_tests']} 项前端通过，包含 {deadline['tests']} 项总时限专项、{snapshot['tests']} 项配方快照和 {diagnostic['tests']} 项诊断互斥。受控时钟测试覆盖慢速正进展、共享重试/能力查询、剩余时间不足、完整性错误、半帧不存不确认和 ACK 回复丢失后对账。虚拟时间是故障注入数据，不是实板链路测速。另有真实本机 TCP 慢速回复测试：将预算缩短为 0.3 秒，确认持续有字节到达仍会截止、关闭连接且不自动重试，之后新请求可成功；这也不代表默认 3/8 秒预算的板端性能。

新实板在 station_0 正常素材上验证两套配方 × RAW/RLE/packed 三种传输配置 × 主动断开后首图/后续图，共 {len(board['cases'])} 次人工存档；另有 {len(board['controls'])} 次控制状态观察。每组保存原图、掩码及元数据，核对完整 720p、CRC、重建像素和候选像素计数，保存后确认完成，此正常输入窗口内错误增量为零。实际编码为 {', '.join(board['actual_wire_codecs'])}，packed 数据格式实板覆盖为 {board['packed_codec_exercised']}；不能将请求 packed 能力算作真正传输了该格式。第一次测试错误地要求 packed 请求必定返回该格式，但固件允许选择更小的 RLE；为强制覆盖而引入全屏噪声后发现上述未解决的采集问题。详见 `reports/v140/validation_summary.json` 与 `reports/v140/deadline_board/summary.json`。

正常链路的实际耗时和预算余量不保证最坏网络情况或硬实时；本版没有人工断网实验。FPGA、ARM/Vitis、参考算法和 BIT/XSA/ELF 经 V1.39 继承封存 V1.37、逐字节一致，仍由 FPGA 在线检测。本版不宣称提高裂纹精度，没有重做 50 图/RTL，也没有新增人工外接屏幕目视确认。下一版优先定位高密度输入失败，再继续改进断电恢复、有限队列背压和独立真实材质测试。

打开 `{R.name}.xpr`；Vitis 工作区 `{W.name}`。回退工程 `{baseline.as_posix()}`，备份 `{Path(plan['backup']).as_posix()}`。只保留逐版摘要，批量后统一报告。
''',encoding='utf-8')
    sources={}
    for folder in ('rtl','constraints','ip_repo','models','scripts','sim','host','diagnostics',W.name+'/ethernet_sources','data/dark_gate'):
        for path in files(R/folder):
            if path.suffix not in ('.pid','.log','.pyc','.wdb') and path.name not in ('player_status.json','player_instance.json','display_command.txt'):
                sources[path.relative_to(R).as_posix()]=sha(path)
    sources['data/real_tiles/hdmi_manifest.json']=sha(R/'data/real_tiles/hdmi_manifest.json')
    for path in W.iterdir():
        if path.is_file() and path.suffix in ('.py','.tcl','.bat'):sources[path.relative_to(R).as_posix()]=sha(path)
    proof_paths={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v140.json'}
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
    text=old_index[:i]+f'更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新有范围限制的实板验收：**V1.40**。TCP 总预算及 12 次正常输入人工帧回归通过；**高密度噪声输入采集失败尚未修复，packed 格式未获本次实板覆盖**。PL/ARM 沿用 V1.37。只保存逐版摘要，批量后统一报告。\n\n'+old_index[j:]
    text='\n'.join(line for line in text.split('\n') if not line.startswith('| V1.40 |'))
    text=text.replace('## 尚在进行',f'| V1.40 | TCP 总时限和正常输入回归；高噪声采集失败待修 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i,j=text.index('## 尚在进行'),text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.40 按限定范围封存。下一版优先定位已实板复现的高密度噪声采集失败，并重新验证 packed 实际编码；保持小步、备份、故障复现和实板验证。本版已加入单次 TCP 总预算。未登记证据的断电恢复、有限队列背压、材质泛化仍待改善。低门禁仅为材质标定，弱阈值 TL34 候选仍维持拒绝。\n\n'+text[j:]
    index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(version=VERSION,status=STATUS,boot_id=program['boot_id'],unit_tests=host['unit_tests']['count'],source_files=len(sources),proof_files=len(proofs))))


if __name__=='__main__':main()

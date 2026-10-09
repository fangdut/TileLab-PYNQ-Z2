"""Check existing V1.38 evidence, then seal a concise host-only iteration.

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

R=Path(__file__).resolve().parents[1];O=R/'reports/v138';W=R/(R.name+'.sdk')
VERSION='V1.38';FIRMWARE=0x12500;STATUS='BOARD_VALIDATED_ATOMIC_RECIPE_REQUEST_SNAPSHOT'
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
    baseline=Path(plan['baseline']);require(baseline.name=='pynq_z2_tile_v1_37','Wrong baseline')
    checked(baseline/'DELIVERY_MANIFEST.json',plan['baseline_manifest_sha256'])
    old=load(baseline/'DELIVERY_MANIFEST.json')
    require(old['version']=='V1.37' and old['validation']['passed'] is True,'Baseline is not sealed/passed V1.37')
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
    require(all(old['artifacts_sha256'][k]==v for k,v in artifacts.items()),'Inherited binaries differ from sealed V1.37')
    audit=load(O/'inheritance_audit.json');passed(audit,'Inheritance audit')
    require(audit['revision']==VERSION,'Wrong inheritance audit revision')
    hashes(R,audit['source_sha256']);hashes(baseline,audit['baseline_source_sha256'])
    hashes(W,audit['artifacts_sha256']);hashes(R/'reports',audit['reports_sha256'])
    checked(R/'scripts/audit_v138_inheritance.py',audit['audit_script_sha256'])
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
    require(host['version']==VERSION and unit['count']>343 and not unit['failures'] and not unit['errors'],'Incomplete host suite')
    hashes(R,host['source_sha256'])
    checked(R/'scripts/validate_v138_host.py',host['validation_script_sha256'])
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
    review=None
    if (O/'independent_profile_review.json').exists():
        review=load(O/'independent_profile_review.json');passed(review,'Independent source review');hashes(R,review['source_sha256'])
        require(review['revision']==VERSION and not review['actionable_findings'] and all(v is True for v in review['checks'].values()),'Unresolved independent review findings')
        checked(O/'recipe_snapshot_summary.json',review['specialist_test_proof_sha256'])
        checked(R.parent/'pynq_z2_tile_v1_37/host/workstation.py',review['baseline_workstation_sha256'])
    return host,snapshot,review


def board_checks(artifacts):
    # Exact physical-proof schema is checked below once the bounded board test
    # is complete; incomplete evidence must never seal a release.
    program=load(R/'reports/programmed_v138.json');ready=load(O/'boot_readiness.json');passed(ready,'Board readiness')
    require(program['active_application']=='hdmi_ethernet' and type(program['boot_id']) is int,'Missing Ethernet programming proof')
    boot=program['boot_id'];stats(ready['state'],boot);hashes(W,program['sha256'])
    require(set(program['sha256'])=={'system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf'} and all(artifacts[k]==v for k,v in program['sha256'].items()),'Programming proof differs from inherited artifacts')
    board=load(O/'profile_switch_board/summary.json');passed(board,'Physical recipe-switch regression')
    verify_board_schema(board,boot,program)
    return program,ready,board


def verify_board_schema(board,boot,program):
    allowed={'A':dict(recipe_id='mvtec_hdmi_weak_v124',threshold=90,enhance=True,passes=4,low_gate=False),
             'B':dict(recipe_id='synthetic_dark_v137',threshold=36,enhance=True,passes=2,low_gate=True)}
    require(board['revision']==VERSION and board['firmware_version']==FIRMWARE and board['boot_id']==boot,'Wrong physical test identity')
    require(board['profiles']==allowed and board['sources_unchanged'] is True and board['programmed_artifacts_unchanged'] is True
            and not board['cleanup_errors'],'Changed board profiles/sources or failed cleanup')
    hashes(R,board['source_sha256'])
    run=inside(O/'profile_switch_board',board['run_directory'])
    require(load(run/'summary.json')==board,'Physical latest/run summary mismatch')
    startup=board['startup_programmed_proof'];provenance=load(run/'provenance.json')
    require(provenance=={key:board[key] for key in ('source_sha256','startup_programmed_proof')},'Physical startup provenance mismatch')
    require(Path(startup['path']).resolve()==(R/'reports/programmed_v138.json').resolve() and startup['record']==program,'Physical programming record mismatch')
    checked(R/'reports/programmed_v138.json',startup['marker_sha256']);hashes(W,startup['artifact_sha256'])
    require(startup['artifact_sha256']==program['sha256'],'Startup artifact/marker mismatch')
    for name in ('before','after'):stats(board[name],boot)
    errors={key:(board['after'][key]-board['before'][key])&0xffffffff for key in ERRORS}
    require(board['error_deltas']==errors and not any(errors.values()),'Physical error deltas nonzero or inconsistent')
    require(board['after']['depth']==0 and not board['final_state']['pending_operation'] and not board['final_state']['pending_confirmation'],'Board queue/pending ACK not drained')
    require(len(board['switches'])>=12 and {v['requested_profile'] for v in board['switches']}==set(allowed),'Insufficient active recipe switching')
    flags=('crc3','captured_recipe_attribution','reconstructed_pixel_crc_matches','boxes_match','areas_match','overflow_match','candidate_area_match')
    def check(row):
        passed(row,'Physical frame check')
        require(row['boot_id']==boot and row['profile'] in allowed and row['mask_mismatch']==0 and all(row[k] is True for k in flags),'CRC/model/region/candidate-count check failed')
    def frame(value,full=False):
        require(value['boot_id']==boot and value['firmware_version']==FIRMWARE and all(value.get(k) is True for k in CRCS),'Physical frame identity/CRC failed')
        require(value['width']==1280 and value['height']==720,'Wrong frame dimensions')
        word=value['config_word'];actual=((word>>8)&255,bool(word&(1<<24)),4 if word&(1<<25) else 2,bool(word&(1<<26)))
        names=[name for name,p in allowed.items() if actual==(p['threshold'],p['enhance'],p['passes'],p['low_gate'])]
        require(len(names)==1,'Captured mixed or unrequested profile');name=names[0];p=allowed[name]
        require(value['recipe_id']==p['recipe_id'] and value['applied_threshold']==p['threshold'] and value['weak_passes']==p['passes']
                and value['low_gate_enabled']==p['low_gate'] and value['applied_product_gate_sum']==(160 if p['low_gate'] else 320),'Captured attribution mismatch')
        if full:require(value['selection']=='FPGA_PRODUCT_BEST_FRAME' and value['selection_full_tile'] is True and value['product_id']>0 and value['event_reason'] in (1,2),'Not complete automatic product evidence')
        return name
    live=board['live_checks'];require(live and len(live)<=192,'Missing/unbounded live checks')
    for row in live:check(row)
    counts={name:sum(row['profile']==name for row in live) for name in allowed}
    require(board['observed_profile_counts']==counts and all(n>0 for n in counts.values()),'Both actually captured profiles are required')
    def picture(value):
        for kind in ('original','mask'):checked(inside(run,value['files'][kind]),value['sha256'][kind])
    retained=board['live_evidence'];require(2<=len(retained)<=4 and {e['profile'] for e in retained}==set(allowed),'Missing retained live evidence')
    for value in retained:
        require(frame(value['frame'])==value['profile'],'Retained live frame profile mismatch');picture(value)
        matches=[c for c in live if c['frame_id']==value['frame']['frame_id'] and c['event_id']==value['frame']['event_id']]
        require(any(c['image_sha256']==value['sha256']['original'] and c['mask_sha256']==value['sha256']['mask'] for c in matches),'Retained live pixels not bound to exact check')
    events,checks,pictures=board['events'],board['event_checks'],board['event_images']
    require(0<len(events)<=32 and len(events)==len(checks)==len(pictures)==board['saved_events']==board['defective_products_delta'],'Product evidence count mismatch')
    require(board['defective_products_delta']==((board['after']['defective_products']-board['before']['defective_products'])&0xffffffff),'Defective product delta mismatch')
    identities={(e['boot_id'],e['product_id']) for e in events};by_id={e['id']:e for e in events}
    require(len(identities)==len(by_id)==len(events),'Duplicate product/record identity')
    require({c['record_id'] for c in checks}=={p['record_id'] for p in pictures}==set(by_id),'Event/check/picture identity mismatch')
    checked_by_id={c['record_id']:c for c in checks}
    for event in events:
        name=frame(event,full=True);c=checked_by_id[event['id']];check(c)
        require(c['profile']==name and c['frame_id']==event['frame_id'] and c['event_id']==event['event_id'] and c['full_tile'] is True and 0<=c['source_barcode']<720,'Product frame/check geometry mismatch')
    for value in pictures:
        event=by_id[value['record_id']];c=checked_by_id[value['record_id']]
        require(value['frame']==event,'Saved proof frame differs from archived metadata');picture(value)
        require(value['sha256']['original']==event['image_sha256']==c['image_sha256'] and value['sha256']['mask']==event['mask_sha256']==c['mask_sha256'],'Event PNG/check/archive hashes differ')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    require(R.name=='pynq_z2_tile_v1_53' and not R.is_symlink() and not R.is_junction(),'Wrong project root')
    plan=load(R/'ITERATION_PLAN.json');require(plan['version']==VERSION,'Wrong iteration plan')
    baseline,audit,artifacts=inherited(plan);host,snapshot,review=host_checks();program,ready,board=board_checks(artifacts)
    index=R.parent/'TileLab_进度与回退.md';old_index=index.read_text(encoding='utf-8')
    require(all(marker in old_index for marker in ('更新：','## 当前产品','## 尚在进行','## 回退和空间')),'Progress index layout changed')
    if args.check_only:
        print(json.dumps(dict(version=VERSION,passed=True,writes=False,verified_files=len(BOUND),unit_tests=host['unit_tests']['count'])));return
    limits=['Only each configure/capture request is atomic; they may legitimately use different complete recipes if the UI changes between requests.',
            'Captured FPGA configuration remains the authority for archived recipe attribution, including delayed queue events.',
            'PL/ARM/model artifacts are inherited unchanged from sealed V1.37; no new RTL simulation or 50-photo run is claimed.',
            'The new board run uses repeated synthetic moving tiles, not independent factory data or a new human HDMI-output visual confirmation.',
            'Finite board queues, material-specific brightness gates, crack generalization and PNG/SQLite power-loss boundaries remain.']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary=dict(version=VERSION,status=STATUS,passed=True,completed_at=now,
                 scope='Atomic complete host recipe requests; unchanged V1.37 FPGA/ARM; bounded physical regression',
                 host_validation=reference(O/'host_validation.json'),unit_tests=host['unit_tests'],
                 frontend_tests=sum(host[k]['tests'] for k in ('review_ui','preview_ui','inventory_ui')),
                 recipe_snapshot=dict(**reference(O/'recipe_snapshot_summary.json'),tests=snapshot['tests']),
                 inheritance=reference(O/'inheritance_audit.json'),programming=reference(R/'reports/programmed_v138.json'),
                 boot_readiness=reference(O/'boot_readiness.json'),board_test=dict(performed=True,boot_id=program['boot_id'],firmware_version=FIRMWARE,
                    **reference(O/'profile_switch_board/summary.json'),saved_events=board['saved_events'],host_captures=board['host_captures'],
                    switches=len(board['switches']),observed_profile_counts=board['observed_profile_counts'],error_deltas=board['error_deltas']),
                 independent_review=reference(O/'independent_profile_review.json') if review else None,limits=limits)
    save(O/'validation_summary.json',summary)
    plan.update(phase='VALIDATED_BOARD',hardware='Byte-identical sealed V1.37 PL/ARM; V1.38 host snapshot and physical switching regression passed')
    save(R/'ITERATION_PLAN.json',plan)
    (R/'README.md').write_text(f'''# TileLab V1.38

状态：{STATUS}。

本版修复电脑端采集期间切换配方的参数组合竞争。旧行为可能把旧高阈值 90 与新配方的两级传播、低亮度门禁混合；现在每次配置或取图在控制锁内保存完整不可变参数，在锁外执行网络请求。保持旧桥接口、暂停/确认流程和按实际 FPGA 配置归因。一次配置和后续取图允许分别采用完整旧、新配方，不把两次请求误称为一个事务。

验证：{host['unit_tests']['count']} 项主机、{summary['frontend_tests']} 项前端及 {snapshot['tests']} 项专门同步测试通过；后者含旧竞态复现、异常恢复、嵌套/线程隔离和暂停/先存后确认检查。新实板运行验证活动切换、完整参数集合、三项 CRC、逐像素掩码/区域与产品证据，错误计数增量为零。详情见 `reports/v138/validation_summary.json`。

FPGA、ARM/Vitis、参考算法及 BIT/XSA/ELF 与封存 V1.37 完全一致，仍由 FPGA 在线检测；本版没有重做 V1.37 的 50 图或 RTL 测试，也不宣称提高裂纹精度。合成反复移动素材不等于真实工厂独立样本，未新增人工外接屏幕目视确认。有限队列、弱裂纹泛化及 PNG/数据库断电边界仍需后续改进。

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
    proof_paths={R/'README.md',R/'ITERATION_PLAN.json',R/'reports/programmed_v138.json'}
    proof_paths.update(R/'reports'/name for name in audit['reports_sha256'])
    proof_paths.update(path for path in files(O) if path.suffix in ('.json','.log','.png','.txt','.rpt'))
    proofs={path.relative_to(R).as_posix():sha(path) for path in sorted(proof_paths)}
    for path in (R/'ITERATION_PLAN.json',O/'validation_summary.json'):BOUND[str(path.resolve())]=sha(path)
    manifest=dict(version=VERSION,status=STATUS,created_at=now,baseline=str(baseline),baseline_manifest_sha256=plan['baseline_manifest_sha256'],
                  backup=plan['backup'],backup_sha256=plan['backup_sha256'],hardware_revision='Byte-identical sealed V1.37 PL/ARM',
                  artifacts_sha256=artifacts,inherited_artifacts_sha256=artifacts,source_sha256=sources,proof_sha256=proofs,
                  executed_input_output_sha256=BOUND,validation=summary,report='README.md',limits=limits,
                  hash_scope='Executed proof inputs are checked against saved hashes; the finalizer is sealed as current source, not claimed as a prior test execution.')
    save(R/'DELIVERY_MANIFEST.json',manifest)
    i,j=old_index.index('更新：'),old_index.index('## 当前产品')
    text=old_index[:i]+f'更新：{datetime.datetime.now().astimezone().isoformat()}\n\n最新实板验收：**V1.38**。电脑端配方请求完整快照与活动切换实板验收通过；PL/ARM 沿用 V1.37。只保存逐版摘要，批量后统一报告。\n\n'+old_index[j:]
    text='\n'.join(line for line in text.split('\n') if not line.startswith('| V1.38 |'))
    text=text.replace('## 尚在进行',f'| V1.38 | 配置/取图完整参数快照、作用域隔离与实板活动切换 | {STATUS} | [摘要]({R.as_posix()}/README.md) |\n\n## 尚在进行',1)
    i,j=text.index('## 尚在进行'),text.index('## 回退和空间')
    text=text[:i]+'## 尚在进行\n\nV1.38 已封存。后续继续按小步、备份、故障复现和实板验证迭代；优先关注未登记证据的断电恢复、材质泛化和传输负载。现有低门禁仅为材质标定，弱阈值 TL34 候选仍维持拒绝。\n\n'+text[j:]
    index.write_text(text,encoding='utf-8')
    print(json.dumps(dict(version=VERSION,status=STATUS,boot_id=program['boot_id'],unit_tests=host['unit_tests']['count'],source_files=len(sources),proof_files=len(proofs))))


if __name__=='__main__':main()

from pathlib import Path
import json,hashlib,datetime,urllib.request,os,time
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_29';W=R/(R.name+'.sdk');O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(R/'ITERATION_PLAN.json');old=read(B/'DELIVERY_MANIFEST.json');program=read(R/'reports/programmed_v132.json');s=read(O/'packed_validation_summary.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
assert all(sha(B/p)==h for p,h in old['source_sha256'].items())
assert s['passed'] and s['unit_tests']==265 and s['baseline_manifest_sha256']==sha(B/'DELIVERY_MANIFEST.json')
for key in ('firmware','review_session','review','process_exit','station','identity','readiness'):assert s[key]['passed'],key
assert s['review_session']['tests']==19 and s['review']['verified_http_images']==20 and s['review']['verified_http_records']==10 and s['review']['original_evidence_and_review_unchanged'] and s['process_exit']['case_count']==3
assert s['station']['saved']==10 and s['identity']['physical_products']==10
assert s['firmware']['source_changes_only_version_and_comments']
assert sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')==s['firmware']['elf_sha256']
for name,h in s['firmware']['source_sha256'].items():assert sha(W/'ethernet_sources'/name)==sha(W/'hdmi_ethernet/src'/name)==h
for name,h in program['sha256'].items():assert sha(W/name)==h
for name,h in plan['inherited_hardware_sha256'].items():assert sha(W/name)==h
# Drawing progress is an observation across reports, not a fact inferable from
# one fresh report after the browser has stopped polling in a background tab.
observations=[];deadline=time.monotonic()+3
while True:
    with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
    observations.append(state['stimulus_status'])
    if state['stimulus_status']['motion']['state']=='PROGRESSING':break
    if time.monotonic()>deadline:raise AssertionError('No drawing progress observed before finalization deadline')
    time.sleep(.2)
(O/'final_motion_observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2),encoding='utf-8')
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.30' and benchmark['passed']
assert state['revision']=='V1.30' and state['enabled'] and state['board_connected'] and not state['error']
assert state['board_stats']['version']==0x11e00 and state['board_stats']['boot_id']==program['boot_id']
assert state['capture_health']['ready'] and not state['capture_health']['stale']
assert state['frame']['recovery_generation']==0 and state['frame']['config_word']&(1<<25) and state['applied_threshold']==90
ss=state['stimulus_status'];assert ss['ready'] and ss['identity_confirmed'] and ss['observed']==ss['requested']=='real_video'
assert ss['request_id']==ss['observed_request_id'] and ss['player_session']==ss['active_player_session']
assert ss['motion']['state']=='PROGRESSING' and ss['motion']['progressing']
player=read(R/'host/player_status.json');assert not player['diagnostic_hold_active'] and player['drawn_frames']>0
assert state['capture_recovery']['state']=='RUNNING' and state['capture_recovery']['attempts']==0
assert all(state['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
assert all(state['board_stats'][k]==0 for k in ('gaps','invalid','dropped','ack_errors','descriptor_crc_errors'))
assert state['storage']['mode']=='preview' and state['storage']['max_archive_mib']==1024 and state['wire_mode']=='rle' and not state['preview_frozen']
assert not state['pending_operation'] and not state['confirmation_journal']['error'] and not state['recovery']['active']
assert state['storage']['image_bytes']==sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
(O/'final_station_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ('rtl','constraints','scripts','sim','models','host','diagnostics',W.name+'/ethernet_sources'):
    for p in sorted((R/folder).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and 'runtime' not in p.parts and p.suffix in ('.py','.v','.vhd','.mem','.hex','.xdc','.sv','.tcl','.html','.c','.h','.dll','.ps1','.cs','.js','.json','.S','.ld','.source','.cmake') and not p.name.startswith('player_'):sources[p.relative_to(R).as_posix()]=sha(p)
for p in W.iterdir():
    if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
size=0
for base,dirs,files in os.walk(R,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
    for name in files:
        p=Path(base)/name
        if not p.is_symlink():size+=p.stat().st_size
report='docs/Tile_V1.30_复核并发与持久化同步报告.md'
proofs=[report,'README.md']+[f'reports/v132/{n}' for n in ('packed_validation_summary.json','final_station_state.json','firmware_audit.json','review_session_native.json','review_audit.json','review_baseline/summary.json','review_ui/browser_observations.json','review_process_exit/summary.json','station_continuous.json','station_identity_audit.json','review_conflict_ui.png','review_reloaded_ui.png','evidence_revision_ui.png','verification_page.png')]
manifest=dict(version='V1.30',status='BOARD_VALIDATED_REVIEW_REVISION_AND_CRASH_ATOMICITY',hardware_revision='V1.24 unchanged four-stage detector and CRC hardware',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(old['source_sha256']),programming=program,source_sha256=sources,unit_tests_passed=265,validation=s,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in proofs},limits=old['limits']+['V1.30 uses persistent review revisions and a SQLite transaction to reject stale submissions; no authenticated reviewer identity or full change history. Abrupt process exits were tested, not physical disk power loss. Old clients must not share the new live database.'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(version=manifest['version'],status=manifest['status'],project_gib=round(size/1024**3,3),images_mib=state['storage']['image_bytes']/1024**2,baseline_verified=len(old['source_sha256']))))

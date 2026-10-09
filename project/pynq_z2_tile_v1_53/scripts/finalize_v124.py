from pathlib import Path
import json,hashlib,datetime,urllib.request,os,sqlite3
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_23';W=R/(R.name+'.sdk');O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');program=read(R/'reports/programmed_v132.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
assert all(sha(B/p)==v for p,v in old['source_sha256'].items())
s=read(O/'quad_weak_validation_summary.json');assert s['passed'] and s['unit_tests']==188 and s['baseline_manifest_sha256']==sha(B/'DELIVERY_MANIFEST.json')
for k in ('firmware','hardware','simulation','mode_boundary','invalid_modes','normal_board','input_equality','transport_full','faults','restarts','ui_restart','admission_board','stimulus_board','station_full','identity','background','recovery_native','health_native','mode_native'):assert s[k]['passed'],k
assert s['normal_board']['images']==230 and s['normal_board']['alarms']==0
assert s['input_equality']['byte_identical']==50 and len(s['invalid_modes']['cases'])==13
for v in s['weak'].values():assert v['passed'] and v['samples']==50 and v['pixel_exact']==50
fw=s['firmware'];assert fw['irq_fp_saved'] and fw['integer_memcpy_preserved'] and fw['irq_stack_bytes']==4096 and fw['new_pl_export'] and fw['queue_ack_unchanged']
assert sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')==fw['elf_sha256']
for name,value in program['sha256'].items():assert sha(W/name)==value
for name,value in s['hardware']['artifacts_sha256'].items():assert sha(W/name)==value
for name,value in s['hardware']['reports_sha256'].items():assert sha(R/'reports'/name)==value
for name,value in s['simulation']['rtl_and_oracle_sha256'].items():assert sha(R/name)==value
for p in (W/'ethernet_sources').iterdir():
 if p.is_file():assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name)
for key in ('firmware','recovery_native','health_native','mode_native'):
 assert s[key]['main_sha256']==sha(W/'ethernet_sources/main.c')
assert sha(W/'build_ethernet.py')==fw['build_script_sha256']
assert s['hardware']['cdc_unsafe_endpoints']==5 and s['hardware']['bus_skew_constraints_met']==8
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.24' and benchmark['passed']
assert state['revision']=='V1.24' and state['enabled'] and state['board_connected'] and not state['error']
assert state['board_stats']['version']==0x11800 and state['capture_health']['ready'] and not state['capture_health']['stale']
assert state['frame']['recovery_generation']==0 and state['frame']['config_word']&(1<<25) and ((state['frame']['config_word']>>8)&255)==90
assert state['stimulus_status']['ready'] and state['stimulus_status']['observed']==state['stimulus_status']['requested']=='real_video'
assert state['capture_recovery']['state']=='RUNNING' and state['capture_recovery']['attempts']==0
assert all(state['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
assert state['board_stats']['descriptor_crc_errors']==0 and state['board_stats']['descriptor_verified_frames']==state['board_stats']['captured']
assert state['storage']['mode']=='preview' and state['storage']['max_archive_mib']==1024
assert not state['pending_operation'] and not state['confirmation_journal']['error'] and not state['recovery']['active']
assert state['frame']['boot_id']==program['boot_id'] and state['compression_enabled'] and not state['preview_frozen']
assert state['storage']['image_bytes']==sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
db=sqlite3.connect(R/'review_records/inspection.sqlite3')
try:assert db.execute('SELECT COUNT(*) FROM pending_confirmation').fetchone()[0]==0
finally:db.close()
(O/'final_station_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ('rtl','constraints','scripts','sim','models','host','diagnostics',W.name+'/ethernet_sources'):
 for p in sorted((R/folder).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and 'runtime' not in p.parts and p.suffix in ('.py','.v','.vhd','.mem','.hex','.xdc','.sv','.tcl','.html','.c','.h','.dll','.ps1','.cs','.json','.S','.ld','.source','.cmake') and not p.name.startswith('player_'):sources[p.relative_to(R).as_posix()]=sha(p)
for p in W.iterdir():
 if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
size=0
for base,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
 for name in files:
  p=Path(base)/name
  if not p.is_symlink():size+=p.stat().st_size
report='docs/Tile_V1.24_四级弱裂纹与实板报告.md'
proofs=[report,'docs/V1.24_弱裂纹四级生长原理.md','README.md']+[f'reports/v132/{name}' for name in ['workstation_final.png','verification_page.png','evidence_crc.png','evidence_crc_details.png','pending_before.png','pending_after.png','command_lock_ui.png','stale_player_ui.png','quad_weak_validation_summary.json','hardware_audit.json','firmware_audit.json','simulation_audit.json','real_input_equality.json','cross_material/results.json','normal_board/summary.json','mode_boundary/summary.json','invalid_modes_board.json','final_station_state.json']]
limits=['Historical development photos are not blind factory accuracy; 800 roof-normal cross-material alarms increased from 547 to 555','No real camera exposure, motion blur, physical cable removal or power-loss test in this release','No strong seed still means weak cracks can be missed; added four-pass propagation is bounded','Five original CDC unsafe endpoints and I/O timing/methodology warnings remain','HDMI boxes use the previous completed frame; PC saved evidence binds boxes to its own frame','Finite 12-event queue and unsaved DDR cannot survive long receiver pauses or power removal','Higher-speed centering has a prior failed 40px case against a 32px target; current normal-speed acceptance does not erase it','Physical DMA halt/recovery campaign inherited from V1.21 with new actual-C regression, not re-injected in V1.24','PNG and SQLite are not a cross-file transaction; one receiver; CRC is not authentication','Full long-period event/product/frame epoch, nested IRQ/FIQ/abort and maximum production stack work remains','Pause cancels before capture admission, after admission current evidence may finish','Player READY is local telemetry, not physical HDMI verification; no unique command transaction ID','Four-pass configuration needs the Ethernet controller; JTAG debug does not send this mode request']
manifest=dict(version='V1.24',status='BOARD_VALIDATED_FOUR_PASS_WEAK_SUPPORT_WITH_MATERIAL_LIMITS',hardware_revision='V1.24 optional four-stage bounded weak support, with V1.15 descriptor/pixel CRC architecture',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(old['source_sha256']),programming=program,source_sha256=sources,unit_tests_passed=188,validation=s,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in proofs},limits=limits)
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(version='V1.24',status=manifest['status'],project_gib=round(size/1024**3,3),baseline_verified=len(old['source_sha256']))))

from pathlib import Path
import json,hashlib,datetime,urllib.request,os,sqlite3
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_20';W=R/(R.name+'.sdk');O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');program=read(R/'reports/programmed_v132.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
preserved={p:sha(B/p)==v for p,v in old['source_sha256'].items()};assert all(preserved.values())
assert {k:sha(W/k) for k in plan['inherited_hardware_sha256']}==plan['inherited_hardware_sha256']
for name,h in program['sha256'].items():assert sha(W/name)==h
for p in (W/'ethernet_sources').iterdir():
 if p.is_file():assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),p.name
summary=read(O/'generation_validation_summary.json');assert summary['passed']
assert summary['player_lock']['passed'] and sha(R/'host/hdmi_display.ps1')==summary['player_lock']['player_sha256']
assert summary['recovery_board']['cleanup_resumed']['resumed_successfully']
assert read(O/'pause_race_audit.json')['undesired_new_capture'] is True # Explicitly retained next-iteration limit.
fw=summary['firmware'];assert fw['passed'] and fw['irq_fp_saved'] and fw['irq_stack_bytes']==4096 and fw['integer_memcpy_preserved'] and fw['queue_ack_unchanged']
assert sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')==fw['elf_sha256']
assert sha(W/'build_ethernet.py')==fw['build_script_sha256']
assert sha(W/'ethernet_sources/capture_health.h')==fw['health_header_sha256']==summary['health_native']['health_header_sha256']
assert sha(W/'ethernet_sources/dma_recovery.h')==fw['recovery_header_sha256']==summary['recovery_native']['recovery_header_sha256']
assert sha(W/'ethernet_sources/main.c')==fw['main_sha256']==summary['health_native']['main_sha256']==summary['recovery_native']['main_sha256']
assert summary['recovery_native']['scenarios']==20
assert sha(W/'ethernet_sources/event_identity.h')==fw['identity_header_sha256']==summary['recovery_native']['identity_header_sha256']
cases=summary['recovery_board']['cases'];assert len(cases)==4
for number,result in enumerate(cases,1):
 assert result['independent_process_reload_passed'] and result['retained_generation']==number-1
 assert result['archived_generations']==([number-1,number,number] if number<=3 else [3])
 assert result['passed'] and result['retained_bytes_equal'] and len(result['rereads'])==2
 assert all(all(v['crc'].values()) for v in result['rereads'])
 assert result['after']['boot_id']==result['before']['boot_id']
 rec=result['after']['capture_recovery']
 if number<=3:
  assert rec['state']=='RUNNING' and rec['successes']==rec['attempts']==number and rec['failures']==0
  assert rec['waiting_new_product'] and result['next_product']['product']!=result['identity']['product']
 else:
  assert rec['state']=='FAILED' and rec['attempts']==rec['successes']==3 and rec['reason_code']==7
  wait=result['terminal_wait'];assert wait['last']['captures']==wait['first']['captures'] and wait['last']['board_connected']
 assert result['final_stats']['dropped']==result['before']['dropped'] and result['final_stats']['ack_errors']==result['before']['ack_errors']
assert summary['recovery_board']['clean_restart']['capture_recovery']['attempts']==0
native=read(O/'descriptor_native.json');assert sha(W/'ethernet_sources/main.c')==native['main_sha256'] and sha(W/'ethernet_sources/descriptor_crc.h')==native['crc_sha256']
assert read(O/'native_sg/result.json')['result']=='PASS' and read(O/'firmware_crc_test.json')['passed']
unit=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 152 tests' in unit and unit.rstrip().endswith('OK')
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.21' and benchmark['passed']
assert state['revision']=='V1.21' and state['enabled'] and state['board_connected'] and not state['error']
assert state['board_stats']['version']==0x11500 and state['capture_health']['ready'] and not state['capture_health']['stale']
assert state['frame']['recovery_generation']==0
assert state['capture_recovery']['state']=='RUNNING' and state['capture_recovery']['attempts']==0
assert all(state['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
assert state['board_stats']['descriptor_crc_errors']==0 and state['board_stats']['descriptor_verified_frames']==state['board_stats']['captured']
assert not state['preview_frozen'] and state['stimulus']=='real_video' and state['storage']['mode']=='preview'
assert state['storage']['auto_saved']==24 and state['records_total']==25 and not state['confirmation_journal']['error']
assert state['frame']['boot_id']==program['boot_id'] and state['compression_enabled'] and not state['recovery']['active']
assert state['storage']['image_bytes']==sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
db=sqlite3.connect(R/'review_records/inspection.sqlite3')
try:
 assert db.execute('SELECT COUNT(*) FROM pending_confirmation').fetchone()[0]==0
 assert db.execute('SELECT COUNT(*) FROM confirmation_history').fetchone()[0]==25
finally:db.close()
(O/'final_station_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ['rtl','constraints','scripts','sim','host','diagnostics',W.name+'/ethernet_sources']:
 for p in sorted((R/folder).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and 'runtime' not in p.parts and p.suffix in ['.py','.v','.vhd','.mem','.hex','.xdc','.sv','.tcl','.html','.c','.h','.dll','.ps1','.cs','.json','.S','.ld','.source','.cmake'] and not p.name.startswith('player_'):sources[p.relative_to(R).as_posix()]=sha(p)
for p in W.iterdir():
 if p.is_file() and p.suffix in ('.py','.tcl','.bat'):sources[p.relative_to(R).as_posix()]=sha(p)
size=0
for base,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
 for name in files:
  p=Path(base)/name
  if not p.is_symlink():size+=p.stat().st_size
report='docs/Tile_V1.21_采集恢复代次与证据同步报告.md'
proofs=[report,'docs/V1.21_采集代次原理.md','README.md']+[f'reports/v132/{name}' for name in ['workstation_final.png','verification_page.png','evidence_crc.png','evidence_crc_details.png','pending_before.png','pending_after.png','generation_recovered_ui.png','generation_failed_ui.png','ui_restart_after.json','restart/summary.json','firmware_audit.json','dma_recovery_native.json','health_native.json','dma_recovery_board/summary.json','generation_validation_summary.json']]
manifest=dict(version='V1.21',status='BOARD_VALIDATED_FRAME_BOUND_GENERATION_WITH_KNOWN_LIMITS',hardware_revision='Unchanged V1.15 shared descriptor port/pixel and descriptor CRC',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(preserved),programming=program,source_sha256=sources,unit_tests_passed=152,validation=summary,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in proofs},limits=['Actual run-stop DMA halt tested; reset-stuck, all DMA errors and timeout boundaries covered natively, not all injected physically','Three attempts per boot; no automatic recovery for pure video stall or initial HDMI wait; not physical HDMI unplug/power-loss validation','Recovery generation identifies acquisition epochs within a boot; does not count every missed physical product or replace full long-period identities','Same V1.15 hardware; no new algorithm-accuracy or implementation-timing claim','Finite event queue and unsaved DDR cannot survive long receiver pauses or board power removal','Weak-crack generalization, previous-frame HDMI overlay, existing CDC and high-speed centering limits remain','Full event/product/frame/archive epoch, nested IRQ/FIQ/abort and maximum production stack verification remain','PNG and SQLite are not a cross-file transaction; single receiver design','CRC is accidental-corruption detection, not security authentication'])
manifest['limits'].extend(['A pause during a blocked preflight status request may still issue one capture; reproduced with a local controlled bridge and scheduled for the next release','V1.21 event reason packing requires a matching workstation; new receiver reads old data as unknown generation, old receivers do not decode new upper bits'])
for name in ('player_lock.json','pause_race_audit.json'):
 manifest['proof_sha256']['reports/v132/'+name]=sha(O/name)
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(version='V1.21',status=manifest['status'],project_gib=round(size/1024**3,3),baseline_verified=len(preserved))))

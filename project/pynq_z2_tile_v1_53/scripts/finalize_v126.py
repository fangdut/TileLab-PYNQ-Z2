from pathlib import Path
import json,hashlib,datetime,urllib.request,os,sqlite3
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_25';W=R/(R.name+'.sdk');O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');program=read(R/'reports/programmed_v132.json');s=read(O/'packed_validation_summary.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
assert all(sha(B/p)==v for p,v in old['source_sha256'].items())
assert s['passed'] and s['unit_tests']==198 and s['baseline_manifest_sha256']==sha(B/'DELIVERY_MANIFEST.json')
for k in ('firmware','gem_ownership','native','stream_native','invalid_requests','legacy_client','transport','faults','packed_faults','noncanonical','restarts','station','identity','background','health_native','recovery_native','ui'):assert s[k]['passed'],k
assert s['stream_native']['borrowed_payload_writes']==0 and s['gem_ownership']['network_sha256']==sha(W/'ethernet_sources/network.c')
bsp=read(O/'app_bsp_unchanged.json');assert bsp['passed']
for name,h in bsp['archive_sha256'].items():assert sha(W/'hdmi_platform/export/hdmi_platform/sw/standalone_a9/lib'/name)==h
assert sha(Path(s['gem_ownership']['vendor_driver']))==s['gem_ownership']['vendor_driver_sha256']
assert s['transport']['byte_exact_triplets']==50 and s['packed_faults']['tests']==4 and s['faults']['tests']==9
assert s['native']['header_sha256']==sha(W/'ethernet_sources/packed_pixels.h')
assert len(s['invalid_requests']['cases'])==20 and all(c['raw_fallback_preserved_all_bits'] and c['host_crc_rejected'] and c['next_event_packed'] for c in s['noncanonical']['cases'])
fw=s['firmware'];assert fw['irq_fp_saved'] and fw['integer_memcpy_preserved'] and fw['irq_stack_bytes']==4096 and fw['queue_ack_unchanged']
assert sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')==fw['elf_sha256']
for name,value in program['sha256'].items():assert sha(W/name)==value
for name,value in plan['inherited_hardware_sha256'].items():assert sha(W/name)==value
for folder in ('rtl','constraints'):
 for p in (R/folder).rglob('*'):
  if p.is_file():assert sha(p)==sha(B/p.relative_to(R))
for p in (W/'ethernet_sources').iterdir():
 if p.is_file():assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name)
assert s['health_native']['main_sha256']==s['recovery_native']['main_sha256']==fw['main_sha256']==sha(W/'ethernet_sources/main.c')
assert sha(W/'build_ethernet.py')==fw['build_script_sha256']
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.26' and benchmark['passed']
assert state['revision']=='V1.26' and state['enabled'] and state['board_connected'] and not state['error']
assert state['board_stats']['version']==0x11a00 and state['capture_health']['ready'] and not state['capture_health']['stale']
assert state['frame']['recovery_generation']==0 and state['frame']['config_word']&(1<<25) and state['applied_threshold']==90
assert state['stimulus_status']['ready'] and state['stimulus_status']['observed']==state['stimulus_status']['requested']=='real_video'
assert state['capture_recovery']['state']=='RUNNING' and state['capture_recovery']['attempts']==0
assert all(state['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
assert state['board_stats']['descriptor_crc_errors']==0 and state['board_stats']['descriptor_verified_frames']==state['board_stats']['captured']
assert state['storage']['mode']=='preview' and state['storage']['max_archive_mib']==1024 and state['wire_mode']=='rle'
assert not state['pending_operation'] and not state['confirmation_journal']['error'] and not state['recovery']['active']
assert state['frame']['boot_id']==program['boot_id'] and state['compression_enabled'] and not state['preview_frozen']
assert state['storage']['image_bytes']==sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
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
report='docs/Tile_V1.26_分块传输与同步实板报告.md'
proofs=[report,'docs/V1.26_流式传输学习说明.md','README.md']+[f'reports/v132/{name}' for name in ('packed_validation_summary.json','final_station_state.json','firmware_audit.json','native_stream/result.json','transport_comparison.json','noncanonical/summary.json','wire_mode_ui.json','wire_packed_ui.png','wire_latency_ui.png','workstation_final.png','evidence_crc.png','evidence_crc_details.png','verification_page.png')]
manifest=dict(version='V1.26',status='BOARD_VALIDATED_BOUNDED_STREAMING_PACK25',hardware_revision='V1.24 unchanged four-stage detector and CRC hardware',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(old['source_sha256']),programming=program,source_sha256=sources,unit_tests_passed=198,validation=s,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in proofs},limits=[v for v in old['limits'] if not v.startswith('PACK25 reduces payload')]+['V1.26 overlaps bounded PACK25 encoding/transmission; measured request latency is workload-dependent; legacy adaptive default retained'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(version='V1.26',status=manifest['status'],project_gib=round(size/1024**3,3),baseline_verified=len(old['source_sha256']))))

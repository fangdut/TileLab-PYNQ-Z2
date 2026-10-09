from pathlib import Path
import json,hashlib,datetime,urllib.request,os,sqlite3
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_15';W=R/(R.name+'.sdk');O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');program=read(R/'reports/programmed_v132.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
preserved={p:sha(B/p)==v for p,v in old['source_sha256'].items()};assert all(preserved.values())
assert {k:sha(W/k) for k in plan['inherited_hardware_sha256']}==plan['inherited_hardware_sha256']
for name,h in program['sha256'].items():assert sha(W/name)==h
for p in (W/'ethernet_sources').iterdir():
 if p.is_file():assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),p.name
summary=read(O/'irq_context_validation_summary.json');assert summary['passed'] and summary['irq_context']['passed']
fw=summary['firmware'];assert fw['passed'] and fw['irq_fp_saved'] and fw['production_irq_stack_bytes']==4096
assert sha(W/'hdmi_ethernet/build/hdmi_ethernet.elf')==fw['elf_sha256']
assert sha(W/'build_ethernet.py')==fw['build_script_sha256']
assert sha(W/'hdmi_ethernet/src/lscript.ld')==fw['linker_sha256']
for case in (summary['irq_context']['baseline'],summary['irq_context']['candidate']):
 for name,h in case['build']['source_sha256'].items():assert sha(R/'diagnostics'/name)==h
 assert sha(O/'irq_context'/case['variant']/'diagnostic.elf')==case['build']['elf_sha256']
native=read(O/'descriptor_native.json');assert sha(W/'ethernet_sources/main.c')==native['main_sha256'] and sha(W/'ethernet_sources/descriptor_crc.h')==native['crc_sha256']
assert read(O/'native_sg/result.json')['result']=='PASS' and read(O/'firmware_crc_test.json')['passed']
unit=(O/'host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 120 tests' in unit and unit.rstrip().endswith('OK')
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.16' and benchmark['passed']
assert state['revision']=='V1.16' and state['enabled'] and state['board_connected'] and not state['error']
assert state['board_stats']['version']==0x11000
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
report='docs/Tile_V1.16_中断保护与实板报告.md'
proofs=[report,'docs/V1.16_中断现场保护原理.md','README.md']+[f'reports/v132/{name}' for name in ['workstation_final.png','verification_page.png','evidence_crc.png','evidence_crc_details.png','pending_before.png','pending_after.png','ui_restart_after.json','restart/summary.json','firmware_audit.json','irq_context/summary.json','irq_context_validation_summary.json']]
manifest=dict(version='V1.16',status='BOARD_VALIDATED_IRQ_FP_CONTEXT_WITH_KNOWN_LIMITS',hardware_revision='Unchanged V1.15 shared descriptor port/pixel and descriptor CRC',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(preserved),programming=program,source_sha256=sources,unit_tests_passed=120,validation=summary,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in proofs},limits=['Actual SGI negative/positive controls do not exhaust Ethernet ISR paths, nested IRQ, FIQ, aborts or maximum production stack depth','Same V1.15 hardware; no new algorithm-accuracy or implementation-timing claim','Finite event queue and unsaved DDR cannot survive long receiver pauses or board power removal','Full event counter wrap ACK zero and legacy JTAG image slot bound remain known limits','Weak-crack generalization, previous-frame HDMI overlay, existing CDC and high-speed centering limits remain','PNG and SQLite are not a cross-file transaction; single receiver design','CRC is accidental-corruption detection, not security authentication'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(version='V1.16',status=manifest['status'],project_gib=round(size/1024**3,3),baseline_verified=len(preserved))))

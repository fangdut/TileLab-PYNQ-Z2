from pathlib import Path
import json,hashlib,datetime,urllib.request,os,sqlite3
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_13';W=R/(R.name+'.sdk')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');program=read(R/'reports/programmed_v132.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
preserved={p:sha(B/p)==v for p,v in old['source_sha256'].items()};assert all(preserved.values())
assert sha(W/'system.bit')!=plan['inherited_hardware_sha256']['system.bit']
assert sha(W/'system.xsa')!=plan['inherited_hardware_sha256']['system.xsa']
for name,h in program['sha256'].items():assert sha(W/name)==h
for p in (W/'ethernet_sources').glob('*'):
 if p.is_file():assert sha(p)==sha(W/'hdmi_ethernet/src'/p.name),p.name
summary=read(R/'reports/v132/descriptor_validation_summary.json');assert summary['passed'] and summary['hardware']['passed']
native=read(R/'reports/v132/descriptor_native.json')
assert sha(W/'ethernet_sources/main.c')==native['main_sha256']
assert sha(W/'ethernet_sources/descriptor_crc.h')==native['crc_sha256']
assert read(R/'reports/v132/native_sg/result.json')['result']=='PASS'
unit=(R/'reports/v132/host_tests_final.log').read_text(encoding='utf-8-sig');assert 'Ran 120 tests' in unit and unit.rstrip().endswith('OK')
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.14' and benchmark['passed']
assert state['revision']=='V1.14' and state['enabled'] and state['board_connected'] and not state['error']
assert state['board_stats']['version']==0x10e00
assert all(state['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
assert state['board_stats']['descriptor_crc_errors']==0
assert state['board_stats']['descriptor_verified_frames']==state['board_stats']['captured']
assert not state['preview_frozen'] and state['stimulus']=='real_video' and state['storage']['mode']=='preview'
assert state['storage']['auto_saved']==24 and state['records_total']==25
assert not state['confirmation_journal']['error']
assert state['frame']['boot_id']==program['boot_id'] and state['compression_enabled'] and not state['recovery']['active']
assert state['storage']['image_bytes']==sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
db=sqlite3.connect(R/'review_records/inspection.sqlite3')
try:
 assert db.execute('SELECT COUNT(*) FROM pending_confirmation').fetchone()[0]==0
 assert db.execute('SELECT COUNT(*) FROM confirmation_history').fetchone()[0]==25
finally:db.close()
(R/'reports/v132/final_station_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ['rtl','constraints','scripts','sim','host',W.name+'/ethernet_sources']:
 for p in sorted((R/folder).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and 'runtime' not in p.parts and p.suffix in ['.py','.v','.vhd','.mem','.hex','.xdc','.sv','.tcl','.html','.c','.h','.dll','.ps1','.cs','.json'] and not p.name.startswith('player_'):sources[p.relative_to(R).as_posix()]=sha(p)
size=0
for base,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
 for name in files:
  p=Path(base)/name
  if not p.is_symlink():size+=p.stat().st_size
report='docs/Tile_V1.14_描述校验与实板报告.md'
proofs=[report,'reports/v132/workstation_final.png','reports/v132/verification_page.png','reports/v132/evidence_crc.png','reports/v132/evidence_crc_details.png','reports/v132/pending_before.png','reports/v132/pending_after.png','reports/v132/ui_restart_after.json','reports/v132/restart/summary.json','reports/v132/descriptor_fault_summary.json','reports/v132/hardware_crc_check.json']
manifest=dict(version='V1.14',status='BOARD_VALIDATED_PL_DESCRIPTOR_CRC_WITH_KNOWN_LIMITS',hardware_revision='V1.14 full-frame pixel and PL descriptor CRC',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(preserved),programming=program,source_sha256=sources,unit_tests_passed=120,validation=summary,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in proofs},limits=['CRC detects accidental corruption, not authentication, algorithm accuracy or every internal program error','Actual DDR bit flip/JTAG reload tested; physical power removal and extended endurance not tested','12-event queue can overflow and unsaved DDR evidence cannot survive board reset','Full event counter wrap ACK zero and legacy JTAG image slot bound remain known limits','Weak-crack/generalization, HDMI previous-frame overlay, existing CDC and high-speed centering limits remain','PNG and SQLite are not one cross-file transaction; single receiver design','Full interrupt floating-point context audit remains open'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(version='V1.14',status=manifest['status'],project_gib=round(size/1024**3,3),baseline_verified=len(preserved))))

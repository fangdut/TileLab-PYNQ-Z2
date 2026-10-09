from pathlib import Path
import json,hashlib,datetime,urllib.request,os
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_9'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');program=read(R/'reports/programmed_v132.json')
assert sha(Path(plan['backup']))==plan['backup_sha256']
preserved={p:sha(B/p)==v for p,v in old['source_sha256'].items()};assert all(preserved.values())
for name in ('system.bit','system.xsa','system.ltx'):assert sha(R/'pynq_z2_tile_v1_53.sdk'/name)==plan['inherited_hardware_sha256'][name]
for p in (R/'rtl').glob('*.v'):assert sha(p)==sha(B/'rtl'/p.name)
for name,v in program['sha256'].items():assert sha(R/'pynq_z2_tile_v1_53.sdk'/name)==v
for p in (R/'pynq_z2_tile_v1_53.sdk/ethernet_sources').glob('*'):
 if p.is_file():assert sha(p)==sha(R/'pynq_z2_tile_v1_53.sdk/hdmi_ethernet/src'/p.name),p.name
summary=read(R/'reports/v132/background_summary.json')
for p in ['configure_without_capture','normal_preview_24s','frozen_background_60s','frozen_ui_check']:assert read(R/f'reports/v132/{p}.json')['passed']
unit=(R/'reports/v132/host_tests.log').read_text(encoding='utf-8-sig');assert 'Ran 84 tests' in unit and unit.rstrip().endswith('OK')
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8770/api/benchmark',timeout=5) as f:benchmark=json.load(f)
assert benchmark['version']=='V1.10' and benchmark['passed']
assert state['revision']=='V1.10' and state['enabled'] and state['board_connected'] and not state['error']
assert not state['preview_frozen'] and state['stimulus']=='real_video' and state['storage']['mode']=='preview' and state['storage']['auto_saved']==0
assert state['frame']['boot_id']==program['boot_id'] and state['compression_enabled'] and not state['recovery']['active']
assert state['storage']['image_bytes']==sum(p.stat().st_size for p in (R/'review_records').glob('*.png'))
(R/'reports/v132/final_station_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ['rtl','constraints','scripts','host','pynq_z2_tile_v1_53.sdk/ethernet_sources']:
 for p in sorted((R/folder).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and 'runtime' not in p.parts and p.suffix in ['.py','.v','.xdc','.sv','.tcl','.html','.c','.h','.dll','.ps1','.cs','.json'] and not p.name.startswith('player_'):sources[p.relative_to(R).as_posix()]=sha(p)
size=0
for base,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
 for name in files:
  p=Path(base)/name
  if not p.is_symlink():size+=p.stat().st_size
report='docs/Tile_V1.10_后台事件接收报告.md'
manifest=dict(version='V1.10',status='BOARD_VALIDATED_BACKGROUND_EVENTS_WITH_KNOWN_LIMITS',hardware_revision='V1.6 unchanged',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(preserved),programming=program,source_sha256=sources,unit_tests_passed=84,background=summary,storage=state['storage'],size_bytes=size,report=report,proof_sha256={p:sha(R/p) for p in [report,'reports/v132/workstation_final.png','reports/v132/verification_page.png','reports/v132/frozen_preview.png']},limits=['12-event queue can overflow during long stop/outage','Full RGB integrity checksum from PL remains future work','Byte-rate savings depend on sparse defect events and frozen preview','V1.6 detection/generalization/CDC and high-speed 40 px centering limits inherited'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(version='V1.10',status=manifest['status'],project_gib=round(size/1024**3,3),baseline_verified=len(preserved))))

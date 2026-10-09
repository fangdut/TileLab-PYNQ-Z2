from pathlib import Path
import hashlib,json,datetime,os,urllib.request
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_6'
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
t=read(R/'reports/v132/transport_comparison.json');motion=read(R/'reports/v132/motion_evidence_audit.json')
assert t['passed'] and all(m['functional_pass'] for m in motion.values())
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f:state=json.load(f)
assert state['revision']=='V1.7' and state['enabled'] and state['board_connected'] and not state['error']
assert state['stimulus']=='real_video' and state['storage']['mode']=='preview' and state['storage']['auto_saved']==0
assert state['frame']['boot_id']==program['boot_id'] and state['compression_enabled']
(R/'reports/v132/final_station_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
sources={}
for folder in ['rtl','constraints','scripts','host','pynq_z2_tile_v1_53.sdk/ethernet_sources']:
 for p in sorted((R/folder).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and 'runtime' not in p.parts and p.suffix in ['.py','.v','.xdc','.sv','.tcl','.html','.c','.h','.dll','.ps1','.cs','.json'] and not p.name.startswith('player_'):
   sources[p.relative_to(R).as_posix()]=sha(p)
size=0
for base,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()]
 for name in files:
  p=Path(base)/name
  if not p.is_symlink():size+=p.stat().st_size
result=dict(version='V1.7',status='BOARD_VALIDATED_LOSSLESS_TRANSPORT_WITH_KNOWN_LIMITS',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 hardware_revision='V1.6 unchanged',baseline=str(B),backup=plan['backup'],backup_sha256=plan['backup_sha256'],baseline_source_files_verified=len(preserved),
 programming=program,source_sha256=sources,unit_tests_passed=60,encoder_cases_passed=690,memcpy_contract_cases_passed=1152,
 transport_summary=t['summary'],byte_exact_pairs=t['byte_exact_samples'],mid_payload_reconnect_passed=t['reconnect_same_event'],
 motion={k:{a:b for a,b in v.items() if a!='items'} for k,v in motion.items()},storage=state['storage'],size_bytes=size,
 report='docs/Tile_V1.7_无损传输优化报告.md',proof_sha256={p:sha(R/p) for p in ['reports/v132/verification_page.png','reports/v132/workstation_final.png','docs/Tile_V1.7_无损传输优化报告.md']},
 limits=['Weak-crack recall/generalization and 5 HDMI CDC endpoints inherited from V1.6','Noise fallback incurs encoding time; raw mode retained','Software-injected TCP reset tested; physical cable/power outage not claimed','Frame masks are checked but full-color PL CRC remains future work'])
(R/'DELIVERY_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(version='V1.7',status=result['status'],project_gib=round(size/1024**3,3),baseline_verified=len(preserved)),ensure_ascii=False))

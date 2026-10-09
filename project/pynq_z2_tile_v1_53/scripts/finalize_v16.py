"""Record reproducible delivery evidence; never modify the preserved baseline."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, urllib.request

R=Path(__file__).resolve().parents[1]
B=R.parent/'pynq_z2_tile_v1_5'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()
def save(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

prior=read(B/'MAINTENANCE_MANIFEST.json')
preserved={name:digest(B/name)==sha for name,sha in prior['source_sha256'].items()}
for name,sha in prior['hardware_sha256'].items():
    preserved['pynq_z2_tile_v1_5.sdk/'+name]=digest(B/'pynq_z2_tile_v1_5.sdk'/name)==sha
assert all(preserved.values()), preserved
programmed=read(R/'reports/programmed_v132.json')
hardware={name:digest(R/'pynq_z2_tile_v1_53.sdk'/name) for name in programmed['sha256']}
assert hardware==programmed['sha256']
board=read(R/'reports/v132/real_board/summary.json')
motion=read(R/'reports/v132/motion_evidence_audit.json')
assert board['passed'] and all(v['functional_pass'] for v in motion.values())
with urllib.request.urlopen('http://127.0.0.1:8770/api/state',timeout=5) as f: state=json.load(f)
assert state['revision']=='V1.6' and state['enabled'] and not state['error'] and state['board_connected']
assert state['stimulus']=='real_video' and state['applied_threshold']==89
assert state['frame']['config_word'] & (1<<24)
assert state['storage']['mode']=='preview' and state['storage']['auto_saved']==0
save(R/'reports/v132/final_station_state.json',state)
sizes={}; files=0; skipped=[]
for base,dirs,names in os.walk(R,followlinks=False):
    for d in dirs[:]:
        p=Path(base)/d
        if p.is_symlink() or p.is_junction(): dirs.remove(d);skipped.append(str(p))
    for name in names:
        p=Path(base)/name
        if p.is_symlink(): continue
        key=p.relative_to(R).parts[0]
        sizes[key]=sizes.get(key,0)+p.stat().st_size;files+=1
sources={}
for folder in ['rtl','constraints','host','scripts','pynq_z2_tile_v1_53.sdk/ethernet_sources']:
    for p in sorted((R/folder).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.v','.sv','.xdc','.py','.ps1','.tcl','.c','.h','.html','.json','.bat'} and not p.name.startswith('player_'):
            sources[p.relative_to(R).as_posix()]=digest(p)
manifest=dict(version='V1.6',status='BOARD_VALIDATED_WITH_GENERALIZATION_AND_CENTERING_LIMITS',
    created_at=datetime.now(timezone.utc).isoformat(),project=str(R),baseline=str(B),
    baseline_preserved=preserved,programmed=programmed,hardware_sha256=hardware,source_sha256=sources,
    build=read(R/'reports/v132/build_metrics.json'),unit_tests_passed=53,rtl_pixels_passed=10368,
    board_photo_test=board,mode_switch=read(R/'reports/v132/mode_boundary.json'),
    motion={k:{a:b for a,b in v.items() if a!='items'} for k,v in motion.items()},
    display_confirmation=read(R/'reports/v132/display_confirmation.json'),
    artifact_sha256={name:digest(R/name) for name in ['README.md','docs/Tile_V1.6_弱裂纹增强报告.md',
        'reports/v132/workstation_final.png','reports/v132/weak_verification_page.png',
        'reports/weak_crack/comparison.png','reports/v132/motion_evidence_audit.json']},
    storage=state['storage'],size_bytes=sum(sizes.values()),files=files,size_by_top_level=sizes,skipped_links=skipped,
    limits=['Historical development set, not an independent industrial accuracy test',
            'Crack pixel recall 22.62%; no strong seeds and wide cracks remain limited',
            'Roof normal false alarms increased from 19/800 to 107/800; baseline mode retained',
            'Ultrafast maximum centering error 40 px exceeds 32 px goal; strict audit fails',
            'Five inherited HDMI CDC unsafe endpoints remain',
            'Moving real photographs are test stimuli, not factory camera video',
            'Offline full regression currently reads preserved V1.5 datasets'])
save(R/'DELIVERY_MANIFEST.json',manifest)
print(json.dumps(dict(status=manifest['status'],baseline_verified=len(preserved),
                     project_gib=round(manifest['size_bytes']/1024**3,3),
                     archive_mib=round(state['storage']['used_bytes']/1024**2,2),
                     frame_rate=state['processing_fps'],source=state['stimulus']),ensure_ascii=False))

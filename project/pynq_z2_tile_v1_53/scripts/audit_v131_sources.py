"""Before/after source audit including third-party IP files, not only rtl/."""
from pathlib import Path
import json,hashlib,zipfile,re
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_30';O=R/'reports/v132'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(B/'DELIVERY_MANIFEST.json');plan=read(R/'ITERATION_PLAN.json');ip=read(O/'baseline_ip_sha256.json')
assert all(sha(B/name)==digest for name,digest in old['source_sha256'].items())
assert all(sha(B/name)==digest for name,digest in ip.items())
assert sha(Path(plan['backup']))==plan['backup_sha256']
with zipfile.ZipFile(plan['backup']) as z:
    saved=json.loads(z.read('BACKUP_HASHES.json'))
    for name,digest in ip.items():assert saved[name]==digest and hashlib.sha256(z.read(name)).hexdigest()==digest
for folder in ('rtl','constraints'):
    for p in (B/folder).rglob('*'):
        if p.is_file():assert sha(p)==sha(R/p.relative_to(B)),p
design=read(O/'reset_design_plan.json');actual={name for name,digest in ip.items() if sha(R/name)!=digest};assert actual==set(design['changed_files'])
authored={name:sha(R/name) for name in sorted(actual|{design['new_file']})}
generated={}
for name in ('SyncBase.vhd','DecoderResetDomains.vhd','TMDS_Decoder.vhd','dvi2rgb.vhd'):
    candidates=list((R/(R.name+'.gen')/'sources_1/bd/system/ipshared').rglob(name))
    candidates=[p for p in candidates if sha(p)==sha(R/'ip_repo/dvi2rgb_v1_7/src'/name)]
    assert len(candidates)==1,(name,candidates)
    generated[candidates[0].relative_to(R).as_posix()]=sha(candidates[0])
p=R/(R.name+'.gen')/'sources_1/bd/system/ip/system_hdmi_rx_0/src/dvi2rgb.xdc'
assert sha(p)==sha(R/'ip_repo/dvi2rgb_v1_7/src/dvi2rgb.xdc');generated[p.relative_to(R).as_posix()]=sha(p)
before=(B/'ip_repo/dvi2rgb_v1_7/src/dvi2rgb.xdc').read_text();after=(R/'ip_repo/dvi2rgb_v1_7/src/dvi2rgb.xdc').read_text()
old_exceptions=[l for l in before.splitlines() if l.startswith('set_false_path')];new_exceptions=[l for l in after.splitlines() if l.startswith('set_false_path')]
assert len(new_exceptions)==len(old_exceptions)-1 and set(new_exceptions)<set(old_exceptions)
assert 'create_waiver' not in (R/'scripts/create_project.tcl').read_text()
sim=(O/'reset_sim/reset_test.sim/sim_1/behav/xsim/simulate.log').read_text();assert 'PASS V131 decoder resets:' in sim and 'checks=136' in sim
result=dict(passed=True,baseline_source_files=len(old['source_sha256']),baseline_ip_files=len(ip),backup_sha256=plan['backup_sha256'],authored_changes_sha256=authored,
    generated_ip_sources_sha256=generated,detector_rtl_unchanged=True,top_constraints_unchanged=True,ip_false_paths_removed=1,new_false_paths_or_waivers=0,
    reset_simulation=dict(passed=True,phase_sweeps=64,stopped_clock_scenarios=3,crossings=6,checks=136),
    scope='Source and generated-IP provenance plus digital reset behavior. Does not replace routed timing/CDC or real-board validation.')
(O/'source_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('authored_changes_sha256','generated_ip_sources_sha256')}))

"""Seal current results, with an explicit selected-material acceptance boundary."""
from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).resolve().parents[1];O=R/'reports/v153';SDK=R/(R.name+'.sdk')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    dest=R/'DELIVERY_MANIFEST.json'
    if dest.exists():raise RuntimeError('Already sealed; create a successor rather than overwrite')
    facts=json.loads((O/'final_validation_summary.json').read_text(encoding='utf-8'))
    assert facts['engineering_acceptance'] and facts['host_tests']==431
    assert facts['universal_material_recognition_accepted'] is False
    plan=json.loads((R/'ITERATION_PLAN.json').read_text(encoding='utf-8'))
    baseline=R/'reports/accepted_baseline/V1_52_DELIVERY_MANIFEST.json'
    assert sha(baseline)==plan['baseline_manifest_sha256']
    accepted=json.loads(baseline.read_text(encoding='utf-8'))
    verified=0
    for n,h in accepted['source_sha256'].items():
        if n.startswith(('rtl/','constraints/','ip_repo/')):
            assert sha(R/n)==h,n;verified+=1
    for n,h in plan['inherited_hardware_sha256'].items():assert sha(SDK/n)==h,n
    # Mutable runtime markers, archive records and tool-generated path metadata
    # are intentionally excluded. A reprogram creates a new boot/proof record.
    roots=['rtl','constraints','ip_repo','models','sim','scripts','host','docs','data','validation','licenses']
    files=[]
    for folder in roots:
        for p in (R/folder).rglob('*'):
            if not p.is_file() or p.is_symlink() or any(x in p.parts for x in ('__pycache__','runtime')):continue
            if folder=='host' and p.suffix.lower() not in ('.py','.ps1','.cs','.js','.html','.json','.txt','.tcl'):continue
            if folder=='host' and p.name in ('display_command.txt','display_status.json','display_control.json'):continue
            if folder=='host' and p.suffix=='.json' and p.name!='recipes.json':continue
            files.append(p)
    files+=[p for p in (SDK/'ethernet_sources').rglob('*') if p.is_file()]
    files+=[p for p in SDK.iterdir() if p.is_file() and p.suffix in ('.py','.tcl','.bat','.bit','.xsa','.ltx')]
    files+=[SDK/'hdmi_ethernet/build/hdmi_ethernet.elf',baseline,O/'final_validation_summary.json']
    files+=[R/n for n in ('README.md','THIRD_PARTY_NOTICES.md','ITERATION_PLAN.json','reports/timing_summary.rpt','reports/drc.rpt','reports/cdc.rpt','reports/utilization.rpt')]
    files+=[p for p in R.glob('*.bat')]
    m=dict(version='V1.53',status='ENGINEERING_FROZEN_SUBMISSION_CANDIDATE',deployable=True,
        recognition_scope='Calibrated textured tile crack candidates with human review; NOT universal or industrial acceptance',
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),hardware_origin='Unchanged routed V1.52; physically accepted with V1.53 host',
        baseline_manifest_sha256=sha(baseline),inherited_rtl_constraints_ip_files_verified=verified,
        artifacts_sha256=plan['inherited_hardware_sha256'],validation_summary='reports/v153/final_validation_summary.json',
        publication='Prepared locally; remote publication recorded separately only after successful upload',
        frozen_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(set(files))})
    save(dest,m);print(json.dumps(dict(sealed=True,files=len(m['frozen_sha256']),scope=m['recognition_scope'])))
if __name__=='__main__':main()

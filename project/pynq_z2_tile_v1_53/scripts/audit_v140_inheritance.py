"""Verify the host-only release retains the sealed PL/ARM design and artifacts."""
from pathlib import Path
import datetime,hashlib,json,zipfile
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v140'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    plan=load(R/'ITERATION_PLAN.json');B=Path(plan['baseline']);BW=B/(B.name+'.sdk')
    assert plan['version']=='V1.40' and B.name=='pynq_z2_tile_v1_39'
    assert sha(B/'DELIVERY_MANIFEST.json')==plan['baseline_manifest_sha256']
    assert sha(Path(plan['backup']))==plan['backup_sha256']
    old=load(B/'DELIVERY_MANIFEST.json')
    for group in ('source_sha256','proof_sha256'):
        for name,digest in old[group].items():assert sha(B/name)==digest,name
    current={};baseline={}
    for folder in ('rtl','constraints','ip_repo','models','ethernet_sources'):
        a=(W if folder=='ethernet_sources' else R)/folder
        b=(BW if folder=='ethernet_sources' else B)/folder
        aa={p.relative_to(a):p for p in a.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        bb={p.relative_to(b):p for p in b.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        assert aa.keys()==bb.keys(),folder
        for name,p in aa.items():
            digest=sha(p);assert digest==sha(bb[name]),str(p)
            current[p.relative_to(R).as_posix()]=digest;baseline[bb[name].relative_to(B).as_posix()]=digest
    artifacts={n:sha(W/n) for n in plan['inherited_hardware_sha256']}
    assert artifacts==plan['inherited_hardware_sha256']==old['artifacts_sha256']
    reports={name:sha(R/'reports'/name) for name in ('timing_summary.rpt','utilization.rpt','drc.rpt','cdc.rpt','cdc_details.rpt','methodology.rpt','bus_skew.rpt')}
    assert all(digest==sha(B/'reports'/name) for name,digest in reports.items())
    with zipfile.ZipFile(W/'system.xsa') as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')];assert len(bits)==1
        assert hashlib.sha256(z.read(bits[0])).hexdigest()==artifacts['system.bit']
        ps7_sha=hashlib.sha256(z.read('ps7_init.tcl')).hexdigest()
        assert ps7_sha==sha(W/'ps7_init.tcl')
    result=dict(passed=True,revision='V1.40',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Read-only byte comparison to sealed V1.39 (original V1.37 PL/ARM); no new synthesis, firmware build or board result is claimed.',
        source_sha256=current,baseline_source_sha256=baseline,unchanged_source_files=len(current),
        artifacts_sha256=artifacts,reports_sha256=reports,ps7_init_sha256=ps7_sha,
        baseline_manifest_sha256=plan['baseline_manifest_sha256'],backup_sha256=plan['backup_sha256'],
        audit_script_sha256=sha(Path(__file__)))
    (O/'inheritance_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,unchanged_source_files=len(current),artifacts_unchanged=True)))
if __name__=='__main__':main()

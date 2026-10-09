"""Host-only release validation. No hardware access or capture claims."""
from pathlib import Path
import datetime, hashlib, json, os, sqlite3, subprocess, sys, unittest
R=Path(__file__).resolve().parents[1]; B=R.parent/'pynq_z2_tile_v1_32'; O=R/'reports/v133'
sys.path.insert(0,str(R/'host'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    old=load(B/'DELIVERY_MANIFEST.json'); plan=load(R/'ITERATION_PLAN.json')
    for group in ('source_sha256','proof_sha256'):
        for rel,h in old[group].items():assert sha(B/rel)==h,('baseline modified',rel)
    assert sha(Path(plan['backup']))==plan['backup_sha256']
    same={}
    for folder in ('rtl','constraints','ip_repo'):
        for p in (B/folder).rglob('*'):
            if p.is_file():
                rel=p.relative_to(B);assert sha(R/rel)==sha(p),rel;same[rel.as_posix()]=sha(p)
    bw=B/(B.name+'.sdk'); w=R/(R.name+'.sdk')
    for p in (bw/'ethernet_sources').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            rel=p.relative_to(bw);assert sha(w/rel)==sha(p),rel;same[(Path(w.name)/rel).as_posix()]=sha(p)
    for rel,h in plan['inherited_hardware_sha256'].items():assert sha(w/rel)==h,rel
    assert sha(w/'ps7_init.tcl')==sha(bw/'hdmi_ethernet/_ide/psinit/ps7_init.tcl')
    assert (R/(R.name+'.xpr')).is_file()
    assert (R/(R.name+'.srcs')/'sources_1/bd/system/system.bd').is_file()
    project_log=(O/'prepare_project.log').read_text(encoding='utf-8',errors='replace')
    assert 'Exiting Vivado' in project_log and '\nERROR:' not in project_log
    suite=unittest.defaultTestLoader.discover(str(R/'host'),pattern='test_*.py')
    with (O/'host_tests.log').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    tests=dict(passed=result.wasSuccessful(),count=result.testsRun,failures=[str(t) for t,e in result.failures],errors=[str(t) for t,e in result.errors],skipped=[str(t) for t,e in result.skipped])
    (O/'host_tests.json').write_text(json.dumps(tests,indent=2),encoding='utf-8')
    assert tests['passed'],tests
    node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    p=subprocess.run([str(node),str(R/'scripts/test_review_session.js')],capture_output=True,text=True,encoding='utf-8',timeout=30)
    (O/'review_session.log').write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0
    js=load(O/'review_session_native.json');assert js['passed']
    process=load(O/'save_process_exit/summary.json');assert process['passed']
    baseline=load(O/'baseline_save_race.json');assert baseline['reproduced']
    source=dict(passed=True,baseline_source_files_verified=len(old['source_sha256']),baseline_proof_files_verified=len(old['proof_sha256']),unchanged_pl_firmware_files=len(same),unchanged_sources_sha256=same,inherited_artifacts_sha256=plan['inherited_hardware_sha256'])
    (O/'source_audit.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
    summary=dict(version='V1.33',passed=True,status='HOST_VALIDATED_ARCHIVE_WRITER_SERIALIZATION',scope='Host-only; exact V1.32 PL/firmware inherited; no new physical board validation',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),unit_tests=tests,front_end=js,process_exit=process,baseline_failure=baseline,source_audit=source,sqlite_version=sqlite3.sqlite_version,python_version=sys.version,board_test=dict(performed=False,reason='No physical USB/JTAG device enumerated; TCP 169.254.200.10:9133 timed out'),limits=['PNG files and SQLite are not a single power-loss transaction. Uncommitted PNGs may remain after termination.','Cross-process serialization applies only to writers following Records.save; external tools must not overwrite archive files.','Hardware and firmware remain the independently validated V1.32 revision, not a newly tested bitstream.'])
    (O/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,tests=tests['count'],front_end_tests=js['tests'],sqlite=sqlite3.sqlite_version,unchanged_source_files=len(same))))

if __name__=='__main__':main()

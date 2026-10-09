"""Validate preview scheduling without claiming physical-board throughput."""
from pathlib import Path
import hashlib,json,sqlite3,subprocess,sys,unittest,datetime
R=Path(__file__).resolve().parents[1];B=R.parent/'pynq_z2_tile_v1_33';O=R/'reports/v134'
sys.path.insert(0,str(R/'host'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    old=load(B/'DELIVERY_MANIFEST.json');plan=load(R/'ITERATION_PLAN.json');w=R/(R.name+'.sdk');bw=B/(B.name+'.sdk')
    for group in ('source_sha256','proof_sha256'):
        for rel,h in old[group].items():assert sha(B/rel)==h,('baseline changed',rel)
    assert sha(Path(plan['backup']))==plan['backup_sha256']
    same={}
    for folder in ('rtl','constraints','ip_repo'):
        for p in (B/folder).rglob('*'):
            if p.is_file():
                rel=p.relative_to(B);assert sha(R/rel)==sha(p);same[rel.as_posix()]=sha(p)
    for p in (bw/'ethernet_sources').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            rel=p.relative_to(bw);assert sha(w/rel)==sha(p);same[(Path(w.name)/rel).as_posix()]=sha(p)
    for rel,h in plan['inherited_hardware_sha256'].items():assert sha(w/rel)==h
    assert sha(R/'reports/timing_summary.rpt')==sha(B/'reports/timing_summary.rpt')
    assert (R/(R.name+'.xpr')).is_file() and (R/(R.name+'.srcs')/'sources_1/bd/system/system.bd').is_file()
    log=(O/'prepare_project.log').read_text(encoding='utf-8',errors='replace');assert 'Exiting Vivado' in log and '\nERROR:' not in log
    with (O/'host_tests.log').open('w',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.discover(str(R/'host'),pattern='test_*.py'))
    tests=dict(passed=result.wasSuccessful(),count=result.testsRun,failures=[str(t) for t,e in result.failures],errors=[str(t) for t,e in result.errors])
    (O/'host_tests.json').write_text(json.dumps(tests,indent=2));assert tests['passed'],tests
    node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    for name in ('test_review_session.js','test_preview_ui.js'):
        p=subprocess.run([str(node),str(R/'scripts'/name)],capture_output=True,text=True,encoding='utf-8',timeout=30)
        (O/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,(name,p.stderr)
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(R/'scripts/test_preview_tcp_load.py')],capture_output=True,text=True,encoding='utf-8',timeout=90)
    (O/'preview_tcp_load.log').write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,p.stderr
    tcp=load(O/'preview_tcp_load/summary.json');assert tcp['passed']
    source=dict(passed=True,baseline_source_files_verified=len(old['source_sha256']),baseline_proof_files_verified=len(old['proof_sha256']),unchanged_pl_firmware_files=len(same),unchanged_sources_sha256=same,inherited_artifacts_sha256=plan['inherited_hardware_sha256'])
    (O/'source_audit.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
    summary=dict(version='V1.34',passed=True,status='HOST_VALIDATED_EVENT_PRIORITY_PREVIEW_BUDGET',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Host-only scheduling; real loopback TCP; physical board regression pending',unit_tests=tests,review_ui=load(O/'review_session_native.json'),preview_ui=load(O/'preview_ui_native.json'),tcp_load=tcp,source_audit=source,board_test=dict(performed=False,reason='USB/JTAG not enumerated and last direct TCP board probe timed out'),limits=['Loopback reductions are host scheduling measurements, not FPGA Ethernet throughput.','New queued evidence may wait up to a nominal 200 ms polling interval plus scheduling/network/processing delay.','Finite board event queue still overflows if production exceeds sustained receiver capacity.','No new FPGA detector accuracy claim; PL and firmware are identical to V1.32.'])
    (O/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,unit_tests=tests['count'],unchanged_pl_firmware_files=len(same))))
if __name__=='__main__':main()

"""Host regression for host compatibility regression for capture scheduling changes."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,unittest
R=Path(__file__).resolve().parents[1];O=R/'reports/v142';sys.path.insert(0,str(R/'host'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    validation_script_sha256=sha(Path(__file__))
    plan=load(R/'ITERATION_PLAN.json');B=Path(plan['baseline']);old=load(B/'DELIVERY_MANIFEST.json')
    for group in ('source_sha256','proof_sha256'):
        for n,h in old[group].items():assert sha(B/n)==h,('Baseline altered',n)
    assert sha(Path(plan['backup']))==plan['backup_sha256']
    with (O/'host_tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(R/'host'),pattern='test_*.py'))
    tests=dict(passed=result.wasSuccessful(),count=result.testsRun,failures=[str(t) for t,e in result.failures],errors=[str(t) for t,e in result.errors])
    (O/'host_tests.json').write_text(json.dumps(tests,indent=2));assert tests['passed'],tests
    node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    for file in ('test_review_session.js','test_preview_ui.js','test_inventory_ui.js'):
        proc=subprocess.run([str(node),str(R/'scripts'/file)],capture_output=True,text=True,encoding='utf-8',timeout=35)
        (O/(file+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,(file,proc.stderr)
    for file in ('test_preview_tcp_load.py','test_storage_rollback_process.py','test_stimulus_command_native.py'):
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(R/'scripts'/file)],capture_output=True,text=True,encoding='utf-8',timeout=120)
        (O/(file+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,(file,proc.stderr)
    import ast
    def records_node(root):
        tree=ast.parse((root/'host/workstation.py').read_text(encoding='utf-8-sig'))
        return ast.dump(next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Records'))
    assert records_node(R)==records_node(B),'Records storage path unexpectedly changed'
    assert sha(Path(__file__))==validation_script_sha256,'Validator changed during execution'
    result=dict(passed=True,version='V1.42',validation_script_sha256=validation_script_sha256,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),unit_tests=tests,
        review_ui=load(O/'review_session_native.json'),preview_ui=load(O/'preview_ui_native.json'),inventory_ui=load(O/'inventory_ui_native.json'),
        tcp_load=load(O/'preview_tcp_load/summary.json'),storage_process=load(O/'storage_rollback_process/summary.json'),native_stimulus=load(O/'native_stimulus/summary.json'),
        archive_implementation_ast_unchanged=True,source_sha256={p.relative_to(R).as_posix():sha(p) for p in (R/'host').iterdir() if p.is_file() and p.suffix in ('.py','.html','.json','.cs','.ps1','.js') and p.name not in ('player_status.json','player_instance.json')},
        scope='Host and loopback regression only; no physical board conclusion')
    assert result['tcp_load']['passed'] and result['storage_process']['passed'] and result['native_stimulus']['passed']
    (O/'host_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,tests=tests['count'])))
if __name__=='__main__':main()

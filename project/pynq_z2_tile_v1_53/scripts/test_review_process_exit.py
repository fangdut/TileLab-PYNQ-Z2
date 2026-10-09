"""Terminate a child process at three real SQLite transaction boundaries."""
from pathlib import Path
import sys,json,hashlib,subprocess,os
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/review_process_exit';sys.path.insert(0,str(R/'host'))
from workstation import Records
from review_revision import ReviewError
import test_workstation as fixtures
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if len(sys.argv)>1:
    case=sys.argv[1];root=Path(sys.argv[2]).resolve();assert root.parent==O.resolve()
    r=Records(root);key=r.all()[0]['id'];db=r.db
    def die(stage):
        with (root/'exit_boundary.txt').open('w') as f:f.write(stage);f.flush();os.fsync(f.fileno())
        os._exit(74)
    class CrashConnection:
        def __getattr__(self,name):return getattr(db,name)
        def execute(self,sql,*args):
            if sql.startswith('INSERT INTO review_revisions') and case=='before_revision':die(case)
            value=db.execute(sql,*args)
            if sql.startswith('INSERT INTO review_revisions') and case=='after_revision':die(case)
            return value
        def commit(self):
            db.commit()
            if case=='after_commit':die(case)
    r.db=CrashConnection();r.review(key,'confirmed_crack','committed child conclusion',0);raise AssertionError('Expected abrupt exit')
O.mkdir(parents=True,exist_ok=False);results=[]
for case in ('before_revision','after_revision','after_commit'):
    root=O/case;root.mkdir();r=Records(root);f,image,mask=fixtures.FrameTests().decode(fixtures.FrameTests().packet());key=r.save(f,image,mask,'isolated_process_test')
    before=r.get(key);digests={suffix:sha(r.file(key,suffix=='_mask.png')) for suffix in ('.png','_mask.png')};r.db.close()
    result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),case,str(root)],capture_output=True,text=True,timeout=15,creationflags=0x08000000 if os.name=='nt' else 0)
    assert result.returncode==74,(result.returncode,result.stderr);assert (root/'exit_boundary.txt').read_text()==case
    r=Records(root)
    try:
        observed=r.get(key)
        assert all(sha(r.file(key,suffix=='_mask.png'))==digest for suffix,digest in digests.items())
        if case=='after_commit':
            assert observed['review_revision']==1 and observed['review']=='confirmed_crack' and observed['note']=='committed child conclusion'
            try:r.review(key,'confirmed_crack','committed child conclusion',0)
            except ReviewError as e:assert e.code=='REVIEW_CONFLICT';retry='CONFLICT_PRESERVED_COMMIT'
            else:raise AssertionError('Duplicate stale request must not commit again')
        else:
            assert observed==before
            assert r.review(key,'confirmed_crack','retry after rollback',0)['review_revision']==1;retry='ROLLED_BACK_RETRY_ACCEPTED'
        results.append(dict(case=case,passed=True,exit_code=74,recovered=observed,retry=retry,images_unchanged=True))
    finally:r.db.close()
summary=dict(passed=True,cases=results,case_count=len(results),scope='Actual abrupt Python child exits around SQLite metadata writes/commit. Not a disk power-loss or board power-cycle test.')
(O/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(passed=True,case_count=len(results),retries=[x['retry'] for x in results])))

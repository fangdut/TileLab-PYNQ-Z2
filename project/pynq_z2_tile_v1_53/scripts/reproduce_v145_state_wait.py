"""Bounded baseline: real HTTP state is blocked by an in-progress PNG publication."""
from pathlib import Path
import hashlib,json,sys,threading,time,urllib.request
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
import workstation
from test_save_pause import SavePauseTests
O=R/'reports/v145/state_wait_baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    O.mkdir(parents=True,exist_ok=False)
    sources={}
    for name in ('workstation.py','workstation.html'):
        p=R/'host'/name;sources['host/'+name]=sha(p);(O/name).write_bytes(p.read_bytes())
    case=SavePauseTests();result={};finished=threading.Event();entered_state=threading.Event()
    try:
        s,b,entered,release,server=case.begin();old=s.state
        def observe(*a,**kw):entered_state.set();return old(*a,**kw)
        s.state=observe
        s.action({'op':'capture'});assert entered.wait(3)
        def request():
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/state',timeout=3) as r:result['state']=json.load(r)
            except Exception as e:result['error']=repr(e)
            finally:finished.set()
        reader=threading.Thread(target=request);reader.start();assert entered_state.wait(1)
        blocked=not finished.wait(.3);assert blocked
        t=time.monotonic();case.pause_http(s,server);pause_ms=round((time.monotonic()-t)*1000,2)
        release.set();reader.join(3);case.until_idle(s)
        assert finished.is_set() and 'error' not in result and len(s.records.all())==1
        assert b.calls.count('ack')==1
        out=dict(passed=True,negative_baseline_reproduced=True,state_blocked_during_png_publish=blocked,
            pause_ms=pause_ms,scope='Isolated HTTP and actual Records PNG save; fake board',
            source_sha256=sources,source_unchanged=all(sha(R/n)==h for n,h in sources.items()),
            script_sha256=sha(Path(__file__)))
        (O/'summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
    finally:case.doCleanups()
if __name__=='__main__':main()

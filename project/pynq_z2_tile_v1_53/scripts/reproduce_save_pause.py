"""Negative baseline: delayed real save publication blocks the actual HTTP Pause."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,sys,threading,time,traceback,urllib.request
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];O=R/'reports/v144/pause_save_baseline'
sys.path.insert(0,str(R/'host'))
import workstation
from test_recovery import Controlled
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def node(p,name):
    cls=next(n for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef) and n.name=='Station')
    return ast.dump(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name))
def main():
    assert R.name=='pynq_z2_tile_v1_53';O.mkdir(parents=True,exist_ok=False)
    source=R/'host/workstation.py';baseline=R.parent/'pynq_z2_tile_v1_43/host/workstation.py'
    assert all(node(source,n)==node(baseline,n) for n in ('loop','action'))
    before={n:sha(R/n) for n in ('host/workstation.py','host/confirmation_journal.py','host/test_recovery.py','host/test_events.py','scripts/reproduce_save_pause.py')}
    result=dict(passed=False,negative_baseline_reproduced=False,source_sha256=before,
        scope='Actual Station/Records/HTTP with controlled test bridge; delayed PNG publication on isolated archive; no physical board',
        baseline_behavior_ast_equal=True,started_at=datetime.now(timezone.utc).isoformat())
    root=O/'isolated';root.mkdir();bridge=Controlled();station=workstation.Station(root,bridge)
    server=workstation.ThreadingHTTPServer(('127.0.0.1',0),workstation.handler(station))
    http=threading.Thread(target=server.serve_forever,daemon=True);http.start()
    api='http://127.0.0.1:'+str(server.server_port)+'/api/action'
    entered=threading.Event();release=threading.Event();pause_entered=threading.Event();done=threading.Event();outcome={}
    actual_atomic=workstation.atomic;actual_action=station.action
    def action(body):
        if body['op']=='pause':pause_entered.set()
        return actual_action(body)
    station.action=action
    def delayed(path,data):
        if path.suffix=='.png' and not entered.is_set():
            entered.set()
            if not release.wait(5):raise TimeoutError('Save fixture not released')
        return actual_atomic(path,data)
    def request(op):
        req=urllib.request.Request(api,data=json.dumps(dict(op=op)).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=3) as response:return json.load(response)
    def pause():
        started=time.monotonic()
        try:outcome['response']=request('pause')
        except Exception:outcome['error']=traceback.format_exc()
        finally:outcome['milliseconds']=(time.monotonic()-started)*1000;done.set()
    thread=threading.Thread(target=pause,daemon=True)
    try:
        with patch.object(workstation,'atomic',side_effect=delayed):
            assert request('capture')=={'ok':True};assert entered.wait(3)
            available=station.lock.acquire(blocking=False)
            if available:station.lock.release()
            assert not available,'Baseline no longer holds Station lock during disk save'
            thread.start();assert pause_entered.wait(2)
            blocked=not done.wait(.15);assert blocked,'Baseline Pause no longer waits for disk save'
            assert bridge.calls.count('ack')==0
            release.set();thread.join(4);assert done.is_set() and 'error' not in outcome,outcome
            end=time.monotonic()+3
            while station.busy:
                assert time.monotonic()<end;time.sleep(.005)
        assert not station.enabled and station.captures==1 and len(station.records.all())==1
        assert bridge.calls.count('ack')==1 and not station.pending_ack
        result.update(passed=True,negative_baseline_reproduced=True,station_lock_unavailable_during_save=True,
            pause_blocked_before_storage_release=blocked,pause=outcome,captures=station.captures,
            acknowledged_after_save=True,history=station.records.confirmations.history())
    finally:
        release.set()
        if thread.ident is not None:thread.join(4)
        station.exit=True;station.worker.join(5);server.shutdown();server.server_close();http.join(2)
        assert not station.worker.is_alive()
        station.records.db.close();bridge.close()
        result['source_unchanged']=before=={n:sha(R/n) for n in before};assert result['source_unchanged']
        (O/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

"""Baseline: slow storage configuration holds the Station lock and delays Pause."""
from pathlib import Path
import hashlib,json,sys,tempfile,threading,time,urllib.request
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
import workstation
from test_recovery import Controlled
O=R/'reports/v146/storage_control_baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    O.mkdir(parents=True,exist_ok=False);p=R/'host/workstation.py';source=sha(p);(O/'workstation.py').write_bytes(p.read_bytes())
    with tempfile.TemporaryDirectory(prefix='tile_v146_baseline_') as tmp:
        s=workstation.Station(tmp,Controlled());server=workstation.ThreadingHTTPServer(('127.0.0.1',0),workstation.handler(s))
        http=threading.Thread(target=server.serve_forever,daemon=True);http.start()
        entered=threading.Event();release=threading.Event();pause_entered=threading.Event();pause_done=threading.Event();out={};original=s.action
        def action(body):
            if body.get('op')=='pause':pause_entered.set()
            return original(body)
        s.action=action
        def delayed(path,data):
            if path.name=='storage_policy.json':
                entered.set();assert release.wait(4)
            return actual(path,data)
        def post(op,extra):
            try:
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/action',data=json.dumps(dict(op=op,**extra)).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=5) as resp:out[op]=json.load(resp)
            except Exception as e:out[op]=repr(e)
            finally:
                if op=='pause':pause_done.set()
        actual=workstation.atomic;setting=threading.Thread(target=post,args=('storage',dict(mode='preview',max_archive_mib=32)));stopper=threading.Thread(target=post,args=('pause',{}))
        try:
            with patch.object(workstation,'atomic',side_effect=delayed):
                setting.start();assert entered.wait(2);stopper.start();assert pause_entered.wait(1)
                blocked=not pause_done.wait(.3);assert blocked;release.set();setting.join(4);stopper.join(4)
            assert out==dict(storage=dict(ok=True),pause=dict(ok=True)),out
            result=dict(passed=True,negative_baseline_reproduced=True,pause_blocked_during_policy_write=blocked,source_unchanged=sha(p)==source,
                source_sha256={'host/workstation.py':source},script_sha256=sha(Path(__file__)),scope='Isolated HTTP with actual policy publication and fake board')
            (O/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
        finally:
            release.set();s.exit=True;s.worker.join(5)
            if setting.ident is not None:setting.join(5)
            if stopper.ident is not None:stopper.join(5)
            server.shutdown();server.server_close();http.join(2);s.records.db.close()
if __name__=='__main__':main()

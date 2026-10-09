"""Injected slow player read proves the baseline control-lock dependency."""
from pathlib import Path
import hashlib,json,sys,tempfile,threading,urllib.request
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
import workstation
from test_recovery import Controlled
O=R/'reports/v148/player_read_baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    O.mkdir(parents=True,exist_ok=False);p=R/'host/workstation.py';source=sha(p);(O/'workstation.py').write_bytes(p.read_bytes())
    with tempfile.TemporaryDirectory(prefix='tile_v148_baseline_') as tmp:
        s=workstation.Station(tmp,Controlled());server=workstation.ThreadingHTTPServer(('127.0.0.1',0),workstation.handler(s));http=threading.Thread(target=server.serve_forever,daemon=True);http.start()
        entered=threading.Event();release=threading.Event();pause_entered=threading.Event();done=threading.Event();out={};old=s.stimulus_status.snapshot;action=s.action
        def snapshot():entered.set();assert release.wait(4);return old()
        def observe(body):
            if body.get('op')=='pause':pause_entered.set()
            return action(body)
        s.action=observe
        def request(name):
            try:
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+('/api/action' if name=='pause' else '/api/live'),
                    data=b'{"op":"pause"}' if name=='pause' else None,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=5) as response:out[name]=json.load(response)
            except Exception as error:out[name]=repr(error)
            finally:
                if name=='pause':done.set()
        reader=threading.Thread(target=request,args=('live',));stopper=threading.Thread(target=request,args=('pause',))
        try:
            with patch.object(s.stimulus_status,'snapshot',side_effect=snapshot):
                reader.start();assert entered.wait(2);stopper.start();assert pause_entered.wait(1);blocked=not done.wait(.25);assert blocked
                release.set();reader.join(4);stopper.join(4)
            assert out['pause']==dict(ok=True) and isinstance(out['live'],dict),out
            result=dict(passed=True,negative_baseline_reproduced=True,pause_blocked_during_player_read=blocked,source_unchanged=sha(p)==source,
                source_sha256={'host/workstation.py':source},script_sha256=sha(Path(__file__)),scope='Isolated real HTTP with injected bounded player-snapshot delay; not a physical disk latency measurement')
            (O/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
        finally:
            release.set();reader.join(5)
            if stopper.ident is not None:stopper.join(5)
            s.exit=True;s.worker.join(5);server.shutdown();server.server_close();http.join(2);s.records.db.close()
if __name__=='__main__':main()

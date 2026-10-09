"""Windows baseline: real rename sharing contention delays Pause during source publication."""
from pathlib import Path
import ctypes,hashlib,json,sys,tempfile,threading,time,urllib.request
from ctypes import wintypes
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
import workstation
from test_recovery import Controlled
from stimulus_command import make_command
O=R/'reports/v147/display_control_baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    O.mkdir(parents=True,exist_ok=False);p=R/'host/workstation.py';source=sha(p);(O/'workstation.py').write_bytes(p.read_bytes())
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
    with tempfile.TemporaryDirectory(prefix='tile_v147_baseline_') as tmp:
        s=workstation.Station(tmp,Controlled());host=Path(tmp)/'host';host.mkdir(exist_ok=True);command=host/'display_command.txt';command.write_bytes(make_command('station_0')[0])
        server=workstation.ThreadingHTTPServer(('127.0.0.1',0),workstation.handler(s));http=threading.Thread(target=server.serve_forever,daemon=True);http.start()
        handle=k.CreateFileW(str(command),0x80000000,3,None,3,0,None);assert handle!=wintypes.HANDLE(-1).value
        pause_entered=threading.Event();pause_done=threading.Event();out={};original=s.action
        def action(body):
            if body.get('op')=='pause':pause_entered.set()
            return original(body)
        s.action=action
        def post(op,extra):
            try:
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/action',data=json.dumps(dict(op=op,**extra)).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=4) as response:out[op]=json.load(response)
            except Exception as e:out[op]=repr(e)
            finally:
                if op=='pause':pause_done.set()
        writer=threading.Thread(target=post,args=('display',dict(value='real_video')));stopper=threading.Thread(target=post,args=('pause',{}))
        try:
            writer.start();deadline=time.monotonic()+1
            while not command.with_suffix('.txt.tmp').exists():
                assert time.monotonic()<deadline;time.sleep(.002)
            stopper.start();assert pause_entered.wait(.2);blocked=not pause_done.wait(.25);assert blocked
            k.CloseHandle(handle);handle=None;writer.join(3);stopper.join(3)
            assert out['pause']==dict(ok=True) and out['display']['ok'],out
            result=dict(passed=True,negative_baseline_reproduced=True,pause_blocked_during_command_publish=blocked,source_unchanged=sha(p)==source,
                source_sha256={'host/workstation.py':source},script_sha256=sha(Path(__file__)),scope='Actual Windows read/write-share file handle denies rename; isolated HTTP and fake board')
            (O/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
        finally:
            if handle:k.CloseHandle(handle)
            writer.join(4)
            if stopper.ident is not None:stopper.join(4)
            s.exit=True;s.worker.join(4);server.shutdown();server.server_close();http.join(2);s.records.db.close()
if __name__=='__main__':main()

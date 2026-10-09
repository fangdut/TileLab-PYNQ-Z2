"""Actual Windows file-sharing contention on the board workstation command file."""
from pathlib import Path
import ctypes,json,threading,time,traceback,urllib.request
from ctypes import wintypes
from board_v147_helpers import Client,ROOT,sha,write,wait_for,adopted,programmed_proof,FIRMWARE,ERRORS

def live():
    t=time.monotonic()
    with urllib.request.urlopen('http://127.0.0.1:8770/api/live',timeout=1) as response:value=json.load(response)
    return dict(milliseconds=(time.monotonic()-t)*1000,response=value)

def main():
    out=ROOT/'reports/v147/display_control_board';out.mkdir(parents=True,exist_ok=False)
    names=['scripts/board_v147_display_control.py','scripts/board_v147_helpers.py','host/workstation.py','host/workstation.html','host/stimulus_status.py','host/stimulus_command.py']
    result=dict(passed=False,programming=programmed_proof(),source_sha256={n:sha(ROOT/n) for n in names},live_observations=[],
        scope='Actual board-connected Station and actual Windows rename denial; pending publication versus old player adoption checked by HTTP')
    c=Client('http://127.0.0.1:8770');handle=None;thread=None;publication=[]
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
    try:
        s=c.state();assert not s['enabled'] and not s['busy'] and s['captures']==0 and s['storage']['mode']=='preview'
        before=c.ok('status')['response'];assert before['boot_id']==result['programming']['record']['boot_id'] and before['version']==FIRMWARE;result['before']=before
        initial=c.ok('display',value='real_video')['response']['request_id'];wait_for(c,lambda s:adopted(s,'real_video',initial))
        command=ROOT/'host/display_command.txt';old=command.read_bytes()
        handle=k.CreateFileW(str(command),0x80000000,3,None,3,0,None);assert handle!=wintypes.HANDLE(-1).value;held=time.monotonic()
        def publish():
            try:publication.append(c.action('display',value='real_video'))
            except Exception as e:publication.append(dict(error=repr(e)))
        thread=threading.Thread(target=publish);thread.start();deadline=time.monotonic()+.5
        while not command.with_suffix('.txt.tmp').exists():
            if time.monotonic()>deadline:raise TimeoutError('Command publication did not reach temporary file')
            time.sleep(.002)
        pause=c.ok('pause');assert pause['milliseconds']<1000;result['pause_during_publish']=pause
        for i in range(4):
            v=live();s=v['response'];pending=s['display_pending'];assert pending and pending['value']=='real_video'
            assert pending['request_id']!=initial and s['stimulus_status']['request_id']==initial
            assert s['stimulus_status']['observed_request_id']==initial and not s['enabled'] and s['captures']==0
            assert v['milliseconds']<1000;result['live_observations'].append(v);time.sleep(.025)
        rejected=c.action('display',value='station_6');assert rejected['status']==400 and rejected['milliseconds']<1000;result['second_publish_rejected']=rejected
        assert not publication and command.read_bytes()==old;result['writer_held_seconds']=time.monotonic()-held
        k.CloseHandle(handle);handle=None;thread.join(4);assert not thread.is_alive() and len(publication)==1 and publication[0]['status']==200
        published=publication[0]['response']['request_id'];assert published==result['live_observations'][0]['response']['display_pending']['request_id']
        result['publication']=publication[0];final=wait_for(c,lambda s:adopted(s,'real_video',published))
        assert final['display_pending'] is None and not final['enabled'] and final['captures']==0;result['adopted_input']=final['stimulus_status']
        after=c.ok('status')['response'];result['after']=after;result['error_deltas']={k:(after[k]-before[k])&0xffffffff for k in ERRORS};assert not any(result['error_deltas'].values())
        assert not c.records();assert all(sha(ROOT/n)==h for n,h in result['source_sha256'].items())
        result.update(passed=True,final_paused=True,no_unrequested_capture=True,old_command_preserved_until_release=True,
            exact_new_request_adopted=True,live_max_ms=max(v['milliseconds'] for v in result['live_observations']))
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        if handle and handle!=wintypes.HANDLE(-1).value:k.CloseHandle(handle)
        if thread and thread.is_alive():thread.join(4)
        write(out/'summary.json',result)
    print(json.dumps({k:result[k] for k in ('passed','writer_held_seconds','live_max_ms','error_deltas')}))
if __name__=='__main__':main()

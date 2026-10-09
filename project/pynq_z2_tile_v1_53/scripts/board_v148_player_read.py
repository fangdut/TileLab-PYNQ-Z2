"""Real Windows read denial on player identity while physical capture continues."""
from pathlib import Path
import ctypes,json,time,traceback,urllib.request
from ctypes import wintypes
from board_v148_helpers import Client,ROOT,sha,write,wait_for,adopted,programmed_proof,FIRMWARE,ERRORS

def live():
    t=time.monotonic()
    with urllib.request.urlopen('http://127.0.0.1:8770/api/live',timeout=1) as response:value=json.load(response)
    return dict(milliseconds=(time.monotonic()-t)*1000,response=value)

def main():
    out=ROOT/'reports/v148/player_read_board';out.mkdir(parents=True,exist_ok=False)
    names=['scripts/board_v148_player_read.py','scripts/board_v148_helpers.py','host/workstation.py','host/stimulus_status.py']
    result=dict(passed=False,programming=programmed_proof(),source_sha256={n:sha(ROOT/n) for n in names},observations=[],
        scope='Actual Windows read denial, not a stalled disk; live board captures must continue while player identity is unconfirmed')
    c=Client('http://127.0.0.1:8770');handle=None
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
    try:
        s=c.state();assert not s['enabled'] and not s['busy'] and s['storage']['mode']=='preview'
        c.ok('recipe',value='mvtec_hdmi_weak_v124');c.ok('wire_mode',value='packed');request=c.ok('display',value='real_video')['response']['request_id'];c.ok('start')
        s=wait_for(c,lambda s:adopted(s,'real_video',request) and s['captures']>=2 and s['capture_health']['ready'])
        before=s['board_stats'];assert before['boot_id']==result['programming']['record']['boot_id'] and before['version']==FIRMWARE;result['before']=before
        marker=ROOT/'host/player_instance.json';marker_hash=sha(marker)
        # Allow write/delete but deny additional readers. The active player
        # publishes this marker once and does not consume it on rendering ticks.
        handle=k.CreateFileW(str(marker),0x80000000,6,None,3,0,None);assert handle!=wintypes.HANDLE(-1).value;held=time.monotonic()
        while time.monotonic()-held<1.5:
            v=live();s=v['response'];assert s['stimulus_status']['state']=='PLAYER_INSTANCE_UNAVAILABLE' and not s['stimulus_status']['ready']
            assert s['capture_health']['ready'] and not s['error'] and s['enabled'];result['observations'].append(v);time.sleep(.12)
        delta=result['observations'][-1]['response']['captures']-result['observations'][0]['response']['captures'];assert delta>=2
        assert len({o['response']['frame']['pixel_crc32'] for o in result['observations']})>=2
        pause=c.ok('pause');assert pause['milliseconds']<1000;result['pause_during_read_denial']=pause
        result['held_seconds']=time.monotonic()-held;k.CloseHandle(handle);handle=None;assert sha(marker)==marker_hash
        final=wait_for(c,lambda s:not s['busy'] and not s['pending_operation'] and adopted(s,'real_video',request))
        assert not final['enabled'] and not final['error'] and not c.records()
        after=c.ok('status')['response'];result['after']=after;result['error_deltas']={k:(after[k]-before[k])&0xffffffff for k in ERRORS};assert not any(result['error_deltas'].values())
        assert all(sha(ROOT/n)==h for n,h in result['source_sha256'].items())
        result.update(passed=True,capture_delta_during_denial=delta,identity_confirmation_recovered=True,marker_unchanged=True,final_paused=True,
            live_max_ms=max(v['milliseconds'] for v in result['observations']))
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        if handle and handle!=wintypes.HANDLE(-1).value:k.CloseHandle(handle)
        write(out/'summary.json',result)
    print(json.dumps({k:result[k] for k in ('passed','held_seconds','capture_delta_during_denial','live_max_ms','error_deltas')}))
if __name__=='__main__':main()

"""Bounded live moving-photo smoke + one durable manual archive. Leaves preview running."""
from pathlib import Path
import json,time,traceback
from board_v144_helpers import (Client,ROOT,ERRORS,FIRMWARE,sha,write,wait_for,paused,
    adopted,healthy,checked_pixels,save_evidence,programmed_proof)

def main():
    out=ROOT/'reports/v144/motion_board';out.mkdir(parents=True,exist_ok=False)
    c=Client('http://127.0.0.1:8770');names=['scripts/board_v144_motion.py','scripts/board_v144_helpers.py',
        'host/workstation.py','host/tcp_transport.py','host/ConveyorStimulus.cs']
    result=dict(passed=False,scope='15s moving-photo preview plus one manually saved/ACKed frame; no human monitor confirmation',
        source_sha256={n:sha(ROOT/n) for n in names},programming=programmed_proof(),observations=[])
    boot=result['programming']['record']['boot_id']
    try:
        paused(c);assert c.state()['storage']['mode']=='preview'
        c.ok('recipe',value='mvtec_hdmi_weak_v124');c.ok('wire_mode',value='packed');c.ok('preview_rate',value=2)
        c.ok('freeze_preview',enabled=False)
        request=c.ok('display',value='real_video')['response']['request_id'];count=c.state()['captures'];c.ok('start')
        s=wait_for(c,lambda s:s['captures']>count+1 and adopted(s,'real_video',request) and not s['pending_operation'])
        healthy(s,boot);before=s['board_stats'];old_ids={r['id'] for r in c.records()};started=time.monotonic()
        while time.monotonic()-started<15:
            s=c.state();healthy(s,boot)
            result['observations'].append({k:s[k] for k in ('captures','frame','stimulus_status','board_stats')})
            time.sleep(.25)
        paused(c);last=c.state();result['before']=before;result['after_window']=last['board_stats']
        result['error_deltas']={k:(last['board_stats'][k]-before[k])&0xffffffff for k in ERRORS}
        assert not any(result['error_deltas'].values())
        assert result['observations'][-1]['captures']-result['observations'][0]['captures']>=15
        assert len({r['frame']['pixel_crc32'] for r in result['observations']})>=6
        assert result['observations'][-1]['stimulus_status']['rendered_frames']-result['observations'][0]['stimulus_status']['rendered_frames']>=300
        assert {r['id'] for r in c.records()}==old_ids,'Preview created archive rows'
        count=c.state()['captures'];c.ok('capture')
        final=wait_for(c,lambda s:s['captures']==count+1 and not s['busy'] and not s['pending_operation'] and not s['pending_confirmation'])
        healthy(final,boot);new=[r for r in c.records() if r['id'] not in old_ids]
        assert len(new)==1 and new[0]['reason']=='manual'
        f=new[0];original,mask=c.image(f,archived=True),c.image(f,True,True)
        check=checked_pixels(f,original,mask,boot,FIRMWARE)
        result['manual_evidence']=save_evidence(out,'manual_moving',f,original,mask,check)
        result['manual_saved_and_confirmed']=True;result['new_manual_archives']=1
        assert all(sha(ROOT/n)==d for n,d in result['source_sha256'].items())
        c.ok('start');wait_for(c,lambda s:s['enabled'] and s['captures']>count+1)
        result.update(passed=True,final_enabled=True,source_kept_moving=True)
    except Exception:
        result['error']=traceback.format_exc();raise
    finally:write(out/'summary.json',result)
    print(json.dumps(dict(passed=True,observations=len(result['observations']),errors=result['error_deltas'],manual_archives=1)))
if __name__=='__main__':main()

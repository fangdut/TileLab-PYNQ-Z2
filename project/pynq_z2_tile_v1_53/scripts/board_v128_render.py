"""Freeze the real WPF source briefly, then verify the actual HDMI frame codes."""
from pathlib import Path
import json,time,sys,subprocess,hashlib,urllib.request,urllib.error,urllib.parse
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/render_board';O.mkdir(parents=True,exist_ok=True)
from board_v18_continuous import action,state,read_player,barcode

def dump(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def healthy(s):
    assert s['revision']=='V1.28' and s['enabled'] and s['board_connected'] and not s['error']
    assert s['board_stats']['version']==0x11c00 and s['capture_health']['ready'] and not s['capture_health']['stale']
    assert all(s['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
def until(fn,seconds=15):
    end=time.monotonic()+seconds
    while True:
        s=state()
        if fn(s):return s
        if time.monotonic()>end:raise TimeoutError(json.dumps(s['stimulus_status'],ensure_ascii=False))
        time.sleep(.08)
def restart(hold,log):
    p=read_player()
    with (O/(log+'_launcher.log')).open('wb') as output:
        proc=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'scripts/restart_player_test.ps1'),'-Root',str(R),'-ExpectedPid',str(p['player_pid']),'-HoldSeconds',str(hold),'-AfterSeconds','8','-LogName',log],stdout=output,stderr=subprocess.STDOUT,timeout=20,creationflags=0x08000000)
    assert proc.returncode==0,'Renderer test launcher failed'
    return p
def frame_sample(s):
    f=s.get('frame')
    if not f or f['event_reason']!=3:return None # Fresh requested preview, not an older retained product event.
    key=str(f['frame_id'])+'_'+f['acquired_at']
    try:
        with urllib.request.urlopen('http://127.0.0.1:8770/api/image?frame='+urllib.parse.quote(key),timeout=2) as response:png=response.read()
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise
    return dict(frame=f['frame_id'],barcode=barcode(png),sha256=hashlib.sha256(png).hexdigest(),pixel_crc=f['pixel_crc32'])
def run():
    result=dict(passed=False,scope='Actual bounded WPF animation hold, fresh player telemetry, and real HDMI/FPGA frame-code capture; not a physical cable-disconnect test')
    injected=False
    try:
        action('storage',mode='preview',max_archive_mib=1024);action('recipe',value='mvtec_hdmi_weak_v124');action('display',value='real_video');action('start')
        before=until(lambda s:s['board_connected'] and s['capture_health'].get('ready') and s['stimulus_status']['ready'] and s['stimulus_status']['motion']['state']=='PROGRESSING');healthy(before)
        old=restart(8,'diagnostic_hold');injected=True
        until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['player_session']!=old['player_session'] and s['stimulus_status']['motion']['state']=='PROGRESSING')
        rows=[];before_codes=[];held=[];after_codes=[];hold_started=None;stalled_at=None;repeat=None;resumed=None;begin=time.monotonic()
        while time.monotonic()-begin<23:
            s=state();healthy(s);p=read_player();m=s['stimulus_status']['motion'];t=time.monotonic()-begin
            phase='hold' if p['diagnostic_hold_active'] else 'after' if hold_started is not None else 'before'
            if phase=='hold' and hold_started is None:hold_started=t
            sample=frame_sample(s)
            row=dict(seconds=t,phase=phase,player=p,state=s,frame_sample=sample);rows.append(row)
            if phase=='before' and sample:before_codes.append(sample)
            if phase=='hold' and m['state']=='STALLED':
                assert s['stimulus_status']['ready'] and s['stimulus_status']['identity_confirmed'] and s['stimulus_status']['age_seconds']<1.5
                if stalled_at is None:
                    stalled_at=t;dump('stalled_checkpoint.json',row);print('STALLED_UI_READY: telemetry is fresh, actual animation is held, FPGA still captures complete frames',flush=True)
                    repeat=action('display',value='real_video')
                if sample and t-stalled_at>.4:held.append(dict(player_frame=p['drawn_source_frame'],request_id=s['stimulus_status']['request_id'],**sample))
            if phase=='after' and m['state']=='PROGRESSING' and sample:
                if resumed is None:resumed=t
                after_codes.append(sample)
                if t-resumed>1.3 and len({f['barcode'] for f in after_codes})>=3:break
            time.sleep(.1)
        assert stalled_at is not None and resumed is not None and repeat and len(held)>=3
        assert len({f['barcode'] for f in before_codes})>=3 and len({f['barcode'] for f in after_codes})>=3
        assert len({f['barcode'] for f in held})==1 and all(f['barcode']==f['player_frame'] for f in held)
        assert len({f['sha256'] for f in held})==1 and len({f['pixel_crc'] for f in held})==1
        assert any(f['request_id']==repeat['request_id'] for f in held),'Repeated selection hid the stall or restarted motion'
        hold_rows=[r for r in rows if r['phase']=='hold'];assert hold_rows[-1]['state']['board_stats']['captured']-hold_rows[0]['state']['board_stats']['captured']>300
        assert hold_rows[-1]['player']['utc']!=hold_rows[0]['player']['utc']
        assert all(r['player']['drawn_source_frame']==hold_rows[0]['player']['drawn_source_frame'] for r in hold_rows)
        result.update(before=before,rows=rows,before_codes=before_codes,held=held,after_codes=after_codes,repeat_request=repeat,
            hold_first_observed_seconds=hold_started,stall_first_observed_seconds=stalled_at,stall_detection_delay_seconds=stalled_at-hold_started,resumed_seconds=resumed,
            complete_frames_during_hold=hold_rows[-1]['state']['board_stats']['captured']-hold_rows[0]['state']['board_stats']['captured'])
        dump('animation_hold_passed.json',dict(result,passed=True));print('Held real HDMI images had one frame code/PNG/CRC; resumed HDMI codes advance again',flush=True)
        restart(0,'normal_player');injected=False
        normal=until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['motion']['state']=='PROGRESSING')
        action('display',value='station_6');static=until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['motion']['state']=='NOT_REQUIRED')
        static_rows=[];start=time.monotonic()
        while time.monotonic()-start<2.2:
            s=state();healthy(s);assert s['stimulus_status']['motion']['state']=='NOT_REQUIRED';static_rows.append(s);time.sleep(.12)
        action('display',value='real_video');final=until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['motion']['state']=='PROGRESSING');healthy(final)
        for key in ('boot_id','gaps','invalid','dropped','ack_errors','descriptor_crc_errors'):assert final['board_stats'][key]==before['board_stats'][key],key
        assert final['records_total']==before['records_total'] and final['storage']['mode']=='preview'
        assert not read_player()['diagnostic_hold_active']
        result.update(passed=True,static_exemption=dict(passed=True,rows=static_rows),normal_player=normal,after=final,no_new_records=True)
        dump('summary.json',result);print(json.dumps(dict(passed=True,held_hdmi_samples=len(held),complete_frames_during_hold=result['complete_frames_during_hold'],stall_detection_delay_seconds=result['stall_detection_delay_seconds'],static_exempt=True)),flush=True)
    except Exception as e:result['error']=str(e);dump('failure_'+str(time.time_ns())+'.json',result);raise
    finally:
        if injected:restart(0,'normal_player_after_failure')
        action('storage',mode='preview',max_archive_mib=1024);action('display',value='real_video');action('start')
if __name__=='__main__':run()

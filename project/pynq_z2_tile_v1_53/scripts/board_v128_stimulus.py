"""Actual WPF, Windows sharing locks, HTTP and HDMI board acceptance."""
from pathlib import Path
import json,time,sys,subprocess,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132/stimulus_board';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from workstation import atomic
from board_v18_continuous import action,state,read_player
from board_v123_stimulus import FileHold

def dump(name,value):(O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def until(fn,seconds=15):
    end=time.monotonic()+seconds
    while True:
        s=state()
        if fn(s):return s
        if time.monotonic()>end:raise TimeoutError(json.dumps(s['stimulus_status'],ensure_ascii=False))
        time.sleep(.06)
def healthy(s):
    assert s['revision']=='V1.28' and s['enabled'] and s['board_connected'] and not s['error']
    assert s['board_stats']['version']==0x11c00 and s['capture_health']['ready'] and not s['capture_health']['stale']
    if s.get('frame'):assert all(s['frame'][k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified'))
def ready(source='real_video',request=None):
    s=until(lambda s:s['board_connected'] and s['capture_health'].get('ready') and s['stimulus_status']['ready'] and s['stimulus_status']['observed']==source and (request is None or s['stimulus_status']['observed_request_id']==request))
    healthy(s);return s
def samples(seconds,states):
    rows=[];begin=time.monotonic()
    while time.monotonic()-begin<seconds:
        s=state();healthy(s);assert s['stimulus_status']['state'] in states,s['stimulus_status']
        rows.append(dict(seconds=time.monotonic()-begin,state=s));time.sleep(.1)
    assert rows[-1]['state']['captures']>rows[0]['state']['captures']
    return rows
def run():
    result=dict(passed=False,scope='Actual player and board; local adoption does not prove the physical display appearance',cases={});before=None
    try:
        action('storage',mode='preview',max_archive_mib=1024);action('recipe',value='mvtec_hdmi_weak_v124');action('display',value='real_video');action('start')
        before=ready();healthy(before);cases=result['cases'];p0=read_player();repeats=[]
        for _ in range(10):
            reply=action('display',value='real_video');s=ready(request=reply['request_id']);p=read_player()
            assert p['player_session']==p0['player_session'] and p['position_seconds']>=p0['position_seconds']
            assert s['stimulus_status']['identity_confirmed'];repeats.append(dict(request=reply,position=p['position_seconds'],rendered=p['rendered_frames']))
        assert len({r['request']['request_id'] for r in repeats})==10
        cases['same_source_no_restart']=dict(passed=True,before=p0,requests=repeats,after=read_player())
        print('10 distinct same-source IDs adopted without resetting the moving timeline',flush=True)
        with FileHold('display_command.txt',0):rows=samples(2.2,{'COMMAND_UNAVAILABLE'})
        after=ready();cases['exclusive_command']=dict(passed=True,rows=rows,after=after)
        until(lambda s:s['stimulus_status']['ready'] and s['stimulus_status']['age_seconds']<.12)
        with FileHold('player_status.json',1):
            previous=state()['stimulus_status'];reply=action('display',value='real_video');pending=state()
            assert pending['stimulus_status']['state']=='SWITCHING' and pending['stimulus_status']['request_id']!=previous['request_id']
            rows=samples(2.2,{'SWITCHING','STALE'});assert rows[-1]['state']['stimulus_status']['state']=='STALE'
        after=ready(request=reply['request_id']);cases['same_name_held_report']=dict(passed=True,pending=pending,rows=rows,after=after)
        with FileHold('player_status.json',0):rows=samples(1.1,{'PLAYER_UNAVAILABLE'})
        cases['exclusive_telemetry']=dict(passed=True,rows=rows,after=ready())
        with FileHold('player_instance.json',0):rows=samples(1.1,{'PLAYER_INSTANCE_UNAVAILABLE'})
        cases['exclusive_instance']=dict(passed=True,rows=rows,after=ready())
        print('Command, report and startup-marker file locks: acquisition continues',flush=True)
        for name,payload in [('oversized_command',b'x'*129),('bad_utf8_command',b'\xff')]:
            p0=read_player();atomic(R/'host/display_command.txt',payload);rows=samples(1.1,{'COMMAND_UNAVAILABLE'})
            reply=action('display',value='real_video');s=ready(request=reply['request_id']);p=read_player()
            assert p['player_session']==p0['player_session'] and p['rendered_frames']>p0['rendered_frames'] and p['position_seconds']>p0['position_seconds']
            cases[name]=dict(passed=True,before=p0,rows=rows,after=s,player_after=p)
        atomic(R/'host/display_command.txt',b'real_video\n')
        until(lambda s:s['stimulus_status']['state']=='LEGACY_UNCONFIRMED')
        rows=samples(1.1,{'LEGACY_UNCONFIRMED'});reply=action('display',value='real_video')
        cases['legacy_not_confirmed']=dict(passed=True,rows=rows,after=ready(request=reply['request_id']))
        # Keep a genuine old telemetry file while restarting the actual player.
        old=read_player();current_id=old['request_id']
        script=r'''
param([string]$Root,[int]$ExpectedPid)
$ErrorActionPreference='Stop'
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$ExpectedPid"
if(!$proc -or $proc.CommandLine -notlike ('*'+$Root+'*hdmi_display.ps1*')){throw 'Player identity mismatch'}
Stop-Process -Id $ExpectedPid
$next=Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $Root 'host/hdmi_display.ps1')+'"') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Root 'reports/display_restart.log') -RedirectStandardError (Join-Path $Root 'reports/display_restart_error.log')
$next.Id | Set-Content -LiteralPath (Join-Path $Root 'host/display.pid')
$next.Id
'''
        (O/'restart_player.ps1').write_text(script,encoding='utf-8-sig')
        dump('before_restart_partial.json',result)
        with FileHold('player_status.json',1):
            # Windows Start-Process descendants can retain an inherited pipe;
            # waiting for its EOF is not the same as waiting for the launcher.
            # A real file avoids an unbounded communicate() drain after timeout.
            with (O/'restart_player.log').open('wb') as log:
                proc=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(O/'restart_player.ps1'),'-Root',str(R),'-ExpectedPid',str(old['player_pid'])],stdout=log,stderr=subprocess.STDOUT,timeout=20,creationflags=0x08000000)
            assert proc.returncode==0,'Player restart shell failed; inspect restart_player.log'
            end=time.monotonic()+12
            while True:
                marker=json.loads((R/'host/player_instance.json').read_text())
                if marker['session']!=old['player_session']:break
                if time.monotonic()>end:raise TimeoutError('New player marker not published')
                time.sleep(.08)
            rows=samples(1.1,{'PLAYER_SESSION_SWITCHING','STALE'})
        after=ready(request=current_id);p=read_player()
        assert p['player_session']!=old['player_session'] and p['player_pid']!=old['player_pid']
        cases['actual_player_restart_with_old_report']=dict(passed=True,old_player=old,new_marker=marker,rows=rows,after=after,new_player=p)
        final=ready()
        for k in ('boot_id','gaps','invalid','dropped','ack_errors','descriptor_crc_errors'):assert before['board_stats'][k]==final['board_stats'][k],k
        assert before['records_total']==final['records_total'] and final['storage']['mode']=='preview'
        result.update(passed=True,before=before,after=final,case_count=len(cases),captured_delta=final['board_stats']['captured']-before['board_stats']['captured'],host_capture_delta=final['captures']-before['captures'])
        dump('summary.json',result);print(json.dumps(dict(passed=True,cases=len(cases),captured_delta=result['captured_delta'],host_capture_delta=result['host_capture_delta'])),flush=True)
    except Exception as e:
        result['error']=str(e);dump('failure_'+str(time.time_ns())+'.json',result);raise
    finally:action('storage',mode='preview',max_archive_mib=1024);action('display',value='real_video');action('start')
if __name__=='__main__':run()

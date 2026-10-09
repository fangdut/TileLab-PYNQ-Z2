"""Bounded physical archive persistence check across an actual Station restart."""
from pathlib import Path
import json,subprocess,time,traceback
from board_v143_helpers import Client,ROOT,sha,write,paused,wait_for,checked_pixels,programmed_proof,FIRMWARE
def main():
    out=ROOT/'reports/v143/station_restart';out.mkdir(parents=True,exist_ok=False)
    c=Client('http://127.0.0.1:8770');names=['scripts/test_v143_station_restart.py','scripts/restart_station_v143.ps1',
        'scripts/board_v143_helpers.py','host/workstation.py','host/confirmation_journal.py']
    result=dict(passed=False,source_sha256={n:sha(ROOT/n) for n in names},programming=programmed_proof(),
        scope='Actual paused Station process restart, saved physical image/CRC and confirmation history readback; no board reset or power-loss injection')
    boot=result['programming']['record']['boot_id']
    try:
        paused(c);before=c.state();records=c.records();assert len(records)==1
        history=before['confirmation_journal']['history'];assert len(history)==1 and not before['confirmation_journal']['error']
        record=records[0];images=[c.image(record,archived=True),c.image(record,mask=True,archived=True)]
        result['before']={k:before[k] for k in ('revision','board_stats','confirmation_journal','pending_confirmation','captures')}
        result['record_before']=record
        # A background Windows service can inherit an output pipe even after
        # its launcher exits. Use a file, so communicate() cannot wait forever
        # for the live service to close an inherited pipe handle.
        with (out/'restart_console.log').open('w',encoding='utf-8') as log:
            process=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/restart_station_v143.ps1')],
                stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=20)
        assert process.returncode==0,(out/'restart_console.log').read_text(encoding='utf-8')
        deadline=time.monotonic()+15
        while True:
            try:after=c.state();break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.1)
        assert not after['enabled'] and not after['busy'] and not after['pending_confirmation'] and not after['confirmation_journal']['error']
        assert c.records()==records and after['confirmation_journal']['history']==history
        assert images==[c.image(record,archived=True),c.image(record,mask=True,archived=True)]
        result['image_check']=checked_pixels(record,*images,boot,FIRMWARE)
        c.ok('status');status=c.state()['board_stats'];assert status['boot_id']==boot and status['version']==FIRMWARE
        result['after']={k:c.state()[k] for k in ('revision','board_stats','confirmation_journal','pending_confirmation','captures')}
        assert result['after']['captures']==0,'Restart made a new capture while paused'
        # Restore the already moving player and preview reception.
        c.ok('recipe',value='mvtec_hdmi_weak_v124');c.ok('wire_mode',value='packed');c.ok('preview_rate',value=2)
        c.ok('start');wait_for(c,lambda s:s['captures']>=2 and s['enabled'] and not s['error'])
        assert c.records()==records and c.state()['confirmation_journal']['history']==history
        assert all(sha(ROOT/n)==d for n,d in result['source_sha256'].items())
        result.update(passed=True,record_count=1,completion_history_count=1,archive_bytes_identical=True,
            unchanged_board_boot=True,no_extra_capture_while_paused=True,final_enabled=True)
    except Exception:result['error']=traceback.format_exc();raise
    finally:write(out/'summary.json',result)
    print(json.dumps(dict(passed=True,record_count=1,completion_history_count=1,unchanged_board_boot=True)))
if __name__=='__main__':main()

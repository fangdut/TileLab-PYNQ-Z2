"""Actual board capture; hold the real archive SQLite writer while testing Pause."""
from pathlib import Path
import json,sqlite3,time,traceback,urllib.error,urllib.request
from board_v144_helpers import Client,ROOT,sha,write,wait_for,adopted,checked_pixels,save_evidence,programmed_proof,FIRMWARE,ERRORS
def main():
    out=ROOT/'reports/v144/save_pause_board';out.mkdir(parents=True,exist_ok=False)
    names=['scripts/board_v144_save_pause.py','scripts/board_v144_helpers.py','host/workstation.py','host/confirmation_journal.py','host/storage_policy.py']
    c=Client('http://127.0.0.1:8770');result=dict(passed=False,source_sha256={n:sha(ROOT/n) for n in names},programming=programmed_proof(),
        scope='Real FPGA image, actual Station HTTP and deliberate independent SQLite writer contention; no disk-failure or power-loss claim')
    blocker=None;boot=result['programming']['record']['boot_id']
    try:
        s=c.state();assert not s['enabled'] and not s['busy'] and s['captures']==0 and s['frame'] is None
        assert s['storage']['mode']=='preview' and not c.records(),'Requires freshly activated empty host archive'
        c.ok('recipe',value='mvtec_hdmi_weak_v124');c.ok('wire_mode',value='packed');c.ok('status')
        request=c.ok('display',value='real_video')['response']['request_id']
        wait_for(c,lambda v:adopted(v,'real_video',request));before=c.state();result['before']=before['board_stats']
        assert result['before']['boot_id']==boot and result['before']['version']==FIRMWARE
        blocker=sqlite3.connect(ROOT/'review_records/inspection.sqlite3',timeout=1)
        blocker.execute('BEGIN IMMEDIATE');held=time.monotonic()
        c.ok('capture')
        # With no previous image, publication proves this admitted capture has
        # returned. The same control-lock section sets SAVE before exposing it.
        # No /api/state reads here: archive reads can wait for the writer.
        deadline=time.monotonic()+2
        while True:
            try:
                with urllib.request.urlopen('http://127.0.0.1:8770/api/image',timeout=1) as response:image_during_save=response.read()
                break
            except urllib.error.HTTPError as error:
                if error.code!=404:raise
                if time.monotonic()>deadline:raise TimeoutError('Capture image not published while writer held')
                time.sleep(.02)
        busy=c.action('status');assert busy['status']==400 and 'current transfer' in busy['response']['error'],busy
        pause=c.ok('pause');assert pause['milliseconds']<1000,pause
        assert blocker.in_transaction and blocker.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0
        result['pause_while_writer_reserved']=pause;result['busy_diagnostic_rejected']=busy
        result['writer_held_seconds']=time.monotonic()-held
        blocker.rollback();blocker.close();blocker=None
        final=wait_for(c,lambda v:v['captures']==1 and not v['busy'] and not v['pending_operation'] and not v['pending_confirmation'])
        assert not final['enabled'] and not final['error']
        records=c.records();assert len(records)==1 and records[0]['reason']=='manual'
        frame=records[0];original,mask=c.image(frame,archived=True),c.image(frame,mask=True,archived=True)
        assert original==image_during_save
        check=checked_pixels(frame,original,mask,boot,FIRMWARE)
        result['saved_evidence']=save_evidence(out,'manual_after_pause',frame,original,mask,check)
        history=final['confirmation_journal']['history'];assert len(history)==1 and history[0]['frame']['event_id']==frame['event_id']
        result['after']=final['board_stats'];result['history']=history
        result['error_deltas']={k:(result['after'][k]-result['before'][k])&0xffffffff for k in ERRORS}
        assert not any(result['error_deltas'].values())
        time.sleep(.15);assert c.state()['captures']==1 and not c.state()['enabled']
        assert all(sha(ROOT/n)==d for n,d in result['source_sha256'].items())
        result.update(passed=True,one_admitted_frame_saved=True,final_paused=True,no_extra_capture=True,
            post_commit_confirmation=True,limits='No claim of an overall storage completion deadline; archive list reads may still wait')
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        if blocker:blocker.rollback();blocker.close()
        write(out/'summary.json',result)
    print(json.dumps(dict(passed=True,pause_ms=result['pause_while_writer_reserved']['milliseconds'],writer_held_seconds=result['writer_held_seconds'],error_deltas=result['error_deltas'])))
if __name__=='__main__':main()

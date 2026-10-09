"""Bounded physical capture while the real archive writer is deliberately busy."""
from pathlib import Path
import json,sqlite3,time,traceback,urllib.error,urllib.request
from board_v145_helpers import Client,ROOT,sha,write,wait_for,adopted,checked_pixels,save_evidence,programmed_proof,FIRMWARE,ERRORS

def read(path):
    started=time.monotonic()
    try:response=urllib.request.urlopen('http://127.0.0.1:8770'+path,timeout=1)
    except urllib.error.HTTPError as error:response=error
    with response:body=json.load(response);code=response.status
    elapsed=(time.monotonic()-started)*1000
    return dict(status=code,milliseconds=elapsed,response=body)

def main():
    out=ROOT/'reports/v145/live_state_board';out.mkdir(parents=True,exist_ok=False)
    names=['scripts/board_v145_live_state.py','scripts/board_v145_helpers.py','host/workstation.py','host/status_channel.js','host/workstation.html']
    c=Client('http://127.0.0.1:8770');result=dict(passed=False,source_sha256={n:sha(ROOT/n) for n in names},programming=programmed_proof(),
        scope='Real FPGA manual capture and actual SQLite writer contention; HTTP interface validation, no human monitor observation',live_observations=[],archive_observations=[])
    blocker=None;boot=result['programming']['record']['boot_id']
    try:
        s=c.state();assert not s['enabled'] and not s['busy'] and s['captures']==0 and s['frame'] is None
        assert s['storage']['mode']=='preview' and not c.records(),'Requires freshly activated empty host archive'
        c.ok('recipe',value='mvtec_hdmi_weak_v124');c.ok('wire_mode',value='packed');c.ok('status')
        request=c.ok('display',value='real_video')['response']['request_id'];wait_for(c,lambda v:adopted(v,'real_video',request))
        result['before']=c.state()['board_stats'];assert result['before']['boot_id']==boot and result['before']['version']==FIRMWARE
        blocker=sqlite3.connect(ROOT/'review_records/inspection.sqlite3',timeout=1);blocker.execute('BEGIN IMMEDIATE');held=time.monotonic()
        c.ok('capture');deadline=time.monotonic()+2
        while True:
            observed=read('/api/live');assert observed['status']==200
            if observed['response']['capture_control']['phase']=='SAVE':break
            if time.monotonic()>deadline:raise TimeoutError('Frame did not reach SAVE while external writer held')
            time.sleep(.02)
        result['live_observations'].append(observed)
        pause=c.ok('pause');assert pause['milliseconds']<1000;result['pause_while_writer_reserved']=pause
        for i in range(8):
            live=read('/api/live');archive=read('/api/archive?limit=2')
            assert live['status']==200 and live['milliseconds']<1000
            value=live['response'];assert not value['enabled'] and value['busy'] and value['capture_control']['phase']=='SAVE'
            assert not value['pending_confirmation'] and value['captures']==1
            assert archive['status']==503 and archive['response']['code']=='ARCHIVE_BUSY' and archive['milliseconds']<1000
            assert blocker.in_transaction and blocker.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0
            result['live_observations'].append(live);result['archive_observations'].append(archive)
            time.sleep(.03)
        result['writer_held_seconds']=time.monotonic()-held;blocker.rollback();blocker.close();blocker=None
        final=wait_for(c,lambda v:not v['busy'] and not v['pending_operation'] and not v['pending_confirmation'])
        assert not final['enabled'] and not final['error'];records=c.records();assert len(records)==1
        f=records[0];assert f['reason']=='manual';original,mask=c.image(f,archived=True),c.image(f,mask=True,archived=True)
        check=checked_pixels(f,original,mask,boot,FIRMWARE);result['saved_evidence']=save_evidence(out,'after_busy_archive',f,original,mask,check)
        result['after_archive']=read('/api/archive?limit=2');assert result['after_archive']['status']==200
        assert result['after_archive']['response']['records'][0]['id']==f['id']
        history=final['confirmation_journal']['history'];assert len(history)==1 and history[0]['frame']['event_id']==f['event_id']
        result['after']=final['board_stats'];result['history']=history
        result['error_deltas']={k:(result['after'][k]-result['before'][k])&0xffffffff for k in ERRORS};assert not any(result['error_deltas'].values())
        time.sleep(.15);assert c.state()['captures']==1 and not c.state()['enabled']
        assert all(sha(ROOT/n)==d for n,d in result['source_sha256'].items())
        result.update(passed=True,one_admitted_frame_saved=True,post_commit_confirmation=True,no_extra_capture=True,final_paused=True,
            live_max_ms=max(v['milliseconds'] for v in result['live_observations']),limits='Bounded contention experiment, not a hard real-time latency guarantee')
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        if blocker:blocker.rollback();blocker.close()
        write(out/'summary.json',result)
    print(json.dumps({k:result[k] for k in ('passed','live_max_ms','writer_held_seconds','error_deltas')}))
if __name__=='__main__':main()

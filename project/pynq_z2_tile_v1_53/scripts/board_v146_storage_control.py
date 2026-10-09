"""Actual Station on the verified board boot: storage setting with a held DB writer."""
from pathlib import Path
import json,sqlite3,threading,time,traceback,urllib.request
from board_v146_helpers import Client,ROOT,sha,write,programmed_proof,FIRMWARE,ERRORS

def live():
    t=time.monotonic()
    with urllib.request.urlopen('http://127.0.0.1:8770/api/live',timeout=1) as response:value=json.load(response)
    return dict(milliseconds=(time.monotonic()-t)*1000,response=value)

def main():
    out=ROOT/'reports/v146/storage_control_board';out.mkdir(parents=True,exist_ok=False)
    names=['scripts/board_v146_storage_control.py','scripts/board_v146_helpers.py','host/workstation.py','host/workstation.html','host/storage_policy.py','host/storage_policy.json']
    result=dict(passed=False,programming=programmed_proof(),source_sha256={n:sha(ROOT/n) for n in names},live_observations=[],actions=[],
        scope='Actual board-connected Station and independent SQLite writer contention; no image capture intended during configuration')
    c=Client('http://127.0.0.1:8770');blocker=None;thread=None;setting=[];restore=False
    try:
        s=c.state();assert not s['enabled'] and not s['busy'] and s['storage']['mode']=='preview' and s['captures']==0
        before=c.ok('status')['response'];assert before['boot_id']==result['programming']['record']['boot_id'] and before['version']==FIRMWARE
        result['before']=before
        blocker=sqlite3.connect(ROOT/'review_records/inspection.sqlite3',timeout=1);blocker.execute('BEGIN IMMEDIATE');held=time.monotonic()
        def configure():
            try:setting.append(c.action('storage',mode='archive',max_archive_mib=32))
            except Exception as e:setting.append(dict(error=repr(e)))
        thread=threading.Thread(target=configure);thread.start();deadline=time.monotonic()+2
        while True:
            value=live()
            if value['response']['capture_control']['phase']=='STORAGE':break
            if time.monotonic()>deadline:raise TimeoutError('STORAGE reservation did not become visible')
            time.sleep(.02)
        result['live_observations'].append(value)
        for op in ('pause','start','pause'):
            r=c.ok(op);assert r['milliseconds']<1000;result['actions'].append(r)
            for i in range(3):
                v=live();s=v['response'];assert v['milliseconds']<1000 and s['busy'] and s['capture_control']['phase']=='STORAGE'
                assert s['storage']['mode']=='preview' and s['storage']['max_archive_mib']==1024
                assert s['captures']==0 and s['enabled']==(op=='start');result['live_observations'].append(v);time.sleep(.03)
        for op,args in [('capture',{}),('status',{}),('storage',dict(mode='preview',max_archive_mib=16))]:
            r=c.action(op,**args);assert r['status']==400 and r['milliseconds']<1000;result['actions'].append(r)
        assert not setting and blocker.in_transaction;result['writer_held_seconds']=time.monotonic()-held
        blocker.rollback();blocker.close();blocker=None;thread.join(5);assert not thread.is_alive()
        assert len(setting)==1 and setting[0]['status']==200;restore=True;result['configuration_result']=setting[0]
        s=c.state();assert not s['enabled'] and not s['busy'] and s['captures']==0 and s['storage']['mode']=='archive' and s['storage']['max_archive_mib']==32
        stored=json.loads((ROOT/'host/storage_policy.json').read_text());assert stored==dict(mode='archive',max_archive_mib=32);result['committed_policy']=stored
        c.ok('storage',mode='preview',max_archive_mib=1024);restore=False
        after=c.ok('status')['response'];result['after']=after;result['error_deltas']={k:(after[k]-before[k])&0xffffffff for k in ERRORS}
        assert not any(result['error_deltas'].values());assert not c.records()
        assert all(sha(ROOT/n)==h for n,h in result['source_sha256'].items())
        result.update(passed=True,final_paused=True,policy_restored_exactly=True,no_capture_before_commit=True,no_capture_after_final_pause=True,
            live_max_ms=max(v['milliseconds'] for v in result['live_observations']))
    except Exception:result['error']=traceback.format_exc();raise
    finally:
        if blocker:blocker.rollback();blocker.close()
        if thread and thread.is_alive():thread.join(6)
        if restore:
            try:c.ok('storage',mode='preview',max_archive_mib=1024)
            except Exception:result['restore_error']=traceback.format_exc()
        write(out/'summary.json',result)
    print(json.dumps({k:result[k] for k in ('passed','writer_held_seconds','live_max_ms','error_deltas')}))
if __name__=='__main__':main()

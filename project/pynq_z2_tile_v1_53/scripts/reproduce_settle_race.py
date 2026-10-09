"""Negative baseline only: actual journal, two SQLite connections, isolated DB."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sqlite3,sys,threading,traceback
R=Path(__file__).resolve().parents[1];O=R/'reports/v143/settle_baseline'
sys.path.insert(0,str(R/'host'))
from confirmation_journal import ConfirmationJournal
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert R.name=='pynq_z2_tile_v1_53'
    O.mkdir(parents=True,exist_ok=False)
    source=R/'host/confirmation_journal.py';baseline=R.parent/'pynq_z2_tile_v1_42/host/confirmation_journal.py'
    before=sha(source);assert before==sha(baseline)
    result=dict(passed=False,negative_baseline_reproduced=False,started_at=datetime.now(timezone.utc).isoformat(),
        scope='Actual unmodified ConfirmationJournal, two independent SQLite connections; synthetic pending records; no board/network or production archive',
        source_sha256={'host/confirmation_journal.py':before,'scripts/reproduce_settle_race.py':sha(Path(__file__))})
    a=sqlite3.connect(O/'isolated.sqlite3',check_same_thread=False);b=sqlite3.connect(O/'isolated.sqlite3',check_same_thread=False)
    for db in (a,b):db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
    ja=ConfirmationJournal(a,threading.RLock(),O);jb=ConfirmationJournal(b,threading.RLock(),O)
    first=dict(boot_id=7,event_id=1,frame_id=101,product_id=3,pixel_crc32=11,recovery_generation=0)
    second=dict(first,event_id=2,frame_id=102,product_id=4,pixel_crc32=12)
    a.execute('BEGIN IMMEDIATE');ja.prepare('event_one',first,'tcp://fixture:9133');a.commit()
    read=threading.Event();release=threading.Event();outcome={}
    class Cursor:
        def __init__(self,actual):self.actual=actual
        def fetchone(self):
            value=self.actual.fetchone();self.actual.close();read.set()
            if not release.wait(8):raise TimeoutError('Baseline schedule not released')
            return value
    class Connection:
        def execute(self,sql,*args):
            cursor=a.execute(sql,*args)
            return Cursor(cursor) if sql=='SELECT payload FROM pending_confirmation WHERE id=1' else cursor
        def __getattr__(self,name):return getattr(a,name)
    ja.db=Connection()
    def old_settle():
        try:ja.settle(first,'ACKNOWLEDGED',7);outcome['completed']=True
        except Exception:outcome['error']=traceback.format_exc()
    thread=threading.Thread(target=old_settle,daemon=True)
    try:
        thread.start();assert read.wait(3),'Old SELECT not reached'
        jb.settle(first,'ACKNOWLEDGED',7)
        b.execute('BEGIN IMMEDIATE');jb.prepare('event_two',second,'tcp://fixture:9133');b.commit()
        pending=json.loads(b.execute('SELECT payload FROM pending_confirmation').fetchone()[0])
        assert pending['frame']['event_id']==2
        result['new_pending_before_old_settlement']=pending
        release.set();thread.join(4);assert not thread.is_alive() and outcome=={'completed':True},outcome
        after=b.execute('SELECT payload FROM pending_confirmation').fetchone()
        history=[json.loads(row[0]) for row in b.execute('SELECT payload FROM confirmation_history ORDER BY id')]
        assert after is None and len(history)==2 and all(row['frame']['event_id']==1 for row in history)
        result.update(passed=True,negative_baseline_reproduced=True,new_pending_after_old_settlement=None,
                      settled_event_ids=[row['frame']['event_id'] for row in history],
                      conclusion='Old settlement deleted newer event2 pending record and duplicated event1 completion history')
    finally:
        release.set();thread.join(4)
        assert not thread.is_alive()
        a.close();b.close();result['source_unchanged']=sha(source)==before
        assert result['source_unchanged']
        result['database_sha256']=sha(O/'isolated.sqlite3')
        (O/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

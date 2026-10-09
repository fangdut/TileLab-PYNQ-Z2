"""Kill a real Python/SQLite writer at transaction boundaries, then retry."""
from pathlib import Path
import argparse,hashlib,json,os,sqlite3,subprocess,sys,threading
R=Path(__file__).resolve().parents[1];O=R/'reports/v143/settle_process'
sys.path.insert(0,str(R/'host'))
from confirmation_journal import ConfirmationJournal
FRAME=dict(boot_id=7,event_id=1,frame_id=101,product_id=3,pixel_crc32=11,recovery_generation=0)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def crash(marker,phase,transaction):
    with marker.open('w',encoding='utf-8') as stream:
        json.dump(dict(phase=phase,in_transaction=transaction,pid=os.getpid()),stream);stream.flush();os.fsync(stream.fileno())
    os._exit(73)
def worker(db_path,phase,marker):
    db=sqlite3.connect(db_path);journal=ConfirmationJournal(db,threading.RLock(),db_path.parent)
    class Proxy:
        def __getattr__(self,name):return getattr(db,name)
        def execute(self,sql,*args):
            cursor=db.execute(sql,*args)
            if phase=='after_read' and sql=='SELECT payload FROM pending_confirmation WHERE id=1':
                class Cursor:
                    def fetchone(self):
                        row=cursor.fetchone();cursor.close();crash(marker,phase,db.in_transaction);return row
                return Cursor()
            if (phase=='after_insert' and sql.startswith('INSERT INTO confirmation_history')) or (phase=='after_delete' and sql=='DELETE FROM pending_confirmation WHERE id=1'):
                crash(marker,phase,db.in_transaction)
            return cursor
        def commit(self):
            db.commit()
            if phase=='after_commit':crash(marker,phase,db.in_transaction)
    journal.db=Proxy();journal.settle(FRAME,'ACKNOWLEDGED',7)
    raise AssertionError('Crash hook not reached')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path);parser.add_argument('--phase');parser.add_argument('--marker',type=Path);args=parser.parse_args()
    if args.worker:worker(args.worker,args.phase,args.marker);return
    O.mkdir(parents=True,exist_ok=False)
    source={n:sha(R/n) for n in ('host/confirmation_journal.py','scripts/test_settle_crash_process.py')}
    result=dict(passed=False,source_sha256=source,scope='Abrupt process exit and actual SQLite WAL recovery; no physical power-loss or board test',cases=[])
    try:
        for phase in ('after_read','after_insert','after_delete','after_commit'):
            path=O/(phase+'.sqlite3');marker=O/(phase+'.json')
            db=sqlite3.connect(path);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
            journal=ConfirmationJournal(db,threading.RLock(),O)
            db.execute('BEGIN IMMEDIATE');journal.prepare('event_one',FRAME,'tcp://fixture:9133');db.commit();db.close()
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),'--worker',str(path),'--phase',phase,'--marker',str(marker)],capture_output=True,text=True,timeout=10)
            assert p.returncode==73,(phase,p.returncode,p.stdout,p.stderr)
            boundary=json.loads(marker.read_text());assert boundary['in_transaction']==(phase!='after_commit')
            db=sqlite3.connect(path);journal=ConfirmationJournal(db,threading.RLock(),O)
            pending=db.execute('SELECT COUNT(*) FROM pending_confirmation').fetchone()[0]
            history=len(journal.history());assert (pending,history)==((0,1) if phase=='after_commit' else (1,0)),(phase,pending,history)
            journal.settle(FRAME,'ALREADY_ACKNOWLEDGED',7)
            assert len(journal.history())==1 and db.execute('SELECT COUNT(*) FROM pending_confirmation').fetchone()[0]==0
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.in_transaction
            db.close()
            result['cases'].append(dict(phase=phase,exit_code=p.returncode,pending_after_restart=pending,history_after_restart=history,retry_history_count=1,passed=True,boundary=boundary,database_sha256=sha(path)))
        assert source=={n:sha(R/n) for n in source}
        result['passed']=True;result['source_unchanged']=True
    finally:(O/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,cases=len(result['cases']))))
if __name__=='__main__':main()

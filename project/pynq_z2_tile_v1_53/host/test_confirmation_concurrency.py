"""Independent SQLite writers must never settle a replacement pending event."""
import json,os,sqlite3,tempfile,threading,unittest
from pathlib import Path
from confirmation_journal import ConfirmationJournal

class ConnectionProxy:
    def __init__(self,db,after_read=None,fail_sql=None,fail_commit=False):
        self.db=db;self.after_read=after_read;self.fail_sql=fail_sql;self.fail_commit=fail_commit
    def __getattr__(self,name):return getattr(self.db,name)
    def execute(self,sql,*args):
        if self.fail_sql and sql.startswith(self.fail_sql):raise sqlite3.OperationalError('Injected journal SQL failure')
        cursor=self.db.execute(sql,*args)
        if sql=='SELECT payload FROM pending_confirmation WHERE id=1' and self.after_read:
            callback=self.after_read
            class Cursor:
                def fetchone(self):
                    row=cursor.fetchone();cursor.close();callback();return row
            return Cursor()
        return cursor
    def commit(self):
        if self.fail_commit:raise sqlite3.OperationalError('Injected commit failure')
        return self.db.commit()

class ConfirmationConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='tile_confirmation_v143_');self.root=Path(self.temp.name)
        self.a=sqlite3.connect(self.root/'journal.sqlite3',check_same_thread=False)
        self.b=sqlite3.connect(self.root/'journal.sqlite3',check_same_thread=False)
        for db in (self.a,self.b):db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        self.ja=ConfirmationJournal(self.a,threading.RLock(),self.root)
        self.jb=ConfirmationJournal(self.b,threading.RLock(),self.root)
        self.first=dict(boot_id=7,event_id=1,frame_id=101,product_id=3,pixel_crc32=11,recovery_generation=0)
        self.second=dict(self.first,event_id=2,frame_id=102,product_id=4,pixel_crc32=12)
        self.prepare(self.ja,self.first)
    def tearDown(self):self.a.close();self.b.close();self.temp.cleanup()
    def prepare(self,journal,frame):
        journal.db.execute('BEGIN IMMEDIATE')
        try:journal.prepare('event_'+str(frame['event_id']),frame,'tcp://fixture:9133');journal.db.commit()
        except Exception:journal.db.rollback();raise
    def pending_id(self):
        row=self.b.execute('SELECT payload FROM pending_confirmation').fetchone()
        return json.loads(row[0])['frame']['event_id'] if row else None
    def history_ids(self):return [row['frame']['event_id'] for row in self.jb.history()]
    def released(self):
        self.assertFalse(self.a.in_transaction)
        self.b.execute('BEGIN IMMEDIATE');self.b.rollback()
    def test_old_settlement_cannot_delete_new_pending_across_connections(self):
        entered=threading.Event();release=threading.Event();attempted=threading.Event();finished=threading.Event();errors=[]
        def after_read():
            entered.set()
            if not release.wait(5):raise TimeoutError('Writer fixture not released')
        self.ja.db=ConnectionProxy(self.a,after_read=after_read)
        self.b.set_trace_callback(lambda sql:attempted.set() if sql=='BEGIN IMMEDIATE' else None)
        def first():
            try:self.ja.settle(self.first,'ACKNOWLEDGED',7)
            except Exception as error:errors.append(error)
        def second():
            try:self.jb.settle(self.first,'ALREADY_ACKNOWLEDGED',7);self.prepare(self.jb,self.second)
            except Exception as error:errors.append(error)
            finally:finished.set()
        one=threading.Thread(target=first);two=threading.Thread(target=second)
        try:
            one.start();self.assertTrue(entered.wait(3));two.start();self.assertTrue(attempted.wait(3))
            self.assertFalse(finished.wait(.08),'Another writer replaced the pending row during settlement')
        finally:
            release.set();one.join(6)
            if two.ident is not None:two.join(6)
            self.b.set_trace_callback(None)
        self.assertFalse(one.is_alive() or two.is_alive());self.assertEqual(errors,[])
        self.assertEqual(self.pending_id(),2);self.assertEqual(self.history_ids(),[1]);self.released()
    def test_stale_settlement_after_replacement_keeps_new_event(self):
        self.jb.settle(self.first,'ACKNOWLEDGED',7);self.prepare(self.jb,self.second)
        with self.assertRaisesRegex(ValueError,'different confirmation'):self.ja.settle(self.first,'ACKNOWLEDGED',7)
        self.assertEqual(self.pending_id(),2);self.assertEqual(self.history_ids(),[1]);self.released()
    def test_duplicate_completion_is_idempotent_and_unlocks(self):
        self.ja.settle(self.first,'ACKNOWLEDGED',7);self.jb.settle(self.first,'ALREADY_ACKNOWLEDGED',7)
        self.assertIsNone(self.pending_id());self.assertEqual(self.history_ids(),[1]);self.released()
    def test_identity_and_generation_errors_release_writer(self):
        for wrong in (dict(self.first,boot_id=8),dict(self.first,event_id=2),dict(self.first,recovery_generation=1)):
            with self.subTest(wrong=wrong),self.assertRaises(ValueError):self.ja.settle(wrong,'ACKNOWLEDGED')
            self.assertEqual(self.pending_id(),1);self.assertEqual(self.history_ids(),[]);self.released()
    def test_sql_and_commit_failure_roll_back_history_and_pending_together(self):
        for point in ('INSERT INTO confirmation_history','DELETE FROM pending_confirmation','DELETE FROM confirmation_history','commit'):
            with self.subTest(point=point):
                self.ja.db=ConnectionProxy(self.a,fail_sql=None if point=='commit' else point,fail_commit=point=='commit')
                with self.assertRaises(sqlite3.OperationalError):self.ja.settle(self.first,'ACKNOWLEDGED',7)
                self.assertEqual(self.pending_id(),1);self.assertEqual(self.history_ids(),[]);self.released()
        self.ja.db=self.a;self.ja.settle(self.first,'ACKNOWLEDGED',7);self.assertEqual(self.history_ids(),[1])
    def test_busy_writer_timeout_keeps_pending_for_retry(self):
        self.a.execute('PRAGMA busy_timeout=20');self.b.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(sqlite3.OperationalError):self.ja.settle(self.first,'ACKNOWLEDGED',7)
            self.assertFalse(self.a.in_transaction)
        finally:self.b.rollback()
        self.assertEqual(self.pending_id(),1);self.assertEqual(self.history_ids(),[])
        self.ja.settle(self.first,'ACKNOWLEDGED',7);self.released()
    def test_existing_caller_transaction_is_not_committed_or_rolled_back(self):
        self.a.execute('CREATE TABLE caller_work(value INTEGER)');self.a.commit()
        self.a.execute('INSERT INTO caller_work VALUES(9)')
        with self.assertRaisesRegex(RuntimeError,'existing transaction'):self.ja.settle(self.first,'ACKNOWLEDGED',7)
        self.assertTrue(self.a.in_transaction);self.assertEqual(self.a.execute('SELECT value FROM caller_work').fetchall(),[(9,)])
        self.a.rollback();self.assertEqual(self.pending_id(),1);self.assertEqual(self.history_ids(),[]);self.released()

if __name__=='__main__':unittest.main(verbosity=2)

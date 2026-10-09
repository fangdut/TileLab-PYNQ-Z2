"""Two independent SQLite connections must not publish conflicting evidence.

All fixtures live in temporary directories; no board or station is contacted.
The first writer pauses immediately before publishing its first PNG, while a
second connection attempts the same transaction. This was an unsafe gap in
V1.32: the loser could overwrite the winner's files before its INSERT failed.
"""
import multiprocessing
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import workstation
from workstation import Records, png
from storage_policy import ArchiveCapacityError


def competing_process(directory,frame,image,mask,ready,go,attempted,finished,output):
    """Spawn-compatible writer with an independent interpreter/connection."""
    record=Records(directory)
    try:
        record.db.set_trace_callback(lambda sql:attempted.set() if sql.startswith('BEGIN IMMEDIATE') else None)
        ready.set()
        if not go.wait(10):raise TimeoutError('Test did not start child writer')
        try:output.put(dict(key=record.save(frame,image,mask,'isolated_process_test')))
        except Exception as error:output.put(dict(error=type(error).__name__,message=str(error)))
    finally:record.db.close();finished.set()


class ArchiveConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_archive_concurrency_')
        self.root=Path(self.tmp.name)
        self.a=Records(self.root);self.b=Records(self.root)
        self.frame=dict(boot_id=17,event_id=90,frame_id=73,product_id=4,
                        candidate_pixels=12,boxes=[[2,3,5,6]],region_areas=[12],
                        config_word=90,recovery_generation=1)
        self.image=png(np.full((16,24,3),100,np.uint8))
        self.mask=png(np.zeros((16,24),np.uint8))
    def tearDown(self):
        self.a.db.close();self.b.db.close();self.tmp.cleanup()
    def contend(self,second_frame=None,second_image=None,second_mask=None):
        """Return outcomes after both connections have attempted publication."""
        first_entered=threading.Event();second_attempted=threading.Event()
        release=threading.Event();second_finished=threading.Event()
        results={};writes=[];real_atomic=workstation.atomic
        def guarded_atomic(path,data):
            name=threading.current_thread().name
            writes.append((name,path.name))
            if name=='archive-first' and path.name=='pl_17_90.png':
                first_entered.set()
                if not release.wait(5):raise TimeoutError('Test did not release first writer')
            return real_atomic(path,data)
        def trace(sql):
            if sql.startswith(('BEGIN IMMEDIATE','SELECT payload FROM events')):
                second_attempted.set()
        def save(which,record,frame,image,mask):
            try:results[which]=record.save(frame,image,mask,'isolated_concurrency_test')
            except Exception as error:results[which]=error
            finally:
                if which=='second':second_finished.set()
        self.b.db.set_trace_callback(trace)
        first=threading.Thread(target=save,name='archive-first',args=('first',self.a,self.frame,self.image,self.mask))
        second=threading.Thread(target=save,name='archive-second',args=(
            'second',self.b,second_frame or self.frame,
            self.image if second_image is None else second_image,
            self.mask if second_mask is None else second_mask))
        with patch('workstation.atomic',side_effect=guarded_atomic):
            try:
                first.start();self.assertTrue(first_entered.wait(5))
                second.start();self.assertTrue(second_attempted.wait(5))
                # This is the actual filesystem race boundary, not an ordering
                # assumption based on which thread happened to start first.
                self.assertFalse(second_finished.wait(.05))
                self.assertEqual([name for name,_ in writes],['archive-first'])
            finally:
                release.set();first.join(6)
                if second.ident is not None:second.join(6)
                self.b.db.set_trace_callback(None)
        self.assertFalse(first.is_alive());self.assertFalse(second.is_alive())
        self.assertEqual(results['first'],'pl_17_90')
        self.assertFalse(self.a.db.in_transaction);self.assertFalse(self.b.db.in_transaction)
        return results,writes
    def assert_original(self):
        row=self.a.get('pl_17_90')
        self.assertEqual(row['frame_id'],73)
        self.assertEqual(self.a.read_image(row['id'])[0],self.image)
        self.assertEqual(self.a.read_image(row['id'],True)[0],self.mask)
        self.assertEqual(self.a.summary()['total'],1)
    def test_same_key_different_decisions_never_replaces_committed_pixels(self):
        results,writes=self.contend(dict(self.frame,frame_id=74))
        self.assertIsInstance(results['second'],ValueError)
        self.assertIn('different FPGA decisions',str(results['second']))
        self.assertEqual(len(writes),2);self.assert_original()
    def test_same_key_different_pixels_never_replaces_committed_pixels(self):
        changed=png(np.full((16,24,3),200,np.uint8))
        results,writes=self.contend(second_image=changed)
        self.assertIsInstance(results['second'],ValueError)
        self.assertIn('different pixels',str(results['second']))
        self.assertEqual(len(writes),2);self.assert_original()
    def test_same_key_different_mask_never_replaces_committed_mask(self):
        changed=png(np.full((16,24),255,np.uint8))
        results,writes=self.contend(second_mask=changed)
        self.assertIsInstance(results['second'],ValueError)
        self.assertIn('different pixels',str(results['second']))
        self.assertEqual(len(writes),2);self.assert_original()
    def test_same_key_same_contents_is_idempotent_and_releases_transaction(self):
        results,writes=self.contend()
        self.assertEqual(results['second'],'pl_17_90')
        self.assertEqual(len(writes),2);self.assert_original()
        self.a.update('pl_17_90','needs_recheck','Keep existing human conclusion')
        self.b.save(self.frame,self.image,self.mask,'manual')
        self.assertEqual(self.b.get('pl_17_90')['note'],'Keep existing human conclusion')
        self.assertEqual(self.b.get('pl_17_90')['review_revision'],1)
        self.assertFalse(self.b.db.in_transaction)
    def test_distinct_keys_cannot_spend_the_same_remaining_quota(self):
        rng=np.random.default_rng(133)
        self.image=png(rng.integers(0,256,(256,256,3),dtype=np.uint8))
        self.mask=png(rng.integers(0,2,(256,256),dtype=np.uint8)*255)
        # Both pre-existing connections cache zero PNG bytes. The later writer
        # must refresh that cache after the first SQLite commit, inside BEGIN.
        self.assertEqual(self.a.image_bytes,0);self.assertEqual(self.b.image_bytes,0)
        limit=self.a.storage()['used_bytes']+len(self.image)+len(self.mask)+65536+16384
        self.a.max_archive_bytes=limit;self.b.max_archive_bytes=limit
        results,writes=self.contend(dict(self.frame,event_id=91,frame_id=74))
        self.assertIsInstance(results['second'],ArchiveCapacityError)
        self.assertEqual(len(writes),2);self.assert_original()
        self.assertEqual(self.b.storage()['image_bytes'],len(self.image)+len(self.mask))
        self.assertFalse((self.a.dir/'pl_17_91.png').exists())
    def test_each_save_failure_releases_writer_for_another_connection(self):
        # Exercise errors before publication, during publication, and during
        # confirmation preparation. File orphan recovery is a separate feature.
        for phase in ('quota','png','confirmation'):
            with self.subTest(phase=phase):
                self.a.max_archive_bytes=1 if phase=='quota' else 1024**3
                if phase=='png':guard=patch('workstation.atomic',side_effect=OSError('Injected PNG write failure'))
                elif phase=='confirmation':guard=patch.object(self.a.confirmations,'prepare',side_effect=OSError('Injected confirmation write failure'))
                else:guard=patch('workstation.stamp',wraps=workstation.stamp)
                with guard:
                    with self.assertRaises((ArchiveCapacityError,OSError)):
                        self.a.save(self.frame,self.image,self.mask,'test',confirmation_endpoint='tcp://fixture')
                self.assertFalse(self.a.db.in_transaction)
                self.assertEqual(self.a.summary()['total'],0)
                self.assertIsNone(self.a.confirmations.pending())
                self.b.db.execute('PRAGMA busy_timeout=50')
                self.b.db.execute('BEGIN IMMEDIATE');self.b.db.rollback()
    def test_busy_reservation_writes_no_files_and_retry_preserves_identity(self):
        self.a.db.execute('BEGIN IMMEDIATE')
        self.b.db.execute('PRAGMA busy_timeout=50')
        with self.assertRaises(sqlite3.OperationalError):
            self.b.save(self.frame,self.image,self.mask,'test')
        self.assertFalse(self.b.db.in_transaction)
        self.assertEqual(list(self.b.dir.glob('*.png')),[])
        self.a.db.rollback()
        self.b.save(self.frame,self.image,self.mask,'test');self.assert_original()
    def test_commit_failure_rolls_back_rows_and_pending_ack_and_releases_writer(self):
        connection=self.a.db
        class FailCommit:
            def __getattr__(self,name):return getattr(connection,name)
            def commit(self):raise sqlite3.OperationalError('Injected commit failure')
        self.a.db=FailCommit()
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError,'Injected commit'):
                self.a.save(self.frame,self.image,self.mask,'manual',confirmation_endpoint='tcp://fixture')
            self.assertFalse(connection.in_transaction)
            self.assertEqual(self.b.summary()['total'],0)
            self.assertIsNone(self.b.confirmations.pending())
            self.b.db.execute('PRAGMA busy_timeout=50')
            self.b.save(self.frame,self.image,self.mask,'manual',confirmation_endpoint='tcp://fixture')
            self.assertEqual(self.b.confirmations.pending()['record_id'],'pl_17_90')
            self.assert_original()
        finally:self.a.db=connection
    def test_separate_process_waits_then_rejects_conflicting_identity(self):
        ctx=multiprocessing.get_context('spawn')
        ready=ctx.Event();go=ctx.Event();attempted=ctx.Event();finished=ctx.Event();output=ctx.Queue()
        child=ctx.Process(target=competing_process,args=(str(self.root),dict(self.frame,frame_id=74),
            self.image,self.mask,ready,go,attempted,finished,output))
        entered=threading.Event();release=threading.Event();errors=[];real_atomic=workstation.atomic
        def gate(path,data):
            if path.name=='pl_17_90.png':
                entered.set()
                if not release.wait(10):raise TimeoutError('Did not release parent writer')
            return real_atomic(path,data)
        def parent_write():
            try:self.a.save(self.frame,self.image,self.mask,'isolated_process_test')
            except Exception as error:errors.append(error)
        writer=threading.Thread(target=parent_write)
        child.start()
        try:
            self.assertTrue(ready.wait(10))
            with patch('workstation.atomic',side_effect=gate):
                try:
                    writer.start();self.assertTrue(entered.wait(5))
                    go.set();self.assertTrue(attempted.wait(5))
                    self.assertFalse(finished.wait(.05))
                finally:release.set();writer.join(6)
            child.join(10)
            self.assertEqual(child.exitcode,0);self.assertEqual(errors,[])
            result=output.get(timeout=2)
            self.assertEqual(result['error'],'ValueError')
            self.assertIn('different FPGA decisions',result['message']);self.assert_original()
        finally:
            go.set();release.set()
            if writer.ident is not None:writer.join(6)
            if child.is_alive():child.terminate();child.join(5)
            output.close();output.join_thread()
    def test_evidence_and_pending_ack_become_visible_in_one_commit(self):
        real_prepare=self.a.confirmations.prepare;observed=[]
        def prepare(key,frame,endpoint):
            real_prepare(key,frame,endpoint)
            # A WAL reader never sees either new row before the writer commits.
            observed.append((self.b.summary()['total'],self.b.confirmations.pending()))
        with patch.object(self.a.confirmations,'prepare',side_effect=prepare):
            key=self.a.save(self.frame,self.image,self.mask,'manual',confirmation_endpoint='tcp://fixture')
        self.assertEqual(observed,[(0,None)])
        self.assertEqual(self.b.summary()['total'],1)
        self.assertEqual(self.b.confirmations.pending()['record_id'],key)
        self.assert_original();self.assertFalse(self.a.db.in_transaction)


if __name__=='__main__':unittest.main(verbosity=2)

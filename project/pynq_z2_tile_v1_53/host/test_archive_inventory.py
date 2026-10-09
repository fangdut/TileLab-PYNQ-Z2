"""Capacity snapshots include uncommitted files and never traverse links."""
import hashlib
import os
import sqlite3
import stat
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import archive_inventory
import workstation
from workstation import Records
from storage_policy import ArchiveCapacityError


def directory_link(link,target):
    if os.name=='nt':
        # Junction creation does not need the Windows symlink privilege. Both
        # paths are isolated fixtures; no cleanup ever follows this junction.
        quote=lambda value:"'"+str(value).replace("'","''")+"'"
        command='New-Item -ItemType Junction -Path '+quote(link)+' -Target '+quote(target)+' | Out-Null'
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],check=True,capture_output=True)
    else:os.symlink(target,link,target_is_directory=True)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_inventory_');self.root=Path(self.tmp.name)
        self.r=Records(self.root);self.f=dict(boot_id=1,event_id=1,frame_id=73)
    def tearDown(self):self.r.db.close();self.tmp.cleanup()
    def test_all_regular_bytes_are_counted_once_with_preserved_top_level_categories(self):
        key=self.r.save(self.f,b'image',b'mask','fixture')
        (self.r.dir/'orphan.png').write_bytes(b'orphan')
        (self.r.dir/'orphan_mask.png.tmp').write_bytes(b'partial')
        (self.r.dir/'unknown.dat').write_bytes(b'unknown')
        nested=self.r.dir/'staging'/'item';nested.mkdir(parents=True)
        (nested/'image.png').write_bytes(b'staged-image');(nested/'intent.json').write_bytes(b'{}')
        (nested/'mask.png.tmp').write_bytes(b'pending-mask')
        result=self.r.storage()
        self.assertTrue(result['scan_complete']);self.assertEqual(result['scan_issue_count'],0)
        self.assertEqual(result['image_bytes'],len(b'imagemaskorphan'))
        self.assertEqual(result['auxiliary_bytes'],len(b'partialunknownstaged-image{}pending-mask'))
        self.assertEqual(result['unindexed_png_count'],2);self.assertEqual(result['temp_file_count'],2)
        files=[p for p in self.r.dir.rglob('*') if p.is_file()]
        self.assertEqual(result['used_bytes'],sum(p.stat().st_size for p in files))
        self.assertEqual(result['file_count'],len(files))
        self.assertEqual(result['used_bytes'],sum(result[k] for k in ('image_bytes','metadata_bytes','auxiliary_bytes')))
        self.assertEqual(self.r.get(key)['frame_id'],73)
    def test_rollback_files_refresh_even_when_sqlite_data_version_does_not_change(self):
        other=Records(self.root)
        try:
            before=self.r.db.execute('PRAGMA data_version').fetchone()[0];self.r.storage()
            with patch.object(other.confirmations,'prepare',side_effect=OSError('Injected rollback')):
                with self.assertRaises(OSError):other.save(self.f,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
            self.assertEqual(self.r.db.execute('PRAGMA data_version').fetchone()[0],before)
            result=self.r.storage();self.assertEqual(result['image_bytes'],9)
            self.assertEqual(result['unindexed_png_count'],2);self.assertEqual(self.r.summary()['total'],0)
        finally:other.db.close()
    def test_auxiliary_files_spend_capacity_and_no_failed_save_ack_is_created(self):
        initial=self.r.storage()['used_bytes'];self.r.max_archive_bytes=initial+65536+100
        (self.r.dir/'pending.png.tmp').write_bytes(b'x'*200)
        with self.assertRaises(ArchiveCapacityError):
            self.r.save(self.f,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
        self.assertEqual(self.r.summary()['total'],0);self.assertIsNone(self.r.confirmations.pending())
        self.assertFalse((self.r.dir/'pl_1_1.png').exists())
    def test_inventory_failure_is_not_capacity_fallback_and_does_not_write_or_prepare_ack(self):
        real_scan=archive_inventory.os.scandir
        def denied(path):
            if Path(path)==self.r.dir:raise PermissionError('Injected enumeration failure')
            return real_scan(path)
        with patch('archive_inventory.os.scandir',side_effect=denied):
            result=self.r.storage();self.assertFalse(result['scan_complete'])
            with self.assertRaises(OSError) as caught:
                self.r.save(self.f,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
            self.assertNotIsInstance(caught.exception,ArchiveCapacityError)
        self.assertFalse(self.r.db.in_transaction);self.assertEqual(self.r.summary()['total'],0)
        self.assertIsNone(self.r.confirmations.pending());self.assertEqual(list(self.r.dir.glob('*.png')),[])
    def test_unknown_nested_directory_read_failure_is_reported_with_relative_paths(self):
        (self.r.dir/'staging').mkdir();real_scan=archive_inventory.os.scandir
        def denied(path):
            if Path(path).name=='staging':raise PermissionError('Blocked')
            return real_scan(path)
        with patch('archive_inventory.os.scandir',side_effect=denied):result=self.r.storage()
        self.assertFalse(result['scan_complete'])
        self.assertEqual(result['scan_issues'],[dict(path='staging',reason='directory_unavailable')])
    def test_worker_inventory_failure_keeps_archive_mode_evidence_and_board_event_unacked(self):
        from test_storage_policy import StorageTests
        fixture=StorageTests();station,board,frame,image,mask=fixture.setup_event(self.root)
        try:
            key=station.records.save(dict(frame,event_id=2),image,mask,'manual')
            station.records.update(key,'confirmed_crack','Keep reviewed evidence')
            before=station.records.get(key)
            station.action(dict(op='storage',mode='archive',max_archive_mib=16))
            policy_before=(self.root/'host/storage_policy.json').read_bytes()
            real_inventory=workstation.inventory
            def incomplete(*args,**kwargs):
                return dict(real_inventory(*args,**kwargs),scan_complete=False,scan_issue_count=1,
                            scan_issues=[dict(path='staging',reason='directory_unavailable')])
            with patch('workstation.inventory',side_effect=incomplete):
                station.action(dict(op='start'));deadline=time.monotonic()+4
                while (not station.error or station.busy) and time.monotonic()<deadline:time.sleep(.01)
            self.assertIn('清点未完成',station.error);self.assertFalse(station.busy);self.assertFalse(station.enabled)
            self.assertFalse(board.acked);self.assertEqual(station.storage_policy.mode,'archive')
            self.assertEqual((self.root/'host/storage_policy.json').read_bytes(),policy_before)
            self.assertEqual(station.records.summary()['total'],1);self.assertIsNone(station.records.confirmations.pending())
            self.assertEqual(station.records.get(key),before)
            self.assertEqual(station.records.read_image(key)[0],image);self.assertEqual(station.records.read_image(key,True)[0],mask)
            self.assertEqual(station.skipped_automatic,0);self.assertEqual(station.storage_warning,'')
            self.assertFalse((station.records.dir/f"pl_{frame['boot_id']}_{frame['event_id']}.png").exists())
        finally:fixture.close(station)
    def test_actual_directory_link_never_counts_or_changes_external_target(self):
        external=self.root/'external';external.mkdir();evidence=external/'keep.png';evidence.write_bytes(b'external evidence')
        link=self.r.dir/'outside';directory_link(link,external)
        try:
            result=self.r.storage();self.assertFalse(result['scan_complete'])
            self.assertEqual(result['image_bytes'],0);self.assertEqual(result['auxiliary_bytes'],0)
            self.assertEqual(result['scan_issues'],[dict(path='outside',reason='link_or_reparse_point')])
            with self.assertRaises(OSError):self.r.save(self.f,b'image',b'mask','fixture')
            self.assertEqual(evidence.read_bytes(),b'external evidence')
        finally:
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()
    def test_archive_root_link_is_rejected_before_opening_external_database(self):
        parent=self.root/'another';parent.mkdir();external=self.root/'external';external.mkdir()
        link=parent/'review_records';directory_link(link,external)
        try:
            with self.assertRaises(OSError):Records(parent)
            self.assertEqual(list(external.iterdir()),[])
        finally:
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()
    def test_database_and_sqlite_sidecar_reparse_points_are_rejected_before_connect(self):
        real_lstat=Path.lstat
        for filename in ('inspection.sqlite3','inspection.sqlite3-wal','inspection.sqlite3-shm','inspection.sqlite3-journal'):
            with self.subTest(filename=filename):
                parent=self.root/filename.replace('.','_');parent.mkdir();directory=parent/'review_records';directory.mkdir()
                target=directory/filename;target.write_bytes(b'placeholder')
                def reparse(path,*args,**kwargs):
                    if path==target:return SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0x400)
                    return real_lstat(path,*args,**kwargs)
                with patch.object(Path,'lstat',reparse),patch('workstation.sqlite3.connect',side_effect=AssertionError('Must not open reparse database')):
                    with self.assertRaises(OSError):Records(parent)
                self.assertEqual(target.read_bytes(),b'placeholder')
    @unittest.skipUnless(os.name=='nt','Windows case-insensitive pathname behavior')
    def test_windows_uppercase_png_name_is_still_registered_evidence(self):
        self.r.save(self.f,b'image',b'mask','fixture')
        path=self.r.dir/'pl_1_1.png';path.rename(self.r.dir/'PL_1_1.PNG')
        result=self.r.storage();self.assertEqual(result['unindexed_png_count'],0)
        self.assertEqual(self.r.read_image('pl_1_1')[0],b'image')
    def test_complete_snapshot_does_not_commit_or_end_callers_transaction(self):
        self.r.db.execute('BEGIN IMMEDIATE')
        self.r.db.execute('INSERT INTO review_revisions VALUES(?,?)',('fixture',4))
        try:
            result=self.r.storage();self.assertTrue(result['scan_complete']);self.assertTrue(self.r.db.in_transaction)
            other=sqlite3.connect(self.r.dir/'inspection.sqlite3')
            try:self.assertIsNone(other.execute('SELECT revision FROM review_revisions WHERE event_id=?',('fixture',)).fetchone())
            finally:other.close()
        finally:self.r.db.rollback()
        self.r.storage();self.assertFalse(self.r.db.in_transaction)
    def test_snapshot_waits_for_other_writer_instead_of_classifying_half_published_files(self):
        other=Records(self.root);entered=threading.Event();release=threading.Event();attempted=threading.Event();finished=threading.Event()
        result={};real_atomic=workstation.atomic
        def gate(path,data):
            if path.name=='pl_1_1_mask.png':
                entered.set()
                if not release.wait(5):raise TimeoutError('Writer release missing')
            return real_atomic(path,data)
        def save():
            try:other.save(self.f,b'image',b'mask','fixture')
            except Exception as error:result['save_error']=error
        def scan():
            try:result['scan']=self.r.storage()
            except Exception as error:result['scan_error']=error
            finally:finished.set()
        self.r.db.set_trace_callback(lambda sql:attempted.set() if sql=='BEGIN IMMEDIATE' else None)
        writer=threading.Thread(target=save);reader=threading.Thread(target=scan)
        try:
            with patch('workstation.atomic',side_effect=gate):
                try:
                    writer.start();self.assertTrue(entered.wait(5));reader.start();self.assertTrue(attempted.wait(5))
                    self.assertFalse(finished.wait(.05))
                finally:
                    release.set();writer.join(6)
                    if reader.ident is not None:reader.join(6)
            self.assertNotIn('save_error',result);self.assertNotIn('scan_error',result)
            self.assertTrue(result['scan']['scan_complete']);self.assertEqual(result['scan']['unindexed_png_count'],0)
        finally:self.r.db.set_trace_callback(None);other.db.close()
    def test_scanning_preserves_review_images_metadata_and_confirmation_history(self):
        key=self.r.save(self.f,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
        self.r.confirmations.settle(self.f,'ACKNOWLEDGED',1);self.r.update(key,'confirmed_crack','Preserved conclusion')
        before=self.r.get(key);history=self.r.confirmations.history()
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.r.dir.glob('*.png')}
        for _ in range(3):self.r.storage()
        self.assertEqual(self.r.get(key),before);self.assertEqual(self.r.confirmations.history(),history)
        self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.r.dir.glob('*.png')},hashes)
    def test_entry_limit_returns_partial_counts_and_bounded_issues(self):
        result=archive_inventory.inventory(self.r.dir,[],max_entries=1)
        self.assertFalse(result['scan_complete']);self.assertIn(dict(path='.',reason='entry_limit'),result['scan_issues'])
        result=archive_inventory.inventory(self.r.dir,['../bad']*30)
        self.assertFalse(result['scan_complete']);self.assertEqual(result['scan_issue_count'],30)
        self.assertEqual(len(result['scan_issues']),archive_inventory.MAX_ISSUES)


if __name__=='__main__':unittest.main(verbosity=2)

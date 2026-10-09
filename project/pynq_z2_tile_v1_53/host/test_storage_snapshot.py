"""Display snapshots may be stale; every storage admission still scans fresh."""
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import workstation
from workstation import Records,Station
from archive_inventory import ArchiveInventoryError
from storage_policy import ArchiveCapacityError


class IdleBridge:
    def capture(self,threshold):raise AssertionError('No board requests in snapshot tests')
    def close(self):pass


class StorageSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_storage_snapshot_');self.root=Path(self.tmp.name)
        self.r=Records(self.root);self.clock=[100.0];self.r._storage_clock=lambda:self.clock[0]
        self.r.storage();self.frame=dict(boot_id=3,event_id=7,frame_id=50)
    def tearDown(self):self.r.db.close();self.tmp.cleanup()
    def test_default_storage_always_fresh_while_display_reuses_fresh_result(self):
        with patch('workstation.inventory',wraps=workstation.inventory) as scan:
            self.r.storage();self.r.storage();self.assertEqual(scan.call_count,2)
            for _ in range(8):self.assertTrue(self.r.storage_snapshot()['snapshot_cached'])
            self.assertEqual(scan.call_count,2)
    def test_ttl_uses_monotonic_age_and_does_not_reset_observation_on_hit(self):
        first=self.r.storage_snapshot()
        with patch('workstation.inventory',wraps=workstation.inventory) as scan,patch('workstation.time.time',return_value=-999999):
            self.clock[0]=104.999;cached=self.r.storage_snapshot()
            self.assertEqual(scan.call_count,0);self.assertTrue(cached['snapshot_cached'])
            self.assertEqual(cached['snapshot_age_seconds'],4.999)
            self.assertEqual(cached['snapshot_observed_at'],first['snapshot_observed_at'])
            self.clock[0]=105.0;fresh=self.r.storage_snapshot()
            self.assertEqual(scan.call_count,1);self.assertFalse(fresh['snapshot_cached'])
            self.assertEqual(fresh['snapshot_age_seconds'],0);self.assertFalse(fresh['snapshot_stale'])
    def test_snapshots_and_issue_lists_are_independent_copies(self):
        real=workstation.inventory
        def incomplete(*args,**kwargs):return dict(real(*args,**kwargs),scan_complete=False,scan_issue_count=1,scan_issues=[dict(path='staging',reason='directory_unavailable')])
        with patch('workstation.inventory',side_effect=incomplete):self.r.storage()
        first=self.r.storage_snapshot();first['used_bytes']=0;first['scan_issues'][0]['path']='changed'
        second=self.r.storage_snapshot();self.assertGreater(second['used_bytes'],0)
        self.assertEqual(second['scan_issues'][0]['path'],'staging');self.assertFalse(second['scan_complete'])
    def test_parallel_expired_display_requests_coalesce_to_one_inventory(self):
        self.clock[0]=106;barrier=threading.Barrier(8);results=[];errors=[]
        def run():
            try:barrier.wait(3);results.append(self.r.storage_snapshot())
            except Exception as error:errors.append(error)
        with patch('workstation.inventory',wraps=workstation.inventory) as scan:
            threads=[threading.Thread(target=run) for _ in range(8)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(5)
            self.assertEqual(errors,[]);self.assertEqual(len(results),8);self.assertEqual(scan.call_count,1)
        self.assertEqual(sum(not result['snapshot_cached'] for result in results),1)
    def test_each_new_save_scans_fresh_and_invalidates_its_prepublication_snapshot(self):
        with patch('workstation.inventory',wraps=workstation.inventory) as scan:
            self.r.save(self.frame,b'image',b'mask','fixture');self.assertEqual(scan.call_count,1)
            snapshot=self.r.storage_snapshot();self.assertEqual(scan.call_count,2)
            self.assertFalse(snapshot['snapshot_cached']);self.assertEqual(snapshot['image_bytes'],9)
            self.assertEqual(snapshot['unindexed_png_count'],0)
            self.r.save(dict(self.frame,event_id=8),b'image',b'mask','fixture');self.assertEqual(scan.call_count,3)
    def test_partial_publication_failure_invalidates_display_without_creating_ack(self):
        real_atomic=workstation.atomic
        def second_fails(path,data):
            if path.name.endswith('_mask.png'):
                path.with_suffix('.png.tmp').write_bytes(b'partial mask');raise OSError('Injected second PNG failure')
            return real_atomic(path,data)
        with patch('workstation.atomic',side_effect=second_fails):
            with self.assertRaises(OSError):self.r.save(self.frame,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
        result=self.r.storage_snapshot();self.assertFalse(result['snapshot_cached'])
        self.assertEqual(result['image_bytes'],5);self.assertEqual(result['unindexed_png_count'],1)
        self.assertEqual(result['temp_file_count'],1);self.assertEqual(result['auxiliary_bytes'],len(b'partial mask'))
        self.assertEqual(self.r.summary()['total'],0);self.assertIsNone(self.r.confirmations.pending())
    def test_idempotent_save_keeps_review_and_invalidates_display(self):
        key=self.r.save(self.frame,b'image',b'mask','fixture');self.r.update(key,'confirmed_crack','Keep note')
        self.r.storage_snapshot();before=self.r.get(key)
        with patch('workstation.inventory',wraps=workstation.inventory) as scan:
            self.r.save(self.frame,b'image',b'mask','fixture');self.assertEqual(scan.call_count,0)
            self.assertFalse(self.r.storage_snapshot()['snapshot_cached']);self.assertEqual(scan.call_count,1)
        self.assertEqual(self.r.get(key),before)
    def test_external_files_can_lag_display_but_never_quota_admission(self):
        baseline=self.r.storage_snapshot();self.r.max_archive_bytes=baseline['used_bytes']+65536+20
        (self.r.dir/'uncommitted.png').write_bytes(b'x'*500)
        self.clock[0]=101
        cached=self.r.storage_snapshot();self.assertTrue(cached['snapshot_cached'])
        self.assertEqual(cached['image_bytes'],0);self.assertEqual(cached['snapshot_age_seconds'],1)
        with self.assertRaises(ArchiveCapacityError):self.r.save(self.frame,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
        self.assertFalse((self.r.dir/'pl_3_7.png').exists());self.assertIsNone(self.r.confirmations.pending())
        self.assertEqual(self.r.storage_snapshot()['image_bytes'],500)
    def test_healthy_display_cache_cannot_bypass_incomplete_fresh_admission(self):
        self.assertTrue(self.r.storage_snapshot()['scan_complete']);real=workstation.inventory
        def incomplete(*args,**kwargs):return dict(real(*args,**kwargs),scan_complete=False,scan_issue_count=1,scan_issues=[dict(path='blocked',reason='directory_unavailable')])
        with patch('workstation.inventory',side_effect=incomplete):
            with self.assertRaises(ArchiveInventoryError):self.r.save(self.frame,b'image',b'mask','fixture',confirmation_endpoint='tcp://fixture')
            result=self.r.storage_snapshot()
        self.assertFalse(result['scan_complete']);self.assertEqual(self.r.summary()['total'],0)
        self.assertIsNone(self.r.confirmations.pending());self.assertEqual(list(self.r.dir.glob('*.png')),[])
    def test_refresh_error_retains_age_and_values_and_throttles_ui_only(self):
        before=self.r.storage_snapshot();self.clock[0]=106
        with patch('workstation.inventory',side_effect=OSError('denied\n'+'x'*300)) as scan:
            result=self.r.storage_snapshot();self.assertEqual(scan.call_count,1)
            self.assertEqual(result['used_bytes'],before['used_bytes']);self.assertEqual(result['snapshot_age_seconds'],6)
            self.assertEqual(result['snapshot_observed_at'],before['snapshot_observed_at'])
            self.assertTrue(result['snapshot_stale']);self.assertTrue(result['snapshot_cached'])
            self.assertLessEqual(len(result['snapshot_refresh_error']),200);self.assertNotIn('\n',result['snapshot_refresh_error'])
            self.clock[0]=108;self.r.storage_snapshot();self.assertEqual(scan.call_count,1)
            # The failure retry budget is display-only, never fresh capacity.
            with self.assertRaises(OSError):self.r.storage()
            self.assertEqual(scan.call_count,2)
            self.clock[0]=109;self.r.storage_snapshot();self.assertEqual(scan.call_count,2)
            self.clock[0]=114;self.r.storage_snapshot();self.assertEqual(scan.call_count,3)
        self.clock[0]=120;recovered=self.r.storage_snapshot()
        self.assertFalse(recovered['snapshot_stale']);self.assertEqual(recovered['snapshot_refresh_error'],'')
        self.assertEqual(recovered['snapshot_age_seconds'],0)
    def test_new_incomplete_snapshot_is_not_replaced_by_old_complete_one_on_error(self):
        real=workstation.inventory
        with patch('workstation.inventory',side_effect=lambda *a,**k:dict(real(*a,**k),scan_complete=False,scan_issue_count=1,scan_issues=[dict(path='blocked',reason='directory_unavailable')])):
            self.r.storage()
        self.clock[0]=106
        with patch('workstation.inventory',side_effect=OSError('still unavailable')):result=self.r.storage_snapshot()
        self.assertFalse(result['scan_complete']);self.assertEqual(result['scan_issue_count'],1);self.assertTrue(result['snapshot_stale'])
    def test_no_snapshot_failure_never_fabricates_zero_usage(self):
        self.r._storage_snapshot=None
        with patch('workstation.inventory',side_effect=OSError('unavailable')) as scan:
            with self.assertRaises(ArchiveInventoryError):self.r.storage_snapshot()
            with self.assertRaises(ArchiveInventoryError):self.r.storage_snapshot()
            self.assertEqual(scan.call_count,1)
    def test_busy_sqlite_refresh_preserves_cached_data_then_can_recover(self):
        other=sqlite3.connect(self.r.dir/'inspection.sqlite3');other.execute('BEGIN IMMEDIATE')
        self.r.db.execute('PRAGMA busy_timeout=30');self.clock[0]=106
        try:
            result=self.r.storage_snapshot();self.assertTrue(result['snapshot_stale'])
            self.assertIn('OperationalError',result['snapshot_refresh_error']);self.assertFalse(self.r.db.in_transaction)
        finally:other.rollback();other.close()
        self.clock[0]=112;self.assertFalse(self.r.storage_snapshot()['snapshot_stale'])
    def test_current_limit_is_recomputed_without_refreshing_cached_disk_facts(self):
        before=self.r.storage_snapshot();self.r.max_archive_bytes=before['used_bytes']-1
        with patch('workstation.inventory',side_effect=AssertionError('Cache hit must not scan')):
            result=self.r.storage_snapshot()
        self.assertEqual(result['max_bytes'],before['used_bytes']-1);self.assertTrue(result['at_limit'])
        self.assertEqual(result['free_disk_bytes'],before['free_disk_bytes'])
    def test_cached_free_disk_space_is_never_used_for_new_save(self):
        self.assertGreater(self.r.storage_snapshot()['free_disk_bytes'],0)
        with patch('workstation.shutil.disk_usage',return_value=SimpleNamespace(free=1)):
            with self.assertRaises(OSError):self.r.save(self.frame,b'image',b'mask','fixture')
        self.assertEqual(list(self.r.dir.glob('*.png')),[])


class StorageSnapshotStationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_snapshot_station_');self.station=Station(Path(self.tmp.name),IdleBridge())
    def tearDown(self):
        self.station.exit=True;self.station.worker.join(4);self.station.records.db.close();self.tmp.cleanup()
    def assert_pause_during(self,target,method):
        entered=threading.Event();release=threading.Event();paused=threading.Event();errors=[]
        real=getattr(target,method)
        def blocked(*args,**kwargs):
            entered.set()
            if not release.wait(4):raise TimeoutError('Test did not release state read')
            return real(*args,**kwargs)
        def state():
            try:self.station.state()
            except Exception as error:errors.append(error)
        def pause():
            try:self.station.action(dict(op='pause'));paused.set()
            except Exception as error:errors.append(error)
        reader=threading.Thread(target=state);stopper=threading.Thread(target=pause)
        with patch.object(target,method,side_effect=blocked):
            try:
                reader.start();self.assertTrue(entered.wait(3));stopper.start()
                self.assertTrue(paused.wait(1),'A display read held Station.lock while waiting')
            finally:
                release.set();reader.join(5)
                if stopper.ident is not None:stopper.join(5)
        self.assertEqual(errors,[])
    def test_display_inventory_refresh_does_not_hold_station_control_lock(self):
        self.station.records.invalidate_storage_snapshot();self.assert_pause_during(workstation,'inventory')
    def test_page_read_cannot_indirectly_hold_station_lock_behind_inventory(self):
        self.assert_pause_during(self.station.records,'page')
    def test_confirmation_history_read_is_also_outside_station_control_lock(self):
        self.assert_pause_during(self.station.records.confirmations,'history')
    def test_state_uses_current_storage_policy_even_if_limit_changes_after_snapshot(self):
        cached=self.station.records.storage_snapshot();cached['used_bytes']=20*1024*1024
        self.station.storage_policy.max_archive_mib=16;self.station.records.max_archive_bytes=16*1024*1024
        # Deliberately stale cached configuration must not override current one.
        cached['max_bytes']=1024*1024*1024;cached['at_limit']=False
        with patch.object(self.station.records,'storage_snapshot',return_value=cached):state=self.station.state()
        self.assertEqual(state['storage']['max_bytes'],16*1024*1024)
        self.assertEqual(state['storage']['max_archive_mib'],16);self.assertTrue(state['storage']['at_limit'])


if __name__=='__main__':unittest.main(verbosity=2)

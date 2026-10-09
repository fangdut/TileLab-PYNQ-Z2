import tempfile,time,unittest,threading
from pathlib import Path
from unittest.mock import patch
from recovery import Recovery,TransientTransportError
from workstation import Station,Records,Bridge,EthernetBridge
import test_events as fixtures

class Controlled(EthernetBridge):
    def __init__(self,fail_stage=None,failures=1,error=None):
        super().__init__('127.0.0.1');self.check_capture_health=False;self.stage=fail_stage;self.failures=failures;self.error=error
        self.calls=[];self.frame=Bridge.decode_event(*fixtures.packet(),1);self.released=0
    def maybe_fail(self,stage):
        self.calls.append(stage)
        if stage==self.stage and self.failures:
            self.failures-=1;raise self.error or TransientTransportError('Injected connection loss')
    def capture(self,t):self.maybe_fail('capture');return self.frame
    def ack(self,f):
        self.released=1 # simulate ACK executed but its response lost
        self.maybe_fail('ack')
    def stats(self):self.maybe_fail('stats');return dict(depth=0 if self.released else 1,head=self.released,frames=60,boot_id=7)

class RecoveryTests(unittest.TestCase):
    def until(self,predicate,seconds=4):
        end=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>end:self.fail('Condition did not complete')
            time.sleep(.015)
    def begin(self,b):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_recovery_');self.s=Station(self.tmp.name,b)
        self.addCleanup(self.finish);return self.s
    def finish(self):
        self.s.exit=True;self.s.worker.join(5);self.s.records.db.close();self.tmp.cleanup()
    def test_bounded_backoff_clock_and_success_reset(self):
        r=Recovery()
        for t,delay in ((100,.25),(101,.5),(102,1),(103,2),(104,2)):
            r.failed(t,'connection');self.assertAlmostEqual(r.next_retry,t+delay)
        self.assertFalse(r.expired(129.9));self.assertTrue(r.expired(130))
        self.assertTrue(r.success());self.assertEqual(r.recovered,1);self.assertFalse(r.snapshot(131)['active'])
    def test_manual_capture_recovers_without_second_request(self):
        b=Controlled('capture',2);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.recovery.recovered==1 and not s.busy)
        self.assertEqual(b.calls.count('capture'),3);self.assertEqual(b.calls.count('ack'),1)
        self.assertEqual(len(s.records.all()),1);self.assertFalse(s.manual);self.assertFalse(s.error)
    def test_lost_ack_reply_retries_same_confirmation_only(self):
        b=Controlled('ack',2);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.recovery.recovered==1 and not s.busy)
        self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1)
        self.assertEqual(len(s.records.all()),1);self.assertIsNone(s.pending_ack)
    def test_status_failure_does_not_capture_or_ack_another_frame(self):
        b=Controlled('stats',2);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.recovery.recovered==1 and not s.busy)
        self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1)
        self.assertEqual(b.calls.count('stats'),3);self.assertEqual(len(s.records.all()),1)
    def test_invalid_confirmation_preserves_saved_identity_for_resume(self):
        b=Controlled('ack',1,ValueError('Header CRC mismatch'));s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:bool(s.error) and not s.busy)
        self.assertIsNotNone(s.pending_ack);self.assertEqual(len(s.records.all()),1)
        self.assertIsNone(s.recovery.started);self.assertFalse(s.enabled)
        with s.lock:s.retry_requested=True
        self.until(lambda:s.pending_ack is None and not s.busy)
        self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1)
        self.assertEqual(len(s.records.all()),1)
    def test_pause_cancels_backoff_and_pending_manual_request(self):
        b=Controlled('capture',100);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.recovery.attempts==1 and not s.busy)
        s.action(dict(op='pause'));calls=len(b.calls);time.sleep(.4)
        self.assertEqual(len(b.calls),calls);self.assertFalse(s.manual);self.assertFalse(s.retry_requested)
        self.assertEqual(len(s.records.all()),0)
    def test_pause_during_failing_request_does_not_restart_it(self):
        entered=threading.Event();release=threading.Event()
        b=Controlled()
        def capture(t):
            b.calls.append('capture');entered.set();release.wait(2)
            raise TransientTransportError('Request failed after pause')
        b.capture=capture;s=self.begin(b);s.action(dict(op='capture'))
        self.assertTrue(entered.wait(2));s.action(dict(op='pause'));release.set()
        self.until(lambda:not s.busy);time.sleep(.3)
        self.assertEqual(b.calls,['capture']);self.assertFalse(s.manual);self.assertFalse(s.retry_requested)
    def test_disconnect_during_manual_recovery_requires_pause(self):
        b=Controlled('capture',100);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.recovery.attempts==1 and not s.busy)
        with self.assertRaises(ValueError):s.action(dict(op='disconnect'))
        s.action(dict(op='pause'));s.action(dict(op='disconnect'))
    def test_pause_keeps_ack_identity_until_explicit_resume(self):
        b=Controlled('ack',1);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.recovery.attempts==1 and not s.busy);s.action(dict(op='pause'))
        self.assertIsNotNone(s.pending_ack)
        with self.assertRaises(ValueError):s.action(dict(op='capture'))
        # Resume only the pending task; no new continuous capture is requested.
        with s.lock:s.retry_requested=True
        self.until(lambda:s.pending_ack is None and not s.busy)
        self.assertEqual(b.calls.count('capture'),1);self.assertEqual(len(s.records.all()),1)
    def test_recovery_window_expires_and_does_not_ack(self):
        b=Controlled('capture',100);s=self.begin(b);s.recovery.window=.3;s.action(dict(op='start'))
        self.until(lambda:s.recovery.exhausted)
        self.assertFalse(s.enabled);self.assertFalse(s.retry_requested);self.assertEqual(b.released,0)
        self.assertEqual(len(s.records.all()),0);self.assertIn('恢复超时',s.error)
    def test_invalid_data_stops_without_network_retries(self):
        b=Controlled('capture',100,ValueError('Corrupt frame'));s=self.begin(b);s.action(dict(op='start'))
        self.until(lambda:bool(s.error));self.assertFalse(s.enabled);self.assertEqual(len(b.calls),1)
        self.assertEqual(s.recovery.episodes,0);self.assertEqual(b.released,0)
    def test_filesystem_failure_is_fatal_and_never_acknowledged(self):
        b=Controlled();s=self.begin(b)
        with patch.object(s.records,'save',side_effect=OSError('Disk full')):
            s.action(dict(op='capture'));self.until(lambda:bool(s.error))
        self.assertEqual(b.released,0);self.assertEqual(s.recovery.episodes,0);self.assertFalse(s.retry_requested)
    def test_only_transport_os_errors_are_wrapped(self):
        b=EthernetBridge('127.0.0.1')
        for exc,kind in ((TimeoutError('timeout'),TransientTransportError),(ValueError('bad frame'),ValueError)):
            def failure():raise exc
            with self.assertRaises(kind):b.call(failure)
    def test_paused_or_old_preview_is_explicitly_stale(self):
        b=Controlled();s=self.begin(b);s.action(dict(op='capture'));self.until(lambda:s.captures and not s.busy)
        self.assertTrue(s.state()['preview_stale']);self.assertEqual(s.state()['preview_kind'],'LIVE_SAMPLE')
        with s.lock:s.last_update=time.time()-3;s.enabled=True
        self.assertTrue(s.state()['preview_stale'])
    def test_archive_cache_refreshes_after_external_commit(self):
        with tempfile.TemporaryDirectory() as d:
            a=Records(d);b=Records(d)
            try:
                self.assertEqual(a.storage()['image_bytes'],0)
                f,im,mask=Bridge.decode_event(*fixtures.packet(),1);b.save(f,im,mask,'hardware_alarm')
                expected=sum(p.stat().st_size for p in (Path(d)/'review_records').glob('*.png'))
                self.assertEqual(a.storage()['image_bytes'],expected)
                self.assertEqual(a.storage()['image_bytes'],len(im)+len(mask))
            finally:a.db.close();b.db.close()

if __name__=='__main__':unittest.main(verbosity=2)

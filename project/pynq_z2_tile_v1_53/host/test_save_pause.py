"""Slow real archive writes must not hold the Station control lock or release evidence early."""
from pathlib import Path
import json,sqlite3,tempfile,threading,time,unittest,urllib.request
from unittest.mock import patch
import workstation
from test_recovery import Controlled

class SavePauseTests(unittest.TestCase):
    def begin(self,point='image',automatic=False,fail=False,capacity=False):
        tmp=tempfile.TemporaryDirectory(prefix='tile_save_pause_v144_');bridge=Controlled()
        station=workstation.Station(tmp.name,bridge)
        if automatic:station.action(dict(op='storage',mode='archive',max_archive_mib=16))
        if capacity:station.records.max_archive_bytes=1
        entered=threading.Event();release=threading.Event();original=workstation.atomic
        def delayed(path,data):
            match=(point=='image' and path.suffix=='.png' and not path.name.endswith('_mask.png')
                or point=='mask' and path.name.endswith('_mask.png')
                or point=='fallback' and path.name=='storage_policy.json')
            if match and not entered.is_set():
                entered.set()
                if not release.wait(5):raise TimeoutError('Disk fixture not released')
                if fail:raise OSError('Injected storage failure')
            return original(path,data)
        patcher=patch.object(workstation,'atomic',side_effect=delayed);patcher.start()
        server=workstation.ThreadingHTTPServer(('127.0.0.1',0),workstation.handler(station))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def cleanup():
            release.set();station.exit=True;station.worker.join(6)
            server.shutdown();server.server_close();thread.join(2);patcher.stop()
            self.assertFalse(station.worker.is_alive());station.records.db.close();bridge.close();tmp.cleanup()
        self.addCleanup(cleanup)
        return station,bridge,entered,release,server
    def until_idle(self,s):
        end=time.monotonic()+3
        while s.busy:
            self.assertLess(time.monotonic(),end);time.sleep(.005)
    def pause_http(self,s,server):
        started=time.monotonic()
        request=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/api/action',
            data=b'{"op":"pause"}',headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=1) as response:self.assertEqual(json.load(response),{'ok':True})
        self.assertLess(time.monotonic()-started,1)
        self.assertFalse(s.enabled or s.manual or s.retry_requested)
    def assert_control_available(self,s):
        acquired=s.lock.acquire(blocking=False);self.assertTrue(acquired,'Save retains control lock')
        if acquired:s.lock.release()
    def test_http_pause_during_image_and_mask_write_finishes_only_admitted_frame(self):
        for point in ('image','mask'):
            with self.subTest(point=point):
                s,b,entered,release,server=self.begin(point)
                s.action(dict(op='capture'));self.assertTrue(entered.wait(3));self.assert_control_available(s)
                self.assertEqual(s.operation_phase,'SAVE');self.pause_http(s,server)
                self.assertTrue(s.busy);self.assertEqual(b.calls.count('ack'),0)
                release.set();self.until_idle(s);time.sleep(.06)
                self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1)
                self.assertEqual(len(s.records.all()),1);self.assertIsNone(s.pending_ack)
                self.assertEqual(len(s.records.confirmations.history()),1)
    def test_busy_save_rejects_conflicting_operations_without_waiting(self):
        s,b,entered,release,server=self.begin();s.action(dict(op='capture'));self.assertTrue(entered.wait(3))
        for body in (dict(op='capture'),dict(op='disconnect'),dict(op='status'),dict(op='storage',mode='archive',max_archive_mib=16)):
            with self.subTest(body=body),self.assertRaises(ValueError):s.action(body)
        self.assertEqual(s.storage_policy.mode,'preview');self.pause_http(s,server);release.set();self.until_idle(s)
        self.assertEqual(len(s.records.all()),1);self.assertEqual(b.calls.count('capture'),1)
    def test_save_failure_after_pause_never_acks_or_starts_another_capture(self):
        s,b,entered,release,server=self.begin('mask',fail=True)
        s.action(dict(op='capture'));self.assertTrue(entered.wait(3));self.pause_http(s,server)
        release.set();self.until_idle(s);time.sleep(.06)
        self.assertIn('Injected storage failure',s.error);self.assertEqual(b.calls.count('ack'),0)
        self.assertEqual(s.records.all(),[]);self.assertIsNone(s.records.confirmations.pending())
        self.assertEqual(b.calls.count('capture'),1);self.assertFalse(s.enabled)
    def test_automatic_capacity_policy_write_is_pausable_before_ack(self):
        s,b,entered,release,server=self.begin('fallback',automatic=True,capacity=True)
        s.action(dict(op='start'));self.assertTrue(entered.wait(3));self.assert_control_available(s)
        self.pause_http(s,server);self.assertEqual(b.calls.count('ack'),0)
        release.set();self.until_idle(s)
        self.assertEqual(s.storage_policy.mode,'preview');self.assertEqual(s.skipped_automatic,1)
        self.assertEqual(s.records.all(),[]);self.assertEqual(b.calls.count('ack'),1);self.assertFalse(s.enabled)
    def test_pause_start_pause_preserves_latest_intent_and_frame_parameters(self):
        s,b,entered,release,server=self.begin();s.action(dict(op='capture'));self.assertTrue(entered.wait(3))
        config=s.frame['config_word'];self.pause_http(s,server)
        s.action(dict(op='start'));s.action(dict(op='threshold',value=80));self.pause_http(s,server)
        release.set();self.until_idle(s);time.sleep(.08)
        self.assertFalse(s.enabled);self.assertEqual(s.intent_epoch,2);self.assertEqual(b.calls.count('capture'),1)
        self.assertEqual(s.records.all()[0]['config_word'],config);self.assertEqual(s.threshold,80)
    def test_sqlite_writer_contention_keeps_pause_available(self):
        s,b,entered,release,server=self.begin(point='unused')
        other=sqlite3.connect(s.records.dir/'inspection.sqlite3');other.execute('BEGIN IMMEDIATE')
        self.addCleanup(other.close)
        s.records.db.set_trace_callback(lambda sql:entered.set() if sql=='BEGIN IMMEDIATE' else None)
        try:
            s.action(dict(op='capture'));self.assertTrue(entered.wait(3));self.assert_control_available(s)
            self.pause_http(s,server);self.assertEqual(b.calls.count('ack'),0)
        finally:other.rollback();s.records.db.set_trace_callback(None)
        self.until_idle(s);self.assertEqual(len(s.records.all()),1);self.assertEqual(b.calls.count('ack'),1)

if __name__=='__main__':unittest.main(verbosity=2)

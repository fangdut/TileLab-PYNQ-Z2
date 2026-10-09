"""Real Station diagnostic reservation; bounded barriers, no sockets or board."""
from contextlib import contextmanager
import hashlib
import json
import tempfile
import threading
import time
import unittest

from workstation import Bridge, ROOT, Station
import test_events


class FakeBridge:
    """Legacy no-argument stats API with observable connection exclusivity."""
    def __init__(self):
        self.calls=[];self.mutex=threading.Lock();self.active=0;self.max_active=0
        self.stats_entered=threading.Event();self.stats_release=threading.Event()
        self.capture_entered=threading.Event();self.capture_release=threading.Event()
        self.block_stats=True;self.block_capture=False;self.stats_error=None
        self.head=0;self.queued=0;self.closed=False
        raw,descriptor,meta=test_events.packet();descriptor[8]=3
        self.frame=Bridge.decode_event(raw,descriptor,meta,1)
    @contextmanager
    def io(self,operation):
        with self.mutex:
            self.calls.append(operation);self.active+=1;self.max_active=max(self.max_active,self.active)
        try:
            if self.active!=1:raise AssertionError('Concurrent access to the same bridge')
            yield
        finally:
            with self.mutex:self.active-=1
    def stats(self):
        with self.io('stats'):
            if self.block_stats:
                self.block_stats=False;self.stats_entered.set()
                if not self.stats_release.wait(4):raise TimeoutError('Diagnostic fixture not released')
            if self.stats_error:raise self.stats_error
            return dict(version=0x12500,boot_id=7,head=self.head,depth=self.queued,frames=60)
    def capture(self,threshold):
        with self.io('capture'):
            self.capture_entered.set()
            if self.block_capture and not self.capture_release.wait(4):raise TimeoutError('Capture fixture not released')
            return self.frame
    def ack(self,frame):
        with self.io('ack'):self.head=frame['event_id'];self.queued=0
    def close(self):
        with self.io('close'):self.closed=True


class ObservedLock:
    """Keep the actual RLock, observing worker passes through admission.

    Two entries after arming prove one whole preceding worker admission pass
    completed. This avoids inferring non-reentry from a short arbitrary sleep.
    """
    def __init__(self,lock,worker):
        self.lock=lock;self.worker=worker;self.entries=0;self.armed=False;self.observed=threading.Event()
    def acquire(self,*args,**kwargs):
        acquired=self.lock.acquire(*args,**kwargs)
        if acquired and self.armed and threading.current_thread() is self.worker:
            self.entries+=1
            if self.entries>=2:self.observed.set()
        return acquired
    def release(self):self.lock.release()
    def __enter__(self):self.acquire();return self
    def __exit__(self,*args):self.release()


class DiagnosticReservationTests(unittest.TestCase):
    def begin(self,bridge=None):
        temporary=tempfile.TemporaryDirectory(prefix='tile_v139_diagnostic_')
        bridge=bridge or FakeBridge();station=Station(temporary.name,bridge);threads=[]
        observed=ObservedLock(station.lock,station.worker)
        with station.lock:station.lock=observed
        def finish():
            if hasattr(bridge,'stats_release'):bridge.stats_release.set()
            if hasattr(bridge,'capture_release'):bridge.capture_release.set()
            station.exit=True
            for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
            station.worker.join(5);self.assertFalse(station.worker.is_alive())
            station.records.db.close();bridge.close();temporary.cleanup()
        self.addCleanup(finish)
        return station,bridge,threads,observed

    def invoke(self,station,threads,operation):
        outcome={'done':threading.Event()}
        def run():
            try:outcome['value']=station.action(dict(op=operation))
            except Exception as error:outcome['error']=error
            finally:outcome['done'].set()
        thread=threading.Thread(target=run,daemon=True);threads.append(thread);thread.start()
        return outcome

    def until(self,predicate):
        end=time.monotonic()+3
        while not predicate():
            if time.monotonic()>end:self.fail('Bounded condition did not complete')
            time.sleep(.005)

    def blocked(self,station,bridge,threads):
        outcome=self.invoke(station,threads,'status');self.assertTrue(bridge.stats_entered.wait(2))
        self.assertFalse(outcome['done'].is_set())
        return outcome

    def assert_available(self,station):
        acquired=station.lock.acquire(blocking=False)
        self.assertTrue(acquired,'Diagnostic network wait must not retain Station.lock')
        if acquired:station.lock.release()

    def test_pause_and_state_are_responsive_while_legacy_stats_waits(self):
        station,bridge,threads,_=self.begin();outcome=self.blocked(station,bridge,threads)
        self.assert_available(station);snapshot=station.state()
        self.assertTrue(snapshot['busy']);self.assertEqual(station.operation_phase,'DIAGNOSTIC')
        epoch=station.intent_epoch;pause=self.invoke(station,threads,'pause')
        self.assertTrue(pause['done'].wait(1));self.assertNotIn('error',pause)
        self.assertEqual(station.intent_epoch,epoch+1);self.assertFalse(station.enabled)
        self.assertFalse(outcome['done'].is_set());bridge.stats_release.set()
        self.assertTrue(outcome['done'].wait(2));self.assertNotIn('error',outcome)
        self.assertEqual(outcome['value']['version'],0x12500)
        self.assertFalse(station.busy);self.assertEqual(station.operation_phase,'IDLE')
        self.assertEqual(bridge.calls,['stats']);self.assertEqual(bridge.max_active,1)

    def test_start_waits_for_diagnostic_reservation_before_worker_uses_bridge(self):
        station,bridge,threads,lock=self.begin();bridge.block_capture=True
        outcome=self.blocked(station,bridge,threads);self.assert_available(station)
        start=self.invoke(station,threads,'start');self.assertTrue(start['done'].wait(1));self.assertNotIn('error',start)
        lock.armed=True;self.assertTrue(lock.observed.wait(2),'Worker did not revisit admission')
        self.assertEqual(bridge.calls,['stats']);self.assertEqual(bridge.max_active,1)
        self.assertTrue(station.enabled);self.assertFalse(bridge.capture_entered.is_set())
        bridge.stats_release.set();self.assertTrue(outcome['done'].wait(2));self.assertNotIn('error',outcome)
        self.assertTrue(bridge.capture_entered.wait(2));self.assert_available(station)
        station.action(dict(op='pause'));bridge.capture_release.set();self.until(lambda:not station.busy)
        self.assertEqual(bridge.calls,['stats','capture','ack','stats']);self.assertEqual(bridge.max_active,1)
        self.assertEqual(station.captures,1);self.assertIsNone(station.pending_ack)

    def test_start_then_pause_during_diagnostics_never_revives_capture(self):
        station,bridge,threads,lock=self.begin();outcome=self.blocked(station,bridge,threads)
        start=self.invoke(station,threads,'start');self.assertTrue(start['done'].wait(1))
        lock.armed=True;self.assertTrue(lock.observed.wait(2))
        pause=self.invoke(station,threads,'pause');self.assertTrue(pause['done'].wait(1))
        bridge.stats_release.set();self.assertTrue(outcome['done'].wait(2));self.assertNotIn('error',outcome)
        self.assertFalse(station.enabled);self.assertFalse(station.busy);self.assertFalse(station.manual)
        self.assertEqual(bridge.calls,['stats']);self.assertEqual(station.capture_admissions,0)

    def test_conflicting_controls_reject_without_touching_reserved_connection(self):
        station,bridge,threads,_=self.begin();outcome=self.blocked(station,bridge,threads)
        for operation in ('capture','status','disconnect','resume_pending'):
            with self.subTest(operation=operation):
                blocked=self.invoke(station,threads,operation)
                self.assertTrue(blocked['done'].wait(1));self.assertIsInstance(blocked.get('error'),ValueError)
                self.assertTrue(station.busy);self.assertEqual(station.operation_phase,'DIAGNOSTIC')
        self.assertFalse(station.manual);self.assertFalse(bridge.closed);self.assertEqual(bridge.calls,['stats'])
        bridge.stats_release.set();self.assertTrue(outcome['done'].wait(2));self.assertNotIn('error',outcome)
        station.action(dict(op='disconnect'));self.assertTrue(bridge.closed)

    def test_error_finally_releases_reservation_without_overwriting_pause(self):
        for failure in (OSError('Lost stats reply'),ValueError('Malformed stats')):
            with self.subTest(failure=type(failure).__name__):
                station,bridge,threads,_=self.begin();station.board_stats={'old':True};station.error='Earlier capture error'
                bridge.stats_error=failure;outcome=self.blocked(station,bridge,threads)
                pause=self.invoke(station,threads,'pause');self.assertTrue(pause['done'].wait(1))
                bridge.stats_release.set();self.assertTrue(outcome['done'].wait(2))
                self.assertIs(outcome.get('error'),failure);self.assertFalse(station.busy)
                self.assertEqual(station.operation_phase,'IDLE');self.assertFalse(station.enabled)
                self.assertEqual(station.board_stats,{'old':True});self.assertEqual(station.error,'Earlier capture error')
                bridge.stats_error=None;reply=station.action(dict(op='status'))
                self.assertEqual(reply['boot_id'],7);self.assertFalse(station.busy)
                self.assertEqual(bridge.calls,['stats','stats'])

    def test_error_finally_preserves_start_intent_and_worker_runs_after_release(self):
        station,bridge,threads,lock=self.begin();bridge.block_capture=True;error=OSError('Diagnostic failure')
        bridge.stats_error=error;outcome=self.blocked(station,bridge,threads)
        start=self.invoke(station,threads,'start');self.assertTrue(start['done'].wait(1))
        lock.armed=True;self.assertTrue(lock.observed.wait(2));self.assertEqual(bridge.calls,['stats'])
        bridge.stats_release.set();self.assertTrue(outcome['done'].wait(2));self.assertIs(outcome.get('error'),error)
        self.assertTrue(bridge.capture_entered.wait(2));self.assertTrue(station.enabled)
        bridge.stats_error=None;station.action(dict(op='pause'));bridge.capture_release.set()
        self.until(lambda:not station.busy);self.assertEqual(bridge.max_active,1)
        self.assertEqual(bridge.calls,['stats','capture','ack','stats']);self.assertEqual(station.error,'')

    def test_pending_confirmation_rejects_diagnostics_then_resumes_same_identity(self):
        station,bridge,_,_=self.begin();bridge.block_stats=False;bridge.queued=1
        frame,image,mask=bridge.frame
        key=station.records.save(frame,image,mask,'manual',confirmation_endpoint=station.confirmation_endpoint())
        station.pending_ack=dict(frame);station.pending_stats=True
        before=station.records.confirmations.pending();image_hash=station.records.get(key)['image_sha256']
        with self.assertRaises(ValueError):station.action(dict(op='status'))
        self.assertEqual(bridge.calls,[]);self.assertEqual(station.records.confirmations.pending(),before)
        station.action(dict(op='resume_pending'));self.until(lambda:not station.busy and not station.retry_requested)
        self.assertEqual(bridge.calls,['stats','ack','stats']);self.assertEqual(station.captures,0)
        self.assertIsNone(station.pending_ack);self.assertIsNone(station.records.confirmations.pending())
        self.assertEqual(station.records.get(key)['image_sha256'],image_hash)

    def test_unsent_manual_retry_pending_stats_and_worker_busy_take_priority(self):
        for field,value in (('manual',True),('retry_requested',True),('pending_stats',True),('busy',True)):
            with self.subTest(field=field):
                station,bridge,_,_=self.begin()
                # Retain the real RLock so the worker cannot consume the intent
                # before this test checks the synchronous diagnostic admission.
                with station.lock:
                    setattr(station,field,value)
                    try:
                        with self.assertRaises(ValueError):station.action(dict(op='status'))
                        self.assertEqual(bridge.calls,[]);self.assertEqual(getattr(station,field),value)
                    finally:setattr(station,field,False)

    def test_status_remains_available_during_enabled_idle_gap(self):
        station,bridge,threads,_=self.begin()
        with station.lock:station.enabled=True;station.next_idle_poll=time.monotonic()+60
        outcome=self.blocked(station,bridge,threads);self.assertTrue(station.enabled)
        station.action(dict(op='pause'));bridge.stats_release.set()
        self.assertTrue(outcome['done'].wait(2));self.assertNotIn('error',outcome)
        self.assertEqual(bridge.calls,['stats']);self.assertFalse(station.busy)

    def test_missing_or_noncallable_legacy_stats_does_not_reserve_connection(self):
        for stats in ('missing',None):
            with self.subTest(stats=stats):
                class Legacy:
                    def close(self):pass
                    def capture(self,threshold):raise AssertionError('Unexpected capture')
                bridge=Legacy()
                if stats is None:bridge.stats=None
                station,_,_,_=self.begin(bridge)
                with self.assertRaises(ValueError):station.action(dict(op='status'))
                self.assertFalse(station.busy);self.assertEqual(station.operation_phase,'IDLE')


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DiagnosticReservationTests);names=[test.id() for test in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    output=ROOT/'reports/v148';output.mkdir(parents=True,exist_ok=True)
    summary=dict(passed=result.wasSuccessful(),tests=result.testsRun,test_ids=names,
                 failures=len(result.failures),errors=len(result.errors),
                 source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                for name in ('host/workstation.py','host/test_diagnostic_reservation.py')},
                 scope='Actual Station, fake no-argument legacy stats, event barriers and isolated temporary archive; no sockets or board.',
                 concurrency_evidence='Nonblocking control-lock acquisition and two observed worker lock entries during blocked stats; bridge max concurrent I/O remains 1.')
    (output/'diagnostic_reservation_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())

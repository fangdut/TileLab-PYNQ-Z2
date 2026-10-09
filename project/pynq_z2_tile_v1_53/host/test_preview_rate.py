"""Ordinary preview budgeting, event priority and real worker admission races."""
import tempfile
import threading
import time
import unittest
from pathlib import Path

from preview_policy import PreviewPolicy
from workstation import Station, EthernetBridge, Bridge
from recovery import TransientTransportError
import test_events


class PolicyTests(unittest.TestCase):
    def test_strict_choices(self):
        p=PreviewPolicy(2)
        for value in (True,False,None,'2',2.0,-1,1,3,10,[],{}):
            with self.assertRaises(ValueError):p.set_rate(value)
            self.assertEqual(p.fps,2)
        for value in (0,2,5):p.set_rate(value);self.assertEqual(p.fps,value)

    def test_actual_starts_enforce_no_catchup_burst(self):
        p=PreviewPolicy(2)
        self.assertTrue(p.due(10));p.started(10)
        self.assertFalse(p.due(10.499));self.assertTrue(p.due(10.5))
        # A long block earns one request, not the missed requests.
        self.assertTrue(p.due(20));p.started(20)
        self.assertFalse(p.due(20));self.assertFalse(p.due(20.499))
        self.assertEqual(p.preview_requests,2)

    def test_priority_does_not_consume_or_shift_budget(self):
        p=PreviewPolicy(2);p.started(10)
        p.started(10.1,priority=True);p.started(10.2,priority=True)
        self.assertEqual(p.last_start,10);self.assertFalse(p.due(10.4))
        self.assertTrue(p.due(10.5));self.assertEqual(p.priority_requests,2)

    def test_rate_changes_keep_last_actual_start(self):
        p=PreviewPolicy(5);p.started(10);p.set_rate(2)
        self.assertFalse(p.due(10.2));self.assertTrue(p.due(10.5))
        p.set_rate(5);self.assertTrue(p.due(10.2));p.set_rate(0)
        self.assertTrue(p.due(10.01))

    def test_idle_poll_never_waits_longer_than_200ms_or_preview_deadline(self):
        p=PreviewPolicy(2);p.started(10)
        self.assertAlmostEqual(p.next_poll(10.01),10.21)
        self.assertAlmostEqual(p.next_poll(10.4),10.5)
        self.assertAlmostEqual(p.next_poll(10.4,True),10.6)
        self.assertEqual(p.snapshot(),dict(event_priority=True,idle_poll_ms=200,
            preview_requests=1,priority_requests=0,deferred_polls=0))


class Source(EthernetBridge):
    """No socket; FPGA events and clock continue independently of host requests."""
    def __init__(self,queued=0):
        super().__init__('127.0.0.1');self.check_capture_health=False
        self.lock=threading.Lock();self.queued=queued;self.released=0
        self.calls=[];self.starts=[];self.parameters=[]
        self.frame=Bridge.decode_event(*test_events.packet(),1)
        self.pending_kind=None;self.fail_ack=False;self.fail_configure=False
        self.block=None;self.entered=threading.Event();self.release=threading.Event()

    def barrier(self,operation):
        if self.block==operation:
            self.block=None;self.entered.set()
            if not self.release.wait(3):raise TimeoutError('Test barrier not released')

    def configure(self,threshold):
        self.calls.append('configure');self.parameters.append(threshold);self.barrier('configure')
        if self.fail_configure:
            self.fail_configure=False;raise TransientTransportError('Lost configuration reply')

    def stats(self):
        self.calls.append('stats');self.barrier('stats')
        with self.lock:return dict(depth=self.queued,head=self.released,frames=60,boot_id=7)

    def capture(self,threshold):
        self.calls.append('capture');self.barrier('capture')
        with self.lock:
            self.pending_kind='event' if self.queued else 'preview'
            self.starts.append((time.monotonic(),self.pending_kind))
            f,img,mask=self.frame
            return dict(f,event_id=self.released+1,event_reason=1 if self.queued else 3),img,mask

    def ack(self,frame):
        self.calls.append('ack');self.barrier('ack')
        with self.lock:
            self.released=frame['event_id']
            if self.pending_kind=='event':self.queued-=1
            self.pending_kind=None
        if self.fail_ack:
            self.fail_ack=False;raise TransientTransportError('Lost ACK response')

    def inject(self,count):
        with self.lock:self.queued+=count


class StationTests(unittest.TestCase):
    def begin(self,b=None,fps=2):
        b=b or Source();tmp=tempfile.TemporaryDirectory(prefix='tile_preview_rate_')
        s=Station(tmp.name,b)
        def finish():
            b.release.set();s.exit=True;s.worker.join(4)
            self.assertFalse(s.worker.is_alive());s.records.db.close();tmp.cleanup()
        self.addCleanup(finish)
        s.action(dict(op='preview_rate',value=fps));return s,b

    def until(self,predicate,seconds=3):
        deadline=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>deadline:self.fail('Worker condition timed out')
            time.sleep(.005)

    def pause(self,s):
        s.action(dict(op='pause'));self.until(lambda:not s.busy)

    def test_real_bridge_default_2_and_compatible_subclass_unlimited(self):
        with tempfile.TemporaryDirectory() as d:
            b=EthernetBridge('127.0.0.1');s=Station(d,b)
            try:
                self.assertEqual(s.state()['preview_rate_fps'],2)
                self.assertTrue(s.state()['preview_rate_supported'])
            finally:s.exit=True;s.worker.join(2);s.records.db.close();b.close()
        s,b=self.begin(fps=0);self.assertEqual(s.state()['preview_rate_fps'],0)

    def test_unsupported_bridge_cannot_silently_limit_without_event_polling(self):
        class Legacy:
            def capture(self,threshold):raise AssertionError('No capture expected')
        with tempfile.TemporaryDirectory() as d:
            s=Station(d,Legacy())
            try:
                self.assertFalse(s.state()['preview_rate_supported'])
                for value in (2,5):
                    with self.assertRaises(ValueError):s.action(dict(op='preview_rate',value=value))
                s.action(dict(op='preview_rate',value=0))
            finally:s.exit=True;s.worker.join(2);s.records.db.close()

    def test_empty_queue_budget_and_status_polling(self):
        for fps in (2,5):
            with self.subTest(fps=fps):
                s,b=self.begin(fps=fps);s.action(dict(op='start'))
                self.until(lambda:len(b.starts)>=3);self.pause(s)
                starts=[t for t,k in b.starts]
                self.assertTrue(all(y-x>=1/fps-.002 for x,y in zip(starts,starts[1:])))
                self.assertTrue(all(k=='preview' for _,k in b.starts))
                self.assertGreaterEqual(b.calls.count('stats'),len(starts)*2)
                self.assertGreater(s.state()['preview_policy']['deferred_polls'],0)

    def test_events_arriving_between_previews_drain_before_deadline(self):
        s,b=self.begin();s.action(dict(op='storage',mode='archive'));s.action(dict(op='start'))
        self.until(lambda:len(b.starts)==1 and not s.busy)
        deadline=b.starts[0][0]+.5;b.inject(3)
        self.until(lambda:b.queued==0 and len(b.starts)>=4);self.pause(s)
        events=[t for t,k in b.starts if k=='event']
        self.assertEqual(len(events),3);self.assertLess(events[-1],deadline)
        self.assertEqual(s.auto_saved,3);self.assertEqual(len(s.records.all()),3)
        self.assertEqual(s.preview_policy.priority_requests,3)
        self.assertLess(abs(s.preview_policy.last_start-b.starts[0][0]),.01)

    def test_manual_capture_bypasses_budget_and_idle_poll(self):
        s,b=self.begin();s.action(dict(op='start'))
        self.until(lambda:len(b.starts)==1 and not s.busy);self.pause(s)
        old_start=s.preview_policy.last_start
        with s.lock:s.next_idle_poll=time.monotonic()+20
        s.action(dict(op='capture'));self.until(lambda:len(b.starts)==2 and not s.busy)
        self.assertLess(b.starts[1][0],old_start+.5)
        self.assertEqual(s.preview_policy.last_start,old_start)
        self.assertEqual(s.preview_policy.priority_requests,1);self.assertEqual(len(s.records.all()),1)

    def test_freeze_drains_events_but_never_ordinary_previews(self):
        s,b=self.begin(Source(3));s.action(dict(op='freeze_preview',enabled=True))
        s.action(dict(op='start'));self.until(lambda:b.released==3 and s.preview_policy.deferred_polls>=2)
        self.pause(s);self.assertEqual(len(b.starts),3)
        self.assertEqual(s.preview_policy.preview_requests,0);self.assertEqual(s.preview_policy.priority_requests,3)

    def test_pause_during_configuration_prevents_status_and_image(self):
        s,b=self.begin();b.block='configure';s.action(dict(op='start'))
        self.assertTrue(b.entered.wait(2));s.action(dict(op='pause'));b.release.set()
        self.until(lambda:not s.busy);self.assertEqual(b.calls,['configure'])
        self.assertEqual(s.cancelled_before_capture,1)

    def test_pause_during_status_prevents_queued_image(self):
        s,b=self.begin(Source(2));b.block='stats';s.action(dict(op='start'))
        self.assertTrue(b.entered.wait(2));s.action(dict(op='pause'));b.release.set()
        self.until(lambda:not s.busy);self.assertEqual(b.calls,['configure','stats'])
        self.assertEqual(b.queued,2);self.assertEqual(s.cancelled_before_capture,1)

    def test_old_preflight_cannot_revive_after_pause_then_start(self):
        s,b=self.begin();b.block='configure';s.action(dict(op='start'))
        self.assertTrue(b.entered.wait(2));s.action(dict(op='pause'));s.action(dict(op='start'))
        b.release.set();self.until(lambda:len(b.starts)>=1);self.pause(s)
        self.assertEqual(s.cancelled_before_capture,1)
        self.assertEqual(b.calls[:3],['configure','configure','stats'])

    def test_rate_or_freeze_changed_during_health_check_rechecks_before_admission(self):
        for freeze in (False,True):
            with self.subTest(freeze=freeze):
                s,b=self.begin(fps=0);b.check_capture_health=True;b.block='stats'
                s.action(dict(op='start'));self.assertTrue(b.entered.wait(2))
                if freeze:s.action(dict(op='freeze_preview',enabled=True))
                else:s.action(dict(op='preview_rate',value=2))
                b.release.set();self.until(lambda:b.calls.count('stats')>=2)
                if not freeze:self.until(lambda:len(b.starts)>=1)
                self.pause(s)
                self.assertEqual(b.calls[:3],['stats','configure','stats'])
                if freeze:self.assertFalse(b.starts)

    def test_pending_ack_reconciles_without_waiting_for_preview_budget(self):
        s,b=self.begin();b.fail_ack=True;s.action(dict(op='capture'))
        self.until(lambda:s.recovery.attempts==1 and not s.busy)
        with s.lock:s.next_idle_poll=time.monotonic()+20
        self.until(lambda:s.pending_ack is None and s.recovery.recovered==1)
        self.assertEqual(len(b.starts),1);self.assertEqual(b.calls.count('ack'),1)
        self.assertEqual(len(s.records.all()),1)

    def test_configure_failure_recovers_then_budgeted_preview(self):
        s,b=self.begin();b.fail_configure=True;s.action(dict(op='start'))
        self.until(lambda:len(b.starts)>=1 and s.recovery.recovered==1);self.pause(s)
        self.assertFalse(s.error);self.assertEqual(b.calls[:2],['configure','configure'])

    def test_threshold_is_configured_while_preview_budget_waits(self):
        s,b=self.begin();s.action(dict(op='start'))
        self.until(lambda:len(b.starts)==1 and not s.busy)
        s.action(dict(op='threshold',value=123));self.until(lambda:123 in b.parameters)
        self.pause(s);self.assertEqual(len(b.starts),1)

    def test_invalid_rate_is_rejected_without_changing_mode(self):
        s,b=self.begin()
        for value in (True,False,None,'2',2.0,-1,3,[],{}):
            with self.assertRaises(ValueError):s.action(dict(op='preview_rate',value=value))
        self.assertEqual(s.state()['preview_rate_fps'],2);self.assertFalse(b.calls)

    def test_invalid_queue_depth_stops_without_image_or_ack(self):
        for depth in (None,True,-1,13):
            with self.subTest(depth=depth):
                s,b=self.begin();b.stats=lambda:dict(depth=depth,head=0,frames=60,boot_id=7)
                s.action(dict(op='start'));self.until(lambda:bool(s.error) and not s.busy)
                self.assertIn('Invalid board event depth',s.error)
                self.assertFalse(s.enabled);self.assertFalse(b.starts)
                self.assertNotIn('ack',b.calls)


if __name__=='__main__':unittest.main(verbosity=2)

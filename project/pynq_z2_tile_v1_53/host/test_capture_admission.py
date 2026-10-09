import threading,time,unittest
from test_capture_health import HealthSource
import test_recovery as recovery
TransientTransportError=recovery.TransientTransportError

class BarrierHealth(HealthSource):
 def __init__(self,queued=0,block='stats'):
  super().__init__(1,queued);self.block=block;self.once=True
  self.entered=threading.Event();self.release=threading.Event();self.raise_after=False
 def barrier(self,operation):
  if self.once and operation==self.block:
   self.once=False;self.entered.set()
   if not self.release.wait(3):raise TimeoutError('Test barrier was not released')
   if self.raise_after:raise TransientTransportError('Controlled failure after stop')
 def configure(self,t):self.calls.append('configure');self.barrier('configure')
 def stats(self):self.barrier('stats');return super().stats()
 def capture(self,t):self.barrier('capture');return super().capture(t)
 def ack(self,f):self.barrier('ack');return super().ack(f)

class CaptureAdmissionTests(unittest.TestCase):
 until=recovery.RecoveryTests.until;begin=recovery.RecoveryTests.begin;finish=recovery.RecoveryTests.finish
 def setup_barrier(self,b,manual=False):
  s=self.begin(b);self.addCleanup(b.release.set)
  s.action(dict(op='capture' if manual else 'start'));self.assertTrue(b.entered.wait(3));return s
 def test_pause_while_preflight_status_waits_cancels_capture(self):
  b=BarrierHealth();s=self.setup_barrier(b);self.assertEqual(s.state()['capture_control']['phase'],'CHECK')
  s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy)
  self.assertEqual(b.calls,['stats']);self.assertEqual(s.captures,0)
  self.assertEqual(s.state()['capture_control'],dict(phase='IDLE',admitted=0,cancelled_before_capture=1,intent_epoch=1))
 def test_queued_event_is_not_taken_after_pause_during_status(self):
  b=BarrierHealth(1);s=self.setup_barrier(b);s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy)
  self.assertEqual(b.calls,['stats']);self.assertEqual(b.queued,1)
 def test_manual_request_cancelled_before_admission_is_not_saved(self):
  b=BarrierHealth();s=self.setup_barrier(b,manual=True);s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy)
  self.assertFalse(s.manual);self.assertEqual(s.records.all(),[]);self.assertNotIn('capture',b.calls)
 def test_new_start_does_not_revive_old_blocked_turn(self):
  b=BarrierHealth();s=self.setup_barrier(b);s.action(dict(op='pause'));s.action(dict(op='start'))
  b.release.set();self.until(lambda:s.captures>=1);s.action(dict(op='pause'));self.until(lambda:not s.busy)
  self.assertEqual(s.cancelled_before_capture,1);self.assertGreaterEqual(s.capture_admissions,1)
  self.assertFalse(s.error)
 def test_pause_during_frozen_configure_does_not_read_queued_image(self):
  b=BarrierHealth(1,block='configure');s=self.begin(b);self.addCleanup(b.release.set)
  s.action(dict(op='freeze_preview',enabled=True));s.action(dict(op='start'));self.assertTrue(b.entered.wait(3))
  self.assertEqual(s.state()['capture_control']['phase'],'CONFIGURE');s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy)
  self.assertNotIn('capture',b.calls);self.assertEqual(b.queued,1)
 def test_admitted_manual_frame_finishes_save_and_ack_after_pause(self):
  b=BarrierHealth(1,block='capture');s=self.setup_barrier(b,manual=True)
  self.assertEqual(s.state()['capture_control']['phase'],'CAPTURE');s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy)
  self.assertEqual(b.calls,['stats','capture','ack','stats']);self.assertEqual(len(s.records.all()),1)
  self.assertIsNone(s.pending_ack);self.assertEqual(s.capture_admissions,1)
 def test_admitted_failed_frame_is_not_retried_after_pause(self):
  b=BarrierHealth(1,block='capture');b.raise_after=True;s=self.setup_barrier(b,manual=True)
  s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy);time.sleep(.3)
  self.assertFalse(s.retry_requested);self.assertEqual(s.capture_admissions,1);self.assertEqual(s.records.all(),[])
 def test_saved_frame_confirmation_can_finish_after_pause(self):
  b=BarrierHealth(1,block='ack');s=self.setup_barrier(b,manual=True)
  self.assertEqual(s.state()['capture_control']['phase'],'ACK');self.assertEqual(len(s.records.all()),1)
  s.action(dict(op='pause'));b.release.set();self.until(lambda:not s.busy)
  self.assertIsNone(s.pending_ack);self.assertEqual(b.calls.count('capture'),1)
  self.assertEqual(s.records.confirmations.history()[0]['status'],'ACKNOWLEDGED')

if __name__=='__main__':unittest.main(verbosity=2)

import threading,time,unittest
from live_status_cache import LiveStatusCache

class LiveStatusCacheTests(unittest.TestCase):
 def wait(self,predicate,timeout=2):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   if predicate():return True
   time.sleep(.01)
  return False
 def test_first_read_is_nonblocking_while_source_waits(self):
  entered=threading.Event();release=threading.Event()
  def source():entered.set();release.wait(2);return dict(requested='real_video',observed='real_video',ready=True)
  c=LiveStatusCache(source,.01)
  try:
   self.assertTrue(entered.wait(1));begun=time.monotonic();v=c.read();elapsed=time.monotonic()-begun
   self.assertLess(elapsed,.1);self.assertFalse(v['cache_ready']);release.set();self.assertTrue(self.wait(lambda:c.read()['cache_ready']))
  finally:release.set();c.close()
 def test_complete_snapshot_and_age_are_published_together(self):
  n=[0]
  def source():n[0]+=1;return dict(requested='a',observed=str(n[0]))
  c=LiveStatusCache(source,.01)
  try:
   self.assertTrue(self.wait(lambda:c.read()['cache_ready']));v=c.read();self.assertEqual(v['requested'],'a');self.assertGreaterEqual(v['cache_age_seconds'],0);self.assertEqual(v['cache_error'],'')
  finally:c.close()
 def test_reader_failure_keeps_last_good_snapshot(self):
  n=[0]
  def source():
   n[0]+=1
   if n[0]>1:raise OSError('player busy')
   return dict(requested='good',observed='good')
  c=LiveStatusCache(source,.01)
  try:
   self.assertTrue(self.wait(lambda:c.read()['cache_ready']));self.assertTrue(self.wait(lambda:'player busy' in c.read()['cache_error']));v=c.read();self.assertEqual(v['observed'],'good')
  finally:c.close()
 def test_close_stops_reader(self):
  c=LiveStatusCache(lambda:{'requested':'x'},.01);self.assertTrue(self.wait(lambda:c.thread.is_alive()));c.close();self.assertFalse(c.thread.is_alive())
 def test_invalid_configuration(self):
  with self.assertRaises(ValueError):LiveStatusCache(None)
  with self.assertRaises(ValueError):LiveStatusCache(lambda:{},0)
  with self.assertRaises(ValueError):LiveStatusCache(lambda:{},float('inf'))
  with self.assertRaises(ValueError):LiveStatusCache(lambda:{},freshness=0)
 def test_stalled_reader_revokes_ready_without_blocking_reads(self):
  entered=threading.Event();release=threading.Event();n=[0]
  def source():
   n[0]+=1
   if n[0]>1:entered.set();release.wait(2)
   return dict(requested='good',ready=True,identity_confirmed=True,age_seconds=0)
  c=LiveStatusCache(source,.01,freshness=.05)
  try:
   self.assertTrue(entered.wait(1));time.sleep(.08)
   begun=time.monotonic();v=c.read();self.assertLess(time.monotonic()-begun,.1)
   self.assertEqual(v['state'],'TELEMETRY_STALE');self.assertFalse(v['ready']);self.assertFalse(v['identity_confirmed'])
  finally:release.set();c.close()
 def test_failure_revokes_previously_ready_confirmation(self):
  n=[0]
  def source():
   n[0]+=1
   if n[0]>1:raise OSError('unavailable')
   return dict(requested='good',ready=True,identity_confirmed=True)
  c=LiveStatusCache(source,.01)
  try:
   self.assertTrue(self.wait(lambda:bool(c.read()['cache_error']) and c.read()['cache_ready']))
   v=c.read();self.assertEqual(v['state'],'TELEMETRY_ERROR');self.assertFalse(v['ready'])
  finally:c.close()
 def test_cached_source_age_advances_and_expires(self):
  c=LiveStatusCache(lambda:dict(requested='good',ready=True,age_seconds=1.49),interval=10)
  try:
   self.assertTrue(self.wait(lambda:c.read()['cache_ready']));time.sleep(.04)
   v=c.read();self.assertGreater(v['age_seconds'],1.5);self.assertFalse(v['ready'])
  finally:c.close()
if __name__=='__main__':unittest.main(verbosity=2)

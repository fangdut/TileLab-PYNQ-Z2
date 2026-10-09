import json,tempfile,time,unittest
from pathlib import Path
from workstation import Records,Station,ArchiveCapacityError
from test_events import packet
from workstation import Bridge

class StorageTests(unittest.TestCase):
 def wait_capture(self,s):
  deadline=time.monotonic()+3
  while (s.captures<1 or s.busy) and not s.error and time.monotonic()<deadline:time.sleep(.01)
 def close(self,s):
  s.exit=True;s.worker.join(3);s.records.db.close()
 def setup_event(self,p):
  f,img,mask=Bridge.decode_event(*packet(),1)
  class Stub:
   acked=False
   def capture(self,t):return f,img,mask
   def ack(self,f):self.acked=True
   def close(self):pass
  b=Stub();return Station(p,b),b,f,img,mask
 def test_preview_confirms_event_without_file_or_database_growth(self):
  with tempfile.TemporaryDirectory() as p:
   s,b,_,_,_=self.setup_event(p)
   s.action(dict(op='start'));self.wait_capture(s);s.action(dict(op='pause'))
   self.assertTrue(b.acked);self.assertEqual(s.records.summary()['total'],0)
   self.assertEqual(s.skipped_automatic,1);self.assertEqual(list(s.records.dir.glob('*.png')),[]);self.close(s)
 def test_manual_capture_still_saves_in_preview(self):
  with tempfile.TemporaryDirectory() as p:
   s,b,_,_,_=self.setup_event(p);s.action(dict(op='capture'));self.wait_capture(s)
   self.assertEqual(s.records.summary()['total'],1);self.assertTrue(b.acked);self.close(s)
 def test_capacity_switches_to_preview_without_deleting_existing(self):
  with tempfile.TemporaryDirectory() as p:
   s,b,f,img,mask=self.setup_event(p);old=s.records.save(dict(f,event_id=2),img,mask,'manual')
   s.action(dict(op='storage',mode='archive',max_archive_mib=16))
   s.records.max_archive_bytes=s.records.storage()['used_bytes']+1
   s.action(dict(op='start'));self.wait_capture(s);s.action(dict(op='pause'))
   self.assertEqual(s.storage_policy.mode,'preview');self.assertIn('容量',s.storage_warning)
   self.assertEqual(s.records.file(old).read_bytes(),img);self.assertEqual(s.records.summary()['total'],1)
   self.assertTrue(b.acked);self.assertEqual(s.skipped_automatic,1)
   self.assertEqual(json.loads((Path(p)/'host/storage_policy.json').read_text())['mode'],'preview');self.close(s)
 def test_full_manual_archive_does_not_ack_or_remove(self):
  with tempfile.TemporaryDirectory() as p:
   s,b,_,_,_=self.setup_event(p);s.records.max_archive_bytes=1
   s.action(dict(op='capture'));self.wait_capture(s)
   self.assertIn('容量',s.error);self.assertFalse(b.acked);self.assertEqual(s.records.summary()['total'],0);self.close(s)
 def test_invalid_setting_does_not_change_saved_policy(self):
  with tempfile.TemporaryDirectory() as p:
   s,_,_,_,_=self.setup_event(p)
   for mode,limit in [('bad',1024),('preview',0),('archive',True)]:
    with self.assertRaises(ValueError):s.action(dict(op='storage',mode=mode,max_archive_mib=limit))
   self.assertEqual(s.storage_policy.mode,'preview');self.close(s)
 def test_byte_limit_is_checked_before_writing(self):
  with tempfile.TemporaryDirectory() as p:
   r=Records(p);r.max_archive_bytes=1
   with self.assertRaises(ArchiveCapacityError):r.save(dict(boot_id=1,event_id=1),b'i',b'm','test')
   self.assertEqual(list(r.dir.glob('*.png')),[]);r.db.close()

if __name__=='__main__':unittest.main()

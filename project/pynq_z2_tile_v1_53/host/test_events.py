import unittest,tempfile,json,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from workstation import Bridge,Records,Station,atomic

def packet():
 a=np.zeros((720,1280,4),np.uint8);a[:,:,:3]=[5,9,17];a[110:150,300:302,3]=1;a[220:280,800:802,3]=1
 d=[0]*40;m=[0]*24
 d[0]=1;d[1]=0x10100000;d[2]=60;d[3]=200;d[4]=(110<<16)|300;d[5]=(279<<16)|801;d[6]=13;d[7]=0x00f32407;d[8]=1;d[9]=2
 d[10:14]=[(110<<16)|300,(149<<16)|301,(220<<16)|800,(279<<16)|801];d[26:28]=[80,120];d[34]=7;d[35]=a.nbytes;d[36]=1000
 m[0]=0x54494c33;m[2]=7;m[6]=1;m[18]=420
 return a.tobytes(),d,m

class EventTests(unittest.TestCase):
 def test_manual_calibration_images_do_not_flood_automatic_review(self):
  f,img,mask=Bridge.decode_event(*packet(),1)
  with tempfile.TemporaryDirectory() as p:
   r=Records(p)
   manual=r.save(f,img,mask,'manual')
   auto=r.save(dict(f,event_id=3),img,mask,'hardware_alarm')
   best=r.save(dict(f,event_id=4,product_id=5,selection='FPGA_PRODUCT_BEST_FRAME'),img,mask,'manual')
   r.update(manual,'needs_recheck','Keep test evidence')
   self.assertEqual(r.page(kind='automatic')[1],2)
   self.assertEqual({v['id'] for v in r.page(kind='automatic')[0]},{auto,best})
   self.assertEqual(r.summary('manual')['pending'],1)
   self.assertEqual(r.page(kind='manual')[0][0]['note'],'Keep test evidence')
   self.assertEqual(r.page(kind='all')[1],3)
   with self.assertRaises(ValueError):r.page(kind="automatic' OR 1=1")
   r.db.close()
 def test_transient_windows_file_lock_retries_without_truncating_target(self):
  with tempfile.TemporaryDirectory() as p:
   dest=Path(p)/'response.txt';dest.write_bytes(b'previous');replace=Path.replace;attempts=[]
   def locked_then_released(src,target):
    attempts.append(1)
    if len(attempts)<3:
     self.assertEqual(dest.read_bytes(),b'previous');raise PermissionError('Sharing violation')
    return replace(src,target)
   with patch.object(Path,'replace',locked_then_released):atomic(dest,b'complete new response')
   self.assertEqual(dest.read_bytes(),b'complete new response');self.assertEqual(len(attempts),3)
 def test_two_hardware_regions_and_queue_metadata(self):
  f,_,_=Bridge.decode_event(*packet(),6000)
  self.assertEqual(f['boxes'],[[300,110,301,149],[800,220,801,279]]);self.assertEqual(f['region_areas'],[80,120]);self.assertEqual(f['event_id'],1)
 def test_invalid_regions_and_reboot_are_rejected(self):
  for idx,value in [(9,9),(9,0x80000002),(10,1400),(26,201),(34,8),(35,1)]:
   a,d,m=packet();d[idx]=value
   with self.assertRaises(ValueError):Bridge.decode_event(a,d,m,1)
 def test_same_event_retry_is_idempotent_and_keeps_review(self):
  f,img,mask=Bridge.decode_event(*packet(),1)
  with tempfile.TemporaryDirectory() as p:
   r=Records(p);key=r.save(f,img,mask,'hardware_alarm');r.update(key,'needs_recheck','Retained review')
   self.assertEqual(key,r.save(f,img,mask,'hardware_alarm'));self.assertEqual(len(r.all()),1);self.assertEqual(r.all()[0]['note'],'Retained review')
   with self.assertRaises(ValueError):r.save(f,b'wrong',mask,'hardware_alarm')
   r.db.close()
 def test_reencoded_png_retry_is_valid_but_modified_mask_is_rejected(self):
  import io
  from PIL import Image
  f,img,mask=Bridge.decode_event(*packet(),1)
  with tempfile.TemporaryDirectory() as p:
   r=Records(p);key=r.save(f,img,mask,'hardware_alarm')
   b=io.BytesIO();Image.open(io.BytesIO(img)).save(b,format='PNG',compress_level=9)
   self.assertEqual(key,r.save(f,b.getvalue(),mask,'hardware_alarm'))
   a=np.asarray(Image.open(io.BytesIO(mask))).copy();a[0,0]=255;b=io.BytesIO();Image.fromarray(a).save(b,format='PNG')
   with self.assertRaises(ValueError):r.save(f,img,b.getvalue(),'hardware_alarm')
   r.db.close()
 def test_archive_failure_does_not_ack(self):
  f,img,mask=Bridge.decode_event(*packet(),1)
  class Stub:
   acked=False
   def capture(self,t):return f,img,mask
   def ack(self,f):self.acked=True
   def close(self):pass
  with tempfile.TemporaryDirectory() as p:
   b=Stub();s=Station(p,b)
   def failure(*a,**kwargs):raise OSError('Injected disk full')
   s.records.save=failure;s.manual=True
   end=time.time()+3
   while not s.error and time.time()<end:time.sleep(.02)
   self.assertIn('disk full',s.error);self.assertFalse(b.acked);s.exit=True;s.worker.join(2);s.records.db.close()
 def test_archive_is_committed_before_ack(self):
  f,img,mask=Bridge.decode_event(*packet(),1)
  with tempfile.TemporaryDirectory() as p:
   class Stub:
    acked=False
    def capture(self,t):return f,img,mask
    def ack(inner,f):
     self.assertEqual(len(s.records.all()),1);inner.acked=True
    def stats(inner):
     self.assertTrue(inner.acked);return dict(depth=0,events=1,dropped=0,invalid=0)
    def close(self):pass
   b=Stub();s=Station(p,b);s.manual=True;end=time.time()+3
   while not b.acked and time.time()<end:time.sleep(.02)
   self.assertTrue(b.acked);s.exit=True;s.worker.join(2);self.assertEqual(s.state()['board_stats']['depth'],0);s.records.db.close()

if __name__=='__main__':unittest.main(verbosity=2)

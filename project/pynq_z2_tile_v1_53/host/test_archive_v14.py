import unittest,tempfile
from unittest.mock import patch
from workstation import Records

class ArchiveTests(unittest.TestCase):
 def test_completed_product_uses_boot_and_product_identity(self):
  with tempfile.TemporaryDirectory() as p:
   r=Records(p)
   f=dict(boot_id=17,event_id=90,product_id=4,selection='FPGA_PRODUCT_BEST_FRAME',frame_id=73)
   self.assertEqual(r.save(f,b'image',b'mask','hardware_alarm'),'tile_17_4')
   self.assertEqual(r.save(dict(f,event_id=91),b'image',b'mask','hardware_alarm'),'tile_17_4')
   self.assertEqual(r.summary()['total'],1)
   with self.assertRaises(ValueError):r.save(dict(f,frame_id=74),b'image',b'mask','hardware_alarm')
   self.assertEqual(r.save(dict(f,boot_id=18),b'image',b'mask','hardware_alarm'),'tile_18_4');r.db.close()
 def test_more_than_500_and_global_filtered_pagination(self):
  with tempfile.TemporaryDirectory() as p:
   r=Records(p)
   for n in range(505):
    r.save(dict(boot_id=1,event_id=n+1,frame_id=n,candidate_pixels=0,boxes=[],region_areas=[],config_word=0),b'image',b'mask','test')
   self.assertEqual(r.summary()['total'],505)
   rows,total=r.page(480);self.assertEqual(len(rows),24);self.assertEqual(total,505)
   r.update('pl_1_2','confirmed_crack','unique review')
   rows,total=r.page(review='confirmed_crack',query='unique');self.assertEqual(total,1);self.assertEqual(rows[0]['id'],'pl_1_2')
   self.assertEqual(r.summary()['confirmed'],1);r.db.close()
 def test_disk_reserve_retains_existing_records(self):
  with tempfile.TemporaryDirectory() as p:
   r=Records(p)
   with patch('workstation.shutil.disk_usage') as d:
    d.return_value.free=1
    with self.assertRaises(OSError):r.save(dict(boot_id=1,event_id=1),b'i',b'm','test')
   self.assertEqual(r.summary()['total'],0);r.db.close()

if __name__=='__main__':unittest.main(verbosity=2)

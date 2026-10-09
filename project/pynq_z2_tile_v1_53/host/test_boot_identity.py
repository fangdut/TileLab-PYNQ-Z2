import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'pynq_z2_tile_v1_53.sdk/reserve_boot_id.py'
spec=importlib.util.spec_from_file_location('boot_ids',p);boot_ids=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot_ids)

class BootIdentityTests(unittest.TestCase):
 def test_rejects_reserved_and_archived_ids_across_loader_restarts(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);(r/'review_records').mkdir();db=sqlite3.connect(r/'review_records/inspection.sqlite3')
   db.execute('CREATE TABLE events(payload TEXT)');db.execute('INSERT INTO events VALUES(?)',(json.dumps(dict(boot_id=7)),));db.commit();db.close()
   with patch.object(boot_ids.secrets,'randbits',side_effect=[0,0xffffffff,7,42]):self.assertEqual(boot_ids.reserve(r),42)
   with patch.object(boot_ids.secrets,'randbits',side_effect=[42,7,43]):self.assertEqual(boot_ids.reserve(r),43)
   self.assertEqual([v['boot_id'] for v in json.loads((r/'reports/boot_id_history.json').read_text())],[42,43])
   self.assertEqual(json.loads((r/'reports/current_boot_reservation.json').read_text())['boot_id'],43)

if __name__=='__main__':unittest.main(verbosity=2)

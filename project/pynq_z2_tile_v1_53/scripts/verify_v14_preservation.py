from pathlib import Path
import sqlite3,json,hashlib
R=Path(__file__).resolve().parents[1];old=R.parent/'pynq_z2_tile_v1_3/review_records';new=R/'review_records'
def rows(folder):
 c=sqlite3.connect(f'file:{(folder/"inspection.sqlite3").as_posix()}?mode=ro',uri=True)
 try:return dict(c.execute('SELECT id,payload FROM events'))
 finally:c.close()
a=rows(old);b=rows(new);checked=0
assert len(a)>=500
for key,payload in a.items():
 assert key in b,key
 for field in ('frame_id','image_sha256','mask_sha256'):
  assert json.loads(payload).get(field)==json.loads(b[key]).get(field),(key,field)
 for suffix in ('.png','_mask.png'):
  assert hashlib.sha256((old/(key+suffix)).read_bytes()).digest()==hashlib.sha256((new/(key+suffix)).read_bytes()).digest(),key
  checked+=1
result=dict(result='PASS',old_records=len(a),verified_original_files=checked,new_total_at_check=len(b))
(R/'reports/v14/preserved_records_check.json').write_text(json.dumps(result,indent=2));print(result)

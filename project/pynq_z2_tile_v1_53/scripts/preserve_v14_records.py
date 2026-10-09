"""Run after V1.4 receiver is paused, source is empty and its queue is drained."""
from pathlib import Path
import sqlite3,shutil,json,hashlib
old=Path('D:/Vivado/pynq_z2_tile_v1_4');new=Path(__file__).resolve().parents[1]
dest=new/'review_records';dest.mkdir(exist_ok=True)
src=sqlite3.connect(old/'review_records/inspection.sqlite3');dst=sqlite3.connect(dest/'inspection.sqlite3')
existing=dst.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'").fetchone()
if existing:assert dst.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0,'Do not overwrite new evidence'
src.backup(dst);n=dst.execute('SELECT COUNT(*) FROM events').fetchone()[0]
files=0
for key,payload in dst.execute('SELECT id,payload FROM events'):
    data=json.loads(payload)
    for suffix,hash_field in [('.png','image_sha256'),('_mask.png','mask_sha256')]:
        a=old/'review_records'/(key+suffix);b=dest/(key+suffix);assert a.is_file()
        shutil.copy2(a,b);assert hashlib.sha256(b.read_bytes()).hexdigest()==data[hash_field];files+=1
src.close();dst.close()
if (old/'reports/boot_id_history.json').exists():shutil.copy2(old/'reports/boot_id_history.json',new/'reports/boot_id_history.json')
result=dict(source=str(old),destination=str(new),records=n,images_verified=files,old_files_unchanged=True,sqlite_online_backup=True)
(new/'reports/v15/preserved_records.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

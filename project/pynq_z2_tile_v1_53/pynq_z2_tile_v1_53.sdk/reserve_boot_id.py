"""Reserve a non-reused 32-bit boot ID before running either ARM application.

IDs are checked against both a durable programming ledger and the image archive.
The complementary seed words are consumed and cleared by queue_init in firmware.
"""
from pathlib import Path
import datetime,json,os,secrets,sqlite3,msvcrt

def atomic_json(path,value):
 tmp=path.with_suffix('.tmp')
 with open(tmp,'w',encoding='utf-8') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def reserve(root):
 root=Path(root);reports=root/'reports';reports.mkdir(exist_ok=True)
 ledger=reports/'boot_id_history.json'
 with open(reports/'boot_id_history.lock','a+b') as lock:
  lock.seek(0,2)
  if lock.tell()==0:lock.write(b'0');lock.flush()
  lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
  try:
   history=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else []
   used={int(v['boot_id']) for v in history}
   archive=root/'review_records/inspection.sqlite3'
   if archive.exists():
    db=sqlite3.connect(archive.as_uri()+'?mode=ro',uri=True)
    try:
     for payload, in db.execute('SELECT payload FROM events'):
      event=json.loads(payload)
      if 'boot_id' in event:used.add(int(event['boot_id']))
    finally:db.close()
   while True:
    boot=secrets.randbits(32)
    if boot not in used and boot not in (0,0xffffffff):break
   record=dict(boot_id=boot,reserved_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
   history.append(record);atomic_json(ledger,history);atomic_json(reports/'current_boot_reservation.json',record)
   return boot
  finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

if __name__=='__main__':print(reserve(Path(__file__).resolve().parents[1]))

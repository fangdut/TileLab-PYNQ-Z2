"""One durable, saved-evidence ACK plus bounded completion history.

Uses the Records SQLite connection and lock. prepare() is committed in the
same transaction as the evidence row; previews deliberately do not write a
journal entry. A reboot retires an ACK identity, never acknowledges a new one.
"""
import hashlib,json
from datetime import datetime,timezone
IDENTITY_FIELDS=('boot_id','event_id','frame_id','product_id','pixel_crc32','recovery_generation')

def stamp():return datetime.now(timezone.utc).isoformat()

class ConfirmationJournal:
    def __init__(self,db,lock,directory):
        self.db=db;self.lock=lock;self.directory=directory
        with lock:
            db.execute('CREATE TABLE IF NOT EXISTS pending_confirmation(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS confirmation_history(id INTEGER PRIMARY KEY AUTOINCREMENT,created TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL)')
            db.commit()
    def prepare(self,record_id,frame,endpoint):
        # Caller holds the Records lock and commits this together with save().
        if not isinstance(endpoint,str) or not endpoint:raise ValueError('Confirmation endpoint missing')
        for key in ('boot_id','event_id','frame_id'):
            if type(frame.get(key)) is not int or not 0<=frame[key]<=0xffffffff:raise ValueError('Invalid confirmation identity')
        payload=dict(record_id=record_id,frame={k:frame.get(k) for k in IDENTITY_FIELDS},endpoint=endpoint,created=stamp())
        old=self.db.execute('SELECT payload FROM pending_confirmation WHERE id=1').fetchone()
        if old:
            previous=json.loads(old[0])
            if any(previous[k]!=payload[k] for k in ('record_id','endpoint')) or any(previous['frame'].get(k)!=payload['frame'].get(k) for k in IDENTITY_FIELDS):raise ValueError('A different saved event still awaits confirmation')
            return
        self.db.execute('INSERT INTO pending_confirmation VALUES(1,?)',(json.dumps(payload),))
    def pending(self):
        with self.lock:
            row=self.db.execute('SELECT payload FROM pending_confirmation WHERE id=1').fetchone()
            if row is None:return None
            value=json.loads(row[0]);key=value['record_id'];frame=value['frame']
            if not isinstance(key,str) or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in key):raise ValueError('Invalid pending evidence key')
            saved=self.db.execute('SELECT payload FROM events WHERE id=?',(key,)).fetchone()
            if not saved:raise ValueError('Pending confirmation evidence row is missing')
            data=json.loads(saved[0])
            for field in ('boot_id','frame_id','product_id','pixel_crc32','recovery_generation'):
                if frame.get(field)!=data.get(field):raise ValueError('Pending confirmation identity differs from saved evidence')
            for suffix,field in (('.png','image_sha256'),('_mask.png','mask_sha256')):
                if hashlib.sha256((self.directory/(key+suffix)).read_bytes()).hexdigest()!=data[field]:raise ValueError('Pending confirmation evidence failed integrity check')
            return value
    def settle(self,frame,status,observed_boot=None):
        if status not in ('ACKNOWLEDGED','ALREADY_ACKNOWLEDGED','BOARD_RESTARTED_UNCONFIRMED'):raise ValueError('Invalid confirmation result')
        with self.lock:
            # This operation owns its transaction; never commit or roll back
            # unrelated work accidentally left open by a caller.
            if self.db.in_transaction:raise RuntimeError('Cannot settle inside an existing transaction')
            try:
                # The Python lock protects only this connection. Reserve the
                # SQLite writer BEFORE reading identity, so another process
                # cannot replace the pending row before our DELETE id=1.
                self.db.execute('BEGIN IMMEDIATE')
                row=self.db.execute('SELECT payload FROM pending_confirmation WHERE id=1').fetchone()
                if row is None:self.db.rollback();return
                value=json.loads(row[0])
                if any(value['frame'][k]!=frame[k] for k in ('boot_id','event_id')):raise ValueError('Cannot settle a different confirmation')
                if value['frame'].get('recovery_generation')!=frame.get('recovery_generation'):raise ValueError('Cannot settle a different acquisition generation')
                value['observed_boot']=observed_boot
                self.db.execute('INSERT INTO confirmation_history(created,status,payload) VALUES(?,?,?)',(stamp(),status,json.dumps(value)))
                self.db.execute('DELETE FROM pending_confirmation WHERE id=1')
                self.db.execute('DELETE FROM confirmation_history WHERE id NOT IN (SELECT id FROM confirmation_history ORDER BY id DESC LIMIT 64)')
                self.db.commit()
            except Exception:self.db.rollback();raise
    def history(self):
        with self.lock:
            return [dict(json.loads(p),settled_at=c,status=s) for c,s,p in self.db.execute('SELECT created,status,payload FROM confirmation_history ORDER BY id DESC')]

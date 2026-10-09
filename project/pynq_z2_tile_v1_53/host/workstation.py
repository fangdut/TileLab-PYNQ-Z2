"""Local inspection workstation. Live pixels and decisions come ONLY from PL.

No reference detector is imported. JTAG is a slow debug image transport;
HDMI/PL processing continues at its own frame rate while DDR is downloaded.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from datetime import datetime,timezone
from dataclasses import dataclass
from contextvars import ContextVar
import argparse,hashlib,io,json,sqlite3,subprocess,threading,time,webbrowser,csv,os,shutil,copy
import numpy as np
from PIL import Image
import recipes
from frame_rate import FrameRate
from preview_policy import PreviewPolicy
from storage_policy import StoragePolicy,ArchiveCapacityError
from recovery import Recovery,TransientTransportError
from confirmation_journal import ConfirmationJournal
from archive_integrity import EvidenceReadError,read_verified_image
from archive_inventory import inventory,linked,ArchiveInventoryError
from review_revision import ReviewError,require_revision,MAX_REVISION
from event_identity import decode_event_identity
from stimulus_status import StimulusStatus,valid_source
from stimulus_command import make_command
from live_status_cache import LiveStatusCache

ROOT=Path(__file__).resolve().parents[1]
STATUSES={'pending','confirmed_crack','false_alarm','needs_recheck'}
def stamp():return datetime.now(timezone.utc).isoformat()
def png(a):
    b=io.BytesIO();Image.fromarray(np.ascontiguousarray(a)).save(b,format='PNG',compress_level=3);return b.getvalue()
def atomic(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with open(tmp,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    for attempt in range(100):
        try:tmp.replace(path);return
        except PermissionError:
            if attempt==99:raise
            time.sleep(.01)

class Records:
    STORAGE_SNAPSHOT_SECONDS=5.0
    @staticmethod
    def kind_clause(kind):
        automatic="(COALESCE(json_extract(payload,'$.selection'),'')='FPGA_PRODUCT_BEST_FRAME' OR COALESCE(json_extract(payload,'$.reason'),'')='hardware_alarm')"
        if kind=='all':return ''
        if kind=='automatic':return automatic
        if kind=='manual':return 'NOT '+automatic
        raise ValueError('Invalid archive category')
    def __init__(self,root=ROOT):
        self.root=Path(root);self.dir=self.root/'review_records'
        try:
            if linked(self.dir.lstat()):raise OSError('存档根目录是链接或重解析点；为避免访问外部证据，已停止打开存档')
        except FileNotFoundError:pass
        self.dir.mkdir(exist_ok=True)
        if linked(self.dir.lstat()):raise OSError('存档根目录是链接或重解析点；为避免访问外部证据，已停止打开存档')
        for name in ('inspection.sqlite3','inspection.sqlite3-wal','inspection.sqlite3-shm','inspection.sqlite3-journal'):
            try:
                if linked((self.dir/name).lstat()):raise OSError('存档数据库或日志是链接或重解析点；已停止打开存档')
            except FileNotFoundError:pass
        self.lock=threading.RLock();self.db=sqlite3.connect(self.dir/'inspection.sqlite3',check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,created TEXT,status TEXT,note TEXT,payload TEXT)');self.db.commit()
        self.db.execute('CREATE INDEX IF NOT EXISTS events_created ON events(created DESC)')
        self.db.execute('CREATE TABLE IF NOT EXISTS review_revisions(event_id TEXT PRIMARY KEY,revision INTEGER NOT NULL CHECK(revision>=0))');self.db.commit()
        self.confirmations=ConfirmationJournal(self.db,self.lock,self.dir)
        self.min_free_bytes=512*1024*1024
        self.max_archive_bytes=1024*1024*1024
        self.image_bytes=0
        self.data_version=self.db.execute('PRAGMA data_version').fetchone()[0]
        self._storage_snapshot=None;self._storage_observed_mono=None;self._storage_observed_at=None
        self._storage_dirty=True;self._storage_refresh_error='';self._storage_retry_at=0.0
        self._storage_clock=time.monotonic
        self.storage()
    def storage(self):
        """Always refresh capacity under the writer reservation, never cached."""
        with self.lock:
            # A process can publish PNGs then roll back/exit without changing
            # SQLite data_version. Capacity must therefore be counted afresh.
            # Reuse save()'s reservation; standalone snapshots take their own so
            # they cannot observe another cooperating save halfway through.
            owns_transaction=not self.db.in_transaction
            try:
                if owns_transaction:self.db.execute('BEGIN IMMEDIATE')
                result=inventory(self.dir,(row[0] for row in self.db.execute('SELECT id FROM events')))
                self.image_bytes=result['image_bytes']
                result=dict(result,max_bytes=self.max_archive_bytes,
                            free_disk_bytes=shutil.disk_usage(self.dir).free,
                            at_limit=result['used_bytes']>=self.max_archive_bytes)
            except Exception as error:
                self._storage_dirty=True
                self._storage_refresh_error=(type(error).__name__+': '+' '.join(str(error).split()))[:200]
                self._storage_retry_at=self._storage_clock()+self.STORAGE_SNAPSHOT_SECONDS
                raise
            finally:
                if owns_transaction and self.db.in_transaction:self.db.rollback()
            # Incomplete inventories replace older complete ones: cached UI data
            # must never hide a newly observed unreadable path or reparse point.
            self._storage_snapshot=copy.deepcopy(result)
            self._storage_observed_mono=self._storage_clock();self._storage_observed_at=stamp()
            self._storage_dirty=False;self._storage_refresh_error='';self._storage_retry_at=0.0
            return result
    def invalidate_storage_snapshot(self):
        with self.lock:
            self._storage_dirty=True;self._storage_retry_at=0.0
    def storage_snapshot(self):
        """Display only. Saving and capacity configuration use storage() fresh.

        A failed display refresh retains its original observation time and last
        values. A separate retry deadline limits UI retries, never quota checks.
        The Records lock coalesces simultaneous expired display requests.
        """
        with self.lock:
            now=self._storage_clock();refreshed=False
            expired=self._storage_observed_mono is None or now-self._storage_observed_mono>=self.STORAGE_SNAPSHOT_SECONDS
            if (self._storage_snapshot is None or self._storage_dirty or expired) and now>=self._storage_retry_at:
                try:self.storage();refreshed=True
                except (OSError,sqlite3.Error) as error:
                    self._storage_dirty=True
                    self._storage_refresh_error=(type(error).__name__+': '+' '.join(str(error).split()))[:200]
                    self._storage_retry_at=self._storage_clock()+self.STORAGE_SNAPSHOT_SECONDS
                    if self._storage_snapshot is None:
                        raise ArchiveInventoryError('暂无可用存档盘点；请检查文件和数据库，未将未知占用视为零')
            if self._storage_snapshot is None:
                raise ArchiveInventoryError('暂无可用存档盘点；等待重新清点，未将未知占用视为零')
            age=max(0.0,self._storage_clock()-self._storage_observed_mono)
            value=copy.deepcopy(self._storage_snapshot)
            # A storage limit is current configuration, not a sampled disk fact.
            value.update(max_bytes=self.max_archive_bytes,at_limit=value['used_bytes']>=self.max_archive_bytes,
                         snapshot_cached=not refreshed,snapshot_age_seconds=round(age,3),
                         snapshot_observed_at=self._storage_observed_at,
                         snapshot_stale=bool(self._storage_dirty or age>=self.STORAGE_SNAPSHOT_SECONDS or self._storage_refresh_error),
                         snapshot_refresh_error=self._storage_refresh_error)
            return value
    def all(self):
        with self.lock:
            return [self.decode_row(row) for row in self.db.execute(self.select_records()+' ORDER BY created DESC')]
    def page(self,offset=0,limit=24,review='all',query='',kind='all'):
        if not 0<=offset<=10000000 or not 1<=limit<=100 or review not in STATUSES|{'all'} or len(query)>200:raise ValueError('Invalid archive page')
        category=self.kind_clause(kind);clauses=[category] if category else [];args=[]
        if review!='all':clauses.append('status=?');args.append(review)
        if query:
            clauses.append("(CAST(json_extract(payload,'$.frame_id') AS TEXT) LIKE ? OR CAST(json_extract(payload,'$.product_id') AS TEXT) LIKE ? OR note LIKE ?)")
            args.extend(['%'+query+'%']*3)
        where=(' WHERE '+' AND '.join(clauses)) if clauses else ''
        with self.lock:
            total=self.db.execute('SELECT COUNT(*) FROM events'+where,args).fetchone()[0]
            rows=self.db.execute(self.select_records()+where+' ORDER BY created DESC,id DESC LIMIT ? OFFSET ?',args+[limit,offset])
            return [self.decode_row(row) for row in rows],total
    def summary(self,kind='all'):
        clause=self.kind_clause(kind)
        with self.lock:
            counts=dict(self.db.execute('SELECT status,COUNT(*) FROM events'+(' WHERE '+clause if clause else '')+' GROUP BY status'))
        return dict(total=sum(counts.values()),pending=counts.get('pending',0)+counts.get('needs_recheck',0),confirmed=counts.get('confirmed_crack',0),false_alarm=counts.get('false_alarm',0))
    def save(self,frame,image,mask,reason,confirmation_endpoint=None):
        completed=frame.get('selection')=='FPGA_PRODUCT_BEST_FRAME' and frame.get('product_id',0)>0
        key=(f"tile_{frame['boot_id']}_{frame['product_id']}" if completed else f"pl_{frame['boot_id']}_{frame['event_id']}" if 'event_id' in frame else f"pl_{frame['frame_id']}_{time.time_ns()}")
        payload=dict(frame,reason=reason,origin='FPGA_HDMI_CAPTURE',image_sha256=hashlib.sha256(image).hexdigest(),mask_sha256=hashlib.sha256(mask).hexdigest())
        with self.lock:
            self.invalidate_storage_snapshot()
            try:
                # Reserve the SQLite writer before inspecting the identity or
                # quota, and retain it while publishing both files. The Python
                # lock only protects this connection: a second station/import
                # process must not overwrite evidence before its INSERT loses
                # a primary-key race. WAL readers can still see committed rows.
                self.db.execute('BEGIN IMMEDIATE')
                old=self.db.execute('SELECT payload FROM events WHERE id=?',(key,)).fetchone()
                if old:
                    saved=json.loads(old[0])
                    for field in ('frame_id','candidate_pixels','boxes','region_areas','config_word','product_id','selection','selection_center_distance_x2','recovery_generation'):
                        if saved.get(field)!=payload.get(field):raise ValueError('Event identity reused with different FPGA decisions')
                    for suffix,field,new_data in (('.png','image_sha256',image),('_mask.png','mask_sha256',mask)):
                        old_data=(self.dir/(key+suffix)).read_bytes()
                        if hashlib.sha256(old_data).hexdigest()!=saved[field]:raise ValueError('Stored evidence failed integrity check')
                        if saved[field]!=hashlib.sha256(new_data).hexdigest():
                            # PNG compression may change between host versions;
                            # compare the unchanged pixels, not encoding bytes.
                            try:same=np.array_equal(np.asarray(Image.open(io.BytesIO(old_data))),np.asarray(Image.open(io.BytesIO(new_data))))
                            except (OSError,ValueError):same=False
                            if not same:raise ValueError('Event identity reused with different pixels')
                else:
                    if shutil.disk_usage(self.dir).free<len(image)+len(mask)+self.min_free_bytes:
                        raise OSError('磁盘可用空间不足 512 MiB；已保留旧记录，当前板端事件尚未确认，请释放空间后继续')
                    # This check shares the writer reservation with publication;
                    # another connection cannot spend the same remaining quota.
                    storage=self.storage()
                    if not storage['scan_complete']:
                        raise ArchiveInventoryError('存档文件清点未完成；请检查不可读文件或目录链接，当前未新增存图、未确认板端事件')
                    if storage['used_bytes']+len(image)+len(mask)+65536>self.max_archive_bytes:
                        raise ArchiveCapacityError('存档容量达到上限；旧证据保留，自动采集将转为仅预览')
                    for suffix,data in (('.png',image),('_mask.png',mask)):
                        path=self.dir/(key+suffix);old_size=path.stat().st_size if path.exists() else 0
                        atomic(path,data);self.image_bytes+=len(data)-old_size
                    self.db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(key,stamp(),'pending','',json.dumps(payload)))
                if confirmation_endpoint is not None:self.confirmations.prepare(key,frame,confirmation_endpoint)
                self.db.commit()
            except Exception:self.db.rollback();raise
            finally:
                # The quota scan precedes PNG publication. Even a failed save
                # may leave files, so it cannot be shown as a post-save snapshot.
                self.invalidate_storage_snapshot()
        return key
    @staticmethod
    def select_records():
        return 'SELECT events.*,COALESCE((SELECT revision FROM review_revisions WHERE event_id=events.id),0) FROM events'
    @staticmethod
    def decode_row(row):
        i,c,s,n,p,v=row
        return dict(json.loads(p),id=i,created=c,review=s,note=n,review_revision=v)
    def get(self,key):
        if not isinstance(key,str) or not key or len(key)>128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in key):raise ValueError('Invalid record key')
        with self.lock:
            row=self.db.execute(self.select_records()+' WHERE id=?',(key,)).fetchone()
            if row is None:raise ValueError('Record not found')
            return self.decode_row(row)
    def update(self,key,status,note):
        # Internal fixture/import API; production HTTP requires a read revision.
        # Still advance the revision so previously opened pages cannot overwrite it.
        return self._write_review(key,status,note,None,False)
    def _write_review(self,key,status,note,expected,verify_images):
        if status not in STATUSES or not isinstance(note,str) or len(note)>2000:raise ValueError('Invalid review')
        with self.lock:
            try:
                # Reserve the SQLite writer before reading the revision. A Python
                # lock alone cannot protect two separate service connections.
                self.db.execute('BEGIN IMMEDIATE')
                current=self.get(key);revision=current['review_revision']
                if expected is not None and expected!=revision:
                    raise ReviewError('这条记录已被其他窗口更新；本次草稿未提交，请查看最新结论',current=current)
                if type(revision) is not int or not 0<=revision<MAX_REVISION:
                    raise ReviewError('复核修订号无效或已达上限；原结论保持不变',code='REVIEW_REVISION_EXHAUSTED',http_status=409)
                if verify_images:self.read_image(key,False);self.read_image(key,True)
                self.db.execute('UPDATE events SET status=?,note=? WHERE id=?',(status,note,key))
                self.db.execute('INSERT INTO review_revisions(event_id,revision) VALUES(?,?) ON CONFLICT(event_id) DO UPDATE SET revision=excluded.revision',(key,revision+1))
                self.db.commit()
                return dict(current,review=status,note=note,review_revision=revision+1)
            except sqlite3.Error as error:
                self.db.rollback()
                raise ReviewError('复核存储暂不可写；请保留草稿并稍后重新读取',code='REVIEW_STORAGE_UNAVAILABLE',http_status=503) from error
            except Exception:
                self.db.rollback();raise
    def read_image(self,key,mask=False):
        if not isinstance(key,str) or not key or len(key)>128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in key):raise ValueError('Invalid record key')
        with self.lock:
            row=self.db.execute('SELECT payload FROM events WHERE id=?',(key,)).fetchone()
            if row is None:raise ValueError('Record not found')
            try:
                payload=json.loads(row[0]);expected=payload['mask_sha256' if mask else 'image_sha256']
            except (ValueError,KeyError,TypeError) as error:
                raise EvidenceReadError('存档元数据不完整；不能核对本次图像读取',code='ARCHIVE_METADATA_INVALID') from error
            return read_verified_image(self.dir/(key+('_mask' if mask else '')+'.png'),expected)
    def review(self,key,status,note,expected_revision=None):
        expected=require_revision(expected_revision)
        # Recheck both files inside the same metadata transaction before commit.
        return self._write_review(key,status,note,expected,True)
    def file(self,key,mask=False):
        with self.lock:
            if not self.db.execute('SELECT 1 FROM events WHERE id=?',(key,)).fetchone():raise ValueError('Record not found')
        return self.dir/(key+('_mask' if mask else '')+'.png')

class Bridge:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.run=self.root/'host/runtime';self.run.mkdir(exist_ok=True);self.proc=None;self.log=None
    def start(self):
        if self.proc and self.proc.poll() is None:return
        if not self.firmware_matches():
            raise RuntimeError('请先下载本版配套 BIT 与 ELF（正式网口程序使用 .sdk/program_ethernet.bat）；当前下载登记与文件不匹配')
        for name in ('stop','bridge_state.txt','request.txt','response.txt'):
            p=self.run/name
            if p.exists():p.unlink()
        self.log=open(self.root/'reports/live_jtag.log','ab',buffering=0)
        self.proc=subprocess.Popen(['D:/2025.2/Vitis/bin/xsdb.bat',str(self.root/'host/event_capture.tcl')],stdout=self.log,stderr=subprocess.STDOUT,creationflags=0x08000000)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            p=self.run/'bridge_state.txt'
            if p.exists() and p.read_text().strip()=='ready':return
            if self.proc.poll() is not None:raise RuntimeError('JTAG bridge exited; inspect reports/live_jtag.log')
            time.sleep(.1)
        raise RuntimeError('JTAG initialization timeout')
    def firmware_matches(self):
        marker=self.root/'reports/programmed_v153.json';ws=self.root/'pynq_z2_tile_v1_53.sdk'
        try:
            record=json.loads(marker.read_text());saved=record['sha256']
            app=record.get('active_application','hdmi_monitor')
            if app not in ('hdmi_monitor','hdmi_ethernet'):return False
            names=('system.bit','system.xsa',f'{app}/build/{app}.elf')
            return all(hashlib.sha256((ws/name).read_bytes()).hexdigest()==saved[name] for name in names)
        except (OSError,ValueError,KeyError,TypeError):return False
    def exchange(self,command):
        self.start();key=str(time.time_ns())
        atomic(self.run/'request.txt',f'{command[0]} {key} {command[1]}\n'.encode())
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            p=self.run/'response.txt'
            if p.exists():
                try:words=p.read_text().strip().split()
                except PermissionError:time.sleep(.01);continue
                if len(words)>1 and words[1]==key:
                    if words[0]=='error':raise RuntimeError(' '.join(words[2:]))
                    return key,words
            if self.proc.poll() is not None:raise RuntimeError('JTAG disconnected; unacknowledged events retained')
            time.sleep(.05)
        raise RuntimeError('Transfer timeout; unacknowledged events retained')
    def capture(self,threshold):
        key,words=self.exchange(('capture',str(threshold)))
        if words[0]!='ok' or len(words)!=67:raise ValueError('Malformed event response')
        elapsed=int(words[2]);d=list(map(int,words[3:43]));m=list(map(int,words[43:]))
        rawpath=self.run/f'frame_{key}.bin';raw=rawpath.read_bytes();rawpath.unlink()
        return self.decode_event(raw,d,m,elapsed)
    def ack(self,frame):
        self.exchange(('ack',f"{frame['boot_id']} {frame['event_id']}"))
    def stats(self):
        _,words=self.exchange(('status','0'))
        if words[0]!='status' or len(words)!=26:raise ValueError('Invalid status response')
        m=list(map(int,words[2:]))
        names=['magic','version','boot_id','heartbeat','head','tail','depth','events','dropped','captured','invalid','ack','request','reason','request_ack','threshold','enabled','gaps','frames','last_seq','active','config','error_status','ack_errors']
        return dict(zip(names,m))
    @staticmethod
    def decode_event(raw,d,m,elapsed):
        if len(d)!=40 or len(m)!=24 or m[0]!=0x54494c33 or d[34]!=m[2] or d[35]!=3686400:raise ValueError('Invalid queue header')
        identity=decode_event_identity(d[8],m[1])
        f,image,mask=Bridge.decode(raw,d[2],d[3],d[4],d[5],d[6],d[7],m[18],elapsed)
        n=d[9]&15
        if n>8 or d[9]&0x80000000:raise ValueError('Invalid hardware region snapshot')
        boxes=[];areas=[]
        for i in range(n):
            lo,hi=d[10+i*2:12+i*2];box=[lo&65535,lo>>16,hi&65535,hi>>16];area=d[26+i]
            if not(0<=box[0]<=box[2]<1280 and 0<=box[1]<=box[3]<720 and 32<=area<=d[3]):raise ValueError('Invalid PL region coordinates or area')
            boxes.append(box);areas.append(area)
        if sum(areas)>d[3]:raise ValueError('Region areas exceed captured mask')
        if f['config_word']&(1<<25) and (not f['config_word']&(1<<24) or m[1]<0x11800):raise ValueError('Four-pass captured mode/version mismatch')
        if f['config_word']&(1<<27) and (not f['config_word']&(1<<25) or not f['config_word']&(1<<24) or m[1]<0x12b00):raise ValueError('Wide weak captured mode/version mismatch')
        if f['config_word']&(1<<26) and m[1]<0x12500:raise ValueError('Low product gate captured mode/version mismatch')
        f.update(boxes=boxes,region_areas=areas,alarm=bool(n or d[9]&256),region_overflow=bool(d[9]&256),
          event_id=d[0],boot_id=d[34],firmware_version=m[1],**identity,captured_ms=d[36],queue_depth=m[6],
          event_total=m[7],events_dropped=m[8],board_captures=m[9],invalid_frames=m[10],capture_gaps=m[17],
          algorithm=('FPGA_DUALSCALE_VALLEY17_R16_HYST4_SUPPORT3_GRID32' if f['config_word']&(1<<27) else ('FPGA_VALLEY17_HYST4_SUPPORT3_GRID32' if f['config_word']&(1<<25) else 'FPGA_VALLEY17_HYST2_SUPPORT3_GRID32')) if f['config_word']&(1<<24) else 'FPGA_VALLEY17_GRID32_REGIONS8',transport='USB_JTAG_EVENT_QUEUE')
        if m[1]>=0x00010400:
            f.update(product_id=d[37],product_flags=d[38],selection_score=d[39]&0x7fffffff,selection_full_tile=bool(d[39]&0x80000000),selection='FPGA_PRODUCT_BEST_FRAME' if d[38]&32 else 'LIVE_PREVIEW')
        if m[1]>=0x00010500:
            f.update(selection_metric='CENTER_DISTANCE_X2',selection_center_distance_x2=d[39]&0x1ffff,selection_center_error_px=(d[39]&0x1ffff)/2)
        return f,image,mask
    @staticmethod
    def decode(raw,seq,n,lo,hi,status,cfg,frames,elapsed):
        if len(raw)!=1280*720*4 or status&0x80000000 or not status&4:raise ValueError('Invalid frame transport')
        if ((cfg>>16)&3)!=3:raise ValueError('Frame was captured with a non-inspection source configuration')
        a=np.frombuffer(raw,dtype=np.uint8).reshape(720,1280,4)
        # Transport consistency check only: no candidate extraction/classification.
        m=a[:,:,3]
        if np.any(m>1) or int(m.sum())!=n:raise ValueError('FPGA mask and snapshot disagree')
        if n:
            yy,xx=np.where(m);box=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]
            if box!=[lo&65535,lo>>16,hi&65535,hi>>16]:raise ValueError('FPGA coordinates and frame disagree')
        else:box=None
        frame=dict(frame_id=seq,candidate_pixels=n,boxes=[box] if status&8 and box else [],alarm=bool(status&8),
          config_word=cfg,status_word=status,device_frames=frames,transfer_ms=elapsed,width=1280,height=720,
          acquired_at=stamp(),transport='USB_JTAG_DEBUG',source='HDMI',algorithm='FPGA_OPPOSED_VALLEY17' if cfg&(1<<23) else 'FPGA_LOCAL_CONTRAST')
        return frame,png(a[:,:,2::-1]),png(m*255)
    def close(self):
        atomic(self.run/'stop',b'stop\n')

@dataclass(frozen=True)
class InspectionRequest:
    threshold:int
    enhance:bool
    passes:int
    low_gate:bool
    wide_weak:bool=False


class EthernetBridge:
    def __init__(self,address):
        from tcp_transport import EventTCP
        self.transport=EventTCP(address);self.enhance=True;self.passes=2;self.low_gate=False;self.wide_weak=False;self.check_capture_health=True
        self._inspection_request=ContextVar('inspection_request',default=None)
    def request_parameters(self,threshold):
        request=self._inspection_request.get()
        return request if request is not None else InspectionRequest(threshold,self.enhance,self.passes,self.low_gate,self.wide_weak)
    def bind_request(self,operation,threshold):
        # Station calls this while holding its control lock, then invokes the
        # returned callback after releasing it. Freeze ALL fields together.
        if operation not in ('capture','configure'):raise ValueError('Unknown inspection request')
        request=InspectionRequest(threshold,self.enhance,self.passes,self.low_gate,self.wide_weak)
        callback=getattr(self,operation)
        def invoke():
            # A scoped value preserves legacy capture/configure(threshold)
            # subclass dispatch, including overrides that call super() later.
            # Never temporarily overwrite mutable UI-requested bridge fields.
            token=self._inspection_request.set(request)
            try:return callback(request.threshold)
            finally:self._inspection_request.reset(token)
        return invoke
    def capture(self,threshold):
        request=self.request_parameters(threshold)
        kwargs=dict(enhance=request.enhance,passes=request.passes,low_gate=request.low_gate)
        if request.wide_weak: kwargs['wide_weak']=True
        packet=self.call(self.transport.capture,request.threshold,**kwargs)
        f,img,mask=Bridge.decode_event(*packet)
        f.update(transport='ETHERNET_TCP',**self.transport.last_timing);return f,img,mask
    def call(self,fn,*args,**kw):
        try:return fn(*args,**kw)
        except OSError as e:raise TransientTransportError(str(e)) from e
    def ack(self,frame):self.call(self.transport.ack,frame['boot_id'],frame['event_id'])
    def stats(self):return self.call(self.transport.stats)
    def configure(self,threshold):
        request=self.request_parameters(threshold)
        kwargs=dict(enhance=request.enhance,passes=request.passes,low_gate=request.low_gate)
        if request.wide_weak: kwargs['wide_weak']=True
        self.call(self.transport.configure,request.threshold,**kwargs)
    def close(self):self.transport.close()

class Station:
    def __init__(self,root=ROOT,bridge=None):
        self.root=Path(root);self.records=Records(root);self.bridge=bridge or Bridge(root);self.lock=threading.RLock()
        self.recipe_catalog=recipes.load(root);self.recipe_id='mvtec_hdmi_weak_v16';self.enabled=False;self.manual=False;self.busy=False;self.threshold=89;self.frame=None;self.image=None;self.mask=None
        self.error='';self.last_update=0;self.rate=FrameRate();self.processing_fps=None;self.captures=0;self.incident=False;self.board_stats=None
        self.storage_policy=StoragePolicy(self.root);self.records.max_archive_bytes=self.storage_policy.max_bytes
        self.skipped_automatic=0;self.last_skipped_identity=None;self.storage_warning='';self.auto_saved=0
        self.recovery=Recovery();self.retry_requested=False;self.intent_epoch=0
        self.operation_phase='IDLE';self.capture_admissions=0;self.cancelled_before_capture=0
        self.stimulus_status=StimulusStatus(self.root);self.stimulus_io_lock=threading.RLock();self.display_pending=None
        default=next((r for r in self.recipe_catalog if r['id']=='mvtec_hdmi_weak_v124'),None)
        if default and isinstance(self.bridge,EthernetBridge):
            self.recipe_id=default['id'];self.threshold=default['threshold']
            if isinstance(self.bridge,EthernetBridge):self.bridge.passes=default['weak_passes']
        self.pending_ack=None;self.pending_stats=False;self.last_success=0.0
        self.pending_check=False;self.journal_error='';self.synchronization_warning=''
        self.preview_frozen=False;self.next_idle_poll=0.0;self.health_observed=0.0
        self.preview_rate_supported=callable(getattr(self.bridge,'configure',None)) and callable(getattr(self.bridge,'stats',None))
        # Preserve legacy/custom bridge behavior; a real Ethernet station starts
        # with a bounded ordinary preview. Detection and queued evidence are not limited.
        self.preview_policy=PreviewPolicy(2 if type(self.bridge) is EthernetBridge else 0)
        self.log=[];self.live_frames={};self.exit=False;self.live_cache=LiveStatusCache(self._read_stimulus_status,stop=lambda:self.exit)
        try:
            pending=self.records.confirmations.pending()
            if pending:
                if pending['endpoint']!=self.confirmation_endpoint():raise ValueError('待确认记录属于另一板端连接；保持暂停并使用原连接恢复')
                self.pending_ack=pending['frame'];self.pending_stats=True;self.pending_check=True
                self.add_log('已恢复本地待确认记录；开始采集或恢复待确认会先核对板端身份')
        except Exception as e:self.journal_error=str(e);self.error='待确认记录检查失败：'+str(e)
        self.worker=threading.Thread(target=self.loop,daemon=True);self.worker.start()
    def confirmation_endpoint(self):
        if isinstance(self.bridge,EthernetBridge):return f'tcp://{self.bridge.transport.address}:{self.bridge.transport.port}'
        return 'jtag://'+str(self.root.resolve())
    def _read_stimulus_status(self):
        with self.stimulus_io_lock:return self.stimulus_status.snapshot()
    def finish_confirmation(self,status,observed_boot=None):
        # Durable completion first: if this fails after a board ACK, a restart
        # still reconciles the same saved identity instead of grabbing a new one.
        self.records.confirmations.settle(self.pending_ack,status,observed_boot)
        with self.lock:self.pending_ack=None;self.pending_check=False
    def reconcile_confirmation(self):
        pending=self.pending_ack
        if pending is None or not self.pending_check:return
        if not hasattr(self.bridge,'stats'):raise ValueError('Cannot reconcile pending identity without board status')
        with self.lock:self.operation_phase='RECONCILE'
        stats=self.bridge.stats();self.note_stats(stats)
        for key in ('boot_id','head','depth'):
            if type(stats.get(key)) is not int:raise ValueError('Incomplete board status for confirmation recovery')
        if stats['boot_id']!=pending['boot_id']:
            old=pending['boot_id'];event=pending['event_id']
            self.finish_confirmation('BOARD_RESTARTED_UNCONFIRMED',stats['boot_id'])
            with self.lock:
                self.synchronization_warning=f'板卡启动号 {old} → {stats["boot_id"]}；旧事件 {event} 的已存证据保留，旧确认已结束；重启期间未保存事件无法恢复'
                self.add_log(self.synchronization_warning)
        elif stats['head']==pending['event_id']:
            self.finish_confirmation('ALREADY_ACKNOWLEDGED',stats['boot_id'])
            self.add_log('板端已确认原事件；本地完成恢复，没有重复抓图')
        elif ((stats['head']+1)&0xffffffff)==pending['event_id'] and 1<=stats['depth']<=12:
            with self.lock:self.pending_check=False
        else:raise ValueError('待确认事件与板端队列不一致；保持原证据并暂停，未确认其他事件')
    def add_log(self,text):
        self.log.insert(0,dict(time=stamp(),text=text));self.log=self.log[:60]
    def skipped(self,frame):
        identity=(frame.get('boot_id'),frame.get('event_id',frame.get('frame_id')))
        if identity!=self.last_skipped_identity:self.skipped_automatic+=1;self.last_skipped_identity=identity
    def note_stats(self,stats):
        with self.lock:
            self.board_stats=dict(stats,observed_at=stamp());self.health_observed=time.monotonic()
            if 'frames' in stats and 'boot_id' in stats:self.processing_fps=self.rate.observe(stats['frames'],time.monotonic(),stats['boot_id'])
    def received_successfully(self):
        with self.lock:
            self.retry_requested=False;self.error='';self.last_success=time.monotonic()
            if self.recovery.success():self.add_log('连接已恢复；未确认事件处理完成')
    def capture_intent_current(self,epoch,manual):
        # Called only with self.lock held, including after each preflight stage.
        if epoch!=self.intent_epoch or not(self.enabled or manual or self.retry_requested):
            self.cancelled_before_capture+=1
            self.add_log('停止请求已生效：取消状态检查后尚未开始的取图')
            return False
        return True
    def bind_inspection_request(self,operation):
        # Called only under self.lock at the existing configure/admission
        # boundary. Legacy non-Ethernet bridges still receive one integer.
        if isinstance(self.bridge,EthernetBridge):return self.bridge.bind_request(operation,self.threshold)
        callback=getattr(self.bridge,operation);threshold=self.threshold
        return lambda:callback(threshold)
    def loop(self):
        while not self.exit:
            with self.lock:
                wanted=self.enabled or self.manual or self.retry_requested
                if wanted and self.recovery.expired(time.monotonic()):
                    self.error='网络恢复超时；未主动释放未确认事件，检查连接后可重新开始'
                    self.recovery.exhausted=True
                    self.enabled=self.manual=self.retry_requested=False;self.add_log(self.error)
                    wanted=False
                urgent=self.pending_ack is not None or self.pending_stats
                # The same short lock reserves the bridge for either this
                # worker or a manual diagnostic. Never share its TCP/JTAG I/O.
                run=wanted and not self.busy and self.recovery.ready(time.monotonic()) and (urgent or time.monotonic()>=self.next_idle_poll)
                manual=self.manual if run else False;epoch=self.intent_epoch
                if run:self.manual=False
                if run:self.busy=True;self.operation_phase='CHECK'
            if not run:time.sleep(.05);continue
            try:
                # Once saved/handled, retry only its ACK. If the reply was lost
                # after the board freed it, an idempotent ACK must not cause a
                # second manual screenshot of the next queued product.
                if self.pending_ack is None and not self.pending_stats:
                    queued=False
                    with self.lock:
                        controlled=self.preview_rate_supported and not manual and (self.preview_frozen or self.preview_policy.fps!=0)
                    if controlled:
                        with self.lock:
                            self.operation_phase='CONFIGURE'
                            configure=self.bind_inspection_request('configure')
                        configure()
                        # Pause during configuration must not advance to another
                        # network stage or revive the old turn after a new Start.
                        with self.lock:
                            if not self.capture_intent_current(epoch,manual):continue
                            self.operation_phase='CHECK'
                        stats=self.bridge.stats();self.note_stats(stats)
                        depth=stats.get('depth')
                        if type(depth) is not int or not 0<=depth<=12:
                            raise ValueError('Invalid board event depth; preview scheduling stopped')
                        queued=depth>0
                    # Health polling never precedes a pending ACK/reconciliation.
                    # Drain retained evidence even when new capture is unavailable.
                    if getattr(self.bridge,'check_capture_health',False):
                        if time.monotonic()-self.health_observed>=.2:
                            self.note_stats(self.bridge.stats())
                        health=(self.board_stats or {}).get('capture_health')
                        if health and not health['ready'] and self.board_stats['depth']==0:
                            self.received_successfully()
                            with self.lock:
                                if epoch==self.intent_epoch and manual:self.manual=True
                                self.next_idle_poll=time.monotonic()+.2
                            continue
                    # Admission and pause use the same lock. A pause while a
                    # preflight request is in progress invalidates this turn.
                    # Once admitted, the current frame may finish validation,
                    # saving and confirmation; never abandon half-handled proof.
                    with self.lock:
                        if not self.capture_intent_current(epoch,manual):continue
                        current_controlled=self.preview_rate_supported and not manual and (self.preview_frozen or self.preview_policy.fps!=0)
                        if current_controlled and not controlled:
                            # A UI change during a blocking health check must
                            # take effect before a new image request is admitted.
                            # Re-enter configure/status rather than guess that
                            # an old depth snapshot contains no retained event.
                            self.next_idle_poll=0
                            continue
                        now=time.monotonic();priority=manual or queued
                        if controlled and not priority and (self.preview_frozen or not self.preview_policy.due(now)):
                            self.preview_policy.deferred_polls+=1
                            self.next_idle_poll=self.preview_policy.next_poll(now,self.preview_frozen)
                            self.received_successfully()
                            continue
                        self.preview_policy.started(now,priority)
                        self.next_idle_poll=0
                        self.operation_phase='CAPTURE';self.capture_admissions+=1
                        capture=self.bind_inspection_request('capture')
                    frame,image,mask=capture()
                    frame.update(recipes.evidence(frame,self.recipe_catalog))
                    now=time.time()
                    with self.lock:
                        self.frame=frame;self.image=image;self.mask=mask;self.last_update=now;self.captures+=1
                        image_key=str(frame['frame_id'])+'_'+frame['acquired_at'];self.live_frames[image_key]=(image,mask)
                        while len(self.live_frames)>3:self.live_frames.pop(next(iter(self.live_frames)))
                        automatic=frame.get('event_reason') in (1,2) or ('event_id' not in frame and frame['alarm'] and not self.incident)
                        save_frame=manual or automatic and self.storage_policy.mode=='archive'
                        endpoint=self.confirmation_endpoint() if hasattr(self.bridge,'ack') else None
                        storage_limit=self.storage_policy.max_archive_mib
                        if save_frame:self.operation_phase='SAVE'
                    # Records owns its own writer lock/transaction. Disk IO must
                    # not retain the control lock needed by Pause. This already
                    # admitted frame still finishes saving before any board ACK;
                    # Pause only invalidates future admissions/retries.
                    if save_frame:
                        try:
                            self.records.save(frame,image,mask,'manual' if manual else 'hardware_alarm',confirmation_endpoint=endpoint)
                            with self.lock:
                                if automatic and not manual:self.auto_saved+=1
                                self.add_log(f"已留存帧 {frame['frame_id']} · {'人工抓拍' if manual else 'FPGA 候选报警'}")
                        except ArchiveCapacityError as e:
                            if manual:raise
                            # Storage-setting actions are rejected while this
                            # operation owns busy, including this policy write.
                            self.storage_policy.write('preview',storage_limit,atomic)
                            with self.lock:
                                self.storage_warning=str(e);self.skipped(frame);self.add_log(self.storage_warning)
                    elif automatic:
                        with self.lock:self.skipped(frame)
                    with self.lock:
                        self.incident=frame['alarm']
                        self.pending_ack=frame if hasattr(self.bridge,'ack') else None;self.pending_stats=True
                if self.pending_ack is not None:
                    self.reconcile_confirmation()
                    if self.pending_ack is not None:
                        with self.lock:self.operation_phase='ACK'
                        self.bridge.ack(self.pending_ack)
                        self.finish_confirmation('ACKNOWLEDGED',self.pending_ack['boot_id'])
                if self.pending_stats and hasattr(self.bridge,'stats'):
                    with self.lock:self.operation_phase='STATUS'
                    stats=self.bridge.stats()
                    self.note_stats(stats)
                with self.lock:
                    self.pending_stats=False
                self.received_successfully()
            except TransientTransportError as e:
                with self.lock:
                    if self.pending_ack is not None:self.pending_check=True
                    self.error=str(e)
                    if epoch==self.intent_epoch and (self.enabled or manual or self.retry_requested):
                        self.retry_requested=True
                        if manual and self.pending_ack is None and not self.pending_stats:self.manual=True
                        self.recovery.failed(time.monotonic(),e)
                        self.add_log(f'网络暂时中断，准备重试 {self.recovery.attempts}；最多 30 秒恢复窗口')
                    else:self.add_log('当前传输中断，保持暂停；板端事件未确认')
            except Exception as e:
                with self.lock:
                    if self.pending_ack is not None:self.pending_check=True
                    self.error=str(e);self.enabled=self.manual=self.retry_requested=False;self.recovery.reset();self.add_log('采集暂停：'+str(e))
            finally:
                with self.lock:self.busy=False;self.operation_phase='IDLE'
            time.sleep(.02 if isinstance(self.bridge,EthernetBridge) else .3)
    def capture_health_state(self):
        value=dict((self.board_stats or {}).get('capture_health') or {})
        if not value:return dict(supported=False,ready=False,state='UNKNOWN',message='等待采集健康状态')
        age=time.monotonic()-self.health_observed
        value.update(supported=True,observed_age_seconds=round(age,2),stale=age>1)
        return value
    def state(self,offset=0,limit=24,review='all',query='',kind='all'):
        # Compatibility endpoint for scripts. The browser uses independent
        # live and archive requests. Never nest Records -> Station locks.
        archive=self.archive_state(offset,limit,review,query,kind,wait=True)
        live=self.live_state();storage=dict(archive.pop('storage_inventory'),**live['storage'])
        storage['at_limit']=storage['used_bytes']>=storage['max_bytes']
        live['confirmation_journal']['history']=archive.pop('confirmation_history')
        return dict(live,**archive,storage=storage)
    def archive_state(self,offset=0,limit=24,review='all',query='',kind='all',*,wait=False):
        # No queued HTTP waiters behind a save/scan: the browser keeps its last
        # explicitly aged result and retries. RLock allows the existing Records
        # methods to retain their transaction/capacity/integrity semantics.
        if not self.records.lock.acquire(blocking=wait):return None
        try:
            storage=self.records.storage_snapshot()
            records,total=self.records.page(offset,limit,review,query,kind)
            return dict(records=records,records_total=total,archive=self.records.summary(kind),
                page_offset=offset,page_size=limit,storage_inventory=storage,
                confirmation_history=self.records.confirmations.history()[:8],archive_observed_at=stamp())
        finally:self.records.lock.release()
    def live_state(self):
        # No Records calls, database access or inventory scan in this path.
        # Player I/O occurs only in the background reader. HTTP and capture
        # control read a bounded-age snapshot; stale confirmation is revoked.
        input_status=self.live_cache.read()
        stimulus=input_status['requested'] or 'station_0'
        with self.lock:
            age=time.time()-self.last_update if self.last_update else None
            return copy.deepcopy(dict(mode='LIVE_HARDWARE',enabled=self.enabled,busy=self.busy,error=self.error,threshold=self.threshold,
                stimulus=stimulus,stimulus_status=input_status,display_pending=self.display_pending,recipes=self.recipe_catalog,requested_recipe=self.recipe_id,applied_threshold=((self.frame['config_word']>>8)&255 if self.frame else None),
                workstation_release='1.53.0-submission-candidate',requested_low_gate=(self.bridge.low_gate if isinstance(self.bridge,EthernetBridge) else False),requested_wide_weak=(self.bridge.wide_weak if isinstance(self.bridge,EthernetBridge) else False),capture_recovery=(self.board_stats or {}).get('capture_recovery'),capture_health=self.capture_health_state(),manual_waiting=self.manual,recovery=self.recovery.snapshot(time.monotonic()),preview_frozen=self.preview_frozen,
                preview_rate_fps=self.preview_policy.fps,preview_rate_supported=self.preview_rate_supported,preview_policy=self.preview_policy.snapshot(),
                confirmation_journal=dict(error=self.journal_error),synchronization_warning=self.synchronization_warning,
                transport_totals=(dict(received_bytes=self.bridge.transport.total_received_bytes,requests=self.bridge.transport.requests_sent) if isinstance(self.bridge,EthernetBridge) else None),
                pending_confirmation=bool(self.pending_ack),preview_stale=bool(age is not None and (age>2 or self.error or not(self.enabled or self.busy))),
                pending_operation=('ACK' if self.pending_ack is not None else 'STATUS' if self.pending_stats else None),
                capture_control=dict(phase=self.operation_phase,admitted=self.capture_admissions,cancelled_before_capture=self.cancelled_before_capture,intent_epoch=self.intent_epoch),
                preview_kind=('PRODUCT_EVIDENCE' if (self.frame or {}).get('selection')=='FPGA_PRODUCT_BEST_FRAME' else 'LIVE_SAMPLE'),
                wire_mode=(('packed' if self.bridge.transport.packed else 'rle') if self.bridge.transport.compression else 'raw') if isinstance(self.bridge,EthernetBridge) else None,
                compression_enabled=(self.bridge.transport.compression if isinstance(self.bridge,EthernetBridge) else False),storage=dict(mode=self.storage_policy.mode,
                    max_bytes=self.storage_policy.max_bytes,
                    max_archive_mib=self.storage_policy.max_archive_mib,not_archived_events=self.skipped_automatic,
                    auto_saved=self.auto_saved,warning=self.storage_warning),
                board_connected=bool(self.last_success and time.monotonic()-self.last_success<5 and not self.error),
                age_seconds=round(age,1) if age is not None else None,frame=self.frame,board_stats=self.board_stats,processing_fps=self.processing_fps,captures=self.captures,
                revision='V1.53',log=self.log,transport=('ETHERNET_TCP' if isinstance(self.bridge,EthernetBridge) else 'USB_JTAG_EVENT_QUEUE'),board_address=(self.bridge.transport.address if isinstance(self.bridge,EthernetBridge) else None),limitations='板端保留最多 12 个待确认事件，满队列会计数告警；FPGA 最多 8 个区域框，邻近缺陷可能合并；合成视频不能证明工业准确率。'))
    def diagnostic_status(self):
        with self.lock:
            if self.busy:raise ValueError('Wait for current transfer or diagnostics before requesting status')
            if self.pending_ack is not None or self.pending_stats or self.manual or self.retry_requested:
                raise ValueError('Finish or resume the pending capture/confirmation before diagnostics')
            read_status=getattr(self.bridge,'stats',None)
            if not callable(read_status):raise ValueError('Use board UART for Ethernet diagnostics')
            self.busy=True;self.operation_phase='DIAGNOSTIC'
        try:
            # Pause/Start may update intent during this wait. Only this request
            # owns the bridge; the worker and conflicting actions cannot enter.
            value=read_status()
            with self.lock:
                self.board_stats=dict(value,observed_at=stamp())
                return self.board_stats
        finally:
            with self.lock:
                # Release only the reservation: never restore stale intent,
                # clear pending evidence, or start an unsolicited acquisition.
                self.busy=False;self.operation_phase='IDLE'
    def configure_storage(self,body):
        # Reserve worker admission while checking/writing the policy, but never
        # retain the control lock over filesystem or Records work. A separate
        # candidate keeps live settings unchanged until publication succeeds.
        with self.lock:
            if self.busy:raise ValueError('Wait for current transfer or diagnostics before changing storage')
            mode=body.get('mode');limit=body.get('max_archive_mib',self.storage_policy.max_archive_mib)
            self.storage_policy.validate(mode,limit)
            candidate=copy.copy(self.storage_policy)
            self.busy=True;self.operation_phase='STORAGE'
        try:
            if mode=='archive' and self.records.storage()['used_bytes']+65536>=limit*1024*1024:
                raise ValueError('已有存档超过容量上限；请先清理或提高上限。原存储设置保持不变。')
            candidate.write(mode,limit,atomic)
            # The worker cannot save while busy; archive readers may finish
            # before the new in-memory limit is published. No nested locks.
            with self.records.lock:self.records.max_archive_bytes=candidate.max_bytes
            with self.lock:
                self.storage_policy=candidate;self.storage_warning=''
                self.add_log('存储模式：'+('仅预览，自动事件不留图' if mode=='preview' else '自动留图，满额转为仅预览')+f'；上限 {limit} MiB')
            return dict(ok=True)
        finally:
            with self.lock:
                # Keep the newest Pause/Start intent. Releasing this reservation
                # does not itself request capture or restore an earlier mode.
                self.busy=False;self.operation_phase='IDLE'
    def publish_display(self,body):
        value=body.get('value')
        if not valid_source(value):raise ValueError('Unknown stimulus')
        payload,request_id=make_command(value)
        with self.lock:
            if self.display_pending is not None:raise ValueError('输入命令正在保存，请等待本次结果后再切换')
            self.display_pending=dict(value=value,request_id=request_id,started_at=stamp())
        try:
            # Single publisher protects the shared .tmp file. This local source
            # change does not reserve the board transport or block Pause.
            atomic(self.root/'host/display_command.txt',payload)
            with self.stimulus_io_lock:self.stimulus_status.requested(value,request_id)
            with self.lock:
                self.add_log('已请求 HDMI 输入 '+value+'，编号 '+request_id[:8]+'；等待播放器采用同一编号')
            return dict(ok=True,request_id=request_id)
        finally:
            with self.lock:self.display_pending=None
    def action(self,body):
        op=body.get('op')
        if op=='status':return self.diagnostic_status()
        if op=='storage':return self.configure_storage(body)
        if op=='display':return self.publish_display(body)
        with self.lock:
            if op=='start':
                if self.journal_error:raise ValueError(self.error)
                if self.pending_ack is not None:self.pending_check=True
                self.error='';self.enabled=True;self.next_idle_poll=0;self.recovery.reset();self.rate.reset();self.processing_fps=None;self.add_log('开始接收开发板图像')
            elif op=='resume_pending':
                if self.journal_error:raise ValueError(self.error)
                if self.busy or self.enabled:raise ValueError('Pause current reception before resuming only the pending operation')
                if self.pending_ack is None and not self.pending_stats:raise ValueError('No pending confirmation to resume')
                self.pending_check=self.pending_ack is not None;self.retry_requested=True;self.error='';self.next_idle_poll=0;self.recovery.reset();self.add_log('仅恢复待确认处理，不请求下一张图像')
            elif op=='pause':
                self.enabled=self.manual=self.retry_requested=False;self.intent_epoch+=1;self.recovery.reset();self.add_log('已暂停新采集和后续重试，当前传输完成后停止')
            elif op=='freeze_preview':
                enabled=body.get('enabled')
                if type(enabled) is not bool:raise ValueError('Preview freeze must be Boolean')
                self.preview_frozen=enabled;self.next_idle_poll=0
                self.add_log('预览已冻结；后台继续接收事件，留图取决于存储模式' if enabled else '恢复连续抽样预览')
            elif op=='preview_rate':
                value=body.get('value')
                if type(value) is not int or value not in (0,2,5):raise ValueError('Preview rate must be the integer 0, 2 or 5')
                if value and not self.preview_rate_supported:raise ValueError('This bridge cannot poll events independently of image capture')
                self.preview_policy.set_rate(value);self.next_idle_poll=0
                self.add_log('普通预览请求上限：'+(str(value)+' 帧/秒' if value else '不限')+'；报警事件与人工抓拍优先，FPGA 检测速度保持不变')
            elif op=='disconnect':
                if self.busy or self.enabled or self.manual or self.retry_requested:raise ValueError('Pause and finish current transfer before disconnecting')
                self.bridge.close()
            elif op=='capture':
                if self.journal_error:raise ValueError(self.error)
                if self.busy or self.retry_requested or self.pending_ack is not None or self.pending_stats:raise ValueError('Finish or resume the pending event before another manual capture')
                self.error='';self.manual=True;self.next_idle_poll=0;self.recovery.reset()
            elif op=='threshold':
                n=body.get('value')
                if type(n) is not int or not 1<=n<=255:raise ValueError('Threshold must be 1..255')
                self.threshold=n;self.recipe_id='custom';self.add_log(f'阈值 {n} 已请求；在瓷砖间隙应用到 FPGA，当前瓷砖继续使用原参数')
            elif op=='recipe':
                recipe=next((r for r in self.recipe_catalog if r['id']==body.get('value')),None)
                if recipe is None:raise ValueError('Unknown material recipe')
                if recipe.get('weak_passes',2)==4 and not isinstance(self.bridge,EthernetBridge):
                    raise ValueError('四级弱裂纹配方需要以太网控制连接；JTAG 调试通道不发送该模式请求')
                low_gate=recipe.get('low_gate',False)
                wide_weak=recipe.get('wide_weak',False)
                if wide_weak:
                    if not isinstance(self.bridge,EthernetBridge):raise ValueError('双尺度弱裂纹配方需要以太网控制连接')
                    version=(self.board_stats or {}).get('version')
                    if type(version) is not int or version<0x12b00:
                        raise ValueError('双尺度弱裂纹配方需要 V1.52 或更新固件；请先连接并读取板端状态')
                if low_gate:
                    if not isinstance(self.bridge,EthernetBridge):raise ValueError('低亮度产品门禁需要以太网控制连接；JTAG 调试通道不发送该模式请求')
                    version=(self.board_stats or {}).get('version')
                    if type(version) is not int or version<0x12500:
                        raise ValueError('低亮度产品门禁需要 V1.37 或更新固件；请先连接并读取板端状态')
                if isinstance(self.bridge,EthernetBridge):
                    self.bridge.enhance=recipe.get('requires_weak_support',True);self.bridge.passes=recipe.get('weak_passes',2);self.bridge.low_gate=low_gate;self.bridge.wide_weak=wide_weak
                self.threshold=recipe['threshold'];self.recipe_id=recipe['id'];self.add_log('材料参数已请求：'+recipe['name']+'；等待瓷砖间隙应用')
            elif op=='compression':
                enabled=body.get('enabled')
                if type(enabled) is not bool or not isinstance(self.bridge,EthernetBridge):raise ValueError('Ethernet compression requires a Boolean mode')
                self.bridge.transport.packed=False;self.bridge.transport.compression=enabled;self.add_log('传输模式：'+('自动无损压缩' if enabled else '原始数据对照'))
            elif op=='wire_mode':
                mode=body.get('value')
                if mode not in ('rle','packed','raw') or not isinstance(self.bridge,EthernetBridge):raise ValueError('Invalid Ethernet transfer mode')
                self.bridge.transport.packed=mode=='packed';self.bridge.transport.compression=mode!='raw'
                self.add_log('已请求传输模式：'+{'rle':'游程/原始自适应兼容模式','packed':'无损位打包，节省带宽，耗时见实测','raw':'原始数据对照'}[mode]+'；后续取图请求生效，当前帧编码见传输信息')
            else:raise ValueError('Unknown action')
        return dict(ok=True)

def handler(station):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,data,content='application/json; charset=utf-8',code=200,filename=None,archive_sha=None):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(code);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            if archive_sha:
                self.send_header('X-Archive-Integrity','sha256-verified');self.send_header('X-Archive-SHA256',archive_sha)
            self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_GET(self):
            u=urlparse(self.path);q=parse_qs(u.query)
            try:
                if u.path=='/':return self.send((ROOT/'host/workstation.html').read_bytes(),'text/html; charset=utf-8')
                if u.path=='/api/benchmark':
                    p=station.root/'reports/v148/validation_summary.json'
                    if not p.exists():return self.send({'error':'Benchmark is not ready'},code=503)
                    result=json.loads(p.read_text(encoding='utf-8'))
                    return self.send(result)
                if u.path=='/api/benchmark-image':
                    idx=int(q.get('id',['-1'])[0])
                    if not 0<=idx<10000:raise ValueError('Invalid benchmark image')
                    p=station.root/'reports/v132/real_board'/f'real_{idx:03d}_original.png'
                    if not p.exists():raise ValueError('Benchmark image not found')
                    return self.send(p.read_bytes(),'image/png')
                if u.path=='/weak-comparison.png':return self.send((station.root/'reports/weak_crack/comparison.png').read_bytes(),'image/png')
                if u.path=='/review_session.js':return self.send((ROOT/'host/review_session.js').read_bytes(),'text/javascript; charset=utf-8')
                if u.path=='/status_channel.js':return self.send((ROOT/'host/status_channel.js').read_bytes(),'text/javascript; charset=utf-8')
                if u.path=='/benchmark':return self.send((station.root/'host/benchmark.html').read_bytes(),'text/html; charset=utf-8')
                if u.path=='/api/live':return self.send(station.live_state())
                if u.path=='/api/archive':
                    archive=station.archive_state(int(q.get('offset',['0'])[0]),int(q.get('limit',['24'])[0]),q.get('review',['all'])[0],q.get('query',[''])[0],q.get('kind',['all'])[0])
                    if archive is None:return self.send({'error':'存档正在写入或盘点，请稍后刷新；实时状态独立更新','code':'ARCHIVE_BUSY'},code=503)
                    return self.send(archive)
                if u.path=='/api/state':return self.send(station.state(int(q.get('offset',['0'])[0]),int(q.get('limit',['24'])[0]),q.get('review',['all'])[0],q.get('query',[''])[0],q.get('kind',['all'])[0]))
                if u.path=='/api/record':return self.send(station.records.get(q.get('id',[''])[0]))
                if u.path=='/api/image':
                    key=q.get('id',[''])[0];is_mask=q.get('mask',['0'])[0]=='1'
                    if key:
                        data,digest=station.records.read_image(key,is_mask)
                        return self.send(data,'image/png',archive_sha=digest)
                    else:
                        frame_key=q.get('frame',[''])[0]
                        with station.lock:
                            data=(station.live_frames.get(frame_key,(None,None))[int(is_mask)] if frame_key else (station.mask if is_mask else station.image))
                    if not data:return self.send({'error':'No hardware frame yet'},code=404)
                    return self.send(data,'image/png')
                if u.path=='/api/export':
                    rows=station.records.all()
                    if q.get('format',[''])[0]=='csv':
                        f=io.StringIO(newline='');w=csv.writer(f);w.writerow(['id','created','boot_id','product_id','frame_id','recovery_generation','selection','selection_full_tile','review','candidate_pixels','boxes','applied_threshold','recipe_id','recipe_sha256','image_sha256','note','review_revision'])
                        for r in rows:
                            # Spreadsheet formula injection is prevented for editable notes.
                            note=r['note'];note="'"+note if note and note[0] in '=+-@' else note
                            w.writerow([r['id'],r['created'],r.get('boot_id',''),r.get('product_id',''),r['frame_id'],r.get('recovery_generation',''),r.get('selection',''),r.get('selection_full_tile',''),r['review'],r['candidate_pixels'],json.dumps(r['boxes']),r.get('applied_threshold',''),r.get('recipe_id',''),r.get('recipe_sha256',''),r['image_sha256'],note,r['review_revision']])
                        return self.send(f.getvalue().encode('utf-8-sig'),'text/csv; charset=utf-8',filename='inspection-review.csv')
                    return self.send(dict(origin='FPGA_HDMI_CAPTURE',records=rows),filename='inspection-review.json')
                return self.send({'error':'Not found'},code=404)
            except ReviewError as e:return self.send({'error':str(e),'code':e.code,'current':e.current},code=e.http_status)
            except EvidenceReadError as e:return self.send({'error':str(e),'code':e.code},code=e.http_status)
            except ValueError as e:return self.send({'error':str(e)},code=404)
            except (OSError,sqlite3.Error) as e:return self.send({'error':str(e),'code':'ARCHIVE_UNAVAILABLE'},code=503)
        def do_POST(self):
            try:
                origin=self.headers.get('Origin');valid={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=8192:raise ValueError('Invalid body size')
                self.connection.settimeout(2);payload=self.rfile.read(n)
                if origin and origin not in valid:return self.send({'error':'Local origin required'},code=403)
                b=json.loads(payload)
                if self.path=='/api/action':return self.send(station.action(b))
                if self.path=='/api/review':
                    result=station.records.review(b['id'],b['review'],b.get('note',''),b.get('expected_revision'));return self.send({'ok':True,'record':result})
                return self.send({'error':'Not found'},code=404)
            except ReviewError as e:return self.send({'error':str(e),'code':e.code,'current':e.current},code=e.http_status)
            except EvidenceReadError as e:return self.send({'error':str(e),'code':e.code},code=e.http_status)
            except (ValueError,TypeError,KeyError) as e:return self.send({'error':str(e)},code=400)
            except (RuntimeError,OSError,sqlite3.Error) as e:return self.send({'error':str(e)},code=503)
    return Handler

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8770);ap.add_argument('--open',action='store_true');ap.add_argument('--ethernet',default='169.254.200.10',help='Private IPv4 of board running the supplied SG Ethernet ELF (0x12b00)');args=ap.parse_args()
    station=Station(bridge=EthernetBridge(args.ethernet) if args.ethernet else None);server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(station))
    url=f'http://127.0.0.1:{args.port}';print(url+' | FPGA live workstation',flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:station.exit=True;station.live_cache.close();station.bridge.close();server.server_close()


from pathlib import Path
import unittest,tempfile,json,threading,urllib.request,urllib.error,sqlite3
from concurrent.futures import ThreadPoolExecutor
from workstation import Records,Station,ThreadingHTTPServer,handler
from review_revision import ReviewError,MAX_REVISION
from archive_integrity import EvidenceReadError
import test_workstation as fixtures

class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_revision_');self.root=Path(self.tmp.name);self.r=Records(self.root)
        self.frame,self.image,self.mask=fixtures.FrameTests().decode(fixtures.FrameTests().packet())
        self.key=self.r.save(self.frame,self.image,self.mask,'isolated_revision_test')
    def tearDown(self):self.r.db.close();self.tmp.cleanup()
    def test_initial_get_page_export_revision_zero(self):
        self.assertEqual(self.r.get(self.key)['review_revision'],0)
        self.assertEqual(self.r.all()[0],self.r.page()[0][0]);self.assertEqual(self.r.get(self.key),self.r.all()[0])
    def test_older_page_cannot_overwrite_later_conclusion(self):
        saved=self.r.review(self.key,'confirmed_crack','first',0)
        with self.assertRaises(ReviewError) as e:self.r.review(self.key,'false_alarm','stale',0)
        self.assertEqual(e.exception.code,'REVIEW_CONFLICT');self.assertEqual(e.exception.current,saved);self.assertEqual(self.r.get(self.key),saved)
    def test_duplicate_request_conflicts_without_second_write(self):
        self.r.review(self.key,'false_alarm','same',0)
        with self.assertRaises(ReviewError):self.r.review(self.key,'false_alarm','same',0)
        self.assertEqual(self.r.get(self.key)['review_revision'],1)
    def test_same_content_round_trip_still_invalidates_old_page(self):
        self.r.review(self.key,'confirmed_crack','A',0);self.r.review(self.key,'false_alarm','B',1);self.r.review(self.key,'pending','',2)
        with self.assertRaises(ReviewError):self.r.review(self.key,'false_alarm','old zero',0)
        self.assertEqual(self.r.get(self.key)['review_revision'],3)
    def test_internal_import_also_invalidates_open_pages(self):
        self.r.update(self.key,'needs_recheck','import changed')
        with self.assertRaises(ReviewError):self.r.review(self.key,'false_alarm','old',0)
    def test_missing_and_noninteger_revisions_rejected(self):
        for value in (None,True,False,0.0,'0',-1,MAX_REVISION+1,[],{}):
            with self.subTest(value=value),self.assertRaises(ReviewError) as e:self.r.review(self.key,'pending','',value)
            self.assertEqual(e.exception.http_status,428)
        self.assertEqual(self.r.get(self.key)['review_revision'],0)
    def test_revision_persists_after_connection_restart(self):
        self.r.review(self.key,'needs_recheck','restart',0);self.r.db.close();self.r=Records(self.root)
        self.assertEqual(self.r.get(self.key)['review_revision'],1)
        with self.assertRaises(ReviewError):self.r.review(self.key,'pending','stale',0)
    def test_two_independent_connections_accept_only_one_writer(self):
        other=Records(self.root);barrier=threading.Barrier(2)
        def submit(r,name):
            barrier.wait(2)
            try:return ('ok',r.review(self.key,'needs_recheck',name,0)['review_revision'])
            except ReviewError as e:return (e.code,e.current['review_revision'])
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fs=[pool.submit(submit,self.r,'one'),pool.submit(submit,other,'two')];out=[f.result(5) for f in fs]
            self.assertEqual(sorted(out),[('REVIEW_CONFLICT',1),('ok',1)])
        finally:other.db.close()
    def test_two_threads_one_connection_accept_only_one_writer(self):
        barrier=threading.Barrier(2)
        def submit(name):
            barrier.wait(2)
            try:self.r.review(self.key,'pending',name,0);return 'ok'
            except ReviewError as e:return e.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            fs=[pool.submit(submit,str(n)) for n in range(2)];out=[f.result(5) for f in fs]
        self.assertEqual(sorted(out),['REVIEW_CONFLICT','ok'])
    def test_legacy_database_adds_table_without_changing_evidence(self):
        before=self.r.get(self.key);self.r.db.execute('DROP TABLE review_revisions');self.r.db.commit();self.r.db.close();self.r=Records(self.root)
        self.assertEqual(self.r.get(self.key),before);self.assertEqual(self.r.file(self.key).read_bytes(),self.image)
    def test_failure_between_conclusion_and_revision_rolls_back_both(self):
        self.r.db.execute("CREATE TRIGGER fail_revision BEFORE INSERT ON review_revisions BEGIN SELECT RAISE(ABORT,'isolated test failure'); END");self.r.db.commit()
        before=self.r.get(self.key)
        with self.assertRaises(ReviewError) as e:self.r.review(self.key,'confirmed_crack','must rollback',0)
        self.assertEqual(e.exception.code,'REVIEW_STORAGE_UNAVAILABLE');self.assertEqual(self.r.get(self.key),before)
        self.assertFalse(self.r.db.in_transaction)
    def test_corrupt_mask_does_not_advance_revision(self):
        before=self.r.get(self.key);self.r.file(self.key,True).write_bytes(self.mask+b'damaged')
        with self.assertRaises(EvidenceReadError):self.r.review(self.key,'confirmed_crack','no',0)
        self.assertEqual(self.r.get(self.key),before);self.assertFalse(self.r.db.in_transaction)
    def test_locked_writer_is_explicit_and_recoverable(self):
        other=sqlite3.connect(self.r.dir/'inspection.sqlite3');self.r.db.execute('PRAGMA busy_timeout=50');other.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(ReviewError) as e:self.r.review(self.key,'pending','busy',0)
            self.assertEqual(e.exception.http_status,503);self.assertFalse(self.r.db.in_transaction)
        finally:other.rollback();other.close()
        self.assertEqual(self.r.review(self.key,'pending','after lock',0)['review_revision'],1)
    def test_revision_exhaustion_never_wraps(self):
        self.r.db.execute('INSERT INTO review_revisions VALUES(?,?)',(self.key,MAX_REVISION));self.r.db.commit()
        with self.assertRaises(ReviewError) as e:self.r.review(self.key,'pending','no wrap',MAX_REVISION)
        self.assertEqual(e.exception.code,'REVIEW_REVISION_EXHAUSTED');self.assertEqual(self.r.get(self.key)['review_revision'],MAX_REVISION)
    def test_missing_key_does_not_create_review_revision(self):
        with self.assertRaises(ValueError):self.r.review('missing','pending','',0)
        self.assertEqual(self.r.db.execute('SELECT COUNT(*) FROM review_revisions').fetchone()[0],0)

class RevisionHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_review_http_');self.station=Station(Path(self.tmp.name),fixtures.DummyBridge())
        f,im,mask=fixtures.FrameTests().decode(fixtures.FrameTests().packet());self.key=self.station.records.save(f,im,mask,'isolated_http_test')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.station));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.station.exit=True;self.station.worker.join(2);self.server.shutdown();self.server.server_close();self.station.records.db.close();self.tmp.cleanup()
    def post(self,**values):
        req=urllib.request.Request(self.url+'/api/review',data=json.dumps(dict(id=self.key,review='needs_recheck',note='http',**values)).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req) as f:return f.status,json.load(f)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_record_endpoint_is_fresh_and_not_page_dependent(self):
        for version in (0,1):
            with urllib.request.urlopen(self.url+'/api/record?id='+self.key) as f:
                self.assertEqual(f.headers['Cache-Control'],'no-store');self.assertEqual(json.load(f)['review_revision'],version)
            if version==0:self.station.records.review(self.key,'pending','new',0)
    def test_legacy_client_without_revision_is_rejected(self):
        status,body=self.post();self.assertEqual(status,428);self.assertEqual(body['code'],'REVIEW_REVISION_REQUIRED')
    def test_http_conflict_returns_current_record(self):
        status,body=self.post(expected_revision=0);self.assertEqual(status,200);self.assertEqual(body['record']['review_revision'],1)
        status,body=self.post(expected_revision=0);self.assertEqual(status,409);self.assertEqual(body['code'],'REVIEW_CONFLICT');self.assertEqual(body['current']['review_revision'],1)
    def test_export_reports_same_revision_as_record(self):
        self.post(expected_revision=0)
        with urllib.request.urlopen(self.url+'/api/export') as f:self.assertEqual(json.load(f)['records'][0]['review_revision'],1)
        with urllib.request.urlopen(self.url+'/api/export?format=csv') as f:self.assertIn('review_revision',f.read().decode('utf-8-sig').splitlines()[0])

if __name__=='__main__':unittest.main()

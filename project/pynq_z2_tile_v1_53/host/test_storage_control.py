"""Storage configuration reserves capture without holding the control lock."""
import json,sqlite3,threading,time,unittest,urllib.request,urllib.error
from unittest.mock import patch
import workstation
import test_save_pause as fixtures

class StorageControlTests(unittest.TestCase):
    def begin(self):
        f=fixtures.SavePauseTests();self.addCleanup(f.doCleanups);self.fixture=f
        return f.begin(point='unused')
    def post(self,server,op,**extra):
        request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/action',data=json.dumps(dict(op=op,**extra)).encode(),headers={'Content-Type':'application/json'})
        try:response=urllib.request.urlopen(request,timeout=3)
        except urllib.error.HTTPError as e:response=e
        with response:return response.status,json.load(response)
    def run_setting(self,server,mode='archive',limit=32):
        out=[]
        def run():
            try:out.append(self.post(server,'storage',mode=mode,max_archive_mib=limit))
            except Exception as e:out.append(e)
        thread=threading.Thread(target=run);thread.start();return thread,out
    def assert_live(self,s,server,limit=1024):
        t=time.monotonic()
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/live',timeout=1) as response:value=json.load(response)
        self.assertLess(time.monotonic()-t,1);self.assertEqual(value['capture_control']['phase'],'STORAGE');self.assertTrue(value['busy'])
        self.assertEqual(value['storage']['mode'],'preview');self.assertEqual(value['storage']['max_archive_mib'],limit)
        return value
    def test_slow_policy_publication_preserves_control_and_publishes_only_after_success(self):
        for mode in ('preview','archive'):
            with self.subTest(mode=mode):
                s,b,_,_,server=self.begin();entered=threading.Event();release=threading.Event();actual=workstation.atomic
                def slow(path,data):
                    if path.name=='storage_policy.json':entered.set();self.assertTrue(release.wait(3))
                    return actual(path,data)
                with patch.object(workstation,'atomic',side_effect=slow):
                    thread,out=self.run_setting(server,mode)
                    try:
                        self.assertTrue(entered.wait(2));self.assert_live(s,server);self.fixture.pause_http(s,server)
                        self.assertEqual(b.calls.count('capture'),0)
                        for op,extra in [('storage',dict(mode='preview',max_archive_mib=16)),('capture',{}),('status',{}),('disconnect',{})]:
                            code,_=self.post(server,op,**extra);self.assertEqual(code,400)
                    finally:release.set();thread.join(4)
                self.assertEqual(out,[(200,dict(ok=True))]);self.assertFalse(s.enabled or s.busy);self.assertEqual(s.storage_policy.mode,mode)
                self.assertEqual(s.storage_policy.max_archive_mib,32);self.assertEqual(s.records.max_archive_bytes,32*1048576)
                self.assertEqual(json.loads(s.storage_policy.path.read_text()),dict(mode=mode,max_archive_mib=32))
    def test_external_sqlite_writer_keeps_pause_and_live_responsive(self):
        s,b,_,_,server=self.begin();entered=threading.Event();other=sqlite3.connect(s.records.dir/'inspection.sqlite3');other.execute('BEGIN IMMEDIATE')
        s.records.db.set_trace_callback(lambda sql:entered.set() if sql=='BEGIN IMMEDIATE' else None)
        thread,out=self.run_setting(server)
        try:
            self.assertTrue(entered.wait(2));self.assert_live(s,server);self.fixture.pause_http(s,server);self.assertEqual(b.calls.count('capture'),0)
        finally:other.rollback();other.close();s.records.db.set_trace_callback(None);thread.join(4)
        self.assertEqual(out,[(200,dict(ok=True))]);self.assertFalse(s.busy or s.enabled);self.assertEqual(s.storage_policy.mode,'archive')
    def test_pause_start_pause_during_setting_cannot_revive_capture(self):
        s,b,_,_,server=self.begin();entered=threading.Event();release=threading.Event();old=s.records.storage
        def slow():entered.set();self.assertTrue(release.wait(3));return old()
        with patch.object(s.records,'storage',side_effect=slow):
            thread,out=self.run_setting(server)
            try:
                self.assertTrue(entered.wait(2));self.fixture.pause_http(s,server);self.assertEqual(self.post(server,'start')[0],200)
                time.sleep(.1);self.assertEqual(b.calls.count('capture'),0);self.assertTrue(s.enabled);self.fixture.pause_http(s,server)
            finally:release.set();thread.join(4)
        time.sleep(.1);self.assertEqual(out,[(200,dict(ok=True))]);self.assertFalse(s.enabled or s.busy);self.assertEqual(b.calls.count('capture'),0)
    def test_failed_policy_write_keeps_file_memory_limit_and_warning(self):
        s,b,_,_,server=self.begin();s.action(dict(op='storage',mode='preview',max_archive_mib=64));before=s.storage_policy.path.read_bytes();s.storage_warning='preserve warning'
        with patch.object(workstation,'atomic',side_effect=OSError('Injected policy write failure')):
            code,value=self.post(server,'storage',mode='archive',max_archive_mib=32);self.assertEqual(code,503)
        self.assertFalse(s.busy);self.assertEqual(s.operation_phase,'IDLE');self.assertEqual(s.storage_policy.mode,'preview')
        self.assertEqual(s.storage_policy.max_archive_mib,64);self.assertEqual(s.records.max_archive_bytes,64*1048576)
        self.assertEqual(s.storage_policy.path.read_bytes(),before);self.assertEqual(s.storage_warning,'preserve warning');self.assertEqual(b.calls.count('capture'),0)
    def test_capacity_and_inventory_failure_release_reservation_without_new_policy(self):
        s,b,_,_,server=self.begin()
        with patch.object(s.records,'storage',return_value=dict(used_bytes=16*1048576)):
            code,value=self.post(server,'storage',mode='archive',max_archive_mib=16);self.assertEqual(code,400);self.assertIn('原存储设置保持不变',value['error'])
        self.assertFalse(s.busy);self.assertEqual(s.storage_policy.max_archive_mib,1024)
        with patch.object(s.records,'storage',side_effect=OSError('Inventory failure')):
            self.assertEqual(self.post(server,'storage',mode='archive',max_archive_mib=16)[0],503)
        self.assertFalse(s.busy);self.assertEqual(s.storage_policy.mode,'preview');self.assertFalse(s.storage_policy.path.exists())
    def test_invalid_parameters_do_not_reserve_operation(self):
        s,b,_,_,server=self.begin()
        for mode,limit in [('unknown',32),('preview',True),('archive',0)]:
            self.assertEqual(self.post(server,'storage',mode=mode,max_archive_mib=limit)[0],400);self.assertFalse(s.busy);self.assertEqual(s.operation_phase,'IDLE')
    def test_sqlite_writer_timeout_returns_structured_error_and_releases_operation(self):
        s,b,_,_,server=self.begin();other=sqlite3.connect(s.records.dir/'inspection.sqlite3');other.execute('BEGIN IMMEDIATE')
        s.records.db.execute('PRAGMA busy_timeout=30')
        try:
            code,value=self.post(server,'storage',mode='archive',max_archive_mib=16)
            self.assertEqual(code,503);self.assertIn('locked',value['error'])
            self.assertFalse(s.busy);self.assertEqual(s.operation_phase,'IDLE');self.assertEqual(s.storage_policy.mode,'preview')
            self.assertEqual(s.records.max_archive_bytes,1024*1048576)
        finally:other.rollback();other.close()

if __name__=='__main__':unittest.main(verbosity=2)

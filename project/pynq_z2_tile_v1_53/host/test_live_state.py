"""Real HTTP and archive contention, with an isolated fake board."""
import json,threading,time,unittest,urllib.error,urllib.request
from unittest.mock import patch
import test_save_pause as fixtures

class LiveStateTests(unittest.TestCase):
    def begin(self,**kw):
        fixture=fixtures.SavePauseTests();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture
        return fixture.begin(**kw)
    def get(self,server,path):
        t=time.monotonic()
        try:response=urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}'+path,timeout=1)
        except urllib.error.HTTPError as e:response=e
        with response:value=json.load(response);code=response.status
        self.assertLess(time.monotonic()-t,1)
        return code,value
    def test_live_and_pause_during_actual_image_and_mask_save(self):
        for point in ('image','mask'):
            with self.subTest(point=point):
                s,b,entered,release,server=self.begin(point=point)
                s.action(dict(op='capture'));self.assertTrue(entered.wait(3))
                code,live=self.get(server,'/api/live');self.assertEqual(code,200)
                self.assertEqual(live['capture_control']['phase'],'SAVE');self.assertTrue(live['busy'])
                self.assertNotIn('records',live);self.assertNotIn('used_bytes',live['storage'])
                for i in range(8):
                    code,busy=self.get(server,'/api/archive');self.assertEqual(code,503);self.assertEqual(busy['code'],'ARCHIVE_BUSY')
                self.fixture.pause_http(s,server)
                _,live=self.get(server,'/api/live');self.assertFalse(live['enabled']);self.assertTrue(live['busy'])
                self.assertEqual(b.calls.count('ack'),0)
                release.set();self.fixture.until_idle(s)
                code,saved=self.get(server,'/api/archive');self.assertEqual(code,200);self.assertEqual(saved['records_total'],1)
                self.assertEqual(len(saved['confirmation_history']),1);self.assertNotIn('enabled',saved)
                self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1)
    def test_long_inventory_does_not_block_live_or_queue_archive_waiters(self):
        s,b,_,_,server=self.begin(point='unused');entered=threading.Event();release=threading.Event();result=[]
        old=s.records.storage_snapshot
        def delayed():
            entered.set();self.assertTrue(release.wait(3));return old()
        def read():
            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/archive',timeout=4) as response:result.append(json.load(response))
        thread=threading.Thread(target=read)
        with patch.object(s.records,'storage_snapshot',side_effect=delayed):
            try:
                thread.start();self.assertTrue(entered.wait(1))
                self.assertEqual(self.get(server,'/api/live')[0],200)
                for i in range(12):self.assertEqual(self.get(server,'/api/archive')[0],503)
                self.fixture.pause_http(s,server)
            finally:release.set();thread.join(4)
        self.assertFalse(thread.is_alive());self.assertEqual(len(result),1)
        self.assertEqual(self.get(server,'/api/archive')[0],200)
    def test_live_has_no_records_dependency_and_detaches_mutable_values(self):
        s,b,_,_,server=self.begin(point='unused')
        with patch.object(s.records,'storage_snapshot',side_effect=AssertionError),patch.object(s.records,'page',side_effect=AssertionError),patch.object(s.records,'summary',side_effect=AssertionError),patch.object(s.records.confirmations,'history',side_effect=AssertionError):
            old=s.live_state();s.add_log('after snapshot');self.assertNotEqual(old['log'],s.log)
            self.assertEqual(self.get(server,'/api/live')[0],200)
    def test_legacy_endpoint_retains_archive_history_and_current_configuration(self):
        s,b,_,_,server=self.begin(point='unused');code,old=self.get(server,'/api/state?limit=2&kind=manual')
        self.assertEqual(code,200);self.assertEqual(old['records_total'],0);self.assertEqual(old['page_size'],2)
        self.assertEqual(old['confirmation_journal']['history'],[]);self.assertIn('at_limit',old['storage'])
        self.assertEqual(old['storage']['max_archive_mib'],1024)
    def test_archive_failure_releases_reservation_and_is_separate_from_live(self):
        s,b,_,_,server=self.begin(point='unused')
        with patch.object(s.records,'page',side_effect=OSError('fixture archive read failure')):
            self.assertEqual(self.get(server,'/api/archive')[0],503)
            self.assertEqual(self.get(server,'/api/live')[0],200)
        self.assertEqual(self.get(server,'/api/archive')[0],200)

if __name__=='__main__':unittest.main(verbosity=2)

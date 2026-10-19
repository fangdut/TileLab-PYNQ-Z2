"""Slow telemetry readers must not hold capture control; reader state stays serialized."""
import json,threading,time,unittest,urllib.request
from unittest.mock import patch
import test_save_pause as fixtures

class PlayerReadControlTests(unittest.TestCase):
    def begin(self):
        f=fixtures.SavePauseTests();self.addCleanup(f.doCleanups);self.fixture=f
        s,b,_,_,server=f.begin(point='unused');(s.root/'host').mkdir(exist_ok=True)
        s.action(dict(op='display',value='station_0'));return s,b,server
    def reader(self,s,server):
        out=[]
        def run():
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/live',timeout=4) as r:out.append(json.load(r))
            except Exception as e:out.append(e)
        t=threading.Thread(target=run);t.start();return t,out
    def block(self,s):
        entered=threading.Event();release=threading.Event();old=s.stimulus_status.snapshot
        def wait():entered.set();self.assertTrue(release.wait(3));return old()
        return entered,release,patch.object(s.stimulus_status,'snapshot',side_effect=wait)
    def until(self,predicate):
        deadline=time.monotonic()+2
        while not predicate():
            self.assertLess(time.monotonic(),deadline);time.sleep(.01)
    def test_pause_start_pause_during_slow_player_read_preserves_latest_state(self):
        s,b,server=self.begin();entered,release,patcher=self.block(s)
        with patcher:
            reader,out=self.reader(s,server)
            try:
                self.assertTrue(entered.wait(2));self.fixture.pause_http(s,server)
                s.action(dict(op='start'));self.fixture.pause_http(s,server)
                reader.join(.5);self.assertFalse(reader.is_alive());self.assertFalse(s.enabled)
            finally:release.set();reader.join(4)
        self.assertEqual(len(out),1);self.assertIsInstance(out[0],dict)
        current=s.live_state();self.assertFalse(current['enabled']);self.assertEqual(current['capture_control']['intent_epoch'],2)
    def test_capture_save_and_confirmation_can_finish_during_player_read(self):
        s,b,server=self.begin();entered,release,patcher=self.block(s)
        with patcher:
            reader,out=self.reader(s,server)
            try:
                self.assertTrue(entered.wait(2));s.action(dict(op='capture'));deadline=time.monotonic()+2
                while b.calls.count('ack')<1:
                    self.assertLess(time.monotonic(),deadline);time.sleep(.01)
                self.fixture.pause_http(s,server);self.assertEqual(len(s.records.all()),1)
                reader.join(.5);self.assertFalse(reader.is_alive())
            finally:release.set();reader.join(4)
        self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1);self.assertIsInstance(out[0],dict)
    def test_parallel_player_readers_are_serialized_without_capture_lock(self):
        s,b,server=self.begin();entered,release,patcher=self.block(s)
        with patcher as mocked:
            first,one=self.reader(s,server);second=None
            try:
                self.assertTrue(entered.wait(2));second,two=self.reader(s,server);time.sleep(.05)
                self.assertEqual(mocked.call_count,1);self.fixture.pause_http(s,server)
            finally:
                release.set();first.join(4)
                if second:second.join(4)
            self.assertGreaterEqual(mocked.call_count,1)
        self.assertIsInstance(one[0],dict);self.assertIsInstance(two[0],dict)
    def test_publisher_waiting_for_reader_metadata_does_not_hold_capture_lock(self):
        s,b,server=self.begin();entered,release,patcher=self.block(s);published=[];writer=None
        with patcher:
            reader,out=self.reader(s,server)
            try:
                self.assertTrue(entered.wait(2))
                writer=threading.Thread(target=lambda:published.append(s.action(dict(op='display',value='real_video'))));writer.start()
                deadline=time.monotonic()+1
                while True:
                    # Windows may briefly deny a new reader during atomic
                    # replacement. Keep the original deadline and assertions.
                    try:command=(s.root/'host/display_command.txt').read_text()
                    except PermissionError:command=''
                    if 'real_video' in command:break
                    self.assertLess(time.monotonic(),deadline);time.sleep(.002)
                self.assertTrue(writer.is_alive());self.fixture.pause_http(s,server);self.assertIsNotNone(s.display_pending)
            finally:
                release.set();reader.join(4)
                if writer:writer.join(4)
        self.assertEqual(len(published),1);self.assertIsNone(s.display_pending)
        self.until(lambda:s.live_state()['stimulus_status'].get('request_id')==published[0]['request_id'])
    def test_reader_error_releases_telemetry_lock_and_control_stays_usable(self):
        s,b,server=self.begin()
        with patch.object(s.stimulus_status,'snapshot',side_effect=OSError('Injected telemetry error')):
            self.until(lambda:'Injected telemetry error' in s.live_state()['stimulus_status']['cache_error'])
            self.assertFalse(s.live_state()['stimulus_status']['ready'])
        self.fixture.pause_http(s,server);self.assertEqual(s.live_state()['stimulus'],'station_0')
        s.action(dict(op='display',value='real_video'));self.until(lambda:s.live_state()['stimulus']=='real_video')

if __name__=='__main__':unittest.main(verbosity=2)

"""Source command publication must not own capture control or claim adoption."""
import ctypes,json,os,threading,time,unittest,urllib.request,urllib.error
from ctypes import wintypes
from unittest.mock import patch
import workstation
import test_save_pause as fixtures
from stimulus_command import parse_command

class DisplayControlTests(unittest.TestCase):
    def begin(self):
        f=fixtures.SavePauseTests();self.addCleanup(f.doCleanups);self.fixture=f
        s,b,a,r,server=f.begin(point='unused');(s.root/'host').mkdir(exist_ok=True)
        initial=s.action(dict(op='display',value='station_0'))
        deadline=time.monotonic()+2
        while s.live_state()['stimulus_status'].get('request_id')!=initial['request_id']:
            self.assertLess(time.monotonic(),deadline);time.sleep(.01)
        return s,b,server,initial
    def post(self,server,op,**extra):
        req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/action',data=json.dumps(dict(op=op,**extra)).encode(),headers={'Content-Type':'application/json'})
        try:response=urllib.request.urlopen(req,timeout=4)
        except urllib.error.HTTPError as e:response=e
        with response:return response.status,json.load(response)
    def writer(self,server,value='real_video'):
        out=[]
        def run():
            try:out.append(self.post(server,'display',value=value))
            except Exception as e:out.append(e)
        thread=threading.Thread(target=run);thread.start();return thread,out
    def live(self,server):
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/live',timeout=1) as r:return json.load(r)
    def test_pending_command_and_old_adoption_are_separate_and_second_publisher_rejected(self):
        s,b,server,initial=self.begin();old=(s.root/'host/display_command.txt').read_bytes();entered=threading.Event();release=threading.Event();actual=workstation.atomic
        def slow(path,data):
            if path.name=='display_command.txt':entered.set();self.assertTrue(release.wait(3))
            return actual(path,data)
        with patch.object(workstation,'atomic',side_effect=slow):
            thread,out=self.writer(server)
            try:
                self.assertTrue(entered.wait(2));v=self.live(server)
                self.assertEqual(v['display_pending']['value'],'real_video');self.assertEqual(v['stimulus'],'station_0');self.assertFalse(v['busy'])
                self.assertEqual(v['stimulus_status']['request_id'],initial['request_id']);pending=v['display_pending']['request_id']
                self.assertEqual(self.post(server,'display',value='station_6')[0],400);self.fixture.pause_http(s,server)
                self.assertEqual((s.root/'host/display_command.txt').read_bytes(),old);self.assertEqual(b.calls.count('capture'),0)
            finally:release.set();thread.join(4)
        self.assertEqual(out,[(200,dict(ok=True,request_id=pending))]);self.assertIsNone(s.display_pending)
        deadline=time.monotonic()+2
        while True:
            v=self.live(server)
            if v['stimulus']=='real_video':break
            self.assertLess(time.monotonic(),deadline);time.sleep(.01)
        self.assertFalse(v['stimulus_status']['ready'])
        self.assertFalse(s.enabled);self.assertEqual(parse_command((s.root/'host/display_command.txt').read_text())['request_id'],pending)
    def test_capture_can_finish_while_source_publication_is_pending(self):
        s,b,server,_=self.begin();entered=threading.Event();release=threading.Event();actual=workstation.atomic
        def slow(path,data):
            if path.name=='display_command.txt':entered.set();self.assertTrue(release.wait(3))
            return actual(path,data)
        with patch.object(workstation,'atomic',side_effect=slow):
            thread,out=self.writer(server)
            try:
                self.assertTrue(entered.wait(2));self.assertEqual(self.post(server,'capture')[0],200);deadline=time.monotonic()+2
                while b.calls.count('ack')<1:
                    self.assertLess(time.monotonic(),deadline);time.sleep(.01)
                self.assertIsNotNone(s.display_pending);self.assertEqual(len(s.records.all()),1);self.fixture.pause_http(s,server)
            finally:release.set();thread.join(4)
        self.assertEqual(out[0][0],200);self.assertEqual(b.calls.count('capture'),1)
    def test_failed_write_preserves_prior_command_and_releases_publication_slot(self):
        s,b,server,initial=self.begin();p=s.root/'host/display_command.txt';before=p.read_bytes()
        with patch.object(workstation,'atomic',side_effect=OSError('Injected command failure')):
            code,_=self.post(server,'display',value='real_video');self.assertEqual(code,503)
        self.assertIsNone(s.display_pending);self.assertEqual(p.read_bytes(),before);self.assertEqual(s.stimulus_status.last_request_id,initial['request_id'])
        self.assertEqual(self.post(server,'display',value='real_video')[0],200)
    def test_invalid_source_does_not_publish_or_reserve_slot(self):
        s,b,server,initial=self.begin();p=s.root/'host/display_command.txt';before=p.read_bytes()
        for value in ('../bad','real_999',None,[]):
            self.assertEqual(self.post(server,'display',value=value)[0],400);self.assertIsNone(s.display_pending);self.assertEqual(p.read_bytes(),before)
    @unittest.skipUnless(os.name=='nt','Windows sharing behavior')
    def test_actual_windows_rename_contention_keeps_control_available(self):
        s,b,server,initial=self.begin();p=s.root/'host/display_command.txt';k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=k.CreateFileW(str(p),0x80000000,3,None,3,0,None);self.assertNotEqual(handle,wintypes.HANDLE(-1).value)
        thread,out=self.writer(server)
        try:
            deadline=time.monotonic()+.5
            while not p.with_suffix('.txt.tmp').exists():
                self.assertLess(time.monotonic(),deadline);time.sleep(.002)
            self.assertIsNotNone(self.live(server)['display_pending']);self.fixture.pause_http(s,server)
            self.assertEqual(parse_command(p.read_text())['request_id'],initial['request_id'])
        finally:k.CloseHandle(handle);thread.join(3)
        self.assertEqual(out[0][0],200);self.assertIsNone(s.display_pending);self.assertFalse(s.enabled)

if __name__=='__main__':unittest.main(verbosity=2)

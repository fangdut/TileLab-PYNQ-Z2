import json,os,tempfile,time,unittest,urllib.request,threading
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from stimulus_status import StimulusStatus,valid_source
from stimulus_command import make_command,parse_command
import stimulus_status
import test_workstation as fixtures
from workstation import Station,handler,ThreadingHTTPServer

class StimulusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_stimulus_');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.host=self.root/'host';self.host.mkdir()
        self.status=StimulusStatus(self.root);self.now=1700000000.
        self.request_id='a'*32;self.session='b'*32
        self.command('real_video');self.player();self.instance()
    def command(self,value):
        p=self.host/'display_command.txt';p.write_bytes(make_command(value,self.request_id)[0]);os.utime(p,(self.now-.2,self.now-.2))
    def player(self,**changes):
        p=dict(request_id=self.request_id,player_session=self.session,player_pid=123,source='real_video',phase='rendering',utc=datetime.fromtimestamp(self.now,timezone.utc).isoformat(),rendered_frames=300,source_frame=299,error=None)
        p.update(changes);(self.host/'player_status.json').write_text(json.dumps(p),encoding='utf-8');return p
    def instance(self,**changes):
        p=dict(version=1,session=self.session,pid=123,started_utc=datetime.fromtimestamp(self.now-10,timezone.utc).isoformat())
        p.update(changes);(self.host/'player_instance.json').write_text(json.dumps(p),encoding='utf-8');return p
    def test_same_name_needs_exact_new_request_id(self):
        self.request_id='c'*32;self.command('real_video');s=self.get()
        self.assertEqual(s['state'],'SWITCHING');self.assertFalse(s['identity_confirmed'])
        self.player();self.assertTrue(self.get()['identity_confirmed'])
    def test_legacy_command_is_never_identity_confirmed(self):
        (self.host/'display_command.txt').write_text('real_video');os.utime(self.host/'display_command.txt',(self.now-.2,)*2)
        self.assertEqual(self.get()['state'],'LEGACY_UNCONFIRMED')
    def test_missing_report_identity_is_unconfirmed(self):
        for change in (dict(request_id=None),dict(request_id='A'*32),dict(player_session='bad'),dict(player_pid=True),dict(player_pid=0)):
            self.player(**change);self.assertEqual(self.get()['state'],'PLAYER_IDENTITY_MISSING')
    def test_wrong_session_or_pid_is_unconfirmed(self):
        for change in (dict(session='c'*32),dict(pid=124),dict(started_utc=datetime.fromtimestamp(self.now+.1,timezone.utc).isoformat())):
            self.instance(**change);self.assertEqual(self.get()['state'],'PLAYER_SESSION_SWITCHING')
    def test_invalid_missing_or_locked_instance(self):
        q=self.host/'player_instance.json';q.unlink();self.assertEqual(self.get()['state'],'PLAYER_INSTANCE_UNAVAILABLE')
        for data in (b'{',b'[]',b'\xff',b'x'*513):
            q.write_bytes(data);self.assertEqual(self.get()['state'],'PLAYER_INSTANCE_INVALID')
        self.instance(version=True);self.assertEqual(self.get()['state'],'PLAYER_INSTANCE_INVALID')
        self.instance(started_utc=datetime.fromtimestamp(self.now+1,timezone.utc).isoformat());self.assertEqual(self.get()['state'],'CLOCK_UNCERTAIN')
    def test_marker_changes_during_snapshot(self):
        original=stimulus_status.read_small;calls=0
        def read(path,limit):
            nonlocal calls
            if path.name=='player_instance.json':
                calls+=1
                if calls==2:self.instance(session='d'*32)
            return original(path,limit)
        with patch('stimulus_status.read_small',side_effect=read):self.assertEqual(self.get()['state'],'PLAYER_SESSION_SWITCHING')
    def test_command_changes_during_snapshot(self):
        original=stimulus_status.read_small;calls=0
        def read(path,limit):
            nonlocal calls
            if path.name=='display_command.txt':
                calls+=1
                if calls==2:self.request_id='e'*32;self.command('real_video')
            return original(path,limit)
        with patch('stimulus_status.read_small',side_effect=read):self.assertEqual(self.get()['state'],'SWITCHING')
    def test_identity_confirmation_and_motion_progress_are_independent(self):
        self.player(drawn_frames=1,drawn_source_frame=1)
        s=self.status.snapshot(self.now,10);self.assertTrue(s['identity_confirmed']);self.assertEqual(s['motion']['state'],'WAITING')
        self.player(drawn_frames=2,drawn_source_frame=2)
        s=self.status.snapshot(self.now,10.1);self.assertEqual(s['motion']['state'],'PROGRESSING')
        self.player(drawn_frames=2,drawn_source_frame=2,utc=datetime.fromtimestamp(self.now+1.2,timezone.utc).isoformat())
        s=self.status.snapshot(self.now+1.2,11.3)
        self.assertTrue(s['ready']);self.assertTrue(s['identity_confirmed']);self.assertEqual(s['motion']['state'],'STALLED')
    def test_unconfirmed_source_never_claims_render_progress(self):
        self.player(drawn_frames=100,drawn_source_frame=100,request_id='d'*32)
        s=self.status.snapshot(self.now,10);self.assertFalse(s['ready']);self.assertEqual(s['motion']['state'],'UNCONFIRMED')
    def get(self):return self.status.snapshot(self.now)
    def test_matching_fresh_player_is_ready(self):
        s=self.get();self.assertTrue(s['ready']);self.assertEqual(s['observed'],'real_video');self.assertEqual(s['state'],'READY')
    def test_command_is_not_confirmation(self):
        self.command('station_6');s=self.get();self.assertEqual(s['state'],'SWITCHING');self.assertEqual(s['observed'],'real_video');self.assertFalse(s['ready'])
    def test_same_source_report_older_than_request_is_pending(self):
        p=self.host/'display_command.txt';os.utime(p,(self.now+.1,self.now+.1))
        self.assertEqual(self.get()['state'],'SWITCHING')
    def test_stale_player_is_not_ready(self):
        self.assertEqual(self.status.snapshot(self.now+1.501)['state'],'STALE')
        self.assertTrue(self.status.snapshot(self.now+1.5)['ready'])
    def test_future_clock_is_not_ready(self):
        self.player(utc=datetime.fromtimestamp(self.now+1,timezone.utc).isoformat());self.assertEqual(self.get()['state'],'CLOCK_UNCERTAIN')
    def test_future_command_clock_is_not_ready(self):
        p=self.host/'display_command.txt';os.utime(p,(self.now+10,self.now+10));self.assertEqual(self.get()['state'],'CLOCK_UNCERTAIN')
    def test_loading_and_priming_are_pending(self):
        for phase in ('loading','priming'):
            self.player(phase=phase);self.assertEqual(self.get()['state'],'SWITCHING')
    def test_static_and_playing_accepted_without_movement_claim(self):
        for phase in ('static','playing'):
            self.player(phase=phase);self.assertTrue(self.get()['ready'])
    def test_player_error_overrides_matching_source(self):
        self.player(error='decode failed');s=self.get();self.assertEqual(s['state'],'PLAYER_ERROR');self.assertFalse(s['ready'])
    def test_missing_command_keeps_previous_request_but_is_unconfirmed(self):
        self.get();(self.host/'display_command.txt').unlink();s=self.get()
        self.assertEqual(s['requested'],'real_video');self.assertEqual(s['state'],'COMMAND_UNAVAILABLE');self.assertFalse(s['ready'])
    def test_unreadable_command_does_not_raise(self):
        self.get()
        with patch('stimulus_status.read_small',side_effect=PermissionError('locked')):s=self.get()
        self.assertEqual(s['requested'],'real_video');self.assertTrue(s['command_error']);self.assertFalse(s['ready'])
    def test_missing_player_does_not_raise_or_reuse_old_telemetry(self):
        self.get();(self.host/'player_status.json').unlink();s=self.get();self.assertEqual(s['state'],'PLAYER_UNAVAILABLE');self.assertIsNone(s['observed'])
    def test_corrupt_or_overlong_player_is_explicitly_invalid(self):
        for data in (b'{',b'\xff',b'[]',b'x'*16385):
            (self.host/'player_status.json').write_bytes(data);self.assertEqual(self.get()['state'],'PLAYER_INVALID')
    def test_invalid_player_fields_are_rejected(self):
        for change in (dict(source='../bad'),dict(phase='unknown'),dict(utc='bad'),dict(utc='2020-01-01T00:00:00'),dict(rendered_frames=-1),dict(source_frame=True),dict(error=[])):
            self.player(**change);self.assertEqual(self.get()['state'],'PLAYER_INVALID')
    def test_invalid_or_overlong_command_does_not_replace_last_request(self):
        self.get()
        for data in (b'\xff',b'../bad',b'x'*129,b''):
            (self.host/'display_command.txt').write_bytes(data);s=self.get();self.assertEqual(s['state'],'COMMAND_UNAVAILABLE');self.assertEqual(s['requested'],'real_video')
    def test_valid_source_ranges_match_available_catalog(self):
        for s in ('station_0','station_6','real_000','real_116','calib_229','real_video'):self.assertTrue(valid_source(s))
        for s in ('station_7','station_00','real_117','calib_230','real_00','real_００１','real_-01',None,[]):self.assertFalse(valid_source(s))
    def test_request_cache_does_not_imply_player_confirmation(self):
        self.status.requested('station_6');(self.host/'display_command.txt').unlink()
        s=self.get();self.assertEqual(s['requested'],'station_6');self.assertFalse(s['ready'])

class StimulusHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_stimulus_http_');self.root=Path(self.tmp.name)
        self.station=Station(self.root,fixtures.DummyBridge());(self.root/'host').mkdir(exist_ok=True)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.station));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}/api/state'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.station.exit=True;self.station.live_cache.close();self.station.worker.join(2);self.station.records.db.close();self.tmp.cleanup()
    def wait_status(self,predicate,timeout=3):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            with urllib.request.urlopen(self.url,timeout=1) as f:s=json.load(f)
            if predicate(s):return s
            time.sleep(.02)
        self.fail('Background telemetry did not adopt expected state: '+str(s))
    def test_each_api_selection_has_unique_identity_and_write_failure_keeps_cache(self):
        first=self.station.action({'op':'display','value':'real_video'})
        second=self.station.action({'op':'display','value':'real_video'})
        self.assertNotEqual(first['request_id'],second['request_id'])
        p=self.root/'host/display_command.txt';c=parse_command(p.read_text());self.assertEqual(c['request_id'],second['request_id'])
        with patch('workstation.atomic',side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):self.station.action({'op':'display','value':'station_6'})
        self.assertEqual(self.station.stimulus_status.last_request_id,second['request_id'])
        self.assertEqual(parse_command(p.read_text()),c)
    def test_status_http_survives_bad_command_encoding(self):
        (self.root/'host/display_command.txt').write_bytes(b'\xff')
        s=self.wait_status(lambda s:s['stimulus_status']['state']=='COMMAND_UNAVAILABLE')
        self.assertEqual(s['stimulus_status']['state'],'COMMAND_UNAVAILABLE');self.assertEqual(s['captures'],0)
    def test_status_http_survives_exclusive_windows_command_lock(self):
        if os.name!='nt':self.skipTest('Windows sharing violation')
        import ctypes
        from ctypes import wintypes
        p=self.root/'host/display_command.txt';p.write_text('real_video',encoding='utf-8')
        self.wait_status(lambda s:s['stimulus']=='real_video')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.CreateFileW(str(p),0x80000000,0,None,3,0,None)
        self.assertNotEqual(handle,wintypes.HANDLE(-1).value)
        try:
            s=self.wait_status(lambda s:s['stimulus_status']['state']=='COMMAND_UNAVAILABLE')
            self.assertEqual(s['stimulus_status']['state'],'COMMAND_UNAVAILABLE');self.assertEqual(s['stimulus'],'real_video')
            self.assertFalse(s['error']);self.assertEqual(s['captures'],0)
        finally:kernel.CloseHandle(handle)
        self.wait_status(lambda s:s['stimulus_status']['state']=='PLAYER_UNAVAILABLE')

if __name__=='__main__':unittest.main(verbosity=2)

import unittest,time,struct,zlib
from capture_health import decode_health
from tcp_transport import MAGIC
import test_tcp_transport as tcp
import test_recovery as recovery

class HealthWire(unittest.TestCase):
    def test_all_states_and_unknown_age(self):
        for code in range(6):
            h=decode_health([0x484c5431,code,10,10 if code==1 else 0xffffffff,0,1])
            self.assertEqual(h['ready'],code==1)
            if code!=1:self.assertIsNone(h['valid_age_ms'])
    def test_invalid_schema_and_false_healthy_rejected(self):
        for w in ([0,1,0,0,0,1],[0x484c5431,6,0,0,0,1],
                  [0x484c5431,1,500,0,0,1],[0x484c5431,1,0,500,0,1],
                  [0x484c5431,1,0,0,0x10,1],[0x484c5431,1,0,0,1,1],
                  [0x484c5431,1,0,0,0,0]):
            with self.assertRaises(ValueError):decode_health(w)
    def test_versioned_status_overlay_does_not_change_size(self):
        for version in (0x11200,0x11300):
            d=[0]*40;d[:6]=[0x484c5431,1,9,9,0x1000,1]
            d[13:16]=[0,123,0xface];m=[0]*24;m[:3]=[0x54494c33,version,77]
            h=struct.pack('<68I',MAGIC,1,0,5,*d,*m);h+=struct.pack('<I',zlib.crc32(h))
            c,t=tcp.TCPTests().server([h])
            try:
                s=c.stats();self.assertEqual(c.total_received_bytes,276)
                self.assertEqual('capture_health' in s,version>=0x11300)
                self.assertEqual(s['descriptor_verified_frames'],123)
            finally:c.close();t.join(3)
    def test_new_version_missing_schema_fails_closed(self):
        m=[0]*24;m[:3]=[0x54494c33,0x11300,1]
        h=struct.pack('<68I',MAGIC,1,0,5,*([0]*40),*m);h+=struct.pack('<I',zlib.crc32(h))
        c,t=tcp.TCPTests().server([h])
        try:
            with self.assertRaisesRegex(ValueError,'health schema'):c.stats()
            self.assertEqual(c.requests_sent,1)
        finally:c.close();t.join(3)

class HealthSource(recovery.Controlled):
    def __init__(self,state=0,queued=0):
        super().__init__();self.check_capture_health=True;self.health_code=state;self.queued=queued
    def stats(self):
        self.calls.append('stats')
        return dict(depth=self.queued,head=self.released,frames=60,boot_id=7,
                    capture_health=decode_health([0x484c5431,self.health_code,10,
                                      10 if self.health_code==1 else 0xffffffff,0,1]))
    def ack(self,f):super().ack(f);self.queued=max(0,self.queued-1)

class HealthStation(unittest.TestCase):
    until=recovery.RecoveryTests.until
    begin=recovery.RecoveryTests.begin
    finish=recovery.RecoveryTests.finish
    def test_wait_first_uses_status_only_and_network_is_online(self):
        b=HealthSource();s=self.begin(b);s.action(dict(op='start'))
        self.until(lambda:b.calls.count('stats')>=3);s.action(dict(op='pause'))
        self.assertNotIn('capture',b.calls);self.assertTrue(s.state()['board_connected'])
        self.assertFalse(s.state()['capture_health']['ready']);self.assertFalse(s.error)
        self.assertLessEqual(b.calls.count('stats'),4)
    def test_pending_manual_is_preserved_then_captured_once(self):
        b=HealthSource();s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:b.calls.count('stats')>=2);self.assertTrue(s.manual)
        b.health_code=1;self.until(lambda:s.captures==1 and not s.busy)
        self.assertEqual(b.calls.count('capture'),1);self.assertEqual(len(s.records.all()),1)
        self.assertFalse(s.manual)
    def test_pause_cancels_waiting_manual_without_capture(self):
        b=HealthSource();s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:b.calls.count('stats')>=2);s.action(dict(op='pause'))
        n=len(b.calls);time.sleep(.3);self.assertEqual(n,len(b.calls));self.assertNotIn('capture',b.calls)
    def test_retained_evidence_drains_during_halt(self):
        b=HealthSource(5,1);s=self.begin(b);s.action(dict(op='storage',mode='archive'));s.action(dict(op='start'))
        self.until(lambda:s.captures==1 and not s.busy);self.until(lambda:b.calls.count('stats')>=3)
        s.action(dict(op='pause'));self.assertEqual(b.calls.count('capture'),1)
        self.assertEqual(b.calls.count('ack'),1);self.assertEqual(len(s.records.all()),1)
    def test_healthy_cached_status_does_not_poll_before_every_frame(self):
        b=HealthSource(1);s=self.begin(b);s.action(dict(op='capture'))
        self.until(lambda:s.captures==1 and not s.busy)
        self.assertEqual(b.calls,['stats','capture','ack','stats'])
    def test_status_becomes_explicitly_stale(self):
        b=HealthSource(1);s=self.begin(b);s.note_stats(b.stats());s.health_observed-=2
        self.assertTrue(s.state()['capture_health']['stale'])

if __name__=='__main__':unittest.main()

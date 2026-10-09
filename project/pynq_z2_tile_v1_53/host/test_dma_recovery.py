import unittest,struct,zlib,tempfile,time
from dma_recovery import decode_recovery
from capture_health import decode_health
from tcp_transport import MAGIC
from workstation import Station
import test_tcp_transport as tcp
import test_capture_health as health

def words(stage=0):return [0x52454331,stage,1,1 if stage==0 else 0,1 if stage==3 else 0,1,1,1,2,1,3,1000,3000,50]
class RecoveryProtocol(unittest.TestCase):
    def test_all_states_and_observed_product_fields(self):
        for stage in range(4):
            r=decode_recovery(words(stage));self.assertEqual(r['attempts'],1)
            self.assertTrue(r['waiting_new_product']);self.assertEqual(r['discarded_packets'],2)
    def test_corrupt_schema_and_limits_rejected(self):
        for idx,value in [(0,0),(1,4),(2,4),(3,2),(5,8),(9,2),(10,9),(11,999),(12,2999)]:
            w=words();w[idx]=value
            with self.assertRaises(ValueError):decode_recovery(w)
    def test_health_extension_is_version_guarded(self):
        for code in (6,7):
            w=[0x484c5431,code,700,700,1,0]
            with self.assertRaises(ValueError):decode_health(w,0x11300)
            self.assertFalse(decode_health(w,0x11400)['ready'])
    def test_wire_status_keeps_header_size_and_previous_fields(self):
        for version in (0x11300,0x11400):
            d=[0]*40;d[:6]=[0x484c5431,1,5,5,0,1];d[13:16]=[0,123,0xcafe]
            d[23:37]=words();d[39]=77;m=[0]*24;m[:3]=[0x54494c33,version,99]
            h=struct.pack('<68I',MAGIC,1,0,5,*d,*m);h+=struct.pack('<I',zlib.crc32(h))
            c,t=tcp.TCPTests().server([h])
            try:
                s=c.stats();self.assertEqual(c.total_received_bytes,276)
                self.assertEqual(s['descriptor_verified_frames'],123);self.assertEqual(s['compression_probe_bypasses'],77)
                self.assertEqual('capture_recovery' in s,version>=0x11400)
            finally:c.close();t.join(3)

class RecoveringSource(health.HealthSource):
    def stats(self):
        self.calls.append('stats')
        return dict(depth=self.queued,head=self.released,frames=60,boot_id=7,
                    capture_health=decode_health([0x484c5431,self.health_code,600,600,1,0],0x11400),
                    capture_recovery=decode_recovery(words(1 if self.health_code==6 else 3)))

class RecoveryReception(unittest.TestCase):
    def run_case(self,code):
        b=RecoveringSource(code,1)
        with tempfile.TemporaryDirectory() as root:
            s=Station(root,b)
            try:
                s.action(dict(op='storage',mode='archive'));s.action(dict(op='start'));end=time.monotonic()+4
                while b.calls.count('stats')<4:
                    if time.monotonic()>end:self.fail('Recovery status polling did not settle')
                    time.sleep(.015)
                s.action(dict(op='pause'))
                self.assertEqual(b.calls.count('capture'),1);self.assertEqual(b.calls.count('ack'),1)
                self.assertEqual(len(s.records.all()),1);self.assertFalse(s.error)
                self.assertTrue(s.state()['board_connected']);self.assertFalse(s.state()['capture_health']['ready'])
                self.assertTrue(s.state()['capture_recovery']['waiting_new_product'])
            finally:s.exit=True;s.worker.join(4);s.records.db.close()
    def test_recovering_drains_existing_evidence_then_only_status(self):self.run_case(6)
    def test_failed_recovery_still_preserves_and_drains_existing_evidence(self):self.run_case(7)

if __name__=='__main__':unittest.main()

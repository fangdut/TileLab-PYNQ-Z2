"""Event zero is real evidence after a 32-bit sequence wrap."""
import hashlib,json,struct,tempfile,time,unittest,zlib
from pathlib import Path
from workstation import Station,Records,Bridge
from test_recovery import Controlled
import test_tcp_transport
from tcp_transport import MAGIC

class ZeroBoard(Controlled):
    def __init__(self,acked=False,fail=None,boot=7):
        super().__init__();self.acked=acked;self.fail=fail;self.boot=boot
        self.frame[0]['event_id']=0
    def ack(self,f):
        self.calls.append('ack')
        if f['boot_id']!=self.boot or f['event_id']!=0:raise ValueError('Wrong zero identity')
        if self.fail=='before':raise ValueError('Injected exit before ACK')
        self.acked=True;self.released+=1
        if self.fail=='after':raise ValueError('Injected exit after ACK, before local settle')
    def stats(self):
        self.calls.append('stats')
        return dict(boot_id=self.boot,head=0 if self.acked else 0xffffffff,depth=0 if self.acked else 1,frames=100)

class ZeroEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_zero_');self.root=Path(self.tmp.name);self.stations=[]
        (self.root/'host').mkdir()
    def tearDown(self):
        for s in self.stations:self.stop(s)
        self.tmp.cleanup()
    def stop(self,s):
        if getattr(s,'_test_closed',False):return
        s.exit=True;s.worker.join(4);s.bridge.close();s.records.db.close();s._test_closed=True
    def station(self,b):
        s=Station(self.root,b);self.stations.append(s);return s
    def until(self,f):
        end=time.monotonic()+4
        while not f():
            if time.monotonic()>end:self.fail('Zero-event recovery did not complete')
            time.sleep(.01)
    def pending(self,fail):
        s=self.station(ZeroBoard(fail=fail));s.action(dict(op='capture'))
        self.until(lambda:bool(s.error) and not s.busy)
        self.assertEqual(s.records.confirmations.pending()['frame']['event_id'],0)
        self.assertEqual(s.records.all()[0]['id'],'pl_7_0')
        images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'review_records').glob('*.png')}
        self.stop(s);return images
    def recover(self,fail,board,status,calls):
        before=self.pending(fail);s=self.station(board);s.action(dict(op='resume_pending'))
        self.until(lambda:not s.busy and not s.retry_requested)
        self.assertFalse(s.error);self.assertIsNone(s.pending_ack);self.assertEqual(s.captures,0)
        self.assertEqual(board.calls,calls);self.assertEqual(s.records.confirmations.history()[0]['status'],status)
        self.assertEqual(len(s.records.all()),1)
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'review_records').glob('*.png')})
    def test_zero_before_ack_restart(self):
        self.recover('before',ZeroBoard(),'ACKNOWLEDGED',['stats','ack','stats'])
    def test_zero_after_ack_restart(self):
        self.recover('after',ZeroBoard(acked=True),'ALREADY_ACKNOWLEDGED',['stats','stats'])
    def test_zero_on_restarted_board_does_not_look_already_acked(self):
        self.recover('before',ZeroBoard(acked=True,boot=8),'BOARD_RESTARTED_UNCONFIRMED',['stats','stats'])
    def test_zero_can_be_saved_and_reopened(self):
        b=ZeroBoard();r=Records(self.root)
        try:
            f,im,mask=b.frame;key=r.save(f,im,mask,'manual',confirmation_endpoint='tcp://127.0.0.1:9133')
            self.assertEqual(key,'pl_7_0')
        finally:r.db.close()
        r=Records(self.root)
        try:self.assertEqual(r.confirmations.pending()['frame']['event_id'],0)
        finally:r.db.close()
    def ack_reply(self,head):
        m=[0]*24;m[0]=0x54494c33;m[1]=0x11100;m[2]=7;m[4]=head
        h=struct.pack('<68I',MAGIC,1,0,5,*([0]*40),*m)
        return test_tcp_transport.TCPTests().server([h+struct.pack('<I',zlib.crc32(h))])
    def test_tcp_ack_zero_identity_is_accepted(self):
        c,t=self.ack_reply(0)
        try:c.ack(7,0);self.assertEqual(c.reconnects,0)
        finally:c.close();t.join(3)
    def test_tcp_ack_zero_mismatched_identity_is_rejected(self):
        c,t=self.ack_reply(0xffffffff)
        try:
            with self.assertRaisesRegex(ValueError,'ACK response identity mismatch'):c.ack(7,0)
        finally:c.close();t.join(3)
    def test_jtag_checks_actual_ethernet_program_identity(self):
        ws=self.root/'pynq_z2_tile_v1_53.sdk';(ws/'hdmi_ethernet/build').mkdir(parents=True);(self.root/'reports').mkdir()
        names=('system.bit','system.xsa','hdmi_ethernet/build/hdmi_ethernet.elf');digests={}
        for name in names:
            (ws/name).write_bytes(name.encode());digests[name]=hashlib.sha256((ws/name).read_bytes()).hexdigest()
        (self.root/'reports/programmed_v153.json').write_text(json.dumps(dict(active_application='hdmi_ethernet',sha256=digests)))
        b=Bridge(self.root);self.assertTrue(b.firmware_matches())
        (ws/names[-1]).write_bytes(b'changed');self.assertFalse(b.firmware_matches())
    def test_jtag_rejects_unrecognized_application_marker(self):
        (self.root/'reports').mkdir()
        (self.root/'reports/programmed_v153.json').write_text(json.dumps(dict(active_application='../elsewhere',sha256={})))
        self.assertFalse(Bridge(self.root).firmware_matches())

if __name__=='__main__':unittest.main(verbosity=2)

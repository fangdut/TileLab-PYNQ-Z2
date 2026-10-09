import tempfile,time,unittest,json,struct,zlib
from pathlib import Path
from unittest.mock import patch
from workstation import Station,Records,Bridge
from test_recovery import Controlled
from test_events import packet
import test_tcp_transport
from tcp_transport import MAGIC

class RestartBoard(Controlled):
    def __init__(self,boot=7,head=0,fail_ack=False):
        super().__init__();self.boot=boot;self.head=head;self.fail_ack=fail_ack
    def ack(self,f):
        self.calls.append('ack')
        if self.fail_ack:raise ValueError('Injected failure before ACK transmission')
        if f['boot_id']!=self.boot or f['event_id']!=self.head+1:raise ValueError('Wrong identity')
        self.head=f['event_id'];self.released+=1
    def stats(self):
        self.calls.append('stats');return dict(boot_id=self.boot,head=self.head,depth=1 if self.head==0 else 0,frames=100)

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_ack_journal_');self.root=Path(self.tmp.name);self.stations=[]
    def tearDown(self):
        for s in self.stations:self.stop(s)
        self.tmp.cleanup()
    def stop(self,s):
        if getattr(s,'_test_closed',False):return
        s.exit=True;s.worker.join(4);s.bridge.close();s.records.db.close();s._test_closed=True
    def station(self,board):
        s=Station(self.root,board);self.stations.append(s);return s
    def until(self,fn):
        end=time.monotonic()+4
        while not fn():
            if time.monotonic()>end:self.fail('Worker did not complete')
            time.sleep(.01)
    def saved_pending(self):
        b=RestartBoard(fail_ack=True);s=self.station(b);s.action(dict(op='capture'))
        self.until(lambda:bool(s.error) and not s.busy)
        self.assertEqual(len(s.records.all()),1);self.assertIsNotNone(s.records.confirmations.pending())
        self.stop(s);return b
    def resume(self,s):
        s.action(dict(op='resume_pending'));self.until(lambda:not s.busy and not s.retry_requested)
    def test_restart_before_ack_resumes_saved_identity_without_capture(self):
        self.saved_pending();b=RestartBoard();s=self.station(b)
        self.assertFalse(s.enabled);self.assertIsNotNone(s.pending_ack)
        self.resume(s)
        self.assertEqual(b.calls,['stats','ack','stats']);self.assertEqual(s.captures,0)
        self.assertEqual(len(s.records.all()),1);self.assertIsNone(s.records.confirmations.pending())
        self.assertEqual(s.records.confirmations.history()[0]['status'],'ACKNOWLEDGED')
    def test_restart_after_board_ack_does_not_repeat_capture_or_ack(self):
        self.saved_pending();b=RestartBoard(head=1);s=self.station(b);self.resume(s)
        self.assertEqual(b.calls,['stats','stats']);self.assertEqual(s.captures,0)
        self.assertEqual(s.records.confirmations.history()[0]['status'],'ALREADY_ACKNOWLEDGED')
    def test_board_reboot_retires_only_old_confirmation_keeps_evidence(self):
        self.saved_pending();b=RestartBoard(boot=8);s=self.station(b);self.resume(s)
        self.assertEqual(b.calls,['stats','stats']);self.assertEqual(len(s.records.all()),1)
        self.assertIsNone(s.pending_ack);self.assertIn('7 → 8',s.synchronization_warning)
        self.assertEqual(s.records.confirmations.history()[0]['status'],'BOARD_RESTARTED_UNCONFIRMED')
    def test_changed_queue_head_in_same_boot_stops_without_ack(self):
        self.saved_pending();b=RestartBoard(head=2);s=self.station(b);self.resume(s)
        self.assertIn('队列不一致',s.error);self.assertIsNotNone(s.pending_ack)
        self.assertEqual(b.calls,['stats']);self.assertIsNotNone(s.records.confirmations.pending())
    def test_wrong_endpoint_keeps_paused_and_preserves_pending(self):
        self.saved_pending();b=RestartBoard();b.transport.port=9999;s=self.station(b)
        self.assertTrue(s.journal_error)
        for op in ('start','capture','resume_pending'):
            with self.assertRaises(ValueError):s.action(dict(op=op))
        self.assertEqual(b.calls,[]);self.assertIsNotNone(s.records.confirmations.pending())
    def test_changed_saved_png_blocks_recovery_before_network(self):
        self.saved_pending();image=next((self.root/'review_records').glob('pl_*.png'));image.write_bytes(b'corrupted')
        b=RestartBoard();s=self.station(b);self.assertTrue(s.journal_error)
        with self.assertRaises(ValueError):s.action(dict(op='resume_pending'))
        self.assertEqual(b.calls,[])
    def test_missing_saved_row_blocks_recovery(self):
        self.saved_pending();r=Records(self.root);r.db.execute('DELETE FROM events');r.db.commit();r.db.close()
        b=RestartBoard();s=self.station(b);self.assertIn('row is missing',s.journal_error);self.assertEqual(b.calls,[])
    def test_journal_prepare_failure_rolls_back_row_and_never_acks(self):
        b=RestartBoard();s=self.station(b)
        with patch.object(s.records.confirmations,'prepare',side_effect=OSError('Injected journal write failure')):
            s.action(dict(op='capture'));self.until(lambda:bool(s.error) and not s.busy)
        self.assertEqual(s.records.all(),[]);self.assertEqual(b.calls,['capture'])
        self.assertIsNone(s.records.confirmations.pending())
    def test_local_completion_failure_can_resume_after_ack_already_succeeded(self):
        b=RestartBoard();s=self.station(b)
        with patch.object(s.records.confirmations,'settle',side_effect=OSError('Injected completion commit failure')):
            s.action(dict(op='capture'));self.until(lambda:bool(s.error) and not s.busy)
        self.assertEqual(b.head,1);self.assertIsNotNone(s.records.confirmations.pending());self.stop(s)
        next_board=RestartBoard(head=1);restored=self.station(next_board);self.resume(restored)
        self.assertEqual(next_board.calls,['stats','stats']);self.assertEqual(len(restored.records.all()),1)
    def test_existing_review_is_preserved_when_same_evidence_gets_pending_ack(self):
        r=Records(self.root);f,im,m=Bridge.decode_event(*packet(),1)
        try:
            key=r.save(f,im,m,'hardware_alarm');r.update(key,'needs_recheck','Human review retained')
            r.save(f,im,m,'manual',confirmation_endpoint='tcp://127.0.0.1:9133')
            self.assertEqual(r.all()[0]['note'],'Human review retained');self.assertEqual(r.all()[0]['review'],'needs_recheck')
            self.assertEqual(r.confirmations.pending()['record_id'],key)
        finally:r.db.close()
    def test_plain_preview_save_path_and_bounded_history(self):
        r=Records(self.root);f,im,m=Bridge.decode_event(*packet(),1)
        try:
            r.save(f,im,m,'test');self.assertIsNone(r.confirmations.pending())
            for i in range(70):
                frame=dict(f,event_id=i+2,frame_id=i+100)
                r.save(frame,im,m,'manual',confirmation_endpoint='tcp://127.0.0.1:9133')
                r.confirmations.settle(frame,'ACKNOWLEDGED',7)
            self.assertEqual(len(r.confirmations.history()),64)
        finally:r.db.close()
    def test_valid_crc_but_wrong_ack_identity_is_rejected(self):
        for boot,head in ((8,9),(7,8),(7,9)):
            m=[0]*24;m[0]=0x54494c33;m[1]=0x10d00;m[2]=boot;m[4]=head
            h=struct.pack('<68I',MAGIC,1,0,5,*([0]*40),*m);c,t=test_tcp_transport.TCPTests().server([h+struct.pack('<I',zlib.crc32(h))])
            try:
                if (boot,head)==(7,9):c.ack(7,9)
                else:
                    with self.assertRaisesRegex(ValueError,'ACK response identity mismatch'):c.ack(7,9)
                self.assertEqual(c.reconnects,0)
            finally:c.close();t.join(3)

if __name__=='__main__':unittest.main(verbosity=2)

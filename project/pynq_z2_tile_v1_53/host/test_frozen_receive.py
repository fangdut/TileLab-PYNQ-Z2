import socket,threading,struct,unittest,time,tempfile
from pathlib import Path
from workstation import Station,Bridge
from tcp_transport import EventTCP,MAGIC
from recovery import TransientTransportError
import test_recovery as helpers

class EventSource(helpers.Controlled):
    def __init__(self,queued=0,fail=False):
        super().__init__();self.queued=queued;self.fail=fail;self.parameters=[]
    def configure(self,t):
        self.calls.append('configure');self.parameters.append((t,self.enhance))
        if self.fail:self.fail=False;raise TransientTransportError('Config exchange interrupted')
    def capture(self,t):
        self.calls.append('capture');f,im,m=self.frame
        return dict(f,event_id=1+self.released),im,m
    def ack(self,f):self.calls.append('ack');self.released+=1;self.queued=max(0,self.queued-1)
    def stats(self):self.calls.append('stats');return dict(depth=self.queued,frames=60,boot_id=7)

class FrozenTests(unittest.TestCase):
    def until(self,fn,seconds=3):
        end=time.monotonic()+seconds
        while not fn():
            if time.monotonic()>end:self.fail('Condition did not complete')
            time.sleep(.01)
    def begin(self,b):
        self.tmp=tempfile.TemporaryDirectory();self.s=Station(self.tmp.name,b);self.addCleanup(self.finish)
        self.s.action(dict(op='freeze_preview',enabled=True));return self.s
    def finish(self):
        self.s.exit=True;self.s.worker.join(4);self.s.records.db.close();self.tmp.cleanup()
    def test_empty_queue_polls_without_creating_image_requests(self):
        b=EventSource();s=self.begin(b);s.action(dict(op='start'));self.until(lambda:len(b.parameters)>=3)
        s.action(dict(op='pause'));self.assertNotIn('capture',b.calls);self.assertEqual(s.captures,0);self.assertTrue(s.state()['board_connected'])
        self.assertLessEqual(len(b.parameters),4)
    def test_queued_events_are_archived_and_acknowledged_while_frozen(self):
        b=EventSource(3);s=self.begin(b);s.action(dict(op='storage',mode='archive'));s.action(dict(op='start'))
        self.until(lambda:b.released==3 and not s.busy);s.action(dict(op='pause'))
        self.assertEqual(b.calls.count('capture'),3);self.assertEqual(len(s.records.all()),3);self.assertEqual(s.auto_saved,3)
    def test_manual_capture_still_works_without_unfreezing(self):
        b=EventSource();s=self.begin(b);s.action(dict(op='capture'));self.until(lambda:b.released==1 and not s.busy)
        self.assertTrue(s.preview_frozen);self.assertEqual(len(s.records.all()),1);self.assertEqual(b.calls,['capture','ack','stats'])
    def test_unfreeze_resumes_preview_and_stop_remains_distinct(self):
        b=EventSource();s=self.begin(b);s.action(dict(op='start'));self.until(lambda:len(b.parameters)>0)
        s.action(dict(op='freeze_preview',enabled=False));self.until(lambda:b.released>0);s.action(dict(op='pause'))
        self.until(lambda:not s.busy);n=b.released;time.sleep(.25);self.assertEqual(n,b.released);self.assertFalse(s.enabled)
    def test_parameters_update_without_requesting_preview(self):
        b=EventSource();s=self.begin(b);s.action(dict(op='threshold',value=123));s.action(dict(op='start'))
        self.until(lambda:len(b.parameters)>=2);s.action(dict(op='pause'))
        self.assertTrue(all(t==123 for t,_ in b.parameters));self.assertNotIn('capture',b.calls)
    def test_freeze_mode_configuration_failure_recovers(self):
        b=EventSource(fail=True);s=self.begin(b);s.action(dict(op='start'))
        self.until(lambda:s.recovery.recovered==1);s.action(dict(op='pause'))
        self.assertNotIn('capture',b.calls);self.assertFalse(s.error)
    def test_freeze_validation_does_not_change_reception(self):
        b=EventSource();s=self.begin(b)
        for value in (1,'yes',None):
            with self.assertRaises(ValueError):s.action(dict(op='freeze_preview',enabled=value))
        self.assertFalse(s.enabled);self.assertTrue(s.preview_frozen)
    def test_configure_wire_contract_and_byte_counter(self):
        for enhance,expected in ((True,0),(False,1)):
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1];requests=[]
            def server():
                conn,_=listener.accept()
                with conn:
                    req=bytearray()
                    while len(req)<16:req.extend(conn.recv(16-len(req)))
                    requests.append(struct.unpack('<4I',req));conn.sendall(struct.pack('<68I',MAGIC,1,0,1,*([0]*64)))
                listener.close()
            th=threading.Thread(target=server);th.start();c=EventTCP('127.0.0.1',port)
            try:c.configure(123,enhance);self.assertEqual(c.total_received_bytes,272);self.assertEqual(c.requests_sent,1)
            finally:c.close();th.join(3)
            self.assertEqual(requests,[(MAGIC,5,123,expected)])
    def test_bad_configure_parameters_never_connect(self):
        c=EventTCP('127.0.0.1')
        for t,e in ((0,True),(256,False),(True,True),(123,1)):
            with self.assertRaises(ValueError):c.configure(t,e)
        self.assertEqual(c.requests_sent,0);self.assertIsNone(c.sock)

if __name__=='__main__':unittest.main(verbosity=2)

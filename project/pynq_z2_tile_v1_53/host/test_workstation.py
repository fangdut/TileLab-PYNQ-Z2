"""Protocol/persistence tests use artificial packets in isolated temp folders."""
import unittest,tempfile,threading,json,urllib.request,urllib.error,hashlib,time,os
from pathlib import Path
import numpy as np
from workstation import Bridge,Records,Station,handler,ThreadingHTTPServer

class FrameTests(unittest.TestCase):
    def test_firmware_digest_survives_reextraction_but_rejects_changed_content(self):
        with tempfile.TemporaryDirectory(prefix='tile_firmware_test_') as d:
            root=Path(d);ws=root/'pynq_z2_tile_v1_53.sdk';(ws/'hdmi_monitor/build').mkdir(parents=True);(root/'reports').mkdir();(root/'host').mkdir()
            names=('system.bit','system.xsa','hdmi_monitor/build/hdmi_monitor.elf');digests={}
            for name in names:
                p=ws/name;p.write_bytes(name.encode());digests[name]=hashlib.sha256(p.read_bytes()).hexdigest()
            (root/'reports/programmed_v153.json').write_text(json.dumps(dict(sha256=digests)))
            bridge=Bridge(root);self.assertTrue(bridge.firmware_matches())
            os.utime(ws/'system.bit',(time.time()+100,time.time()+100));self.assertTrue(bridge.firmware_matches())
            (ws/names[-1]).write_bytes(b'changed ELF');self.assertFalse(bridge.firmware_matches())
    def packet(self):
        a=np.zeros((720,1280,4),np.uint8);a[:,:,:3]=[7,11,19];a[100:140,310:312,3]=1
        return a
    def decode(self,a,n=80,lo=(100<<16)|310,hi=(139<<16)|311,status=13):
        return Bridge.decode(a.tobytes(),52,n,lo,hi,status,0x80f31807,1200,500)
    def test_hardware_packet_color_mask_and_metadata(self):
        from PIL import Image
        import io
        f,image,mask=self.decode(self.packet());self.assertEqual(f['boxes'],[[310,100,311,139]])
        self.assertEqual(Image.open(io.BytesIO(image)).getpixel((0,0)),(19,11,7));self.assertTrue(f['alarm'])
    def test_reject_truncated_and_inconsistent_frames(self):
        a=self.packet()
        for change in [dict(n=79),dict(lo=0),dict(status=0x8000000d)]:
            with self.assertRaises(ValueError):self.decode(a,**change)
        a[0,0,3]=2
        with self.assertRaises(ValueError):self.decode(a,n=82)
        with self.assertRaises(ValueError):Bridge.decode(b'bad',1,0,0,0,4,0,1,1)
        with self.assertRaises(ValueError):Bridge.decode(self.packet().tobytes(),1,80,(100<<16)|310,(139<<16)|311,13,0,1,1)
    def test_normal_frame_is_not_an_alarm(self):
        a=self.packet();a[:,:,3]=0
        f,_,_=self.decode(a,n=0,lo=0,hi=0,status=4);self.assertFalse(f['alarm']);self.assertEqual(f['boxes'],[])
    def test_persistent_review_and_original_hash(self):
        with tempfile.TemporaryDirectory(prefix='tile_review_test_') as d:
            f,image,mask=self.decode(self.packet());s=Records(d);key=s.save(f,image,mask,'test')
            s.update(key,'false_alarm','Protocol test only');self.assertEqual(s.file(key).read_bytes(),image)
            self.assertEqual(s.all()[0]['image_sha256'],hashlib.sha256(image).hexdigest());s.db.close()
            s=Records(d);self.assertEqual(s.all()[0]['note'],'Protocol test only')
            with self.assertRaises(ValueError):s.update(key,'approved','')
            with self.assertRaises(ValueError):s.file('../bad')
            s.db.close()

class DummyBridge:
    def capture(self,t):raise RuntimeError('Injected transport failure')
    def close(self):pass

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='tile_http_test_');self.station=Station(self.tmp.name,DummyBridge())
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.station));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.station.exit=True;self.station.worker.join(2);self.server.shutdown();self.server.server_close();self.station.records.db.close();self.tmp.cleanup()
    def post(self,obj,origin=None):
        h={'Content-Type':'application/json'}
        if origin:h['Origin']=origin
        return urllib.request.urlopen(urllib.request.Request(self.url+'/api/action',data=json.dumps(obj).encode(),headers=h))
    def test_disconnected_is_not_presented_as_live(self):
        state=json.load(urllib.request.urlopen(self.url+'/api/state'));self.assertFalse(state['board_connected']);self.assertIsNone(state['frame'])
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(self.url+'/api/image')
    def test_bad_parameters_and_external_origin_rejected(self):
        for obj in [dict(op='threshold',value=0),dict(op='threshold',value=256),dict(op='display',value='../file')]:
            with self.assertRaises(urllib.error.HTTPError):self.post(obj)
        with self.assertRaises(urllib.error.HTTPError) as e:self.post(dict(op='start'),'https://example.com')
        self.assertEqual(e.exception.code,403)
    def test_transport_failure_pauses_and_never_creates_event(self):
        self.post(dict(op='start')).close()
        deadline=time.time()+2
        while time.time()<deadline and not self.station.error:time.sleep(.05)
        state=self.station.state();self.assertIn('Injected',state['error']);self.assertFalse(state['enabled']);self.assertEqual(state['records'],[])
    def test_reconnect_after_failure_archives_only_the_new_frame(self):
        self.post(dict(op='capture')).close()
        deadline=time.time()+2
        while time.time()<deadline and not self.station.error:time.sleep(.02)
        self.assertEqual(self.station.records.all(),[])
        class Reconnected:
            def capture(inner,t):return FrameTests().decode(FrameTests().packet())
            def close(inner):pass
        self.station.bridge=Reconnected()
        self.post(dict(op='capture')).close()
        deadline=time.time()+3
        while time.time()<deadline and self.station.captures==0:time.sleep(.02)
        s=self.station.state();self.assertEqual(s['captures'],1);self.assertEqual(s['error'],'')
        self.assertEqual(len(s['records']),1);self.assertEqual(s['records'][0]['frame_id'],52)

if __name__=='__main__':unittest.main(verbosity=2)

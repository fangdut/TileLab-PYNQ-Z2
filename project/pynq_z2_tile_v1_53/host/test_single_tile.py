"""The fixed fixture must fail closed across firmware changes and reconnects."""
from pathlib import Path
import copy,json,struct,tempfile,unittest,zlib
from unittest.mock import patch
import numpy as np
from tcp_transport import EventTCP,BOOST_MODEL_ID
from single_tile_profile import load,roi_words,validate_frame,validate_wire_contract
from single_tile_station import SingleTileBridge,SingleTileStation
ROOT=Path(__file__).resolve().parents[1]

class Peer:
    def __init__(self,p,change=None):self.p=p;self.change=change;self.sent=[];self.buffer=bytearray()
    def settimeout(self,value):pass
    def sendall(self,data):
        request=struct.unpack('<4I',data);self.sent.append(request);op=request[1]
        d=[0]*40;m=[0]*24;m[:3]=[0x54494c33,0x13200,123]
        if op==3:
            d[:6]=[0x484c5431,0,0,0xffffffff,0,0]
            d[23:37]=[0x52454331,0,0,0,0,0,0,0,0,0,3,1000,3000,0]
            d[37:39]=[BOOST_MODEL_ID,BOOST_MODEL_ID]
        if op==6:d[:7]=[self.p['profile_id'],*roi_words(self.p),BOOST_MODEL_ID,500,0x13200,1]
        if self.change:self.change(op,d,m)
        body=struct.pack('<68I',0x544c5033,1,0,5,*d,*m)
        self.buffer+=body+struct.pack('<I',zlib.crc32(body))
    def recv_into(self,view,count):
        n=min(count,len(self.buffer));view[:n]=self.buffer[:n];del self.buffer[:n];return n
    def close(self):pass

class SingleTileTests(unittest.TestCase):
    def setUp(self):self.p=load(ROOT)
    def client(self,change=None):
        c=EventTCP('127.0.0.1');c.peer_version=0x13200;c.single_tile_contract=self.p
        c.sock=Peer(self.p,change);return c
    def test_current_socket_success_and_repeat_preflight(self):
        c=self.client();peer=c.sock
        for _ in range(2):c.configure(90,passes=4,wide_weak=True,ridge=True,pixel_boost=True)
        self.assertEqual([r[1] for r in peer.sent],[3,6,5,3,6,5])
        bridge=SingleTileBridge('127.0.0.1');bridge.transport.sock=Peer(self.p)
        try:
            self.assertEqual(bridge.transport.peer_version,0)
            bridge.configure(90)
            self.assertEqual([r[1] for r in bridge.transport.sock.sent],[3,6,3,6,5])
        finally:bridge.close()
    def test_profile_mismatch_never_sends_configuration(self):
        changes=[lambda o,d,m:m.__setitem__(1,0x13100),
                 lambda o,d,m:d.__setitem__(0,0) if o==6 else None,
                 lambda o,d,m:d.__setitem__(1,d[1]+1) if o==6 else None,
                 lambda o,d,m:d.__setitem__(2,d[2]+1) if o==6 else None,
                 lambda o,d,m:d.__setitem__(3,0) if o==6 else None,
                 lambda o,d,m:d.__setitem__(6,0) if o==6 else None,
                 lambda o,d,m:m.__setitem__(2,124) if o==6 else None]
        for change in changes:
            c=self.client(change);peer=c.sock
            with self.assertRaises(ValueError):c.configure(90,passes=4,wide_weak=True,ridge=True,pixel_boost=True)
            self.assertNotIn(5,[r[1] for r in peer.sent])
    def test_reconnected_peer_is_not_trusted(self):
        c=self.client();c.configure(90,passes=4,wide_weak=True,ridge=True,pixel_boost=True)
        c.sock=Peer(self.p,lambda o,d,m:d.__setitem__(1,0) if o==6 else None);peer=c.sock
        with self.assertRaises(ValueError):c.configure(90,passes=4,wide_weak=True,ridge=True,pixel_boost=True)
        self.assertEqual([r[1] for r in peer.sent],[3,6])
    def test_captured_evidence_uses_complete_roi_and_actual_config(self):
        mask=np.zeros((720,1280),bool);mask[110,390]=True;mask[609,889]=True
        f=dict(firmware_version=0x13200,config_word=0x7bf35a07,boxes=[[390,110,889,609]],alarm=True)
        validate_frame(self.p,f,mask);self.assertEqual(f['decision'],'crack_candidate')
        for pixel in [(109,390),(610,889),(110,389),(609,890)]:
            bad=mask.copy();bad[pixel]=True
            with self.assertRaises(ValueError):validate_frame(self.p,f,bad)
        for change in [dict(config_word=0x7bf35907),dict(firmware_version=0x13100),dict(boxes=[[389,110,889,609]])]:
            with self.assertRaises(ValueError):validate_frame(self.p,f|change,mask)
    def test_fixed_station_has_no_legacy_recipe_or_threshold_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            import shutil
            root=Path(tmp);shutil.copytree(ROOT/'config',root/'config');(root/'models').mkdir();shutil.copy2(ROOT/'models/v159_integer_model.json',root/'models');(root/'host').mkdir();shutil.copy2(ROOT/'host/recipes.json',root/'host')
            bridge=SingleTileBridge('127.0.0.1',root)
            with patch('workstation.threading.Thread.start'):
                station=SingleTileStation(root,bridge)
            try:
                self.assertEqual((station.threshold,bridge.passes),(90,4));self.assertEqual(len(station.recipe_catalog),1)
                bridge._request(90)
                for body in [dict(op='threshold',value=91),dict(op='recipe',value='synthetic_v16'),dict(op='display',value='real_video')]:
                    with self.assertRaises(ValueError):station.action(body)
                self.assertFalse(station.live_state()['accuracy_qualified'])
                # Exercise real HTTP routing without a hardware worker or
                # generated live images; only current validation is served.
                from http.server import ThreadingHTTPServer
                from single_tile_station import handler
                import threading,urllib.request,urllib.error
                (root/'host/single_tile.html').write_text('<title>V164 single fixture</title>')
                report=root/'reports/v164';report.mkdir(parents=True,exist_ok=True)
                (report/'validation.html').write_text('<title>Current unqualified evidence</title>')
                (report/'QUALIFICATION.json').write_text('{"qualified":false}')
                server=ThreadingHTTPServer(('127.0.0.1',0),handler(station));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    url=f'http://127.0.0.1:{server.server_port}'
                    with urllib.request.urlopen(url+'/api/live') as response:self.assertFalse(json.load(response)['accuracy_qualified'])
                    with urllib.request.urlopen(url+'/validation/') as response:self.assertIn(b'Current unqualified',response.read())
                    with urllib.request.urlopen(url+'/validation/QUALIFICATION.json') as response:self.assertFalse(json.load(response)['qualified'])
                    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+'/validation/../models/v159_integer_model.json')
                finally:server.shutdown();thread.join(timeout=2);server.server_close()
            finally:station.exit=True;station.records.db.close();bridge.close()
    def test_profile_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir();p=copy.deepcopy(self.p);p['inspection_roi'][0]+=1
            (root/'config/single_tile.json').write_text(json.dumps(p))
            with self.assertRaises(ValueError):load(root)

if __name__=='__main__':unittest.main()

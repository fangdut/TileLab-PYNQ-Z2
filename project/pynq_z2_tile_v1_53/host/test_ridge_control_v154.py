"""Host control/attribution tests. These tests never contact a board."""
from pathlib import Path
from unittest.mock import Mock
import json,tempfile,unittest,struct,zlib
from tcp_transport import EventTCP,RIDGE_VERSION
from workstation import EthernetBridge
import recipes

class RidgeControlTests(unittest.TestCase):
    def make_transport(self):
        c=EventTCP('192.168.33.10');c.peer_version=RIDGE_VERSION
        c.exchange=Mock(return_value=(b'',[],[]))
        return c
    def test_capture_and_configure_use_distinct_opt_in_bit(self):
        c=self.make_transport();c.capture(90,passes=4,wide_weak=True,ridge=True)
        self.assertEqual(c.exchange.call_args.args,(1,90,102))
        c.configure(90,passes=4,wide_weak=True,ridge=True)
        self.assertEqual(c.exchange.call_args.args,(5,90,100))
        c.configure(90,passes=4,wide_weak=True)
        self.assertEqual(c.exchange.call_args.args,(5,90,36))
    def test_reject_old_firmware_or_incompatible_profile(self):
        c=self.make_transport()
        for kwargs in ({'passes':2,'wide_weak':True},{'passes':4,'wide_weak':False},{'passes':4,'wide_weak':True,'ridge':1}):
            kwargs=dict(kwargs);kwargs.setdefault('ridge',True)
            with self.assertRaises(ValueError):c.configure(90,**kwargs)
        with self.assertRaises(ValueError):c.configure(89,passes=4,wide_weak=True,ridge=True)
        c.peer_version=0x12b00
        with self.assertRaises(ValueError):c.configure(90,passes=4,wide_weak=True,ridge=True)
        self.assertFalse(c.exchange.called)
    def test_bound_request_keeps_ridge_flag_with_other_parameters(self):
        b=EthernetBridge('192.168.33.10');b.enhance=True;b.passes=4;b.wide_weak=True;b.ridge=True
        b.transport.configure=Mock()
        invoke=b.bind_request('configure',90)
        b.ridge=False;b.wide_weak=False;b.passes=2
        invoke()
        b.transport.configure.assert_called_once_with(90,enhance=True,passes=4,low_gate=False,wide_weak=True,ridge=True)
        self.assertFalse(b.ridge)
    def test_captured_flag_disambiguates_delayed_event_recipe(self):
        catalog=[dict(id='old',name='old',sha256='a',threshold=90,requires_weak_support=True,weak_passes=4,wide_weak=True),
                 dict(id='new',name='new',sha256='b',threshold=90,requires_weak_support=True,weak_passes=4,wide_weak=True,ridge=True)]
        word=(90<<8)|(1<<24)|(1<<25)|(1<<27)
        self.assertEqual(recipes.evidence(dict(config_word=word),catalog)['recipe_id'],'old')
        self.assertEqual(recipes.evidence(dict(config_word=word|(1<<28)),catalog)['recipe_id'],'new')
    def test_recipe_rejects_incompatible_directional_profile(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'host').mkdir()
            for changes in ({'threshold':89},{'wide_weak':False},{'weak_passes':2},{'ridge':1}):
                recipe=dict(id='x',threshold=90,requires_weak_support=True,weak_passes=4,wide_weak=True,ridge=True);recipe.update(changes)
                (root/'host/recipes.json').write_text(json.dumps(dict(recipes=[recipe])))
                with self.assertRaises(ValueError):recipes.load(root)
    def test_fresh_socket_version_is_probed_before_sending_ridge(self):
        class Peer:
            def __init__(self,version):self.version=version;self.sent=[];self.buffer=bytearray();self.closed=False
            def settimeout(self,value):pass
            def sendall(self,data):
                self.sent.append(struct.unpack('<4I',data))
                words=[0]*68;words[:4]=[0x544c5033,1,0,5];words[44:47]=[0x54494c33,self.version,123]
                body=struct.pack('<68I',*words);self.buffer+=body+struct.pack('<I',zlib.crc32(body))
            def recv_into(self,view,count):
                n=min(count,len(self.buffer));view[:n]=self.buffer[:n];del self.buffer[:n];return n
            def close(self):self.closed=True
        for version in (0x12b00,RIDGE_VERSION):
            c=EventTCP('127.0.0.1');c.peer_version=RIDGE_VERSION;peer=Peer(version);c.sock=peer
            if version<RIDGE_VERSION:
                with self.assertRaisesRegex(ValueError,'current connection'):c.configure(90,passes=4,wide_weak=True,ridge=True)
                self.assertEqual([r[1] for r in peer.sent],[3]);self.assertTrue(peer.closed)
            else:
                c.configure(90,passes=4,wide_weak=True,ridge=True)
                self.assertEqual([r[1] for r in peer.sent],[3,5]);self.assertEqual(peer.sent[-1][3],100)
    def test_decode_attributes_actual_captured_algorithm(self):
        from workstation import Bridge
        import test_events as fixtures
        raw,d,m=fixtures.packet();d[7]|=(1<<24)|(1<<25)|(1<<27)|(1<<28);m[1]=RIDGE_VERSION
        f,_,_=Bridge.decode_event(raw,d,m,1)
        self.assertIn('MEAN7_MEAN15',f['algorithm'])
        m[1]=0x12b00
        with self.assertRaisesRegex(ValueError,'Directional mean'):Bridge.decode_event(raw,d,m,1)
if __name__=='__main__':unittest.main()

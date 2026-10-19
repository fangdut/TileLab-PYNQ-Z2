import unittest,struct,zlib
from pathlib import Path
from unittest.mock import Mock
from tcp_transport import EventTCP,BOOST_VERSION,BOOST_MODEL_ID
from workstation import EthernetBridge,Bridge
import recipes,test_events

class IntegerControlTests(unittest.TestCase):
 def client(self):
  c=EventTCP('127.0.0.1');c.peer_version=BOOST_VERSION;c.exchange=Mock(return_value=(b'',[],[]));return c
 def test_wire_flags(self):
  c=self.client();args=dict(passes=4,wide_weak=True,ridge=True,pixel_boost=True)
  c.configure(90,**args);self.assertEqual(c.exchange.call_args.args,(5,90,612))
  c.capture(90,**args);self.assertEqual(c.exchange.call_args.args,(1,90,614))
  c.configure(90,low_gate=True,**args);self.assertEqual(c.exchange.call_args.args,(5,90,628))
 def test_invalid_modes_never_send(self):
  c=self.client();base=dict(passes=4,wide_weak=True,ridge=True,pixel_boost=True)
  for change in [dict(passes=2),dict(passes=8),dict(enhance=False),dict(wide_weak=False),dict(ridge=False),dict(wide_line=True),dict(directional_growth=True),dict(pixel_boost=1)]:
   with self.assertRaises(ValueError):c.configure(90,**(base|change))
  with self.assertRaises(ValueError):c.configure(89,**base)
  c.peer_version=0x12d00
  with self.assertRaises(ValueError):c.configure(90,**base)
  self.assertFalse(c.exchange.called)
 def test_bound_request_freezes_model_mode(self):
  b=EthernetBridge('127.0.0.1');b.passes=4;b.wide_weak=b.ridge=b.pixel_boost=True;b.transport.configure=Mock()
  call=b.bind_request('configure',90);b.pixel_boost=False;b.passes=2;call()
  b.transport.configure.assert_called_once_with(90,enhance=True,passes=4,low_gate=False,wide_weak=True,ridge=True,pixel_boost=True)
 def test_captured_model_mode_and_recipe(self):
  raw,d,m=test_events.packet();base=(90<<8)|(3<<16)|(1<<23)|(1<<24)|(1<<25)|(1<<27)|(1<<28)
  d[7]=base|(3<<29);m[1]=BOOST_VERSION
  f,_,_=Bridge.decode_event(raw,d,m,1);self.assertIn('INT_BOOST256',f['algorithm'])
  actual=recipes.evidence(f,recipes.load(Path(__file__).resolve().parents[1]));self.assertTrue(actual['pixel_boost_enabled']);self.assertEqual(actual['weak_passes'],4);self.assertIn('integer_boost',actual['recipe_id'])
  m[1]=0x12d00
  with self.assertRaises(ValueError):Bridge.decode_event(raw,d,m,1)
 def test_catalog_model_identity(self):
  found=[r for r in recipes.load(Path(__file__).resolve().parents[1]) if r.get('pixel_boost')]
  self.assertEqual(len(found),1);self.assertEqual(found[0]['model_id'],BOOST_MODEL_ID)
 def test_current_socket_checks_exact_model_and_version(self):
  class Peer:
   def __init__(self,version,physical,expected):self.version=version;self.physical=physical;self.expected=expected;self.sent=[];self.buffer=bytearray()
   def settimeout(self,value):pass
   def sendall(self,data):
    self.sent.append(struct.unpack('<4I',data));words=[0]*68;words[:4]=[0x544c5033,1,0,5];words[41:43]=[self.physical,self.expected];words[44:47]=[0x54494c33,self.version,123]
    body=struct.pack('<68I',*words);self.buffer+=body+struct.pack('<I',zlib.crc32(body))
   def recv_into(self,view,count):
    n=min(count,len(self.buffer));view[:n]=self.buffer[:n];del self.buffer[:n];return n
   def close(self):pass
  for version,physical,expected in [(0x12d00,BOOST_MODEL_ID,BOOST_MODEL_ID),(0x12e00,BOOST_MODEL_ID,BOOST_MODEL_ID),(BOOST_VERSION,0,BOOST_MODEL_ID),(BOOST_VERSION,1,1),(BOOST_VERSION,0xd202c7e3,0xd202c7e3),(BOOST_VERSION,BOOST_MODEL_ID,0),(BOOST_VERSION,BOOST_MODEL_ID,BOOST_MODEL_ID)]:
   c=EventTCP('127.0.0.1');c.peer_version=BOOST_VERSION;peer=Peer(version,physical,expected);c.sock=peer
   if version!=BOOST_VERSION or physical!=BOOST_MODEL_ID or expected!=BOOST_MODEL_ID:
    with self.assertRaises(ValueError):c.configure(90,passes=4,wide_weak=True,ridge=True,pixel_boost=True)
    self.assertEqual([r[1] for r in peer.sent],[3])
   else:
    c.configure(90,passes=4,wide_weak=True,ridge=True,pixel_boost=True);self.assertEqual([r[1] for r in peer.sent],[3,5]);self.assertEqual(peer.sent[-1][3],612)

if __name__=='__main__':unittest.main()

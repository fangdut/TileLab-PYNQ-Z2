"""No board I/O: opt-in flags, socket capability, identity and frozen requests."""
import unittest,struct,zlib,json
from pathlib import Path
from unittest.mock import Mock
from tcp_transport import EventTCP,SUPPORT_VERSION
from workstation import EthernetBridge,Bridge
import recipes,test_events

class SupportControlTests(unittest.TestCase):
 def make(self):
  c=EventTCP('127.0.0.1');c.peer_version=SUPPORT_VERSION;c.exchange=Mock(return_value=(b'',[],[]));return c
 def test_wire_flags(self):
  c=self.make()
  for field,passes,flag in [('wide_line',4,128),('directional_growth',8,256)]:
   args=dict(passes=passes,wide_weak=True,ridge=True,**{field:True})
   c.configure(90,**args);self.assertEqual(c.exchange.call_args.args,(5,90,100+flag))
   c.capture(90,**args);self.assertEqual(c.exchange.call_args.args,(1,90,102+flag))
 def test_reject_malformed_and_old_requests_before_exchange(self):
  c=self.make();base=dict(passes=4,wide_weak=True,ridge=True,wide_line=True)
  for change in [dict(directional_growth=True),dict(passes=8),dict(ridge=False),dict(wide_weak=False),dict(wide_line=1),dict(enhance=False)]:
   with self.assertRaises(ValueError):c.configure(90,**(base|change))
  with self.assertRaises(ValueError):c.configure(89,**base)
  with self.assertRaises(ValueError):c.configure(90,passes=8)
  c.peer_version=0x12c00
  with self.assertRaises(ValueError):c.configure(90,**base)
  self.assertFalse(c.exchange.called)
 def test_bound_request_does_not_follow_mutable_ui(self):
  b=EthernetBridge('127.0.0.1');b.passes=8;b.wide_weak=b.ridge=b.directional_growth=True;b.transport.configure=Mock()
  cb=b.bind_request('configure',90);b.directional_growth=False;b.passes=2;cb()
  b.transport.configure.assert_called_once_with(90,enhance=True,passes=8,low_gate=False,wide_weak=True,ridge=True,directional_growth=True)
 def test_actual_captured_mode_controls_recipe(self):
  catalog=recipes.load(Path(__file__).resolve().parents[1]);base=(90<<8)|(3<<16)|(1<<23)|(1<<24)|(1<<25)|(1<<27)|(1<<28)
  for bit,word in [(29,'conservative'),(30,'sensitive')]:
   actual=recipes.evidence(dict(config_word=base|(1<<bit)),catalog)
   self.assertIn(word,actual['recipe_id']);self.assertEqual(actual['weak_passes'],8 if bit==30 else 4)
 def test_decoder_rejects_stale_version_bad_threshold_and_conflicting_bits(self):
  raw,d,m=test_events.packet();base=d[7]|(1<<23)|(1<<24)|(1<<25)|(1<<27)|(1<<28)
  base=(base&~0xff00)|(90<<8)
  for bit,word in [(29,'WIDELINE'),(30,'DIRECTIONAL_HYST8')]:
   d[7]=base|(1<<bit);m[1]=SUPPORT_VERSION
   f,_,_=Bridge.decode_event(raw,d,m,1);self.assertIn(word,f['algorithm'])
   m[1]=0x12c00
   with self.assertRaises(ValueError):Bridge.decode_event(raw,d,m,1)
  m[1]=SUPPORT_VERSION
  for cfg in [base|(3<<29),((base&~0xff00)|(89<<8))|(1<<29),(base&~(1<<23))|(1<<30)]:
   d[7]=cfg
   with self.assertRaises(ValueError):Bridge.decode_event(raw,d,m,1)
 def test_current_socket_is_probed_for_new_version(self):
  class Peer:
   def __init__(self,version):self.version=version;self.sent=[];self.buffer=bytearray()
   def settimeout(self,value):pass
   def sendall(self,data):
    self.sent.append(struct.unpack('<4I',data));words=[0]*68;words[:4]=[0x544c5033,1,0,5];words[44:47]=[0x54494c33,self.version,123]
    body=struct.pack('<68I',*words);self.buffer+=body+struct.pack('<I',zlib.crc32(body))
   def recv_into(self,view,count):
    n=min(count,len(self.buffer));view[:n]=self.buffer[:n];del self.buffer[:n];return n
   def close(self):pass
  for version in [0x12c00,SUPPORT_VERSION]:
   c=EventTCP('127.0.0.1');c.peer_version=SUPPORT_VERSION;peer=Peer(version);c.sock=peer
   if version<SUPPORT_VERSION:
    with self.assertRaisesRegex(ValueError,'current connection'):c.configure(90,passes=8,wide_weak=True,ridge=True,directional_growth=True)
    self.assertEqual([p[1] for p in peer.sent],[3])
   else:
    c.configure(90,passes=8,wide_weak=True,ridge=True,directional_growth=True)
    self.assertEqual([p[1] for p in peer.sent],[3,5]);self.assertEqual(peer.sent[-1][3],356)
if __name__=='__main__':unittest.main()

import unittest,struct,zlib,tempfile
import numpy as np
from packed_pixels import decode
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
import test_tcp_transport as fixtures

class PackedTests(unittest.TestCase):
 def test_lengths_padding_and_identity(self):
  for n in range(65):
   a=np.arange(n*4,dtype=np.uint8).reshape(n,4);a[:,3]&=1
   p=a[:,:3].copy().tobytes()+np.packbits(a[:,3],bitorder='little').tobytes()
   self.assertEqual(decode(p,n*4),a.tobytes())
   for wrong in (p+b'\0',p[:-1] if p else b'\0'):
    with self.assertRaises(ValueError):decode(wrong,n*4)
   if n%8:
    bad=bytearray(p);bad[-1]|=1<<(n%8)
    with self.assertRaisesRegex(ValueError,'padding'):decode(bad,n*4)
 def test_invalid_expected_size(self):
  for n in (-4,1,True,4.0):
   with self.assertRaises(ValueError):decode(b'',n)
 def test_capability_opt_in_requires_validated_new_peer(self):
  c=EventTCP('127.0.0.1');calls=[];c.exchange=lambda *a:(calls.append(a) or (b'',[],[]))
  for version in (0,0x11800,0x11900):
   c.peer_version=version
   for compress in (False,True):
    for packed in (False,True):
     c.compression=compress;c.packed=packed;c.capture(90,passes=4)
     self.assertEqual(calls[-1][2],4|(2 if compress else 0)|(8 if compress and packed and version>=0x11900 else 0))
 def packet(self,version=0x11900,size=None):
  n=FRAME_BYTES//4;a=np.empty((n,4),np.uint8);a[:,:3]=[0x12,0x34,0x56];a[:,3]=np.arange(n)&1
  raw=a.tobytes();payload=a[:,:3].copy().tobytes()+np.packbits(a[:,3],bitorder='little').tobytes()
  m=[0]*24;m[0]=0x54494c33;m[1]=version;m[3]=zlib.crc32(raw)
  h=struct.pack('<68I',MAGIC,0,len(payload) if size is None else size,527,*([0]*40),*m)
  return h+struct.pack('<I',zlib.crc32(h)),payload,raw
 def invoke(self,header,payload,flags=14,error=None):
  c,t=fixtures.TCPTests().server([header,payload])
  try:
   if error:
    with self.assertRaisesRegex(ValueError,error):c.exchange(1,90,flags)
    self.assertIsNone(c.sock);self.assertEqual(c.reconnects,0);self.assertEqual(c.peer_version,0)
   else:return c.exchange(1,90,flags),dict(c.last_timing),c.peer_version
  finally:c.close();t.join(3)
 def test_real_socket_header_pixel_crc_and_full_reconstruction(self):
  h,p,raw=self.packet();(got,d,m),timing,peer=self.invoke(h,p)
  self.assertEqual(got,raw);self.assertEqual(peer,0x11900)
  self.assertEqual(timing['wire_codec'],'BGR24_MASK1');self.assertEqual(timing['wire_payload_bytes'],2880000)
  self.assertEqual(timing['wire_saving_percent'],21.875)
  self.assertTrue(all(timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')))
 def test_unsolicited_or_old_version_packed_rejected(self):
  h,p,_=self.packet()
  for flag in (0,2,4,6,8,12):self.invoke(h,p,flag,error='packed capability')
  h,p,_=self.packet(version=0x11800);self.invoke(h,p,error='packed capability')
 def test_wrong_packed_length_rejected_before_payload(self):
  for n in (0,2879999,2880001,FRAME_BYTES):
   h,p,_=self.packet(size=n);self.invoke(h,b'',error='packed capability')
 def test_color_or_mask_corruption_rejected(self):
  for index in (1111,FRAME_BYTES//4*3+2111):
   h,p,_=self.packet();bad=bytearray(p);bad[index]^=1
   self.invoke(h,bad,error='frame CRC mismatch')
 def test_invalid_packed_setting(self):
  with self.assertRaises(ValueError):EventTCP('127.0.0.1',packed=1)
 def test_default_preserves_latency_policy_and_modes_are_explicit(self):
  from workstation import Station,EthernetBridge
  c=EventTCP('127.0.0.1');self.assertFalse(c.packed)
  with tempfile.TemporaryDirectory() as root:
   b=EthernetBridge('127.0.0.1');s=Station(root,b)
   try:
    self.assertEqual(s.state()['wire_mode'],'rle')
    for mode in ('packed','raw','rle'):
     s.action(dict(op='wire_mode',value=mode));self.assertEqual(s.state()['wire_mode'],mode)
    for invalid in ('zip',None,True):
     with self.assertRaises(ValueError):s.action(dict(op='wire_mode',value=invalid))
    s.action(dict(op='wire_mode',value='packed'));s.action(dict(op='compression',enabled=True))
    self.assertEqual(s.state()['wire_mode'],'rle')
   finally:s.exit=True;s.worker.join(2);s.records.db.close();b.close()
 def test_capture_uses_one_compression_snapshot(self):
  class Changing(EventTCP):
   def __getattribute__(self,name):
    if name=='compression' and object.__getattribute__(self,'__dict__').get('armed'):
     self.reads+=1;return self.reads==1
    return super().__getattribute__(name)
  c=Changing('127.0.0.1',packed=True);c.peer_version=0x11900;c.reads=0;c.armed=True;calls=[]
  c.exchange=lambda *a:(calls.append(a) or (b'',[],[]));c.capture(90,passes=4)
  self.assertEqual(calls,[(1,90,14)]);self.assertEqual(c.reads,1)

if __name__=='__main__':unittest.main(verbosity=2)

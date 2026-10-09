import struct,unittest,zlib
import test_tcp_transport as fixtures
from tcp_transport import MAGIC,FRAME_BYTES

class FrameCRC(unittest.TestCase):
 def packet(self,raw,codec=0,version=0x10b00,flags=None,crc=None,code=0):
  m=[0]*24;m[0]=0x54494c33;m[1]=version;m[3]=zlib.crc32(raw) if crc is None else crc
  payload=struct.pack('<2I',0x80000000|FRAME_BYTES//4,struct.unpack('<I',raw[:4])[0]) if codec else raw
  flags=(3|(codec<<8)) if flags is None else flags
  return [struct.pack('<68I',MAGIC,code,len(payload) if not code else 0,flags,*([0]*40),*m),payload if not code else b'']
 def run_packet(self,response,valid=True,op=1):
  c,t=fixtures.TCPTests().server(response)
  try:
   if valid:return c.capture(89),dict(c.last_timing)
   with self.assertRaises(ValueError):c.exchange(op,89)
   self.assertIsNone(c.sock);self.assertEqual(c.requests_sent,1);self.assertEqual(c.reconnects,0)
  finally:c.close();t.join(3)
 def test_raw_and_rle_crc_match_after_decode(self):
  raw=struct.pack('<I',0x013579bd)*(FRAME_BYTES//4)
  for codec in (0,1):
   packet,timing=self.run_packet(self.packet(raw,codec));self.assertEqual(packet[0],raw);self.assertTrue(timing['pixel_crc_verified']);self.assertEqual(timing['pixel_crc32'],zlib.crc32(raw))
 def test_rgb_byte_corruption_stops_without_retry(self):
  raw=b'\x12\x34\x56\x00'*(FRAME_BYTES//4);p=self.packet(raw);bad=bytearray(p[1]);bad[11000]^=1;p[1]=bad;self.run_packet(p,False)
 def test_corrupt_rle_color_value_stops(self):
  raw=b'\x12\x34\x56\x00'*(FRAME_BYTES//4);p=self.packet(raw,1);b=bytearray(p[1]);b[5]^=1;p[1]=b;self.run_packet(p,False)
 def test_crc_header_corruption_stops(self):
  raw=bytes(FRAME_BYTES);self.run_packet(self.packet(raw,crc=zlib.crc32(raw)^1),False)
 def test_new_firmware_cannot_omit_crc(self):
  self.run_packet(self.packet(bytes(FRAME_BYTES),flags=1),False)
 def test_old_firmware_cannot_claim_crc(self):
  self.run_packet(self.packet(bytes(FRAME_BYTES),version=0x10a00),False)
 def test_status_crc_flag_rejected(self):
  self.run_packet(self.packet(bytes(FRAME_BYTES),code=1),False,3)
 def test_legacy_raw_accepted_but_not_claimed_verified(self):
  _,t=self.run_packet(self.packet(bytes(FRAME_BYTES),version=0x10a00,flags=1));self.assertFalse(t['pixel_crc_verified']);self.assertIsNone(t['pixel_crc32'])

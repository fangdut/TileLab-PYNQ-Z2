import unittest,struct,zlib
import test_tcp_transport as fixtures
from tcp_transport import MAGIC,FRAME_BYTES

class HeaderCRC(unittest.TestCase):
 def response(self,codec=0,status=False,version=0x10c00,header_crc=True):
  raw=b'\x12\x34\x56\x00'*(FRAME_BYTES//4)
  body=b'' if status else struct.pack('<2I',0x80000000|FRAME_BYTES//4,0x00563412) if codec else raw
  flags=1|(4 if header_crc else 0)|(0 if status else (2|(codec<<8)))
  d=[0]*40;m=[0]*24;m[0]=0x54494c33;m[1]=version;m[3]=12345 if status else zlib.crc32(raw)
  h=struct.pack('<68I',MAGIC,int(status),len(body),flags,*d,*m)
  return h+(struct.pack('<I',zlib.crc32(h)) if header_crc else b''),body,raw
 def invoke(self,response,op=1,error=None):
  c,t=fixtures.TCPTests().server(response)
  try:
   if error:
    with self.assertRaisesRegex(ValueError,error):c.exchange(op,89,2 if op==1 else 0)
    self.assertEqual(c.requests_sent,1);self.assertEqual(c.reconnects,0);self.assertIsNone(c.sock)
   else:return c.exchange(op,89,2 if op==1 else 0),dict(c.last_timing),c.total_received_bytes
  finally:c.close();t.join(3)
 def test_raw_and_rle_complete_header_and_pixel_checks(self):
  for codec in (0,1):
   h,b,raw=self.response(codec);p,t,n=self.invoke([h,b])
   self.assertEqual(p[0],raw);self.assertTrue(t['header_crc_verified']);self.assertTrue(t['pixel_crc_verified'])
   self.assertEqual(n,276+len(b))
 def test_all_status_response_operations_preserve_heartbeat(self):
  for op in (2,3,4,5):
   h,b,_=self.response(status=True);p,t,n=self.invoke([h,b],op)
   self.assertEqual(p[2][3],12345);self.assertTrue(t['header_crc_verified']);self.assertFalse(t['pixel_crc_verified']);self.assertEqual(n,276)
 def test_frame_product_boxes_and_pixel_crc_tampering_rejected(self):
  for word in (6,41,14,47):
   h,b,_=self.response();bad=bytearray(h);bad[word*4]^=1
   self.invoke([bad,b],error='Header CRC mismatch')
 def test_status_or_confirmation_tampering_rejected(self):
  for word in (46,48,50,47): # boot, head, depth, heartbeat
   h,b,_=self.response(status=True);bad=bytearray(h);bad[word*4]^=1
   self.invoke([bad,b],op=3,error='Header CRC mismatch')
 def test_checksum_word_itself_tampering_rejected(self):
  h,b,_=self.response();bad=bytearray(h);bad[-1]^=1
  self.invoke([bad,b],error='Header CRC mismatch')
 def test_new_version_cannot_omit_header_crc(self):
  h,b,_=self.response(header_crc=False);self.invoke([h,b],error='Header CRC/version mismatch')
 def test_old_version_cannot_claim_header_crc(self):
  h,b,_=self.response(version=0x10b00);self.invoke([h,b],error='Header CRC/version mismatch')
 def test_v111_compatibility_is_explicit(self):
  h,b,_=self.response(version=0x10b00,header_crc=False);_,t,_=self.invoke([h,b])
  self.assertTrue(t['pixel_crc_verified']);self.assertFalse(t['header_crc_verified'])
 def test_truncated_header_crc_is_a_connection_failure(self):
  h,b,_=self.response();c,t=fixtures.TCPTests().server([h[:-2]])
  try:
   with self.assertRaises(OSError):c.capture(89)
   self.assertEqual(c.reconnects,1);self.assertIsNone(c.sock)
  finally:c.close();t.join(3)

import unittest,struct,zlib
import test_header_crc as headers
import test_tcp_transport as fixtures
from tcp_transport import MAGIC

class DescriptorProtocolTests(unittest.TestCase):
 def packet(self,codec=0,version=0x10e00,verified=True,status=False):
  h,b,raw=headers.HeaderCRC().response(codec=codec,status=status,version=version)
  words=list(struct.unpack('<68I',h[:272]));words[3]|=8 if verified else 0
  h=struct.pack('<68I',*words);return [h+struct.pack('<I',zlib.crc32(h)),b],raw
 def run_packet(self,response,error=None):
  c,t=fixtures.TCPTests().server(response)
  try:
   if error:
    with self.assertRaisesRegex(ValueError,error):c.capture(89)
    self.assertEqual(c.requests_sent,1);self.assertIsNone(c.sock)
   else:
    raw,*_=c.capture(89);return raw,dict(c.last_timing)
  finally:c.close();t.join(3)
 def test_new_raw_and_rle_require_all_three_proofs(self):
  for codec in (0,1):
   response,expected=self.packet(codec);raw,timing=self.run_packet(response)
   self.assertEqual(raw,expected)
   self.assertTrue(all(timing[k] for k in ('pixel_crc_verified','header_crc_verified','descriptor_crc_verified')))
 def test_new_version_cannot_omit_descriptor_proof(self):
  response,_=self.packet(verified=False);self.run_packet(response,'descriptor CRC/version mismatch')
 def test_old_version_cannot_claim_descriptor_proof(self):
  response,_=self.packet(version=0x10d00);self.run_packet(response,'descriptor CRC/version mismatch')
 def test_old_version_without_descriptor_proof_is_explicit(self):
  response,_=self.packet(version=0x10d00,verified=False);_,timing=self.run_packet(response)
  self.assertFalse(timing['descriptor_crc_verified']);self.assertTrue(timing['header_crc_verified'])
 def test_status_cannot_advertise_a_verified_frame(self):
  response,_=self.packet(status=True);c,t=fixtures.TCPTests().server(response)
  try:
   with self.assertRaises(ValueError):c.stats()
  finally:c.close();t.join(3)
 def test_descriptor_error_counters_are_version_gated(self):
  for version in (0x10d00,0x10e00):
   d=[0]*40;m=[0]*24;d[13:16]=[2,345,0x12345678];m[0]=0x54494c33;m[1]=version
   h=struct.pack('<68I',MAGIC,1,0,5,*d,*m);c,t=fixtures.TCPTests().server([h+struct.pack('<I',zlib.crc32(h))])
   try:
    state=c.stats()
    if version>=0x10e00:self.assertEqual([state[k] for k in ('descriptor_crc_errors','descriptor_verified_frames','last_descriptor_crc32')],[2,345,0x12345678])
    else:self.assertNotIn('descriptor_crc_errors',state)
   finally:c.close();t.join(3)

if __name__=='__main__':unittest.main(verbosity=2)

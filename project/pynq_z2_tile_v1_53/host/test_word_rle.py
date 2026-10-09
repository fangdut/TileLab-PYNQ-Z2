import struct,unittest
from word_rle import decode
from tcp_transport import EventTCP,MAGIC,FRAME_BYTES
import test_tcp_transport as tcp_tests
import word_rle,numpy as np

class RLETests(unittest.TestCase):
 def test_native_decoder_fuzz_matches_python_and_preserves_bounds(self):
  native=word_rle._native
  if native is None:self.skipTest('Optional native decoder unavailable')
  rng=np.random.default_rng(1707)
  for _ in range(2000):
   data=rng.integers(0,130,int(rng.integers(1,32)),dtype=np.uint32)
   data[rng.random(len(data))>.5]|=np.uint32(0x80000000)
   out=np.full(34,0xabcdef01,np.uint32)
   status=native(data.ctypes.data,len(data),out.ctypes.data,32)
   self.assertTrue(np.all(out[32:]==0xabcdef01))
   word_rle._native=None
   try:
    try:expected=decode(data.tobytes(),128)
    except ValueError:self.assertNotEqual(status,0)
    else:self.assertEqual(status,0);self.assertEqual(out[:32].tobytes(),expected)
   finally:word_rle._native=native
 def test_no_native_library_still_decodes_losslessly(self):
  native=word_rle._native;word_rle._native=None
  try:self.assertEqual(decode(struct.pack('<2I',0x8000000a,123),40),struct.pack('<10I',*([123]*10)))
  finally:word_rle._native=native
 def test_mixed_runs_and_literals(self):
  b=struct.pack('<9I',3,11,12,13,0x80000004,90,0x80000003,50,0)
  self.assertEqual(decode(b[:-4],40),struct.pack('<10I',11,12,13,*([90]*4),*([50]*3)))
 def test_reject_invalid_streams(self):
  for b in [b'\x01',struct.pack('<I',0),struct.pack('<I',0x80000001),struct.pack('<2I',0x8000000b,1),struct.pack('<2I',3,1),struct.pack('<2I',0x80000009,1),struct.pack('<3I',0x8000000a,1,0)]:
   with self.assertRaises(ValueError):decode(b,40)
 def test_compressed_protocol(self):
  h=struct.pack('<68I',MAGIC,0,8,257,*([0]*64));p=struct.pack('<2I',0x80000000|FRAME_BYTES//4,0x01030201)
  c,t=tcp_tests.TCPTests().server([h,p]);raw,*_=c.capture(89);c.close();t.join()
  self.assertEqual(raw,struct.pack('<I',0x01030201)*(FRAME_BYTES//4));self.assertEqual(c.last_timing['wire_payload_bytes'],8)
  self.assertEqual(c.last_timing['wire_codec'],'WORD_RLE')
 def test_unrequested_or_unknown_codec(self):
  for flags,compression in [(257,False),(513,True),(3,True)]:
   h=struct.pack('<68I',MAGIC,0,8,flags,*([0]*64));c,t=tcp_tests.TCPTests().server([h,b'12345678']);c.compression=compression
   with self.assertRaises(ValueError):c.capture(89)
   self.assertIsNone(c.sock);t.join()
 def test_reject_compressed_status(self):
  h=struct.pack('<68I',MAGIC,1,0,257,*([0]*64));c,t=tcp_tests.TCPTests().server([h])
  with self.assertRaises(ValueError):c.stats()
  c.close();t.join()

if __name__=='__main__':unittest.main()

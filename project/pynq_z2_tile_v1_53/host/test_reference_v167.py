"""V167 binary boundaries; mock sockets do not count as hardware evidence."""
import io,struct,unittest,zlib,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import reference_frame_tcp as metric
from reference_capture import Capture
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/reference_tile'))
import fixtures,frame_v167,registration_v167,photometric_v167
class Peer:
    def __init__(self,kind='metric',change=None):self.kind=kind;self.change=change;self.buffer=b'';self.cursor=0
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def setsockopt(self,*a):pass
    def settimeout(self,*a):pass
    def sendall(self,data):
        if self.kind=='metric':
            w=struct.unpack('<16I',data[:64]);body=bytes(1000000);r=[metric.MAGIC,0,w[2],len(body),zlib.crc32(body),1000,0,500,500,0x16700601,0x16700,w[4],w[13],w[14],1000000,0]
            if self.change:self.change(r,body)
            raw=struct.pack('<15I',*r[:15]);self.buffer=raw+struct.pack('<I',zlib.crc32(raw))+body
        else:
            raw=bytes(3686400);d=[0]*40;m=[0]*24;d[0]=1;d[2]=7;d[6]=4;d[7]=0x00f35a07;d[8]=3;d[34]=123;d[35]=len(raw);m[:3]=[0x54494c33,0x16700,123];m[3]=zlib.crc32(raw)
            h=struct.pack('<68I',0x544c5033,0,len(raw),15,*d,*m);self.buffer=h+struct.pack('<I',zlib.crc32(h))+raw
        self.cursor=0
    def recv_into(self,view):
        n=min(len(view),4093,len(self.buffer)-self.cursor);view[:n]=self.buffer[self.cursor:self.cursor+n];self.cursor+=n;return n
class Tests(unittest.TestCase):
    def test_mask_completion_requires_an_already_accepted_alarm(self):
        proof=dict(output_crc_verified=True,paired_sha256='test',pl_id=0x16700601,firmware=0x16700,test_double=True)
        for seeded in (False,True):
            words=np.zeros((500,500),np.uint32);words[20,20:61]=12
            if seeded:words[20,20:41]=25|256|512
            r,m=frame_v167.finish(dict(status='PREPARED',paired_sha256='test',alarm=None),words,proof)
            self.assertEqual(r['alarm'],seeded)
            self.assertEqual(int(m.sum()),21 if seeded else 0)
            self.assertFalse(r['completion']['can_create_new_image_alarm'])
        words=np.zeros((500,500),np.uint32);words[20,20:61]=20;words[20,20:41]=25|256|512
        r,m=frame_v167.finish(dict(status='PREPARED',paired_sha256='test',alarm=None),words,proof)
        self.assertTrue(r['alarm']);self.assertEqual(int(m.sum()),41)
    def test_one_directional_print_uses_both_physical_boundary_axes(self):
        reference=fixtures.frame('stripes');current=fixtures.capture(reference,dx=.75,dy=-.5,noise=.6,jpeg=96)
        r,pair,_,_=frame_v167.prepare(reference,current)
        self.assertEqual(r['status'],'PREPARED');self.assertLess(abs(r['registration']['dx']-.75),.125);self.assertLess(abs(r['registration']['dy']+.5),.125)
        words=frame_v167.oracle(pair,r['photometric']);r,m=frame_v167.finish(r,words,dict(output_crc_verified=True,paired_sha256=r['paired_sha256'],pl_id=0x16700601,firmware=0x16700,test_double=True));self.assertFalse(r['alarm'])
    def test_matching_fixture_does_not_accept_wrong_pattern(self):
        result,_,_,_=frame_v167.prepare(fixtures.frame('floral'),fixtures.frame('geometry'))
        self.assertEqual(result['status'],'REJECTED_INPUT');self.assertIsNone(result['alarm'])
    def test_sparse_print_colors_do_not_fit_noise_in_dominant_flat(self):
        reference=np.full((500,500,3),[190,150,115],np.uint8);reference[25:50,25:250]=[65,100,190];reference[100:120,100:220]=[110,210,50]
        gain=np.array([.98,1.02,.97]);offset=np.array([2,-2,3]);current=np.clip(np.rint(reference*gain+offset),0,255).astype(np.uint8)
        fit,error=photometric_v167.fit(reference,current,frame_v167.policy());self.assertIsNone(error)
        normalized=np.clip(((current.astype(np.int32)*np.array(fit['gain_q8'])+128)>>8)+np.array(fit['offset_integer']),0,255)
        difference=np.abs(reference.astype(np.int32)-normalized)
        self.assertLessEqual(int(difference.max()),8);self.assertLessEqual(float(np.median(difference)),1);self.assertTrue(np.all(np.abs(fit['offsets'])<6))
    def test_full_metric_reconstruction_and_fingerprint(self):
        pair=np.zeros((500,500),dtype='<u8');fit=dict(gain_q8=[256]*3,offset_integer=[0]*3)
        with patch('reference_frame_tcp.socket.create_connection',return_value=Peer()):
            words,proof=metric.inspect('127.0.0.1',pair,fit)
        self.assertEqual(words.shape,(500,500));self.assertFalse(words.any());self.assertTrue(proof['output_crc_verified']);self.assertEqual(proof['engine_seconds'],.001)
    def test_wrong_identity_or_size_rejected_before_payload(self):
        for index,value in [(0,0),(2,0),(3,0xffffffff),(7,499),(9,0xd06b3b9b),(10,0x13200),(11,0),(12,1)]:
            pair=np.zeros((500,500),dtype='<u8');peer=Peer(change=lambda r,b:r.__setitem__(index,value))
            with self.subTest(index=index),patch('reference_frame_tcp.socket.create_connection',return_value=peer),self.assertRaises(ValueError):metric.inspect('127.0.0.1',pair,dict(gain_q8=[256]*3,offset_integer=[0]*3))
            self.assertEqual(peer.cursor,64)
    def test_score_corruption_rejected(self):
        peer=Peer(change=lambda r,b:r.__setitem__(4,0))
        with patch('reference_frame_tcp.socket.create_connection',return_value=peer),self.assertRaisesRegex(ValueError,'score CRC'):metric.inspect('127.0.0.1',np.zeros((500,500),'<u8'),dict(gain_q8=[256]*3,offset_integer=[0]*3))
    def test_capture_decodes_actual_png_and_clears_legacy_algorithm_label(self):
        with patch('reference_capture.socket.create_connection',return_value=Peer('capture')):frame,image,mask=Capture('127.0.0.1').request(7,0x16700601)
        self.assertEqual(frame['algorithm'],'RAW_HDMI_CAPTURE_ONLY');self.assertTrue(frame['pixel_crc_verified']);self.assertEqual(frame['boot_id'],123)
        for encoded in (image,mask):
            with Image.open(io.BytesIO(encoded)) as im:self.assertEqual(im.size,(1280,720))
        self.assertFalse(frame['alarm'])
if __name__=='__main__':unittest.main()

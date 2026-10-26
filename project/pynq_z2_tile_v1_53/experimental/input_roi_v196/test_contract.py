"""Communication guards for ROI calibration; no fake accuracy/board claim."""
from pathlib import Path
import sys,unittest,tempfile,json,hashlib,struct,zlib
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/fpga_texture_v170'))
from board_client import Board
ROI=dict(x=3,y=4,width=20,height=22,source_width=32,source_height=32)
class FakeBoard(Board):
    def __init__(self,ack=True,outside=False):self.calls=0;self.ack=ack;self.outside=outside
    def request(self,op,payload=b'',**kw):
        self.calls+=1;w=kw['width'];h=kw['height'];wire=np.zeros(16+28*28+w*h,dtype='<u4')
        wire[:10]=[0x17000001,0,1,2,1,28,1,w*h,47,1]
        if self.ack:wire[10:16]=[ROI[k] for k in ['x','y','width','height','source_width','source_height']]
        wire[16+28*28+(0 if self.outside else ROI['y']*w+ROI['x'])]=1
        reply=[0]*16;reply[4]=zlib.crc32(wire.tobytes());reply[5]=0x17000001;reply[6]=123;reply[8]=7;reply[9]=325;reply[11]=325000000;reply[12]=zlib.crc32(payload);reply[13]=w;reply[14]=h
        return reply,wire.tobytes(),.01
class Contract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.image=self.root/'source.png';Image.new('RGB',(32,32),'gray').save(self.image)
        self.model=dict(grid=28,steps=47,crc32=123,sha256='test-only',input_roi=dict(ROI))
    def tearDown(self):self.temp.cleanup()
    def test_source_size_rejected_before_transmission(self):
        self.model['input_roi']['source_width']=31;b=FakeBoard()
        with self.assertRaisesRegex(ValueError,'dimensions differ'):b.infer(self.image,self.root/'out',self.model)
        self.assertEqual(b.calls,0)
    def test_old_pl_without_roi_ack_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'acknowledge'):FakeBoard(ack=False).infer(self.image,self.root/'out',self.model)
        self.assertFalse((self.root/'out').exists())
    def test_outside_roi_mask_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'escaped'):FakeBoard(outside=True).infer(self.image,self.root/'out',self.model)
        self.assertFalse((self.root/'out').exists())
    def test_valid_ack_preserves_region_evidence(self):
        e=FakeBoard().infer(self.image,self.root/'out',self.model);self.assertEqual(e['pl_input_roi'],ROI)
    def profile(self,metadata):
        blob=bytearray(256);struct.pack_into('<7I',blob,80,*[ROI[k] for k in ['x','y','width','height','source_width','source_height']],0x19600001)
        (self.root/'model.bin').write_bytes(blob);(self.root/'graph.json').write_text(json.dumps(dict(sha256=hashlib.sha256(blob).hexdigest(),**metadata)),encoding='utf8')
    def test_binary_roi_cannot_be_omitted_from_metadata(self):
        self.profile({});b=FakeBoard()
        with self.assertRaisesRegex(RuntimeError,'metadata mismatch'):b.upload(self.root)
        self.assertEqual(b.calls,0)
    def test_metadata_cannot_change_sealed_geometry(self):
        changed=dict(ROI,x=5);self.profile(dict(input_roi=changed));b=FakeBoard()
        with self.assertRaisesRegex(RuntimeError,'metadata mismatch'):b.upload(self.root)
        self.assertEqual(b.calls,0)
if __name__=='__main__':unittest.main()

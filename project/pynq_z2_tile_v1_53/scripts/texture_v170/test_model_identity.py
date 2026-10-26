from pathlib import Path
import tempfile,unittest,json,hashlib,struct,zlib
from model_identity import load_identity,require_hardware_support
class Identity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.blob=bytearray(256)
        struct.pack_into('<5I',self.blob,0,0x17000001,256,47,224,28);struct.pack_into('<I',self.blob,64,32)
        self.graph=dict(sha256=hashlib.sha256(self.blob).hexdigest(),crc32=zlib.crc32(self.blob),model_bytes=256,grid=28,steps=47,workspace_bytes=32)
        self.save()
    def tearDown(self):self.temp.cleanup()
    def save(self):
        (self.root/'model.bin').write_bytes(self.blob);(self.root/'graph.json').write_text(json.dumps(self.graph),encoding='utf8')
    def test_header_tracks_new_actual_model_crc(self):
        _,first=load_identity(self.root);self.blob[200]=1;self.graph.update(sha256=hashlib.sha256(self.blob).hexdigest(),crc32=zlib.crc32(self.blob));self.save()
        _,second=load_identity(self.root);self.assertNotEqual(first,second);self.assertIn(str(zlib.crc32(self.blob))+'u',second)
    def test_stale_crc_rejected_even_with_correct_sha(self):
        self.graph['crc32']^=1;self.save()
        with self.assertRaisesRegex(ValueError,'crc32'):load_identity(self.root)
    def test_size_metadata_rejected(self):
        self.graph['model_bytes']+=8;self.save()
        with self.assertRaisesRegex(ValueError,'model_bytes'):load_identity(self.root)
    def test_grid_metadata_rejected(self):
        self.graph['grid']=14;self.save()
        with self.assertRaisesRegex(ValueError,'grid'):load_identity(self.root)
    def test_corrupt_data_rejected(self):
        self.blob[200]=1;self.save()
        with self.assertRaisesRegex(ValueError,'sha256'):load_identity(self.root)
    def hardware(self,source):
        (self.root/'texture_integer_source.cpp').write_bytes(source)
        (self.root/'candidate_preflight.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source).hexdigest())),encoding='utf8')
    def test_legacy_hardware_cannot_accept_roi_profile(self):
        self.hardware(b'legacy arithmetic fixture')
        with self.assertRaisesRegex(ValueError,'ROI-capable'):require_hardware_support(self.root,dict(input_roi={'x':3}))
    def test_implemented_source_cannot_be_changed(self):
        self.hardware(b'original');(self.root/'texture_integer_source.cpp').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'preflight'):require_hardware_support(self.root,{})
    def test_model_roi_header_cannot_be_unacknowledged(self):
        struct.pack_into('<I',self.blob,104,0x19600001);self.graph.update(sha256=hashlib.sha256(self.blob).hexdigest(),crc32=zlib.crc32(self.blob));self.save()
        with self.assertRaisesRegex(ValueError,'ROI header'):load_identity(self.root)
if __name__=='__main__':unittest.main()

from pathlib import Path
import hashlib,json,tempfile,unittest
from check_mean_candidate import verify
class ManifestTests(unittest.TestCase):
    def fixture(self,d):
        root=Path(d);names=['rtl/directional_mean_valley.v','rtl/mean_dual_scale_valley.v','rtl/video_bypass.v',
            'reports/v154/download/system.bit','reports/v154/download/system.xsa',
            'reports/v154/download/hdmi_ethernet/build/hdmi_ethernet.elf','reports/v154/download/ps7_init.tcl']
        files={}
        for name in names:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(name.encode());files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        data=dict(status='research_candidate',firmware_version=0x12c00,files=files)
        (root/'CANDIDATE_MANIFEST.json').write_text(json.dumps(data));return root,data
    def test_detects_changed_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root,data=self.fixture(d);verify(root)
            (root/'reports/v154/download/system.bit').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify(root)
    def test_rejects_escaped_paths_and_missing_critical_files(self):
        with tempfile.TemporaryDirectory() as d:
            root,data=self.fixture(d);data['files']['../outside']='0'*64
            (root/'CANDIDATE_MANIFEST.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'Unsafe'):verify(root)
            del data['files']['../outside'];del data['files']['reports/v154/download/system.xsa']
            (root/'CANDIDATE_MANIFEST.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'omits required'):verify(root)
if __name__=='__main__':unittest.main()

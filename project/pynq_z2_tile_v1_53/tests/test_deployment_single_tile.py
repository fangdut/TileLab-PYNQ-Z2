from pathlib import Path
import json,sys,tempfile,unittest,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from deployment_single_tile import verify,sha,load

class DeploymentTests(unittest.TestCase):
    def bundle(self,path):
        p=load(ROOT);(path/'system.bit').write_bytes(b'unit-test-bitstream-not-programmable')
        with zipfile.ZipFile(path/'system.xsa','w') as z:z.writestr('system.bit',(path/'system.bit').read_bytes())
        (path/'hdmi_ethernet.elf').write_bytes(b'unit-test-elf-not-programmable');(path/'ps7_init.tcl').write_text('# unit test only')
        (path/'implementation_status.txt').write_text('setup_slack_ns=0.1\nhold_slack_ns=0.1\ndrc_errors=0\n')
        m=dict(release='V1.64',profile_sha256=p['profile_sha256'],firmware_version=0x13200,model_id=p['model_id'],source_sha256={},files={q.name:sha(q) for q in path.iterdir()})
        (path/'DEPLOYMENT.json').write_text(json.dumps(m));return m
    def test_byte_tampering_blocks_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.bundle(path);verify(path);(path/'system.bit').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify(path)
    def test_individually_hashed_but_mismatched_xsa_bit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);m=self.bundle(path)
            with zipfile.ZipFile(path/'system.xsa','w') as z:z.writestr('system.bit',b'other-build')
            m['files']['system.xsa']=sha(path/'system.xsa');(path/'DEPLOYMENT.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):verify(path)
    def test_negative_timing_is_rejected_even_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);m=self.bundle(path);(path/'implementation_status.txt').write_text('setup_slack_ns=-0.1\nhold_slack_ns=0.1\ndrc_errors=0\n');m['files']['implementation_status.txt']=sha(path/'implementation_status.txt');(path/'DEPLOYMENT.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):verify(path)

if __name__=='__main__':unittest.main()

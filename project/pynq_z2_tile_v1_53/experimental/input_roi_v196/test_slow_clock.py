"""Metadata consistency only; does not pretend to configure or measure a board."""
from pathlib import Path
import sys,json,copy,tempfile,unittest,argparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/texture_v170'))
from verify_clock import verify
REL=Path('texture_v170.srcs/sources_1/bd/system/system.bd')
class Clock(unittest.TestCase):
    baseline=None
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.data=json.loads((self.baseline/REL).read_text(encoding='utf8'));d=self.data['design'];ps=d['components']['ps7']['parameters']
        for key,value in [('PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ','50.000000'),('PCW_FPGA0_PERIPHERAL_FREQMHZ','50.000000'),('PCW_CLK0_FREQ','50000000')]:ps[key]['value']=value
        for cell,port in [('pipeline','control_clk'),('video_regs','clk')]:
            c=d['components'][cell];c['ports'][port]['parameters']['FREQ_HZ']['value']='50000000'
            for bus in c['interface_ports'].values():bus['parameters']['FREQ_HZ']={'value':'50000000'}
        d['components']['hpd_startup']['parameters']['STARTUP_CYCLES']['value']='10000000'
    def tearDown(self):self.temp.cleanup()
    def check(self):
        file=self.root/REL;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(self.data),encoding='utf8');return verify(self.root,True)
    def test_consistent_50_metadata(self):self.assertEqual(self.check()['pl_clock_mhz'],50)
    def test_actual_frequency_not_relabelled(self):
        self.data['design']['components']['ps7']['parameters']['PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ']['value']='100.000000'
        with self.assertRaises(ValueError):self.check()
    def test_clock_hz_must_agree(self):
        self.data['design']['components']['ps7']['parameters']['PCW_CLK0_FREQ']['value']='100000000'
        with self.assertRaises(ValueError):self.check()
    def test_axi_clock_must_agree(self):
        self.data['design']['components']['pipeline']['interface_ports']['m_axi_result']['parameters']['FREQ_HZ']['value']='100000000'
        with self.assertRaises(ValueError):self.check()
    def test_hpd_duration_must_be_scaled(self):
        self.data['design']['components']['hpd_startup']['parameters']['STARTUP_CYCLES']['value']='20000000'
        with self.assertRaises(ValueError):self.check()
    def test_hdmi_reference_must_remain_200(self):
        self.data['design']['components']['ps7']['parameters']['PCW_ACT_FPGA1_PERIPHERAL_FREQMHZ']['value']='100.000000'
        with self.assertRaises(ValueError):self.check()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,required=True);a,rest=parser.parse_known_args();Clock.baseline=a.baseline;unittest.main(argv=[sys.argv[0],*rest])

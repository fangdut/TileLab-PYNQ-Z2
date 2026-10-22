"""Exercise real saved BDs and reject the observed clock/HPD mismatch classes."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'scripts/texture_v170'))
from verify_clock import verify
REL=Path('texture_v170.srcs/sources_1/bd/system/system.bd')
def main():
    p=argparse.ArgumentParser()
    for n in ['candidate','baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    original=json.loads((a.candidate/REL).read_text());results=[]
    verify(a.baseline);verify(a.candidate,True)
    results+=['accepted100MHz_physical_metadata','candidate125MHz_BD_only']
    def reject(name,edit):
        data=copy.deepcopy(original);edit(data['design'])
        folder=a.out/name;file=folder/REL;file.parent.mkdir(parents=True);file.write_text(json.dumps(data))
        try:verify(folder,True)
        except ValueError:results.append(name);return
        raise AssertionError('Invalid configuration accepted: '+name)
    def wrong_module(d):d['components']['pipeline']['ports']['control_clk']['parameters']['FREQ_HZ']['value']='100000000'
    def wrong_axi(d):d['components']['pipeline']['interface_ports']['m_axi_result']['parameters']['FREQ_HZ']['value']='100000000'
    def wrong_hpd(d):d['components']['hpd_startup']['parameters']['STARTUP_CYCLES']['value']='20000000'
    def wrong_realized(d):d['components']['ps7']['parameters']['PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ']['value']='100.000000'
    def wrong_net(d):
        for net in d['nets'].values():
            if 'video_regs/clk' in net.get('ports',[]):net['ports'].remove('video_regs/clk')
        d['nets']['injected_wrong_clock']={'ports':['video_regs/clk','ps7/FCLK_CLK1']}
    for name,edit in [('legacy_fixed_module_clock_rejected',wrong_module),('legacy_fixed_AXI_clock_rejected',wrong_axi),
                      ('unscaled_HPD_delay_rejected',wrong_hpd),('requested_unrealized_clock_rejected',wrong_realized),
                      ('mismatched_clock_net_rejected',wrong_net)]:reject(name,edit)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    j=dict(scope='SAVED_CLOCK_CONFIGURATION_TESTS_NOT_PHYSICAL_FREQUENCY_OR_FPS',passed=True,checks=results,
        verifier_sha256=sha(P/'scripts/texture_v170/verify_clock.py'),test_sha256=sha(Path(__file__)),
        candidate_bd_sha256=sha(a.candidate/REL),baseline_bd_sha256=sha(a.baseline/REL))
    (a.out/'summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if __name__=='__main__':main()

from pathlib import Path
import json,re,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def resources(revision):
 s=(O/f'capture_{revision}_utilization.rpt').read_text()
 return {k:int(re.search(r'\|\s*'+re.escape(k)+r'\*?\s*\|\s*(\d+)',s).group(1)) for k in ['Slice LUTs','Slice Registers','Block RAM Tile','DSPs']}
a=resources('v114');b=resources('v115')
assert b['Slice LUTs']<a['Slice LUTs'],'No measured LUT reduction; do not proceed as a resource optimization'
assert b['Slice Registers']<a['Slice Registers']
assert b['Block RAM Tile']==a['Block RAM Tile'] and b['DSPs']==a['DSPs']
log=(O/'equivalence_sim/equivalence_test.sim/sim_1/behav/xsim/simulate.log').read_text()
assert 'PASS continuous SG' in log and 'Fatal:' not in log
cycles=int(re.search(r'EQUIVALENT_CYCLES=(\d+)',log).group(1));assert cycles>400000
old=O/'equivalence_sim/equivalence_test.sim/sim_1/behav/xsim/crc_packets.hex'
crc=json.loads((O/'crc_sim_summary.json').read_text());assert crc['passed']
assert sha(old)==crc['packets_sha256'],'Independent CRC checker did not validate the equivalence run packets'
r=dict(passed=True,baseline=a,optimized=b,lut_saved=a['Slice LUTs']-b['Slice LUTs'],ff_saved=a['Slice Registers']-b['Slice Registers'],lut_reduction_percent=100*(a['Slice LUTs']-b['Slice LUTs'])/a['Slice LUTs'],equivalent_cycles=cycles,baseline_rtl_sha256=json.loads((R/'ITERATION_PLAN.json').read_text())['baseline_rtl_sha256'],optimized_rtl_sha256=sha(R/'rtl/frame_capture_sg.v'),packet_sha256=sha(old),scope='Same Vivado OOC synthesis settings for both RTL versions; exact observable cycle comparison for seven frames/reset/pixel-drop/trailer-backpressure; not a formal proof or full implementation')
(O/'capture_optimization.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))

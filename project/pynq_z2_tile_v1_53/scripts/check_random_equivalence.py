from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'reports/v132'
p=O/'random_equivalence_sim/random_equiv.sim/sim_1/behav/xsim/simulate.log';s=p.read_text()
assert 'Fatal:' not in s and 'PASS randomized' in s
line=re.search(r'RANDOM_EQ (.*)',s).group(1)
c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
assert c['cycles']>1500000 and all(c[k]>=2 for k in ('pixel_resets','crc_resets','trailer_resets'))
r=dict(passed=True,seed='0xcafe1547',coverage=c,scope='Bounded RTL simulation of observable cycle equivalence against manifest-verified V1.14, not formal proof, real CDC metastability or DMA recovery from physical HDMI loss',optimized_rtl_sha256=hashlib.sha256((R/'rtl/frame_capture_sg.v').read_bytes()).hexdigest())
(O/'random_equivalence.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))

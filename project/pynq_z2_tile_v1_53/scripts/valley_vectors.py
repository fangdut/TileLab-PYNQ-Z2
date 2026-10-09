from pathlib import Path
import sys,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models'))
from valley_reference import valley
root=Path(__file__).resolve().parents[1]
rng=np.random.default_rng(923);y=rng.integers(0,256,(36,48),dtype=np.uint8)
y[4:30,23:25]=10;y[4:30,5:18]=150
score=valley(y).astype(np.uint8)
for name,a in [('gray',y),('score',score)]:
 (root/'sim'/('valley_'+name+'.mem')).write_text('\n'.join(f'{int(v):02x}' for v in a.ravel()))

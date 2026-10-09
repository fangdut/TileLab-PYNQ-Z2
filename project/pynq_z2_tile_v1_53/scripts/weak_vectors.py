from pathlib import Path
import sys,numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'models'))
from weak_reference import grow
W,H,N=48,36,6;rng=np.random.default_rng(160926);inputs=[];expected=[]
for k in range(N):
 weak=rng.random((H,W))<(.25 if k<3 else .65);strong=weak&(rng.random((H,W))<.18)
 if k==0:weak[:]=False;strong[:]=False;weak[18,8:40]=True;strong[17:20,10:12]=True;weak|=strong
 if k==1:strong[:]=False # no seed must never invent defects
 if k==2:weak[:]=False;strong[:]=False;weak[16:22,20:28]=True;strong[18,23]=True # isolated seed is retained, not expanded
 for a in (weak,strong):a[[0,-1],:]=0;a[:,[0,-1]]=0
 mask=strong
 for _ in range(2):
  mask=grow(mask,weak,3);mask[[0,-1],:]=0;mask[:,[0,-1]]=0
 inputs.extend((strong.astype('uint8')+2*weak).ravel());expected.extend(mask.ravel().astype('uint8'))
for name,values in [('weak_input.mem',inputs),('weak_expected.mem',expected)]:
 (R/'sim'/name).write_text('\n'.join(f'{v:x}' for v in values)+'\n')
print(f'{W*H*N} pixel vectors; random neighborhoods, no seeds, isolated seed, bounded paths')

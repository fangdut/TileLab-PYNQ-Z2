"""Frozen V1.56 offline oracle. Live detection runs exclusively in PL."""
import numpy as np
from weak_reference import grow
from ridge_reference import shifted
HIGH_Q16=65536
GATE_Q16=-393216
MIN_SUPPORT=5
def mask_from_scores(n,w,s,l,score,keep):
    if score.dtype!=np.int32:raise ValueError('Expected signed integer Q16 scores')
    s=s.max(axis=0) if s.ndim==3 else s;l=l.max(axis=0) if l.ndim==3 else l
    base=((n>90)|(s>40)|(l>48))&keep;weak=((n>45)|(w>45)|(s>20)|(l>24))&keep
    for _ in range(4):base=grow(base,weak,3);base[[0,-1],:]=False;base[:,[0,-1]]=False
    valid=np.ones(keep.shape,bool);valid[:16]=False;valid[-16:]=False;valid[:,:16]=False;valid[:,-16:]=False
    raw=(score>=HIGH_Q16)&keep&valid
    support=sum(shifted(raw.astype(np.uint8),dx,dy) for dy in [-1,0,1] for dx in [-1,0,1])
    return ((base&(score>=GATE_Q16)&valid)|(raw&(support>=MIN_SUPPORT)))&keep
